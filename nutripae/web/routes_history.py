"""Historial por niño y resumen por sede."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from nutripae import auth, db, foods, history, messages
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
        d["kcal"] = round(d["ultima"]["nutrientes"].get("kcal", 0))
    history.auditar(con, usuario["id"], "consulta_historial", estudiante_id)
    faltas = [{"label": foods.GRUPO_LABEL.get(g, g), "color": foods.GRUPO_COLOR.get(g, "#9A96B3"), "dias": n}
              for g, n in sorted(history.faltas_por_grupo(con, estudiante_id, ini, fin).items(),
                                 key=lambda x: -x[1])]
    return request.app.state.templates.TemplateResponse(
        request, "historial.html",
        {"estudiante": est, "dias": dias, "faltas": faltas, "desde": ini.isoformat(), "hasta": fin.isoformat()})


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
