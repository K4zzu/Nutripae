"""Historial por niño y resumen por sede."""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from urllib.parse import quote

from nutripae import auth, db, foods, history, messages, reports
from nutripae.web.routes_verify import GRADOS, ROLES_VERIFICAR, _sede_permitida

router = APIRouter()

ETIQUETA = {"verde": ("✓", "Plato completo"), "amarillo": ("!", "Casi completo"),
            "rojo": ("✕", "Faltó algo"), "no_apto": ("—", "No apto")}


def _sedes_visibles(request: Request) -> list[str]:
    if "admin" in request.state.roles:
        return [r[0] for r in request.app.state.con.execute(
            "SELECT DISTINCT sede FROM estudiantes WHERE activo=1 AND sede IS NOT NULL ORDER BY sede")]
    return sorted(request.state.sedes)


def _grupos(porciones: list[dict]) -> tuple[list[dict], list[dict]]:
    """(presentes, faltantes) como chips con nombre y color de grupo."""
    def chip(g):
        return {"grupo": g, "label": foods.GRUPO_LABEL.get(g, g), "color": foods.GRUPO_COLOR.get(g, foods.GRUPO_COLOR["otro"])}
    faltan = [p["grupo"] for p in porciones if p.get("estado") == "falta" and p.get("grupo")]
    hay = [p["grupo"] for p in porciones if p.get("estado") != "falta" and p.get("grupo")]
    presentes = list(dict.fromkeys(g for g in hay if g not in faltan))
    return [chip(g) for g in presentes], [chip(g) for g in dict.fromkeys(faltan)]


def _alimentos(porciones: list[dict]) -> list[dict]:
    """Lo servido ese día como «nombre · gramos g», con el color de su grupo (los faltantes ya se listan aparte)."""
    return [{"nombre": p.get("nombre") or p.get("alimento", ""), "gramos": round(p.get("gramos") or 0),
             "no_apto": p.get("estado") == "no_apto",
             "color": foods.GRUPO_COLOR.get(p.get("grupo"), foods.GRUPO_COLOR["otro"])}
            for p in porciones if p.get("estado") != "falta"]


@router.get("/estudiantes/{estudiante_id}/historial")
def historial(estudiante_id: int, request: Request, desde: str = "", hasta: str = "",
              usuario=Depends(auth.requiere(*ROLES_VERIFICAR))):
    con = request.app.state.con
    est = db.estudiante(con, estudiante_id)
    if est is None or not _sede_permitida(request, est["sede"]):
        raise HTTPException(status_code=404)
    ini, fin = history.periodo(desde, hasta)
    dias = history.dias_estudiante(con, estudiante_id, ini, fin)
    for d in dias:
        d["etiqueta"] = ETIQUETA.get(d["ultima"]["semaforo"], ("!", d["ultima"]["semaforo"]))
        d["presentes"], d["faltantes"] = _grupos(d["ultima"]["porciones"])
        d["alimentos"] = _alimentos(d["ultima"]["porciones"])
        d["kcal"] = round(d["ultima"]["nutrientes"].get("kcal", 0))
    history.auditar(con, usuario["id"], "consulta_historial", estudiante_id)
    faltas = [{"label": foods.GRUPO_LABEL.get(g, g), "color": foods.GRUPO_COLOR.get(g, "#9A96B3"), "dias": n}
              for g, n in sorted(history.faltas_por_grupo(con, estudiante_id, ini, fin).items(),
                                 key=lambda x: -x[1])]
    return request.app.state.templates.TemplateResponse(
        request, "historial.html",
        {"estudiante": est, "dias": dias, "faltas": faltas, "desde": ini.isoformat(), "hasta": fin.isoformat()})


def _ascii(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9-]+", "_", plano).strip("_") or "x"


@router.get("/estudiantes/{estudiante_id}/historial.pdf")
def historial_pdf(estudiante_id: int, request: Request, desde: str = "", hasta: str = "",
                  usuario=Depends(auth.requiere(*ROLES_VERIFICAR))):
    con = request.app.state.con
    est = db.estudiante(con, estudiante_id)
    if est is None or not _sede_permitida(request, est["sede"]):
        raise HTTPException(status_code=404)
    ini, fin = history.periodo(desde, hasta)
    datos = reports.pdf_historial(con, request.app.state.settings, estudiante_id, ini, fin)
    history.auditar(con, usuario["id"], "pdf_historial", estudiante_id)
    partes = est["nombre"].split()
    nombre = f"historial_{_ascii(partes[-1] if partes else est['nombre'])}_{ini.isoformat()}_{fin.isoformat()}.pdf"
    return Response(datos, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.get("/informes")
def informes(request: Request, usuario=Depends(auth.requiere("nutricionista", "admin"))):
    """Entrada a los informes: el resumen de la primera sede visible, o una explicación si no hay estudiantes."""
    sedes = _sedes_visibles(request)
    if sedes:
        return RedirectResponse(f"/sedes/{quote(sedes[0])}/resumen", status_code=302)
    return request.app.state.templates.TemplateResponse(
        request, "informes_vacio.html", {"es_admin": "admin" in request.state.roles})


@router.get("/sedes/{sede}/resumen")
def resumen(sede: str, request: Request, grado: str = "", desde: str = "", hasta: str = "",
            usuario=Depends(auth.requiere("nutricionista", "admin"))):
    if not _sede_permitida(request, sede):
        raise HTTPException(status_code=404)
    con = request.app.state.con
    grado = grado if grado in GRADOS else ""
    ini, fin = history.periodo(desde, hasta)
    r = history.resumen_sede(con, sede, grado or None, ini, fin)
    mas = r["grupo_mas_falta"]
    return request.app.state.templates.TemplateResponse(
        request, "resumen_sede.html",
        {"sede": sede, "sedes": _sedes_visibles(request), "grados": GRADOS, "grado": grado,
         "desde": ini.isoformat(), "hasta": fin.isoformat(), "por_dia": r["por_dia"],
         "no_aptos": r["no_aptos"],
         "mas_falta": None if mas is None else
         {"label": foods.GRUPO_LABEL.get(mas, mas), "color": foods.GRUPO_COLOR.get(mas, "#9A96B3"),
          "razon": messages.RAZON.get(mas, "")}})
