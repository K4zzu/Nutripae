"""Pantalla de verificación y API de análisis."""
from __future__ import annotations

import base64
import io
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
from pydantic import BaseModel

from nutripae import auth, db, foods, messages, verificaciones
from nutripae.analyze import Analizador, Ocupado, PersonaDetectada
from nutripae.balance import UMBRALES_INICIALES, Veredicto
from nutripae.overlay import COLOR_NO_APTO, reducir
from nutripae.segment import SegmentadorElipses
from nutripae.vision import VisionDemo

log = logging.getLogger("nutripae")
router = APIRouter()

ROLES_VERIFICAR = ("docente", "nutricionista", "admin")
GRADOS = ("preescolar", "primaria", "secundaria")


def _error(status: int, error: str, mensaje: str) -> JSONResponse:
    return JSONResponse({"error": error, "mensaje": mensaje}, status_code=status)


def _data_url(imagen: Image.Image) -> str:
    b = io.BytesIO()
    reducir(imagen, 1024).save(b, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def _primer_nombre(estudiante) -> str | None:
    if estudiante is None or not estudiante["nombre"]:
        return None
    return estudiante["nombre"].split()[0]


def _color(p) -> str:
    if p.estado == "no_apto":
        return COLOR_NO_APTO
    return foods.GRUPO_COLOR.get(p.grupo, foods.GRUPO_COLOR["otro"])


def _respuesta(vid: int, v: Veredicto, titulo: str, detalle: str, estudiante,
               foto_url: str | None, tarjeta_invalida: bool) -> dict:
    return {
        "id": vid, "semaforo": v.semaforo, "titulo": titulo, "detalle": detalle,
        "nombre": _primer_nombre(estudiante),
        "porciones": [{
            "indice": i, "nombre": p.nombre, "grupo": p.grupo,
            "grupo_label": foods.GRUPO_LABEL.get(p.grupo, p.grupo), "gramos": round(p.gramos),
            "estado": p.estado, "poligono": p.poligono, "bbox": list(p.bbox),
            "aproximado": p.aproximado, "color": _color(p),
        } for i, p in enumerate(v.porciones)],
        "nutrientes": v.nutrientes, "total_g": round(v.total_g), "foto_url": foto_url,
        "estudiante": None if estudiante is None else
        {"id": estudiante["id"], "nombre": estudiante["nombre"], "grado": estudiante["grado"]},
        "tarjeta_invalida": tarjeta_invalida,
    }


def _sede_permitida(request: Request, sede: str | None) -> bool:
    """Cada usuario solo ve sus sedes; el administrador ve todas."""
    return "admin" in request.state.roles or (sede is not None and sede in request.state.sedes)


def _umbrales(con):
    return lambda: db.param(con, "umbrales", UMBRALES_INICIALES)


@router.get("/verificar")
def pagina(request: Request, usuario=Depends(auth.usuario_actual)):
    return request.app.state.templates.TemplateResponse(
        request, "verificar.html", {"usuario": usuario, "grados": GRADOS})


@router.post("/api/verificar")
def api_verificar(request: Request, usuario=Depends(auth.requiere(*ROLES_VERIFICAR)),
                  foto: UploadFile = File(...), tarjeta: str = Form(""), estudiante_id: str = Form(""),
                  grado: str = Form("primaria"), modo: str = Form("camara"),
                  escenario: str = Form("completa")):
    app = request.app
    con = app.state.con

    if modo == "demo":
        try:
            analizador = Analizador(VisionDemo(escenario), SegmentadorElipses(), _umbrales(con),
                                  catalogo=lambda: foods.catalogo(con))
        except ValueError:
            return _error(400, "escenario", "Esa situación de práctica no existe.")
    elif modo == "camara":
        analizador = app.state.analizador
        if analizador is None:
            return _error(503, "sin_ia", "El análisis con cámara no está disponible en este equipo.")
    else:
        return _error(400, "modo", "Modo no válido.")

    estudiante, tarjeta_invalida = None, False
    if tarjeta.strip():
        estudiante = db.estudiante_por_tarjeta(con, tarjeta.strip())
        if estudiante is not None and not _sede_permitida(request, estudiante["sede"]):
            estudiante = None  # tarjeta de otra sede: se analiza sin atribuir
        tarjeta_invalida = estudiante is None
    elif estudiante_id.strip():
        estudiante = db.estudiante(con, int(estudiante_id)) if estudiante_id.strip().isdigit() else None
        if estudiante is None or not estudiante["activo"] or not _sede_permitida(request, estudiante["sede"]):
            return _error(404, "estudiante", "Estudiante no encontrado.")

    grado_final = estudiante["grado"] if estudiante is not None and estudiante["grado"] in GRADOS else grado
    if grado_final not in GRADOS:
        return _error(400, "grado", "Grado no válido.")
    sedes = sorted(request.state.sedes)
    sede = estudiante["sede"] if estudiante is not None and estudiante["sede"] else (sedes[0] if sedes else "")

    try:
        imagen = Image.open(foto.file)
        imagen.load()
        imagen = imagen.convert("RGB")
    except Exception:
        if modo != "demo":
            return _error(400, "foto", "No se pudo leer la foto. Intenta de nuevo.")
        imagen = Image.new("RGB", (640, 480), "gray")

    try:
        analisis = analizador.analizar(imagen, grado_final, _primer_nombre(estudiante))
    except PersonaDetectada:
        return _error(422, "persona", "Repite la foto: solo la bandeja.")
    except Ocupado:
        return _error(503, "ocupado", "Un momento…")
    except Exception:
        log.exception("Falló el análisis de la bandeja")
        return _error(502, "analisis", "No se pudo leer la bandeja. Intenta de nuevo.")

    vid = verificaciones.guardar(con, app.state.settings, analisis, estudiante=estudiante, sede=sede,
                                 grado=grado_final, usuario_id=request.state.usuario["id"], modo=modo)
    ruta = con.execute("SELECT foto FROM verificaciones WHERE id=?", (vid,)).fetchone()["foto"]
    foto_url = f"/fotos/{ruta}" if ruta else _data_url(analisis.foto_anotada)
    return _respuesta(vid, analisis.veredicto, analisis.titulo, analisis.detalle, estudiante,
                      foto_url, tarjeta_invalida)


class Correccion(BaseModel):
    indice: int
    alimento: str


@router.post("/api/verificaciones/{vid}/corregir")
def api_corregir(vid: int, cuerpo: Correccion, request: Request,
                 usuario=Depends(auth.requiere(*ROLES_VERIFICAR))):
    con = request.app.state.con
    fila = con.execute("SELECT sede FROM verificaciones WHERE id=?", (vid,)).fetchone()
    if fila is None or not _sede_permitida(request, fila["sede"]):
        return _error(404, "no_encontrada", "No encontramos esa verificación.")
    try:
        v = verificaciones.corregir(con, vid, cuerpo.indice, cuerpo.alimento, usuario["id"])
    except verificaciones.CorreccionInvalida as e:
        return _error(400, "correccion", str(e))
    fila = con.execute("SELECT * FROM verificaciones WHERE id=?", (vid,)).fetchone()
    estudiante = db.estudiante(con, fila["estudiante_id"]) if fila["estudiante_id"] else None
    titulo, detalle = messages.mensaje(v, _primer_nombre(estudiante), grado=fila["grado"])
    foto_url = f"/fotos/{fila['foto']}" if fila["foto"] else None
    return _respuesta(vid, v, titulo, detalle, estudiante, foto_url, False)


@router.get("/api/alimentos")
def api_alimentos(request: Request, usuario=Depends(auth.requiere(*ROLES_VERIFICAR))) -> list[dict]:
    lista = [{"clave": k, "nombre": n, "grupo": g} for k, (n, g) in foods.catalogo(request.app.state.con).items()]
    return sorted(lista, key=lambda a: a["nombre"])


@router.get("/fotos/{ruta:path}")
def fotos(ruta: str, request: Request, usuario=Depends(auth.usuario_actual)):
    con = request.app.state.con
    fila = con.execute("SELECT sede FROM verificaciones WHERE foto=?", (ruta,)).fetchone() or con.execute(
        "SELECT v.sede FROM fotos_entrenamiento f JOIN verificaciones v ON v.id=f.verificacion_id "
        "WHERE f.ruta=?", (ruta,)).fetchone()
    if fila is None or not _sede_permitida(request, fila["sede"]):
        raise HTTPException(status_code=404)
    base = request.app.state.settings.fotos_dir.resolve()
    destino = (base / ruta).resolve()
    if not destino.is_relative_to(base) or not destino.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(destino, media_type="image/jpeg")
