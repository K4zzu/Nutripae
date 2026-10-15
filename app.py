"""NutriPAE — Verificación nutricional con IA para comedores escolares (Neiva).

Ejecutar:  streamlit run app.py
Diseño: sistema de diseño NutriPAE v1 (Claude Design) — ver nutripae/ui.py y .streamlit/config.toml
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from html import escape

import pandas as pd
import streamlit as st
from PIL import Image
from dotenv import load_dotenv

load_dotenv()  # lee .env (ANTHROPIC_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY, NUTRIPAE_SEDE, etc.)

from nutripae import storage, simulate, ui
from nutripae.detector import (DemoDetector, VisionLLMDetector, ENV_KEY,
                               dibujar_overlay, bandeja_sintetica)
from nutripae.menu import MINUTAS, GRADOS, KCAL_META, GRUPO_LABEL, meta_gramos
from nutripae.nutrition import TABLA, sumar, NUTRIENTE_LABEL
from nutripae.verifier import verificar, consumo

st.set_page_config(page_title="NutriPAE · Verificación nutricional con IA", page_icon="🍽️",
                   layout="wide", initial_sidebar_state="expanded")
st.html(ui.CSS)

GRADO_CORTO = {"preescolar": "Preescolar", "primaria": "Primaria", "secundaria": "Secundaria"}
RACIONES_TURNO = int(os.getenv("NUTRIPAE_RACIONES_TURNO", "320"))
META_PUBLICA = 95  # % de raciones completas a la primera que exige el programa
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
log = logging.getLogger("nutripae")
# modos de análisis que ve el usuario (los detalles técnicos se toman del .env del servidor)
MODOS = {"ia": "IA de visión", "demo": "Demostración", "yolo": "Modelo propio (YOLO)"}
MODOS_SUB = {"ia": "Analiza la foto real de cada bandeja", "demo": "Bandejas simuladas, sin cámara",
             "yolo": "Fase 2 · aún no disponible en el piloto"}
ESCENARIOS = {"aleatorio": "Al azar, como en un turno real", "completa": "Ración completa",
              "incompleta": "Ración incompleta", "no_apto": "Alimento en mal estado"}
NOMBRE_MOTOR = {"Visión LLM": "IA de visión", "Demo (simulado)": "Simulación"}
# por qué conviene cada grupo (mensaje amable en la estación de devolución)
BENEFICIO = {"verdura": "te da fibra y vitaminas", "fruta": "te da vitaminas", "proteina": "te ayuda a crecer fuerte",
             "cereal": "te da energía para estudiar", "tuberculo": "te da energía para jugar", "bebida": "te ayuda a hidratarte"}

con = storage.conectar()
ss = st.session_state
ss.setdefault("contador", 1)
ss.setdefault("ultima_entrega", None)

if ss.get("flash"):
    st.toast(ss.pop("flash"), icon="✅")


# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.html(f'<div class="np" style="display:flex;align-items:center;gap:10px">{ui.logo(36)}'
            f'<div style="display:flex;flex-direction:column"><span style="font-size:22px;font-weight:800">NutriPAE</span>'
            f'<span style="font-size:12px;color:{ui.INK2}">Verificación nutricional · PAE Neiva</span></div></div>')
    _sede_env = os.getenv("NUTRIPAE_SEDE")
    sede = st.selectbox("Sede educativa", simulate.SEDES,
                        index=simulate.SEDES.index(_sede_env) if _sede_env in simulate.SEDES else 0)
    minuta_cod = st.selectbox("Minuta del día", list(MINUTAS), format_func=lambda k: MINUTAS[k].nombre)
    minuta = MINUTAS[minuta_cod]
    st.divider()
    # el proveedor de IA se elige solo: NUTRIPAE_PROVEEDOR o el primero con clave configurada en el servidor
    _con_key = [p for p, var in ENV_KEY.items() if os.getenv(var)]
    proveedor = os.getenv("NUTRIPAE_PROVEEDOR") if os.getenv("NUTRIPAE_PROVEEDOR") in _con_key else (_con_key or [None])[0]
    modo = st.radio("Modo de análisis", list(MODOS), format_func=MODOS.get, captions=[MODOS_SUB[m] for m in MODOS],
                    index=0 if proveedor else 1)
    escenario = "aleatorio"
    if modo == "demo":
        escenario = st.selectbox("Situación a simular", list(ESCENARIOS), format_func=ESCENARIOS.get)
    elif modo == "ia" and not proveedor:
        st.html(ui.nota("IA de visión no disponible", "Este equipo aún no tiene activo el servicio de IA. "
                        "Mientras tanto, use el modo Demostración.", "aviso"))
    elif modo == "yolo":
        st.html(ui.nota("Disponible en la fase 2", "El modelo propio se entrenará con fotos de bandejas recolectadas "
                        "durante el piloto. Vea la explicación en la estación.", "aviso"))
    st.divider()
    st.html(ui.nota("Privacidad", "La cámara solo capta la bandeja. No se registran rostros ni datos personales; "
                    "cada bandeja se identifica con un código anónimo.", "ok"))
    with st.expander("Administración"):
        st.caption("Para preparar una demostración del tablero.")
        if st.button("Cargar datos de ejemplo", width="stretch", help="Agrega 10 días de raciones simuladas en las sedes del piloto"):
            with st.spinner("Cargando datos de ejemplo…"):
                simulate.generar(con, dias=10, raciones_por_dia=60)
            ss.flash = "Datos de ejemplo cargados"
            st.rerun()
        borrar_ok = st.checkbox("Quiero borrar todos los registros")
        if st.button("Borrar registros", width="stretch", disabled=not borrar_ok):
            storage.vaciar(con)
            ss.flash = "Registros borrados"
            st.rerun()

puede_analizar = modo == "demo" or (modo == "ia" and proveedor is not None)


def construir_detector(modo_estacion: str = "entrega"):
    if modo == "demo":
        return DemoDetector(escenario)
    return VisionLLMDetector(proveedor=proveedor, modo=modo_estacion)


def mensaje_error(e: Exception) -> str:
    """Traduce el error técnico a una instrucción para quien opera la estación (el detalle va al log)."""
    log.exception("Fallo en el análisis de la bandeja")
    t = f"{type(e).__name__} {e}".lower()
    if "api key" in t or "auth" in t or "401" in t:
        return "El servicio de IA no está activo en este equipo. Avise al administrador o use el modo Demostración."
    if any(x in t for x in ("connect", "timeout", "network", "resolve")):
        return "No hay conexión con el servicio de IA. Revise el internet de la estación e intente de nuevo."
    if any(x in t for x in ("json", "expecting", "decode")):
        return "La IA no pudo leer la bandeja. Tome la foto de nuevo con la bandeja completa y bien iluminada."
    return "Algo falló al analizar la bandeja. Intente de nuevo; si persiste, use el modo Demostración."


def fecha_larga(d: date) -> str:
    return f"{['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][d.weekday()]} {d.day} {MESES[d.month - 1][:3]}"


def texto_veredicto(res, grado: str) -> tuple[str, list[str]]:
    """Subtítulo y líneas de acción del veredicto, en el lenguaje del kiosco."""
    if res.semaforo == "verde":
        return (f"Los {len(res.items)} grupos están presentes y cada porción cumple la meta de "
                f"{GRADO_CORTO[grado].lower()}. Puede entregar la bandeja.", [])
    if res.semaforo == "amarillo":
        return ("Agregue lo que falta y vuelva a analizar.",
                [f"{i.nombre}: faltan {i.meta_g - i.servido_g:.0f} g" for i in res.items if i.estado == "bajo"])
    lineas = []
    for i in res.items:
        if i.estado == "falta":
            lineas.append(f"Falta {GRUPO_LABEL[i.grupo].lower()}: {i.nombre.lower()}")
        elif i.estado == "no_apto":
            lineas.append(f"{i.nombre} no apto: {i.mensaje[:40].rstrip()}")
    return "No entregue esta bandeja. Sirva una nueva ración.", lineas


def chips_resultado(res) -> list[dict]:
    out = []
    for i in res.items:
        texto = {"falta": "No detectado", "no_apto": "Mal aspecto"}.get(i.estado, f"{i.nombre} · {i.servido_g:.0f}/{i.meta_g:.0f} g")
        out.append(dict(estado=i.estado, grupo=GRUPO_LABEL[i.grupo].split(" /")[0], texto=texto))
    return out


def estado_entrega(row) -> str:
    """Estado de una entrega registrada para el tablero: no apto > falta grupo > porción baja > completa."""
    if any("NO APTO" in a for a in row.alertas):
        return "no_apto"
    return {"rojo": "falta", "amarillo": "bajo"}.get(row.semaforo, "ok")


def sin_icono(alerta: str) -> str:
    return alerta.split(" ", 1)[1] if " " in alerta and not alerta[0].isalnum() else alerta


def nutriente_partes(k: str) -> tuple[str, str]:
    etiqueta = NUTRIENTE_LABEL[k]
    nombre, _, unidad = etiqueta.partition(" (")
    return nombre, unidad.rstrip(")")


def tablero(ent_df, dev_df, sede_sel: str, grado_sel: str):
    """Cuerpo del tablero; retorna temprano si el filtro deja la tabla vacía."""
    e = ent_df.copy()
    if sede_sel != "Todas":
        e = e[e.sede == sede_sel]
    if grado_sel != "Todos":
        e = e[e.grado == grado_sel.lower()]
    d = dev_df[dev_df.entrega_id.isin(e.id)] if not dev_df.empty else dev_df
    if e.empty:
        st.html(ui.estado_vacio("Sin entregas para este filtro", "Pruebe con otra sede o con todos los grados."))
        return
    e["estado"] = e.apply(estado_entrega, axis=1)

    total = len(e)
    completas = int(e.aprobada.sum())
    rojas = e[e.semaforo == "rojo"]
    corregidas = int(e.corregida.sum())
    no_aptos = int((e.estado == "no_apto").sum())
    kcal_serv = e.kcal.mean()
    kcal_cons = d.kcal_consumidas.mean() if not d.empty else 0
    sobr_total = d.sobrante.apply(lambda s: sum(s.values())).sum() if not d.empty else 0
    k = st.columns(6)
    k[0].html(ui.kpi("Raciones verificadas", ui.num(total), f"en {e.sede.nunique()} sedes · {e.fecha.nunique()} días"))
    k[1].html(ui.kpi("Completas a la primera", f"{ui.num(100 * completas / total, 1)} %",
                     f"+{100 * corregidas / total:.0f} % corregidas en el momento", sub_color=ui.G700))
    k[2].html(ui.kpi("Alertas rojas", ui.num(len(rojas)), f"{int((~rojas.corregida.astype(bool)).sum())} sin corregir", estado="falta"))
    k[3].html(ui.kpi("Alimentos no aptos", ui.num(no_aptos), "mal aspecto detectado por la IA", estado="no_apto"))
    k[4].html(ui.kpi("kcal servidas / consumidas", f"{kcal_serv:.0f}", f"consumo {100 * kcal_cons / kcal_serv:.0f} % de lo servido"
                     if kcal_serv and kcal_cons else "sin devoluciones", unidad=f"/ {kcal_cons:.0f}"))
    k[5].html(ui.kpi("Desperdicio", ui.num(sobr_total / 1000, 1), f"{sobr_total / len(d):.0f} g por ración" if len(d) else "sin devoluciones",
                     unidad="kg"))

    st.html('<div style="height:6px"></div>')
    g1, g2 = st.columns([1.6, 1])
    dias = []
    for fecha, grp in e.groupby("fecha"):
        n = len(grp)
        v = 100 * (grp.semaforo == "verde").sum() / n
        a_ = 100 * ((grp.semaforo != "verde") & grp.corregida.astype(bool)).sum() / n
        dias.append(dict(d=f"{fecha.day} {MESES[fecha.month - 1][:3]}", v=v, a=a_, r=max(0.0, 100 - v - a_)))
    g1.html(ui.grafico_diario(dias[-12:]))
    energia = []
    if not d.empty:
        m = e.merge(d[["entrega_id", "kcal_consumidas"]], left_on="id", right_on="entrega_id")
        for g in GRADOS:
            mg = m[m.grado == g]
            if not mg.empty:
                energia.append(dict(g=GRADO_CORTO[g], meta=KCAL_META[g], serv=mg.kcal.mean(), cons=mg.kcal_consumidas.mean()))
    g2.html(ui.grafico_energia(energia) if energia else ui.kpi("Energía por grado", "—", "Sin devoluciones registradas"))

    g3, g4, g5 = st.columns([1, 1, 1.15])
    if not d.empty:
        m = e.merge(d[["entrega_id", "sobrante"]], left_on="id", right_on="entrega_id")
        filas = [{"alimento": TABLA[a_].nombre if a_ in TABLA else a_, "servido": g, "sobrante": r.sobrante.get(a_, 0)}
                 for _, r in m.iterrows() for a_, g in r.porciones.items()]
        s = pd.DataFrame(filas).groupby("alimento").sum()
        s["p"] = 100 * s.sobrante / s.servido
        g3.html(ui.grafico_sobrante([(n, p) for n, p in s.p.sort_values(ascending=False).head(8).items()]))
    else:
        g3.html(ui.kpi("Qué dejan en el plato", "—", "Sin devoluciones registradas"))
    sedes_al = (rojas.assign(noapto=rojas.alertas.apply(lambda al: any("NO APTO" in x for x in al)))
                .groupby("sede").noapto.agg(["size", "sum"]).sort_values("size", ascending=False).head(7))
    g4.html(ui.grafico_sedes([(n, int(r["size"] - r["sum"]), int(r["sum"])) for n, r in sedes_al.iterrows()]))
    if not d.empty:
        ns = pd.DataFrame(list(e.nutrientes)).mean()
        nc = pd.DataFrame(list(d.nutrientes)).mean()
        g5.html(ui.grafico_nutrientes(
            [dict(n=nutriente_partes(k_)[0], u=nutriente_partes(k_)[1], serv=ns[k_], cons=nc.get(k_, 0)) for k_ in ns.index],
            f"promedio por ración · {grado_sel.lower() if grado_sel != 'Todos' else 'todos los grados'}"))
    else:
        g5.html(ui.kpi("Nutrientes", "—", "Sin devoluciones registradas"))

    r1, r2 = st.columns([1.5, 1])
    with r1, st.container(border=True):
        h1, h2 = st.columns([1, 2], vertical_alignment="center")
        h1.html('<span class="np np-h">Registro de entregas</span>')
        filtro = h2.pills("Estado", ["Todas", "Completas", "Porción baja", "Falta grupo", "No apto"], default="Todas",
                          label_visibility="collapsed") or "Todas"
        clave = {"Completas": "ok", "Porción baja": "bajo", "Falta grupo": "falta", "No apto": "no_apto"}.get(filtro)
        reg = e if clave is None else e[e.estado == clave]
        reg = reg.sort_values("ts", ascending=False)
        filas = [dict(h=f"{r.ts:%d/%m %H:%M}", sede=r.sede, b=r.bandeja, g=GRADO_CORTO[r.grado], peso=r.peso_g or 0, kcal=r.kcal,
                      estado=r.estado,
                      obs=(" · ".join(sin_icono(x) for x in r.alertas) or "—") + (" · corregida" if r.corregida else ""))
                 for r in reg.head(15).itertuples()]
        st.html(ui.tabla_registro(filas, len(reg)))
        vista = reg[["ts", "sede", "bandeja", "grado", "minuta", "peso_g", "semaforo", "corregida", "kcal", "alertas"]].copy()
        vista["alertas"] = vista.alertas.apply(lambda al: " | ".join(al))
        vista["grado"] = vista.grado.map(GRADOS)
        st.download_button("Exportar CSV", vista.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"nutripae_entregas_{datetime.now():%Y%m%d}.csv", mime="text/csv")
    with r2, st.container(border=True):
        al = e[e.estado.isin(["falta", "no_apto"])].sort_values("ts", ascending=False)
        st.html(f'<div class="np" style="display:flex;align-items:center;gap:8px"><span class="np-h" style="margin-right:auto">Alertas recientes</span>'
                f'<span class="np-sub">{len(al)} en el periodo</span></div>')
        if al.empty:
            st.html(f'<span class="np" style="color:{ui.G700}">✓ Sin alertas rojas en el periodo.</span>')
        for r in al.head(5).itertuples():
            textos = [sin_icono(x) for x in r.alertas]
            detalle = "Ración corregida y entregada en el momento." if r.corregida else "Ración rechazada; se sirvió una nueva."
            st.html(ui.tarjeta_alerta(r.estado, textos[0] if textos else "Ración rechazada",
                                      f"{r.sede} · {GRADO_CORTO[r.grado]} · {r.ts:%d/%m %H:%M} · {r.bandeja}",
                                      " · ".join(textos[1:] + [detalle])))


# ================================================================== pestañas
tab_entrega, tab_devolucion, tab_tablero, tab_publica, tab_como = st.tabs(
    ["Estación de entrega", "Estación de devolución", "Tablero", "Vista pública", "Cómo funciona"])

# ------------------------------------------------------------------ ENTREGA
with tab_entrega:
    st.html(ui.header("Estación de entrega", escape(sede), (storage.contar_hoy(con, sede), RACIONES_TURNO)))
    u = ss.get("ultimo")
    izq, der = st.columns([1.45, 1], gap="medium")

    with izq:
        with st.container(key="controles"):
            a, b = st.columns([1.5, 1])
            grado = a.selectbox("Grado del estudiante", list(GRADOS), format_func=GRADOS.get,
                                help="Se toma de la fila del grado o del código QR de la bandeja.")
            bandeja_id = b.text_input("Bandeja", value=f"B-{ss.contador:03d}", help="Código anónimo de la bandeja")
            fuente = "Cámara"
            if modo == "ia":
                fuente = st.segmented_control("Imagen", ["Cámara", "Subir foto"], default="Cámara", key="fuente") or "Cámara"
        imagen = None
        with st.container(key="camara"):
            if u:
                st.image(u["imagen"], width="stretch")
                st.html(ui.etiqueta_camara(f"Bandeja analizada · {NOMBRE_MOTOR.get(u['backend'], u['backend'])}"))
            elif modo == "demo":
                st.html(ui.panel_camara_vacio("Modo demostración", "La bandeja se simula al analizar; no se necesita cámara."))
            elif modo == "yolo":
                st.html(ui.panel_camara_vacio("Modelo propio en preparación", "Disponible en la fase 2 del proyecto."))
            elif fuente == "Cámara":
                cap = st.camera_input("Cámara cenital · capture la bandeja desde arriba")
                if cap:
                    imagen = Image.open(cap)
            elif fuente == "Subir foto":
                up = st.file_uploader("Foto cenital de la bandeja", type=["jpg", "jpeg", "png"])
                if up:
                    imagen = Image.open(up)
                    st.image(imagen, width="stretch")

        g_vista = u["grado"] if u else grado
        k1, k2, k3 = st.columns(3)
        k1.html(ui.info_card("Bandeja", u["bandeja"] if u else bandeja_id, "Código anónimo", mono=True))
        k2.html(ui.info_card("Grado", GRADO_CORTO[g_vista], f"Meta {KCAL_META[g_vista]} kcal"))
        k3.html(ui.info_card("Peso total estimado", f"{u['peso']:.0f} g" if u else "— g",
                             f"≈ {u['res'].nutrientes['kcal']:.0f} kcal" if u else "esperando bandeja"))
        nombres = [c.nombre for c in minuta.componentes]
        st.html(ui.info_card(f"Minuta del día · {fecha_larga(date.today())}", minuta.nombre,
                             " · ".join(nombres[3:]), grande=22))

    with der:
        ph = st.empty()
        if u:
            res = u["res"]
            sub, lineas = texto_veredicto(res, u["grado"])
            ph.html(ui.veredicto(res.semaforo, sub, lineas))
            if u.get("inicial"):
                st.html(ui.nota("Segundo análisis tras completar la ración",
                                f"El primer veredicto ({u['inicial'].semaforo}) queda registrado para el seguimiento "
                                "del cumplimiento a la primera.", "info"))
            st.html(ui.chips(chips_resultado(res)))
            if res.semaforo != "verde":
                b1, b2 = st.columns([1.25, 1])
                reanalizar = b1.button("Ración completada → reanalizar", key="reanalizar", width="stretch")
                registrar = b2.button("Registrar", key="registrar", width="stretch")
            else:
                reanalizar = False
                registrar = st.button("Registrar", key="registrar", width="stretch")
            if reanalizar:
                ss.correccion = dict(bandeja=u["bandeja"], res=u.get("inicial") or res)
                ss.ultimo = None
                st.rerun()
            if registrar:
                corregida = u.get("inicial") is not None and res.semaforo == "verde"
                storage.registrar_entrega(con, sede=sede, bandeja=u["bandeja"], grado=u["grado"], minuta=minuta.codigo,
                                          peso_g=u["peso"], resultado=res, backend=u["backend"],
                                          corregida=corregida, inicial=u.get("inicial"))
                msg = {"verde": "Ración registrada", "amarillo": "Registrada como incompleta", "rojo": "Rechazo registrado"}
                ss.flash = f"{'Ración corregida registrada' if corregida else msg[res.semaforo]} · {u['bandeja']}"
                ss.correccion = None
                ss.ultimo = None
                ss.contador += 1
                st.rerun()
        elif modo == "yolo":
            st.html(ui.fase2_yolo())
        elif not puede_analizar:
            ph.html(ui.veredicto_neutro("IA no disponible", "Use el modo Demostración desde la barra lateral.",
                                        etiqueta="Estación en pausa"))
        else:
            corr = ss.get("correccion")
            if corr and corr["bandeja"] == bandeja_id:
                ph.html(ui.veredicto_neutro("Complete la ración", "Agregue lo que faltaba, capture de nuevo y analice.",
                                            etiqueta="Corrección"))
            else:
                ph.html(ui.veredicto_neutro("Coloque la bandeja", "Presione Analizar para simular una bandeja servida."
                                            if modo == "demo" else "Capture la foto con la cámara cenital y presione Analizar."))
            if st.button("Analizar ración", key="analizar", width="stretch"):
                if modo == "ia" and imagen is None:
                    ph.html(ui.veredicto_neutro("Falta la foto", "Capture la bandeja con la cámara o suba una foto y vuelva a analizar.",
                                                etiqueta="Atención"))
                else:
                    ph.html(ui.veredicto_neutro("Leyendo bandeja…", "Mantenga la bandeja quieta bajo la cámara.",
                                                analizando=True, etiqueta="Analizando"))
                    try:
                        det = construir_detector()
                        dets = det.detectar(imagen, minuta, grado, None)
                        peso = round(sum(d.gramos for d in dets), 1)  # peso estimado por IA
                        res = verificar(dets, minuta, grado)
                        if imagen is None:
                            imagen = bandeja_sintetica(dets)
                        inicial = corr["res"] if corr and corr["bandeja"] == bandeja_id else None
                        ss.ultimo = dict(dets=dets, res=res, imagen=dibujar_overlay(imagen, dets, res.estados()),
                                         grado=grado, bandeja=bandeja_id, peso=peso, backend=det.nombre, inicial=inicial)
                        st.rerun()
                    except Exception as e:  # noqa: BLE001
                        ph.html(ui.veredicto_neutro("No se pudo analizar", mensaje_error(e), etiqueta="Atención"))

    if u:
        res = u["res"]
        st.html('<div style="height:8px"></div>')
        d1, d2, d3 = st.columns([1.3, 1, 1])
        d1.html(ui.barras_meta([dict(nombre=i.nombre, servido=i.servido_g, meta=i.meta_g, estado=i.estado) for i in res.items]))
        d2.html(ui.medidor_kcal(res.nutrientes["kcal"], res.kcal_meta))
        d3.html(ui.tabla_nutrientes([(nutriente_partes(k)[0], ui.num(v, 1), nutriente_partes(k)[1])
                                     for k, v in res.nutrientes.items() if k != "kcal"]))

# ------------------------------------------------------------------ DEVOLUCIÓN
with tab_devolucion:
    hdr = st.empty()
    izq, der = st.columns([1, 1.25], gap="medium")
    with izq:
        with st.container(key="controles_dev"):
            bandeja_dev = st.text_input("Código de bandeja", value=f"B-{max(1, ss.contador - 1):03d}", key="bdev")
            fuente_d = "Simular" if modo == "demo" else "Cámara"
            if modo == "ia":
                fuente_d = st.segmented_control("Imagen", ["Cámara", "Subir foto"], default="Cámara", key="fdev") or "Cámara"
        ent = storage.ultima_entrega_pendiente(con, bandeja_dev)
        mnt = MINUTAS[ent["minuta"]] if ent else None
        dv = ss.get("devolucion")
        dv = dv if dv and ent and dv["ent"]["id"] == ent["id"] else None

        imagen_d, sobr_frac = None, {}
        if not ent:
            st.html(ui.panel_camara_vacio("Sin entrega pendiente",
                                          f"No hay una entrega sin devolver para {bandeja_dev}. Registre primero la entrega."))
        else:
            with st.container(key="camara_dev"):
                if dv and dv["img"] is not None:
                    st.image(dv["img"], width="stretch")
                    st.html(ui.etiqueta_camara("Sobrante detectado", vivo=False))
                elif modo == "yolo":
                    st.html(ui.panel_camara_vacio("Modelo propio en preparación", "Disponible en la fase 2 del proyecto."))
                elif fuente_d == "Cámara":
                    cap = st.camera_input("Cámara cenital · bandeja devuelta", key="camdev")
                    if cap:
                        imagen_d = Image.open(cap)
                elif fuente_d == "Subir foto":
                    up = st.file_uploader("Foto de la bandeja devuelta", type=["jpg", "jpeg", "png"], key="updev")
                    if up:
                        imagen_d = Image.open(up)
                        st.image(imagen_d, width="stretch")
                else:
                    st.html(ui.panel_camara_vacio("Modo demostración", "Ajuste abajo cuánto quedó de cada alimento."))
            if fuente_d == "Simular" and not dv:
                with st.container(border=True):
                    st.markdown("**¿Cuánto quedó en el plato?**")
                    st.caption("Porcentaje sobrante de cada alimento (modo demostración).")
                    for comp in mnt.componentes:
                        base = {"verdura": 45, "tuberculo": 20, "cereal": 15, "fruta": 10, "proteina": 8, "bebida": 5}[comp.grupo]
                        sobr_frac[comp.alimento] = st.slider(comp.nombre, 0, 100, base, key=f"s_{comp.alimento}") / 100
            if dv:
                c1, c2 = st.columns(2)
                c1.html(ui.tarjeta_dato("Energía que comiste", f"{dv['nutr']['kcal']:.0f}", f"de {KCAL_META[ent['grado']]} kcal"))
                prot_serv = sumar(dv["servido"]).get("proteina_g", 0)
                c2.html(ui.tarjeta_dato("Proteína", ui.num(dv["nutr"].get("proteina_g", 0), 1), f"de {ui.num(prot_serv, 1)} g"))

    derecha = (f'Bandeja <span class="np-mono" style="font-weight:600;color:{ui.INK}">{escape(bandeja_dev)}</span>'
               + (f" · {GRADO_CORTO[ent['grado']]}" if ent else ""))
    hdr.html(ui.header("Estación de devolución", derecha))

    with der:
        if not ent:
            st.html(ui.veredicto_neutro("Esperando bandeja", "Escriba el código de una bandeja ya entregada."))
        elif modo == "yolo" and not dv:
            st.html(ui.fase2_yolo())
        elif not puede_analizar and not dv:
            st.html(ui.veredicto_neutro("IA no disponible", "Use el modo Demostración desde la barra lateral.",
                                        etiqueta="Estación en pausa"))
        elif dv:
            tot_s, tot_c = sum(dv["servido"].values()), sum(dv["cons"].values())
            pct = 100 * tot_c / tot_s if tot_s else 0
            por_alim = []
            for a_, g in dv["servido"].items():
                comp = next((c for c in dv["mnt"].componentes if c.alimento == a_), None)
                nombre = comp.nombre if comp else (TABLA[a_].nombre if a_ in TABLA else a_)
                por_alim.append((nombre, 100 * dv["cons"].get(a_, 0) / g if g else 0, comp.grupo if comp else "otro"))
            enteros = [n for n, p, _ in por_alim if p >= 99]
            peor = min(por_alim, key=lambda x: x[1]) if por_alim else None
            partes = []
            if enteros:
                partes.append(f"¡Te terminaste todo: {enteros[0].lower()}!")
            if peor and peor[1] < 60:
                partes.append(f"{peor[0]} {BENEFICIO.get(peor[2], 'te hace bien')}: mañana intenta un bocado más.")
            mensaje = " ".join(partes) or "¡Muy bien! Comiste de todos los grupos."
            st.html(ui.panel_consumo(pct, f"Hoy comiste el {pct:.0f} % de tu almuerzo{' 💪' if pct >= 75 else ''}", mensaje))
            st.html(ui.barras_consumo([(n, p) for n, p, _ in por_alim]))
            p1, p2 = st.columns([1, 1.1])
            p1.html(f'<div class="np" style="font-size:18px;color:{ui.INK2};padding-top:24px">'
                    f'Desperdicio: {tot_s - tot_c:.0f} g · No se guardan fotos de personas.</div>')
            if p2.button("¡Listo, gracias!", key="listo", width="stretch"):
                storage.registrar_devolucion(con, entrega_id=ent["id"], bandeja=bandeja_dev, peso_g=sum(dv["sobrante"].values()),
                                             sobrante=dv["sobrante"], consumido=dv["cons"], nutrientes=dv["nutr"])
                ss.devolucion = None
                ss.flash = f"Devolución registrada · {bandeja_dev}"
                st.rerun()
        else:
            ph_d = st.empty()
            ph_d.html(ui.veredicto_neutro("Coloque la bandeja devuelta",
                                          f"{mnt.nombre} · {GRADOS[ent['grado']]}. Mediremos lo que quedó en el plato."))
            if st.button("Analizar sobrante", key="analizar_dev", width="stretch"):
                servido = ent["porciones"]
                sobrante, img_d = None, None
                if fuente_d == "Simular":
                    sobrante = {a_: round(g * sobr_frac.get(a_, 0), 1) for a_, g in servido.items()}
                elif imagen_d is None:
                    ph_d.html(ui.veredicto_neutro("Falta la foto", "Capture la bandeja devuelta o suba una foto y vuelva a analizar.",
                                                  etiqueta="Atención"))
                else:
                    ph_d.html(ui.veredicto_neutro("Midiendo sobrante…", "Mantenga la bandeja quieta bajo la cámara.",
                                                  analizando=True, etiqueta="Analizando"))
                    try:
                        det = construir_detector("devolucion")
                        dets = det.detectar(imagen_d, mnt, ent["grado"], None)
                        sobrante = {d.alimento: d.gramos for d in dets}
                        img_d = dibujar_overlay(imagen_d, dets, estado_fijo="sobrante")
                    except Exception as e:  # noqa: BLE001
                        ph_d.html(ui.veredicto_neutro("No se pudo analizar", mensaje_error(e), etiqueta="Atención"))
                if sobrante is not None:
                    cons = consumo(servido, sobrante)
                    ss.devolucion = dict(servido=servido, sobrante=sobrante, cons=cons, nutr=sumar(cons), img=img_d, ent=ent, mnt=mnt)
                    st.rerun()

# ------------------------------------------------------------------ TABLERO
with tab_tablero:
    ent_df = storage.cargar_entregas(con)
    dev_df = storage.cargar_devoluciones(con)
    rango = (f" · periodo {ent_df.fecha.min():%d/%m} – {ent_df.fecha.max():%d/%m/%Y}" if not ent_df.empty else "")
    st.html(ui.titulo_pagina(f"{fecha_larga(date.today())} · actualizado {ui.hora()}{rango}", "Seguimiento del PAE",
                             "Cada comida, todos los días: raciones verificadas en las sedes del piloto."))

    if ent_df.empty:
        st.html(ui.estado_vacio("Aún no hay raciones registradas",
                                "Cuando la estación de entrega registre bandejas, aquí verá el cumplimiento, las alertas y el "
                                "desperdicio. Para una demostración, cargue datos de ejemplo en Administración (barra lateral)."))
    else:
        with st.container(key="filtros"):
            f1, f2 = st.columns([1, 1.3], vertical_alignment="bottom")
            sedes_datos = sorted(ent_df.sede.unique())
            sede_sel = f1.selectbox("Sede", ["Todas"] + sedes_datos,
                                    format_func=lambda s: f"Todas las sedes ({len(sedes_datos)})" if s == "Todas" else s)
            grado_sel = f2.segmented_control("Grado", ["Todos", "Preescolar", "Primaria", "Secundaria"], default="Todos") or "Todos"
        tablero(ent_df, dev_df, sede_sel, grado_sel)

# ------------------------------------------------------------------ VISTA PÚBLICA
with tab_publica:
    ent_df = storage.cargar_entregas(con)
    _, centro, _ = st.columns([1, 1.3, 1])
    with centro:
        if ent_df.empty:
            st.html(ui.estado_vacio("Consulta pública", "Aquí rectores, familias y veedurías verán el cumplimiento semanal "
                                    "de cada sede en cuanto haya raciones registradas."))
        else:
            sedes_pub = sorted(ent_df.sede.unique())
            sede_pub = st.selectbox("Consultar sede", sedes_pub, index=sedes_pub.index(sede) if sede in sedes_pub else 0)
            hoy = date.today()
            lunes = hoy - timedelta(days=hoy.weekday())
            semana_dias = [lunes + timedelta(days=i) for i in range(5)]
            e = ent_df[(ent_df.sede == sede_pub) & (ent_df.fecha >= lunes)]
            if e.empty:  # sin datos esta semana: muestra la última semana con registros
                ultima = ent_df[ent_df.sede == sede_pub].fecha.max()
                lunes = ultima - timedelta(days=ultima.weekday())
                semana_dias = [lunes + timedelta(days=i) for i in range(5)]
                e = ent_df[(ent_df.sede == sede_pub) & (ent_df.fecha >= lunes) & (ent_df.fecha <= lunes + timedelta(days=6))]
            dias_pub, menu = [], []
            for dia in semana_dias:
                ed = e[e.fecha == dia]
                dias_pub.append(dict(d=DIAS_SEMANA[dia.weekday()], pct=100 * ed.aprobada.mean() if len(ed) else None))
                if len(ed):
                    menu.append((DIAS_SEMANA[dia.weekday()], MINUTAS[ed.minuta.mode()[0]].nombre))
            dev_df = storage.cargar_devoluciones(con)
            dsem = dev_df[dev_df.entrega_id.isin(e.id)] if not dev_df.empty else dev_df
            serv = e[e.id.isin(dsem.entrega_id)].porciones.apply(lambda p: sum(p.values())).sum() if not dsem.empty else 0
            cons_pct = 100 * dsem.consumido.apply(lambda c: sum(c.values())).sum() / serv if serv else 0
            rojas_pub = e[e.semaforo == "rojo"]
            n_noapto = int(rojas_pub.alertas.apply(lambda al: any("NO APTO" in x for x in al)).sum())
            viernes = semana_dias[-1]
            semana = (f"Semana del {lunes.day} al {viernes.day} de {MESES[viernes.month - 1]} de {viernes.year}")
            st.html(ui.vista_publica(sede_pub, semana, 100 * e.aprobada.mean() if len(e) else 0, META_PUBLICA,
                                     int(e.aprobada.sum()), len(e), dias_pub, cons_pct, len(rojas_pub),
                                     f"{len(rojas_pub) - n_noapto} faltas · {n_noapto} no apto", menu))

# ------------------------------------------------------------------ CÓMO FUNCIONA
with tab_como:
    st.html(ui.como_funciona())
    st.html(ui.tecnologia())
    filas = [(c.nombre, [meta_gramos(g, minuta)[c.alimento] for g in GRADOS]) for c in minuta.componentes]
    st.html(ui.tabla_metas([GRADO_CORTO[g] for g in GRADOS], filas))
