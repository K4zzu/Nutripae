"""Componentes visuales del sistema de diseño NutriPAE (Claude Design · v1).

Cada función devuelve HTML en una sola línea para `st.html`. Los colores y la
tipografía salen de los tokens de abajo; los estados (ok, bajo, falta, no apto)
siempre se muestran con color + ícono, nunca solo con color.
"""
from __future__ import annotations

import base64
from datetime import datetime
from html import escape

# ---------------------------------------------------------------- tokens

INK, INK2, MUTED = "#1D2622", "#4A554F", "#8A8577"
LINE, LINE2 = "#E3DDD1", "#EFEAE0"
BG, SURF = "#F6F2EA", "#FFFDF9"
G700, G600, G100, G_DARK = "#145236", "#1F7A4D", "#E3F0E7", "#143B2A"
CAM = "#1A201D"
SOBRA = "#F2B53A"
MONO = "'Atkinson Hyperlegible Mono',ui-monospace,monospace"

# estado -> color fuerte (c), texto sobre c (fg), tinte (t), tinta sobre tinte (ink), ícono, etiqueta
S = {
    "ok":      dict(c="#1F7A4D", fg="#fff",    t="#E3F0E7", ink="#145236", glyph="✓", l="Completa"),
    "alto":    dict(c="#1F7A4D", fg="#fff",    t="#E3F0E7", ink="#145236", glyph="+", l="Sobre la meta"),
    "bajo":    dict(c="#E8A317", fg="#2B1D00", t="#FBEFD3", ink="#6E4600", glyph="!", l="Porción baja"),
    "falta":   dict(c="#B8322A", fg="#fff",    t="#F7DEDB", ink="#8E231C", glyph="✕", l="Falta grupo"),
    "no_apto": dict(c="#7A2348", fg="#fff",    t="#F3DCE6", ink="#5E1A37", glyph="—", l="No apto"),
}

# veredicto del semáforo
V = {
    "verde":    dict(bg="#1F7A4D", fg="#fff",    icon_bg="#fff",    icon_fg="#1F7A4D", glyph="✓", color="Verde",
                     titulo="Ración completa", line_bg="rgba(255,255,255,.16)"),
    "amarillo": dict(bg="#E8A317", fg="#2B1D00", icon_bg="#2B1D00", icon_fg="#E8A317", glyph="!", color="Amarillo",
                     titulo="Completar porción", line_bg="rgba(255,255,255,.45)"),
    "rojo":     dict(bg="#B8322A", fg="#fff",    icon_bg="#fff",    icon_fg="#B8322A", glyph="✕", color="Rojo",
                     titulo="Ración rechazada", line_bg="rgba(255,255,255,.16)"),
}

# ---------------------------------------------------------------- estilos globales

CSS = f"""<style>
@keyframes npScan{{0%{{top:6%}}50%{{top:90%}}100%{{top:6%}}}}
@keyframes npSpin{{to{{transform:rotate(360deg)}}}}
@keyframes npPulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
.block-container{{padding-top:3.6rem;padding-bottom:3rem;max-width:1440px}}
header[data-testid="stHeader"]{{background:transparent}}
.np{{font-family:'Atkinson Hyperlegible Next',system-ui,sans-serif;color:{INK}}}
.np-mono{{font-family:{MONO}}}
.np-card{{background:{SURF};border:1px solid {LINE};border-radius:16px;padding:16px}}
.np-h{{font-size:16px;font-weight:800}}
.np-sub{{font-size:12px;color:{INK2}}}
/* pestañas */
.stTabs [role="tablist"]{{gap:4px;padding:4px;background:{LINE2};border-radius:12px;width:fit-content;max-width:100%;overflow-x:auto;border:none}}
.stTabs [data-testid="stTab"]{{height:40px;padding:0 16px;border-radius:9px;color:{INK2};border:none}}
.stTabs [data-testid="stTab"] p{{font-size:15px;font-weight:700}}
.stTabs [data-testid="stTab"][aria-selected="true"]{{background:{SURF};color:{G700};box-shadow:0 1px 2px rgba(0,0,0,.06)}}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"],.stTabs [data-testid="stTabHighlight"]{{display:none}}
/* botones de kiosco (objetivo táctil 88 px) */
.st-key-registrar button,.st-key-analizar button,.st-key-listo button,.st-key-analizar_dev button{{min-height:88px;border-radius:18px;border:none;background:{G700};color:#fff;font-size:28px;font-weight:800}}
.st-key-registrar button:hover,.st-key-analizar button:hover,.st-key-listo button:hover,.st-key-analizar_dev button:hover{{background:#0E3D28;color:#fff}}
.st-key-registrar button:active,.st-key-analizar button:active,.st-key-listo button:active,.st-key-analizar_dev button:active{{background:#0E3D28;transform:scale(.97)}}
.st-key-registrar button:disabled{{background:{LINE};color:{MUTED}}}
.st-key-reanalizar button{{min-height:88px;border-radius:18px;border:3px solid {INK};background:{SURF};color:{INK};font-size:21px;font-weight:800;line-height:1.1}}
.st-key-reanalizar button:hover{{border-color:{INK};color:{INK};background:#EDE7DB}}
.st-key-registrar button p,.st-key-analizar button p,.st-key-listo button p,.st-key-analizar_dev button p{{font-size:clamp(22px,2vw,28px) !important;font-weight:800 !important;line-height:1.1}}
.st-key-registrar button p,.st-key-analizar button p,.st-key-listo button p,.st-key-analizar_dev button p,.st-key-reanalizar button p{{white-space:normal !important;overflow:visible !important}}
.st-key-reanalizar button p{{font-size:clamp(17px,1.5vw,21px) !important;font-weight:800 !important;line-height:1.15}}
/* panel de cámara: botón en español */
[data-testid="stCameraInputButton"]{{font-size:0 !important}}
[data-testid="stCameraInputButton"] *{{display:none}}
[data-testid="stCameraInputButton"]::after{{content:"Tomar foto";font-size:17px;font-weight:700}}
[data-testid="stCameraInput"]:has(img) [data-testid="stCameraInputButton"]::after{{content:"Tomar otra foto"}}
/* panel de cámara */
.st-key-camara,.st-key-camara_dev{{background:{CAM};border-radius:20px;padding:14px}}
.st-key-camara label p,.st-key-camara_dev label p{{color:#A9B5AF}}
.st-key-camara [data-testid="stFileUploaderDropzone"],.st-key-camara_dev [data-testid="stFileUploaderDropzone"]{{background:#2B3430;color:#E3F0E7}}
/* barra de controles */
.st-key-controles,.st-key-controles_dev,.st-key-filtros{{background:{SURF};border:1px solid {LINE};border-radius:14px;padding:10px 14px}}
</style>"""


# ---------------------------------------------------------------- utilidades

def hora(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    h = dt.hour % 12 or 12
    return f"{h}:{dt.minute:02d} {'a. m.' if dt.hour < 12 else 'p. m.'}"


def num(v: float, dec: int = 0) -> str:
    """Formato colombiano: 28.412 · 87,4."""
    s = f"{v:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def _e(s) -> str:
    return escape(str(s))


def logo(size: int = 40, tray: str = G600, handle: str = G700, check: str = "#fff") -> str:
    """Isotipo: bandeja con asas y check. Va como <img> porque st.html elimina los <svg> en línea."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">'
           f'<rect x="1" y="19" width="5" height="10" rx="2.5" fill="{handle}"/>'
           f'<rect x="42" y="19" width="5" height="10" rx="2.5" fill="{handle}"/>'
           f'<rect x="4" y="9" width="40" height="30" rx="8" fill="{tray}"/>'
           f'<path d="M15 24.5l6 6 12-13" fill="none" stroke="{check}" stroke-width="4.5" '
           f'stroke-linecap="round" stroke-linejoin="round"/></svg>')
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return f'<img src="{uri}" width="{size}" height="{size}" alt="" style="flex:none;display:block">'


def glyph(estado: str, size: int = 34, font: int = 20) -> str:
    s = S[estado]
    return (f'<span style="width:{size}px;height:{size}px;flex:none;border-radius:50%;background:{s["c"]};color:{s["fg"]};'
            f'display:flex;align-items:center;justify-content:center;font-size:{font}px;font-weight:800">{s["glyph"]}</span>')


def pill(estado: str, texto: str | None = None) -> str:
    s = S[estado]
    return (f'<span style="display:inline-flex;align-items:center;gap:6px;padding:3px 9px 3px 4px;border-radius:999px;'
            f'background:{s["t"]};color:{s["ink"]};font-size:12px;font-weight:700;white-space:nowrap">'
            f'<span style="width:16px;height:16px;border-radius:50%;background:{s["c"]};color:{s["fg"]};font-size:10px;'
            f'display:flex;align-items:center;justify-content:center">{s["glyph"]}</span>{_e(texto or s["l"])}</span>')


def leyenda(color: str, texto: str, borde: str | None = None) -> str:
    fondo = borde or f"background:{color}"
    return (f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:{INK2}">'
            f'<span style="width:12px;height:12px;border-radius:3px;{fondo}"></span>{_e(texto)}</span>')


# ---------------------------------------------------------------- encabezados

def header(estacion: str, derecha: str = "", progreso: tuple[int, int] | None = None) -> str:
    prog = ""
    if progreso:
        n, meta = progreso
        pct = min(100, round(100 * n / meta)) if meta else 0
        prog = (f'<div style="display:flex;flex-direction:column;gap:4px;min-width:170px;padding-left:16px;border-left:1px solid {LINE}">'
                f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:12px">'
                f'<span style="font-size:14px;color:{INK2}">Raciones del turno</span>'
                f'<span style="font-size:22px;font-weight:800">{n} <span style="font-size:16px;font-weight:500;color:{INK2}">/ {meta}</span></span></div>'
                f'<div style="height:8px;border-radius:4px;background:{LINE};overflow:hidden">'
                f'<div style="height:100%;width:{pct}%;background:{G600}"></div></div></div>')
    return (f'<div class="np" style="display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;padding:12px 20px;'
            f'background:{SURF};border:1px solid {LINE};border-radius:16px">'
            f'<div style="display:flex;align-items:center;gap:10px">{logo(40)}'
            f'<span style="font-size:24px;font-weight:800;letter-spacing:-0.01em">NutriPAE</span></div>'
            f'<div style="width:1px;height:32px;background:{LINE}"></div>'
            f'<span style="font-size:20px;font-weight:600;color:{INK2}">{_e(estacion)}</span>'
            f'<span style="font-size:18px;color:{INK2};margin-left:auto">{derecha}</span>{prog}'
            f'<span class="np-mono" style="font-size:18px;font-weight:600;padding-left:16px;border-left:1px solid {LINE};white-space:nowrap">{hora()}</span></div>')


def titulo_pagina(eyebrow: str, titulo: str, nota: str = "") -> str:
    return (f'<div class="np" style="display:flex;flex-wrap:wrap;align-items:flex-end;gap:12px 24px;margin:4px 0 8px">'
            f'<div style="display:flex;flex-direction:column;gap:4px"><span style="font-size:13px;color:{INK2}">{_e(eyebrow)}</span>'
            f'<span style="font-size:28px;font-weight:800;letter-spacing:-0.01em">{_e(titulo)}</span></div>'
            f'<span style="margin-left:auto;font-size:14px;color:{INK2};max-width:420px">{_e(nota)}</span></div>')


# ---------------------------------------------------------------- estación de entrega

def info_card(label: str, valor: str, sub: str = "", mono: bool = False, grande: int = 30) -> str:
    fam = f"font-family:{MONO};font-weight:600" if mono else "font-weight:800"
    return (f'<div class="np np-card" style="height:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:6px;justify-content:space-between">'
            f'<span style="font-size:15px;color:{INK2}">{_e(label)}</span>'
            f'<span style="font-size:clamp({min(grande, 20)}px,{grande / 19:.2f}vw,{grande}px);{fam};line-height:1.15;overflow-wrap:break-word">{_e(valor)}</span>'
            f'<span style="font-size:14px;color:{INK2}">{_e(sub)}</span></div>')


def veredicto(semaforo: str, sub: str, lineas: list[str]) -> str:
    v = V[semaforo]
    lin = "".join(f'<div style="padding:12px 16px;border-radius:14px;background:{v["line_bg"]};font-size:clamp(20px,1.9vw,28px);font-weight:800;line-height:1.15">{_e(l)}</div>'
                  for l in lineas)
    return (f'<div class="np" role="status" style="border-radius:24px;padding:28px 30px;background:{v["bg"]};color:{v["fg"]};'
            f'display:flex;flex-direction:column;gap:18px;min-height:300px;box-sizing:border-box">'
            f'<div style="display:flex;align-items:center;gap:22px">'
            f'<div style="width:clamp(72px,7vw,108px);aspect-ratio:1;flex:none;border-radius:50%;background:{v["icon_bg"]};color:{v["icon_fg"]};'
            f'display:flex;align-items:center;justify-content:center;font-size:clamp(40px,4.2vw,64px);font-weight:800;line-height:1">{v["glyph"]}</div>'
            f'<div style="display:flex;flex-direction:column;gap:6px;min-width:0">'
            f'<span style="font-size:18px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.85">{v["color"]}</span>'
            f'<span style="font-size:clamp(30px,3vw,52px);font-weight:800;line-height:1;letter-spacing:-0.02em">{v["titulo"]}</span></div></div>'
            f'<span style="font-size:clamp(18px,1.6vw,24px);line-height:1.3;font-weight:500">{_e(sub)}</span>'
            f'<div style="display:flex;flex-direction:column;gap:10px">{lin}</div></div>')


def veredicto_neutro(titulo: str, sub: str, analizando: bool = False, etiqueta: str = "Esperando") -> str:
    """Estado sin resultado: esperando bandeja o analizando (con spinner)."""
    icono = ('<div style="width:56px;height:56px;border-radius:50%;border:6px solid rgba(255,255,255,.2);'
             'border-top-color:#7FE0A6;animation:npSpin .8s linear infinite"></div>') if analizando else logo(64, "#fff", "#C9DDCF", "#2B3430")
    return (f'<div class="np" role="status" style="border-radius:24px;padding:28px 30px;background:#2B3430;color:#fff;'
            f'display:flex;flex-direction:column;gap:18px;min-height:300px;box-sizing:border-box">'
            f'<div style="display:flex;align-items:center;gap:22px">'
            f'<div style="width:clamp(72px,7vw,108px);aspect-ratio:1;flex:none;border-radius:50%;background:rgba(255,255,255,.1);'
            f'display:flex;align-items:center;justify-content:center">{icono}</div>'
            f'<div style="display:flex;flex-direction:column;gap:6px;min-width:0">'
            f'<span style="font-size:18px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.85">{_e(etiqueta)}</span>'
            f'<span style="font-size:clamp(28px,2.6vw,44px);font-weight:800;line-height:1.05;letter-spacing:-0.02em">{_e(titulo)}</span></div></div>'
            f'<span style="font-size:clamp(17px,1.5vw,22px);line-height:1.3;font-weight:500;opacity:.9">{_e(sub)}</span></div>')


def chips(items: list[dict]) -> str:
    """items: dict(estado, grupo, texto)."""
    celdas = []
    for it in items:
        s = S[it["estado"]]
        celdas.append(
            f'<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:14px;background:{s["t"]};min-width:0">'
            f'{glyph(it["estado"])}<div style="display:flex;flex-direction:column;min-width:0">'
            f'<span style="font-size:17px;font-weight:800;color:{s["ink"]}">{_e(it["grupo"])}</span>'
            f'<span style="font-size:14px;color:{s["ink"]};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{_e(it["texto"])}</span></div></div>')
    return f'<div class="np" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px">{"".join(celdas)}</div>'


def panel_camara_vacio(texto: str, sub: str = "") -> str:
    rayado = "repeating-linear-gradient(135deg,#2B3430 0 12px,#252D29 12px 24px)"
    return (f'<div class="np" style="position:relative;height:380px;border-radius:14px;overflow:hidden;background:{CAM}">'
            f'<div style="position:absolute;left:3%;top:7%;width:72%;height:86%;border-radius:28px;background:{rayado};border:2px solid #3A4540"></div>'
            f'<div style="position:absolute;left:79%;top:30%;width:17%;height:40%;border-radius:50%;background:{rayado};border:2px solid #3A4540"></div>'
            f'<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;text-align:center;padding:0 24px">'
            f'<span style="font-size:22px;font-weight:700;color:#E3F0E7">{_e(texto)}</span>'
            f'<span style="font-size:15px;color:#A9B5AF">{_e(sub)}</span></div>'
            f'<span class="np-mono" style="position:absolute;right:16px;bottom:14px;font-size:13px;color:#A9B5AF">Escala: bandeja 32 × 25 cm</span></div>')


def etiqueta_camara(texto: str, vivo: bool = True) -> str:
    punto = ('<span style="width:10px;height:10px;border-radius:50%;background:#E5483D;animation:npPulse 1.4s ease-in-out infinite"></span>'
             if vivo else f'<span style="width:12px;height:12px;border-radius:3px;border:2px dashed {SOBRA}"></span>')
    return (f'<div class="np" style="display:inline-flex;align-items:center;gap:8px;padding:6px 12px;border-radius:999px;'
            f'background:rgba(0,0,0,.55);color:#fff;font-size:15px;font-weight:600;margin-top:8px">{punto}{_e(texto)}</div>')


def barras_meta(filas: list[dict]) -> str:
    """filas: dict(nombre, servido, meta, estado). Escala hasta 120 % de la meta (línea = 100 %)."""
    out = []
    for f in filas:
        s = S[f["estado"]]
        w = min(100, 100 * f["servido"] / (1.2 * f["meta"])) if f["meta"] else 0
        fondo = s["t"] if f["estado"] == "falta" else LINE2
        out.append(f'<div style="display:flex;flex-direction:column;gap:4px">'
                   f'<div style="display:flex;justify-content:space-between;font-size:13px"><span>{_e(f["nombre"])}</span>'
                   f'<b>{f["servido"]:.0f} / {f["meta"]:.0f} g</b></div>'
                   f'<div style="position:relative;height:12px;border-radius:6px;background:{fondo}">'
                   f'<div style="width:{w:.1f}%;height:100%;border-radius:6px;background:{s["c"]}"></div>'
                   f'<div style="position:absolute;left:83.3%;top:-3px;bottom:-3px;width:2px;background:{INK}"></div></div></div>')
    return (f'<div class="np np-card" style="display:flex;flex-direction:column;gap:10px">'
            f'<span class="np-h">Servido vs. meta del grado</span>{"".join(out)}'
            f'<span class="np-sub">Línea: 100 % de la meta · cumple entre 80 % y 120 %</span></div>')


def medidor_kcal(kcal: float, meta: float, titulo: str = "Energía servida") -> str:
    pct = 100 * kcal / meta if meta else 0
    deg = min(180, 180 * pct / 120)  # el semicírculo completo = 120 % de la meta
    color = G600 if 80 <= pct <= 120 else "#E8A317"
    estado = "cumple" if 80 <= pct <= 120 else ("baja" if pct < 80 else "alta")
    return (f'<div class="np np-card" style="display:flex;flex-direction:column;gap:8px;align-items:center">'
            f'<span class="np-h" style="align-self:flex-start">{_e(titulo)}</span>'
            f'<div style="position:relative;width:200px;height:100px;overflow:hidden">'
            f'<div style="position:absolute;left:0;top:0;width:200px;height:200px;border-radius:50%;'
            f'background:conic-gradient(from 270deg,{color} 0 {deg:.0f}deg,{LINE} {deg:.0f}deg 180deg,transparent 180deg)"></div>'
            f'<div style="position:absolute;left:26px;top:26px;width:148px;height:148px;border-radius:50%;background:{SURF}"></div>'
            f'<div style="position:absolute;left:0;right:0;bottom:0;text-align:center;font-size:30px;font-weight:800">{kcal:.0f}</div></div>'
            f'<span style="font-size:13px;color:{INK2}">de {meta:.0f} kcal · {pct:.0f} % · {estado}</span></div>')


def tabla_nutrientes(filas: list[tuple[str, str, str]], titulo: str = "Nutrientes de la ración") -> str:
    """filas: (nutriente, valor, unidad)."""
    celdas = "".join(f'<b style="padding:7px 0;border-bottom:1px solid {LINE2}">{_e(n)}</b>'
                     f'<span style="padding:7px 0;border-bottom:1px solid {LINE2};text-align:right">{_e(v)} '
                     f'<span style="color:{INK2}">{_e(u)}</span></span>' for n, v, u in filas)
    return (f'<div class="np np-card" style="display:flex;flex-direction:column;gap:8px"><span class="np-h">{_e(titulo)}</span>'
            f'<div style="display:grid;grid-template-columns:1fr auto;font-size:14px">{celdas}</div>'
            f'<span class="np-sub">Tabla de Composición de Alimentos Colombianos (ICBF)</span></div>')


# ---------------------------------------------------------------- estación de devolución

def panel_consumo(pct: float, titulo: str, mensaje: str) -> str:
    p = round(pct)
    return (f'<div class="np" style="display:flex;flex-wrap:wrap;align-items:center;gap:28px;padding:24px 28px;border-radius:24px;background:{G100}">'
            f'<div style="position:relative;width:168px;height:168px;flex:none;border-radius:50%;'
            f'background:conic-gradient({G600} 0 {p}%,#C9DDCF {p}% 100%)">'
            f'<div style="position:absolute;inset:20px;border-radius:50%;background:{G100};display:flex;align-items:center;'
            f'justify-content:center;font-size:46px;font-weight:800;color:{G700}">{p} %</div></div>'
            f'<div style="display:flex;flex-direction:column;gap:10px;flex:1;min-width:240px">'
            f'<span style="font-size:42px;font-weight:800;line-height:1.05;letter-spacing:-0.02em;color:{G700}">{_e(titulo)}</span>'
            f'<span style="font-size:22px;color:#2E4A3B;line-height:1.3">{_e(mensaje)}</span></div></div>')


def barras_consumo(filas: list[tuple[str, float]]) -> str:
    """filas: (alimento, % consumido)."""
    rayas = f"repeating-linear-gradient(135deg,{SOBRA} 0 4px,#FBEFD3 4px 8px)"
    celdas = "".join(f'<span style="font-weight:700">{_e(n)}</span>'
                     f'<div style="display:flex;height:26px;border-radius:13px;overflow:hidden;background:{rayas}">'
                     f'<div style="width:{p:.0f}%;background:{G600};border-radius:13px"></div></div>'
                     f'<span style="font-weight:800;text-align:right">{p:.0f} %</span>' for n, p in filas)
    return (f'<div class="np np-card" style="border-radius:20px;padding:20px 24px;display:flex;flex-direction:column;gap:16px">'
            f'<div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px 20px;font-size:16px;color:{INK2}">'
            f'<span style="font-weight:700;color:{INK};font-size:18px;margin-right:auto">Lo que comiste</span>'
            f'{leyenda(G600, "Consumido")}{leyenda("", "Sobrante", "background:" + rayas)}</div>'
            f'<div style="display:grid;grid-template-columns:minmax(110px,170px) minmax(0,1fr) 64px;align-items:center;gap:10px 16px;font-size:19px">{celdas}</div></div>')


def tarjeta_dato(label: str, valor: str, de: str) -> str:
    return (f'<div class="np np-card" style="display:flex;flex-direction:column;gap:6px">'
            f'<span style="font-size:16px;color:{INK2}">{_e(label)}</span>'
            f'<span style="font-size:clamp(26px,2.4vw,36px);font-weight:800">{_e(valor)} <span style="font-size:clamp(15px,1.3vw,20px);font-weight:600;color:{INK2};white-space:nowrap">{_e(de)}</span></span></div>')


# ---------------------------------------------------------------- tablero

def kpi(label: str, valor: str, sub: str = "", estado: str | None = None, sub_color: str | None = None, unidad: str = "") -> str:
    ico = ""
    color_v = INK
    if estado:
        s = S[estado]
        ico = (f'<span style="width:16px;height:16px;border-radius:50%;background:{s["c"]};color:{s["fg"]};font-size:10px;'
               f'font-weight:800;display:flex;align-items:center;justify-content:center">{s["glyph"]}</span>')
        color_v = s["ink"]
    u = f' <span style="font-size:18px;color:{INK2}">{_e(unidad)}</span>' if unidad else ""
    return (f'<div class="np" style="background:{SURF};border:1px solid {LINE};border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:6px;height:100%;box-sizing:border-box">'
            f'<span style="font-size:13px;color:{INK2};display:flex;align-items:center;gap:6px">{ico}{_e(label)}</span>'
            f'<span style="font-size:30px;font-weight:800;letter-spacing:-0.02em;color:{color_v}">{_e(valor)}{u}</span>'
            f'<span style="font-size:12px;color:{sub_color or INK2};{"font-weight:700" if sub_color else ""}">{_e(sub)}</span></div>')


def grafico_diario(dias: list[dict]) -> str:
    """dias: dict(d, v, a, r) en % (completa, tras ajuste, rechazada)."""
    cols = []
    for x in dias:
        tip = f'{x["d"]} · Completa {x["v"]:.0f} % · Ajuste {x["a"]:.0f} % · Rechazo {x["r"]:.0f} %'
        cols.append(f'<div title="{_e(tip)}" style="flex:1;min-width:0;display:flex;flex-direction:column;gap:6px;align-items:center">'
                    f'<div style="flex:1;width:100%;max-width:44px;display:flex;flex-direction:column;border-radius:6px;overflow:hidden;gap:2px">'
                    f'<div style="height:{x["r"]:.1f}%;background:#B8322A"></div><div style="height:{x["a"]:.1f}%;background:#E8A317"></div>'
                    f'<div style="flex:1;background:{G600};display:flex;justify-content:center;padding-top:6px;color:#fff;font-size:11px;font-weight:700">{x["v"]:.0f}</div></div>'
                    f'<span style="font-size:11px;color:{INK2};white-space:nowrap">{_e(x["d"])}</span></div>')
    return (f'<div class="np np-card" style="padding:18px 20px;display:flex;flex-direction:column;gap:14px;height:100%;box-sizing:border-box">'
            f'<div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px"><span class="np-h" style="margin-right:auto">Cumplimiento diario</span>'
            f'{leyenda(G600, "Completa")}{leyenda("#E8A317", "Completada tras ajuste")}{leyenda("#B8322A", "Rechazada")}</div>'
            f'<div style="display:flex;gap:12px;height:220px">'
            f'<div class="np-mono" style="display:flex;flex-direction:column;justify-content:space-between;font-size:11px;color:{MUTED};padding-bottom:22px">'
            f'<span>100 %</span><span>50 %</span><span>0 %</span></div>{"".join(cols)}</div></div>')


def grafico_energia(grupos: list[dict]) -> str:
    """grupos: dict(g, meta, serv, cons)."""
    tope = max([max(x["meta"], x["serv"], x["cons"]) for x in grupos] + [1]) * 1.15
    cols = "".join(
        f'<div style="display:flex;flex-direction:column;gap:6px">'
        f'<div style="position:relative;flex:1;display:flex;align-items:flex-end;justify-content:center;gap:6px;border-bottom:1px solid {LINE}">'
        f'<div style="width:34px;height:{100 * x["serv"] / tope:.1f}%;background:#8FBF9F;border-radius:6px 6px 0 0;display:flex;justify-content:center;font-size:11px;font-weight:700;padding-top:4px;box-sizing:border-box;color:{G_DARK}">{x["serv"]:.0f}</div>'
        f'<div style="width:34px;height:{100 * x["cons"] / tope:.1f}%;background:{G600};border-radius:6px 6px 0 0;display:flex;justify-content:center;font-size:11px;font-weight:700;padding-top:4px;box-sizing:border-box;color:#fff">{x["cons"]:.0f}</div>'
        f'<div style="position:absolute;left:0;right:0;bottom:{100 * x["meta"] / tope:.1f}%;border-top:2px dashed {INK}">'
        f'<span style="position:absolute;right:0;top:-18px;font-size:11px;font-weight:700">{x["meta"]:.0f}</span></div></div>'
        f'<span style="font-size:13px;font-weight:700;text-align:center">{_e(x["g"])}</span></div>' for x in grupos)
    return (f'<div class="np np-card" style="padding:18px 20px;display:flex;flex-direction:column;gap:14px;height:100%;box-sizing:border-box">'
            f'<div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px"><span class="np-h" style="margin-right:auto">Energía por grado</span>'
            f'{leyenda("#8FBF9F", "Servida")}{leyenda(G600, "Consumida")}'
            f'{leyenda("", "Meta", f"height:0;border-top:2px dashed {INK};border-radius:0")}</div>'
            f'<div style="display:grid;grid-template-columns:repeat({max(1, len(grupos))},1fr);gap:16px;height:220px">{cols}</div></div>')


def grafico_sobrante(filas: list[tuple[str, float]]) -> str:
    tope = max([p for _, p in filas] + [45])
    celdas = "".join(f'<span style="font-size:13px">{_e(n)}</span>'
                     f'<div style="height:14px;border-radius:7px;background:{LINE2};overflow:hidden">'
                     f'<div style="height:100%;width:{100 * p / tope:.1f}%;background:{"#C98A0B" if p >= 25 else "#8FBF9F"};border-radius:7px"></div></div>'
                     f'<span style="font-size:13px;font-weight:700;text-align:right">{p:.0f} %</span>' for n, p in filas)
    return (f'<div class="np np-card" style="padding:18px 20px;display:flex;flex-direction:column;gap:12px;height:100%;box-sizing:border-box">'
            f'<div style="display:flex;flex-direction:column;gap:2px"><span class="np-h">Qué dejan en el plato</span>'
            f'<span class="np-sub">% sobrante por alimento · ámbar: 25 % o más</span></div>'
            f'<div style="display:grid;grid-template-columns:minmax(90px,140px) minmax(0,1fr) 40px;gap:8px 10px;align-items:center">{celdas}</div></div>')


def grafico_sedes(filas: list[tuple[str, int, int]]) -> str:
    """filas: (sede, rechazadas, no aptos)."""
    tope = max([r + x for _, r, x in filas] + [1])
    items = "".join(f'<div style="display:flex;flex-direction:column;gap:3px">'
                    f'<div style="display:flex;justify-content:space-between;gap:8px;font-size:13px"><span>{_e(n)}</span><span style="font-weight:700">{r + x}</span></div>'
                    f'<div style="display:flex;height:10px;gap:2px">'
                    f'<div style="width:{100 * r / tope:.1f}%;background:#B8322A;border-radius:3px"></div>'
                    f'<div style="width:{100 * x / tope:.1f}%;background:#7A2348;border-radius:3px"></div></div></div>' for n, r, x in filas)
    vacio = f'<span style="font-size:14px;color:{G700}">✓ Sin alertas rojas en el periodo.</span>' if not filas else ""
    return (f'<div class="np np-card" style="padding:18px 20px;display:flex;flex-direction:column;gap:12px;height:100%;box-sizing:border-box">'
            f'<div style="display:flex;flex-direction:column;gap:2px"><span class="np-h">Alertas por sede</span>'
            f'<span class="np-sub">Raciones rechazadas y alimentos no aptos</span></div>'
            f'<div style="display:flex;flex-direction:column;gap:9px">{items}{vacio}</div>'
            f'<div style="display:flex;gap:14px;margin-top:auto">{leyenda("#B8322A", "Rechazada")}{leyenda("#7A2348", "No apto")}</div></div>')


def grafico_nutrientes(filas: list[dict], nota: str) -> str:
    """filas: dict(n, serv, cons, u). Barra: % consumido de lo servido."""
    celdas = []
    for f in filas:
        p = 100 * f["cons"] / f["serv"] if f["serv"] else 0
        c = G600 if p >= 80 else "#C98A0B"
        celdas.append(f'<span style="font-weight:700">{_e(f["n"])}</span>'
                      f'<span style="text-align:right">{num(f["serv"], 1)} <span style="color:{INK2}">{_e(f["u"])}</span></span>'
                      f'<span style="text-align:right;font-weight:700">{num(f["cons"], 1)}</span>'
                      f'<div style="display:flex;align-items:center;gap:6px"><div style="position:relative;flex:1;height:10px;border-radius:5px;background:{LINE2}">'
                      f'<div style="position:absolute;left:0;top:0;bottom:0;width:{min(p, 100):.0f}%;background:{c};border-radius:5px"></div></div>'
                      f'<span style="font-size:11px;font-weight:700;width:34px;text-align:right">{p:.0f}%</span></div>')
    head = "".join(f'<span style="font-size:11px;color:{INK2};{a}">{t}</span>' for t, a in
                   [("Nutriente", ""), ("Servido", "text-align:right"), ("Consumido", "text-align:right"), ("% consumido", "")])
    return (f'<div class="np np-card" style="padding:18px 20px;display:flex;flex-direction:column;gap:12px;height:100%;box-sizing:border-box">'
            f'<div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:8px"><span class="np-h">Nutrientes</span>'
            f'<span class="np-sub" style="margin-left:auto">{_e(nota)}</span></div>'
            f'<div style="display:grid;grid-template-columns:minmax(80px,1fr) 80px 70px minmax(80px,1.2fr);gap:9px 8px;align-items:center;font-size:13px">{head}{"".join(celdas)}</div>'
            f'<span style="font-size:11px;color:{INK2}">Verde: se consume 80 % o más de lo servido</span></div>')


def tabla_registro(filas: list[dict], total: int) -> str:
    """filas: dict(h, sede, b, g, peso, kcal, estado, obs)."""
    th = "padding:8px 6px;font-size:11px;color:%s;border-bottom:1px solid %s;text-align:left;font-weight:400" % (INK2, LINE)
    td = f"padding:9px 6px;border-bottom:1px solid {LINE2};white-space:nowrap"
    head = "".join(f'<th style="{th};{a}">{t}</th>' for t, a in
                   [("Hora", ""), ("Sede", ""), ("Bandeja", ""), ("Grado", ""), ("Peso", "text-align:right"),
                    ("kcal", "text-align:right"), ("Estado", ""), ("Observación", "")])
    rows = "".join(f'<tr><td class="np-mono" style="{td};font-size:12px">{_e(r["h"])}</td><td style="{td}">{_e(r["sede"])}</td>'
                   f'<td class="np-mono" style="{td};font-size:12px">{_e(r["b"])}</td><td style="{td}">{_e(r["g"])}</td>'
                   f'<td style="{td};text-align:right">{r["peso"]:.0f} g</td><td style="{td};text-align:right">{r["kcal"]:.0f}</td>'
                   f'<td style="{td}">{pill(r["estado"])}</td><td style="{td};color:{INK2};white-space:normal">{_e(r["obs"])}</td></tr>'
                   for r in filas)
    return (f'<div class="np" style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px">'
            f'<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            f'<div class="np np-sub" style="margin-top:8px">Mostrando {len(filas)} de {num(total)} entregas · '
            f'los filtros activos se aplican a la exportación</div>')


def tarjeta_alerta(estado: str, titulo: str, meta: str, detalle: str) -> str:
    return (f'<div class="np" style="display:flex;gap:12px;padding:12px 14px;border:1px solid {LINE};border-left:4px solid {S[estado]["c"]};'
            f'border-radius:12px;background:{SURF}">'
            f'<div style="display:flex;flex-direction:column;gap:4px;min-width:0">{pill(estado)}'
            f'<span style="font-size:15px;font-weight:800">{_e(titulo)}</span>'
            f'<span style="font-size:12px;color:{INK2}">{_e(meta)}</span>'
            f'<span style="font-size:13px;line-height:1.4">{_e(detalle)}</span></div></div>')


# ---------------------------------------------------------------- vista pública

def vista_publica(sede: str, semana: str, pct: float, meta: float, completas: int, total: int,
                  dias: list[dict], consumo_pct: float, rojas: int, rojas_sub: str, menu: list[tuple[str, str]]) -> str:
    circulos = []
    for d in dias:
        if d["pct"] is None:
            c = (f'<span style="width:40px;height:40px;border-radius:50%;border:2px dashed #C8C0B2;color:{MUTED};display:flex;'
                 f'align-items:center;justify-content:center;font-size:13px;box-sizing:border-box">—</span>')
            sub = "pendiente"
        else:
            est = "ok" if d["pct"] >= 90 else "bajo"
            c, sub = glyph(est, 40, 20), f'{d["pct"]:.0f} %'
        circulos.append(f'<div style="display:flex;flex-direction:column;align-items:center;gap:6px">{c}'
                        f'<span style="font-size:14px;font-weight:700">{_e(d["d"])}</span>'
                        f'<span style="font-size:12px;color:{INK2}">{sub}</span></div>')
    menu_html = "".join(f'<div style="display:flex;gap:10px"><span style="width:34px;flex:none;color:{INK2};font-weight:700">{_e(d)}</span>'
                        f'<span>{_e(m)}</span></div>' for d, m in menu) or f'<span style="color:{INK2}">Sin registros esta semana.</span>'
    return (f'<div class="np" style="max-width:420px;margin:0 auto;display:flex;flex-direction:column;gap:16px">'
            f'<div style="display:flex;align-items:center;gap:8px">{logo(30)}<span style="font-size:19px;font-weight:800">NutriPAE</span>'
            f'<span style="margin-left:auto;font-size:13px;color:{INK2}">Consulta pública</span></div>'
            f'<div style="display:flex;flex-direction:column;gap:4px"><span style="font-size:14px;color:{INK2}">{_e(semana)}</span>'
            f'<span style="font-size:26px;font-weight:800;line-height:1.15">{_e(sede)}</span>'
            f'<span style="font-size:14px;color:{INK2}">Neiva · Programa de Alimentación Escolar</span></div>'
            f'<div style="background:{G600};color:#fff;border-radius:22px;padding:22px;display:flex;flex-direction:column;gap:14px">'
            f'<span style="font-size:15px;font-weight:600;opacity:.9">Raciones completas esta semana</span>'
            f'<div style="display:flex;align-items:baseline;gap:10px"><span style="font-size:64px;font-weight:800;line-height:.9;letter-spacing:-0.03em;white-space:nowrap">{pct:.0f} %</span>'
            f'<span style="font-size:15px;opacity:.9">meta del programa: {meta:.0f} %</span></div>'
            f'<div style="height:10px;border-radius:5px;background:rgba(255,255,255,.25);position:relative">'
            f'<div style="width:{min(pct, 100):.0f}%;height:100%;border-radius:5px;background:#fff"></div>'
            f'<div style="position:absolute;left:{meta:.0f}%;top:-4px;width:2px;height:18px;background:#FBEFD3"></div></div>'
            f'<span style="font-size:15px;line-height:1.35">{num(completas)} de {num(total)} raciones verificadas salieron completas a la primera.</span></div>'
            f'<div class="np-card" style="border-radius:18px;display:flex;flex-direction:column;gap:12px"><span style="font-size:16px;font-weight:700">Día a día</span>'
            f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;text-align:center">{"".join(circulos)}</div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'
            f'<div class="np-card" style="padding:14px;display:flex;flex-direction:column;gap:4px"><span style="font-size:13px;color:{INK2}">Consumo promedio</span>'
            f'<span style="font-size:28px;font-weight:800">{consumo_pct:.0f} %</span><span style="font-size:12px;color:{INK2}">de lo servido</span></div>'
            f'<div class="np-card" style="padding:14px;display:flex;flex-direction:column;gap:4px"><span style="font-size:13px;color:{INK2}">Alertas rojas</span>'
            f'<span style="font-size:28px;font-weight:800">{rojas}</span><span style="font-size:12px;color:{INK2}">{_e(rojas_sub)}</span></div></div>'
            f'<div class="np-card" style="border-radius:18px;display:flex;flex-direction:column;gap:10px"><span style="font-size:16px;font-weight:700">Menú servido</span>'
            f'<div style="display:flex;flex-direction:column;gap:8px;font-size:14px">{menu_html}</div></div>'
            f'<span style="font-size:12px;line-height:1.45;color:{INK2}">NutriPAE no capta rostros ni datos personales. Cada bandeja se identifica '
            f'con un código anónimo y el grado. Actualizado hoy, {hora()}.</span></div>')


# ---------------------------------------------------------------- cómo funciona

def como_funciona() -> str:
    def paso(n, t, d):
        return (f'<div class="np-card" style="border-radius:20px;padding:20px;display:flex;flex-direction:column;gap:10px">'
                f'<span class="np-mono" style="font-size:13px;color:{INK2}">{n}</span><span style="font-size:22px;font-weight:800">{t}</span>'
                f'<span style="font-size:15px;line-height:1.4;color:{INK2}">{d}</span></div>')
    check = (f'<span style="width:26px;height:26px;border-radius:50%;background:#fff;color:{G600};display:flex;align-items:center;'
             f'justify-content:center;font-weight:800;flex:none">✓</span>')
    verif = (f'<div style="background:{G600};color:#fff;border-radius:20px;padding:20px;display:flex;flex-direction:column;gap:12px">'
             f'<span class="np-mono" style="font-size:13px;opacity:.85">03</span><span style="font-size:22px;font-weight:800">Verificación</span>'
             f'<div style="display:flex;flex-direction:column;gap:8px;font-size:16px">'
             f'<div style="display:flex;align-items:center;gap:10px">{check}<span><b>Grupos:</b> los 6 presentes</span></div>'
             f'<div style="display:flex;align-items:center;gap:10px">{check}<span><b>Porción:</b> ±20 % de la meta del grado</span></div>'
             f'<div style="display:flex;align-items:center;gap:10px">{check}<span><b>Aptitud:</b> sin mal aspecto</span></div></div></div>')

    def semaforo(est, t, d):
        s = S[est]
        return (f'<div style="display:flex;align-items:center;gap:14px;padding:16px 18px;border-radius:16px;background:{s["t"]}">'
                f'{glyph(est, 44, 22)}<div style="display:flex;flex-direction:column;gap:2px">'
                f'<span style="font-size:18px;font-weight:800;color:{s["ink"]}">{t}</span>'
                f'<span style="font-size:14px;color:{s["ink"]}">{d}</span></div></div>')

    def principio(t, d):
        return (f'<div style="border-top:3px solid {G600};padding-top:12px;display:flex;flex-direction:column;gap:6px">'
                f'<span style="font-size:17px;font-weight:800">{t}</span><span style="font-size:14px;line-height:1.4;color:{INK2}">{d}</span></div>')

    return (f'<div class="np" style="display:flex;flex-direction:column;gap:32px;padding:8px 0">'
            f'<div style="display:flex;flex-wrap:wrap;align-items:flex-end;gap:16px 24px">'
            f'<div style="display:flex;flex-direction:column;gap:10px">'
            f'<span class="np-mono" style="font-size:14px;color:{G600};font-weight:600;letter-spacing:.06em">CÓMO FUNCIONA</span>'
            f'<span style="font-size:40px;font-weight:800;letter-spacing:-0.02em;line-height:1.05">De la bandeja al tablero, ración por ración</span></div>'
            f'<span style="margin-left:auto;max-width:330px;font-size:17px;line-height:1.4;color:{INK2}">Dos estaciones por comedor: entrega y devolución. '
            f'Cada una con cámara cenital, pantalla y luz LED. Sin báscula.</span></div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;align-items:stretch">'
            f'{paso("01", "Cámara cenital", "Fotografía la bandeja desde arriba con luz LED constante. Solo ve la bandeja.")}'
            f'{paso("02", "IA de visión", "Reconoce cada alimento y estima los gramos usando la bandeja como referencia de escala.")}'
            f'{verif}'
            f'{paso("04", "Base de datos", "Guarda gramos, nutrientes y semáforo por bandeja anónima, sede y grado.")}'
            f'{paso("05", "Tablero", "Operador, Secretaría de Educación y veedurías ven cumplimiento, alertas y desperdicio.")}</div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px">'
            f'{semaforo("ok", "Verde · Ración completa", "Se entrega la bandeja")}'
            f'{semaforo("bajo", "Amarillo · Completar porción", "Menos del 80 % de la meta")}'
            f'{semaforo("falta", "Rojo · Ración rechazada", "Falta un grupo o alimento no apto")}</div>'
            f'<div style="display:flex;flex-direction:column;gap:14px"><span style="font-size:20px;font-weight:800">Principios de privacidad</span>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px">'
            f'{principio("Sin rostros", "La cámara apunta solo a la bandeja. Ninguna imagen muestra personas.")}'
            f'{principio("Código anónimo", "Cada bandeja lleva un código y el grado. Sin nombres ni documentos.")}'
            f'{principio("Datos mínimos", "Se guarda lo necesario para verificar: alimento, gramos, nutrientes, hora y sede.")}'
            f'{principio("Transparencia", "Rectores, padres y veedurías consultan el cumplimiento agregado por sede.")}</div></div></div>')


def tabla_metas(columnas: list[str], filas: list[tuple[str, list[float]]]) -> str:
    th = f"padding:8px 10px;font-size:12px;color:{INK2};border-bottom:1px solid {LINE};font-weight:700"
    td = f"padding:8px 10px;border-bottom:1px solid {LINE2}"
    head = f'<th style="{th};text-align:left">Alimento</th>' + "".join(f'<th style="{th};text-align:right">{_e(c)}</th>' for c in columnas)
    rows = "".join(f'<tr><td style="{td};font-weight:700">{_e(n)}</td>' + "".join(f'<td style="{td};text-align:right">{v:.0f} g</td>' for v in vals) + "</tr>"
                   for n, vals in filas)
    return (f'<div class="np np-card" style="display:flex;flex-direction:column;gap:10px;overflow-x:auto">'
            f'<span class="np-h">Metas de porción por grado</span>'
            f'<span class="np-sub">Referencia parametrizable según la minuta patrón del PAE</span>'
            f'<table style="border-collapse:collapse;font-size:14px;width:100%"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>')


# ---------------------------------------------------------------- avisos y estados

_TONOS = {
    "info":  dict(bg=SURF, borde=LINE, acento=G600, ink=INK, ink2=INK2),
    "ok":    dict(bg=G100, borde="#C9DDCF", acento=G600, ink=G700, ink2="#2E4A3B"),
    "aviso": dict(bg="#FBEFD3", borde="#F1D9A0", acento="#E8A317", ink="#6E4600", ink2="#6E4600"),
}


def nota(titulo: str, texto: str, tono: str = "info") -> str:
    t = _TONOS[tono]
    return (f'<div class="np" style="display:flex;flex-direction:column;gap:4px;padding:12px 14px;border-radius:14px;'
            f'background:{t["bg"]};border:1px solid {t["borde"]};border-left:4px solid {t["acento"]}">'
            f'<span style="font-size:15px;font-weight:800;color:{t["ink"]}">{_e(titulo)}</span>'
            f'<span style="font-size:14px;line-height:1.4;color:{t["ink2"]}">{_e(texto)}</span></div>')


def estado_vacio(titulo: str, texto: str) -> str:
    return (f'<div class="np np-card" style="display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;'
            f'padding:48px 24px;border-radius:20px">{logo(56)}'
            f'<span style="font-size:22px;font-weight:800">{_e(titulo)}</span>'
            f'<span style="font-size:15px;line-height:1.45;color:{INK2};max-width:520px">{_e(texto)}</span></div>')


_YOLO_PUNTOS = [
    ("Necesita entrenamiento propio",
     "Un modelo YOLO solo reconoce lo que ha visto. Debe entrenarse con miles de fotos etiquetadas de bandejas reales "
     "de los comedores de Neiva: cada alimento de cada minuta, con distintas porciones y luces."),
    ("El piloto puede producir esas fotos",
     "Con autorización de las sedes, el piloto recolectará fotos anónimas de bandejas (solo la bandeja) con los "
     "alimentos y gramos que reconoce la IA de visión, revisadas por nutricionistas: ese será el conjunto de entrenamiento."),
    ("Qué gana el PAE en la fase 2",
     "El modelo corre en la misma estación, sin internet y sin costo por foto, y responde en menos de un segundo."),
]


def fase2_yolo(compacto: bool = False) -> str:
    """Explica por qué el piloto aún no usa el modelo YOLO propio."""
    puntos = "".join(
        f'<div style="display:flex;gap:12px;align-items:flex-start"><span class="np-mono" style="flex:none;width:26px;height:26px;'
        f'border-radius:50%;background:{G100};color:{G700};display:flex;align-items:center;justify-content:center;font-size:13px;'
        f'font-weight:600">{i}</span><div style="display:flex;flex-direction:column;gap:2px">'
        f'<span style="font-size:16px;font-weight:800">{_e(t)}</span>'
        f'<span style="font-size:14px;line-height:1.45;color:{INK2}">{_e(d)}</span></div></div>'
        for i, (t, d) in enumerate(_YOLO_PUNTOS[:1] if compacto else _YOLO_PUNTOS, 1))
    return (f'<div class="np np-card" style="border-radius:24px;padding:24px 26px;display:flex;flex-direction:column;gap:16px">'
            f'<div style="display:flex;flex-direction:column;gap:6px">'
            f'<span class="np-mono" style="font-size:13px;font-weight:600;color:{G600};letter-spacing:.06em">FASE 2 · EN PREPARACIÓN</span>'
            f'<span style="font-size:clamp(24px,2.2vw,32px);font-weight:800;line-height:1.1">Modelo propio YOLO</span>'
            f'<span style="font-size:15px;line-height:1.45;color:{INK2}">Esta prueba piloto todavía no usa esta opción. '
            f'Para analizar bandejas ahora, elija <b>IA de visión</b> en la barra lateral.</span></div>{puntos}</div>')


def tecnologia() -> str:
    """Sección de 'Cómo funciona': qué IA usa el piloto hoy y qué viene después."""
    def col(etiqueta, titulo, texto, items, destacado):
        bg, fg, sub = (G600, "#fff", "rgba(255,255,255,.85)") if destacado else (SURF, INK, INK2)
        borde = "" if destacado else f"border:1px solid {LINE};"
        lis = "".join(f'<li style="margin:4px 0">{_e(x)}</li>' for x in items)
        return (f'<div style="background:{bg};color:{fg};{borde}border-radius:20px;padding:22px;display:flex;flex-direction:column;gap:10px">'
                f'<span class="np-mono" style="font-size:13px;font-weight:600;letter-spacing:.06em;color:{sub}">{_e(etiqueta)}</span>'
                f'<span style="font-size:22px;font-weight:800">{_e(titulo)}</span>'
                f'<span style="font-size:15px;line-height:1.45;color:{sub}">{_e(texto)}</span>'
                f'<ul style="margin:0;padding-left:18px;font-size:14px;line-height:1.45;color:{sub}">{lis}</ul></div>')
    return ('<div class="np" style="display:flex;flex-direction:column;gap:14px">'
            '<span style="font-size:20px;font-weight:800">La IA del piloto</span>'
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px">'
            + col("HOY · PILOTO", "IA de visión", "Un modelo multimodal analiza cada foto y responde en segundos, sin entrenamiento previo.",
                  ["Reconoce los alimentos de cualquier minuta", "Estima gramos con la bandeja como escala",
                   "Detecta mal aspecto: color, moho, quemado"], True)
            + col("FASE 2", "Modelo propio YOLO", "Se entrenará con fotos anónimas de bandejas recolectadas durante el piloto.",
                  ["Corre en la estación, sin internet", "Sin costo por análisis", "Respuesta en menos de un segundo"], False)
            + '</div></div>')
