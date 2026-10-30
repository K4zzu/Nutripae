"""Estudiantes: administración (carga, consentimiento, baja) y API de búsqueda."""
from __future__ import annotations

import re
from datetime import date
from itertools import groupby

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response

from nutripae import auth, cards, db, students
from nutripae.web.routes_verify import ROLES_VERIFICAR

router = APIRouter()


def _vista(request: Request, mensaje: str | None = None, error: str | None = None, status: int = 200):
    con = request.app.state.con
    filas = con.execute(
        "SELECT e.*, (SELECT t.codigo FROM tarjetas t WHERE t.estudiante_id=e.id AND t.activa=1 "
        "ORDER BY t.creada DESC, t.rowid DESC LIMIT 1) AS codigo_tarjeta "
        "FROM estudiantes e WHERE e.activo=1 ORDER BY e.sede, e.grado, e.grupo, e.orden, e.id").fetchall()
    sedes = [(sede, [(grupo, list(est)) for grupo, est in
                     groupby(lista, key=lambda e: (e["grado"], e["grupo"]))])
             for sede, lista in groupby(filas, key=lambda e: e["sede"])]
    q = request.query_params
    if mensaje is None and "creados" in q:
        mensaje = (f"Listo: {q.get('creados', '0')} nuevos, {q.get('actualizados', '0')} actualizados, "
                   f"{q.get('errores', '0')} filas con problemas.")
    return request.app.state.templates.TemplateResponse(
        request, "admin_estudiantes.html",
        {"sedes": sedes, "mensaje": mensaje, "error": error},
        status_code=status)


@router.get("/admin/estudiantes")
def lista(request: Request, usuario=Depends(auth.requiere("admin"))):
    return _vista(request)


@router.post("/admin/estudiantes/cargar")
def cargar(request: Request, archivo: UploadFile = File(...), usuario=Depends(auth.requiere("admin"))):
    app = request.app
    try:
        r = students.importar_excel(app.state.con, archivo.file.read(), secret=app.state.settings.secret)
    except students.ColumnaFaltante as e:
        return _vista(request, error=str(e), status=400)
    except Exception:
        return _vista(request, error="No se pudo leer el archivo. Sube un Excel (.xlsx).", status=400)
    return RedirectResponse(
        f"/admin/estudiantes?creados={r['creados']}&actualizados={r['actualizados']}&errores={len(r['errores'])}",
        status_code=303)


@router.post("/admin/estudiantes/{estudiante_id}/consentimiento")
def consentimiento(estudiante_id: int, request: Request, valor: str = Form("0"),
                   usuario=Depends(auth.requiere("admin"))):
    students.set_consentimiento(request.app.state.con, estudiante_id, valor == "1")
    return RedirectResponse("/admin/estudiantes", status_code=303)


@router.post("/admin/estudiantes/{estudiante_id}/baja")
def baja(estudiante_id: int, request: Request, usuario=Depends(auth.requiere("admin"))):
    students.dar_de_baja(request.app.state.con, estudiante_id)
    return RedirectResponse("/admin/estudiantes", status_code=303)


def _ascii(texto: str) -> str:
    import unicodedata
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9-]+", "_", plano).strip("_") or "x"


@router.get("/admin/tarjetas.pdf")
def tarjetas_pdf(request: Request, sede: str, grado: str, grupo: str,
                 usuario=Depends(auth.requiere("admin"))):
    datos = cards.pdf_curso(request.app.state.con, sede, grado, grupo)
    nombre = f"tarjetas_{_ascii(sede)}_{_ascii(grado)}_{_ascii(grupo)}.pdf"
    return Response(datos, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.post("/admin/tarjetas/{codigo}/anular")
def tarjeta_anular(codigo: str, request: Request, usuario=Depends(auth.requiere("admin"))):
    cards.anular_tarjeta(request.app.state.con, codigo)
    return RedirectResponse("/admin/estudiantes", status_code=303)


def _sedes(request: Request) -> list[str]:
    if "admin" in request.state.roles:
        return [r[0] for r in request.app.state.con.execute(
            "SELECT DISTINCT sede FROM estudiantes WHERE activo=1 AND sede IS NOT NULL ORDER BY sede")]
    return sorted(request.state.sedes)


def _publico(e) -> dict:
    return {k: e[k] for k in ("id", "nombre", "grado", "grupo", "sede")}


@router.get("/api/estudiantes/buscar")
def api_buscar(request: Request, q: str = "", grado: str = "", usuario=Depends(auth.requiere(*ROLES_VERIFICAR))):
    con = request.app.state.con
    salida = []
    for sede in _sedes(request):
        salida += students.buscar(con, q, sede, grado or None)
    return [_publico(e) for e in salida[:students.MAX_RESULTADOS]]


@router.get("/api/tarjetas/{codigo}")
def api_tarjeta(codigo: str, request: Request, usuario=Depends(auth.requiere(*ROLES_VERIFICAR))):
    """Estudiante de una tarjeta leída en vivo, para mostrar su nombre antes de la toma."""
    e = db.estudiante_por_tarjeta(request.app.state.con, codigo.strip())
    if e is None or e["sede"] not in _sedes(request):
        return JSONResponse({"error": "tarjeta", "mensaje": "Tarjeta no reconocida."}, status_code=404)
    return _publico(e)


@router.get("/api/estudiantes/cursos")
def api_cursos(request: Request, usuario=Depends(auth.requiere(*ROLES_VERIFICAR))):
    return students.cursos(request.app.state.con, _sedes(request))


@router.get("/api/estudiantes/lista")
def api_lista(request: Request, sede: str, grupo: str, usuario=Depends(auth.requiere(*ROLES_VERIFICAR))):
    if sede not in _sedes(request):
        return JSONResponse({"error": "sede", "mensaje": "Sede no permitida."}, status_code=403)
    return students.lista_curso(request.app.state.con, sede, grupo, date.today())


@router.get("/api/estudiantes/siguiente")
def api_siguiente(request: Request, grado: str, grupo: str = "",
                  usuario=Depends(auth.requiere(*ROLES_VERIFICAR))):
    con = request.app.state.con
    for sede in _sedes(request):
        e = students.siguiente(con, sede, grado, grupo or None, date.today())
        if e is not None:
            return _publico(e)
    return JSONResponse(None)
