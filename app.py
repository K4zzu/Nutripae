"""NutriPAE — Verificación nutricional con IA para comedores escolares (Neiva).

Ejecutar:  streamlit run app.py
"""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image
from dotenv import load_dotenv

load_dotenv()  # lee .env (ANTHROPIC_API_KEY / GEMINI_API_KEY, NUTRIPAE_SEDE, etc.)

from nutripae import storage, simulate
from nutripae.detector import (DemoDetector, VisionLLMDetector, YoloDetector,
                               dibujar_overlay, bandeja_sintetica)
from nutripae.menu import MINUTAS, GRADOS, KCAL_META, GRUPO_LABEL, meta_gramos
from nutripae.nutrition import TABLA, sumar, NUTRIENTE_LABEL
from nutripae.verifier import verificar, consumo

st.set_page_config(page_title="NutriPAE · Verificación nutricional con IA", page_icon="🍽️",
                   layout="wide", initial_sidebar_state="expanded")

# ------------------------------------------------------------------ estilos
st.markdown("""
<style>
.semaforo {border-radius: 18px; padding: 28px; text-align: center; color: white; font-weight: 800;
           font-size: 2.1rem; letter-spacing: .5px; box-shadow: 0 8px 24px rgba(0,0,0,.18);}
.verde    {background: linear-gradient(135deg,#1f9d55,#2ecc71);}
.amarillo {background: linear-gradient(135deg,#d68910,#f4b942); color:#2b2b2b;}
.rojo     {background: linear-gradient(135deg,#b03a2e,#e74c3c);}
.kpi {background: var(--secondary-background-color); border-radius: 14px; padding: 14px 18px; margin-bottom: 8px;}
.kpi .v {font-size: 1.9rem; font-weight: 800;} .kpi .l {opacity:.75; font-size:.85rem;}
.item {padding:8px 12px; border-radius:10px; margin-bottom:6px; font-size:.95rem;}
.item.ok {background:#e8f7ee;} .item.bajo,.item.alto {background:#fff4d6;} .item.falta,.item.no_apto {background:#fde3e1;}
h1,h2,h3 {letter-spacing:-.3px}
</style>
""", unsafe_allow_html=True)

SEMAFORO_TXT = {"verde": "✅ RACIÓN COMPLETA", "amarillo": "⚠️ COMPLETAR PORCIÓN", "rojo": "⛔ RACIÓN RECHAZADA"}
ESTADO_ICONO = {"ok": "✅", "bajo": "⚠️", "alto": "➕", "falta": "❌", "no_apto": "⛔"}

con = storage.conectar()
ss = st.session_state
ss.setdefault("contador", 1)
ss.setdefault("ultima_entrega", None)


# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.title("🍽️ NutriPAE")
    st.caption("Verificación nutricional con IA · PAE Neiva")
    sede = st.selectbox("Sede educativa", simulate.SEDES)
    minuta_cod = st.selectbox("Minuta del día", list(MINUTAS), format_func=lambda k: f"{k} · {MINUTAS[k].nombre}")
    minuta = MINUTAS[minuta_cod]
    st.divider()
    st.subheader("Motor de IA")
    _hay_key = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY"))
    backend = st.radio("Backend de visión", ["Visión LLM (Claude / Gemini)", "Demo (simulado)", "YOLO local"],
                       index=0 if _hay_key else 1,
                       help="Visión LLM analiza fotos reales con un modelo multimodal. Demo no requiere cámara ni API.")
    escenario = "aleatorio"
    proveedor = "anthropic"
    api_key = None
    if backend.startswith("Demo"):
        escenario = st.selectbox("Escenario de demo", ["aleatorio", "completa", "incompleta", "no_apto"])
    elif backend.startswith("Visión"):
        proveedor = st.selectbox("Proveedor", ["anthropic", "gemini"],
                                 index=0 if os.getenv("ANTHROPIC_API_KEY") or not os.getenv("GEMINI_API_KEY") else 1)
        env_key = os.getenv("ANTHROPIC_API_KEY" if proveedor == "anthropic" else "GEMINI_API_KEY", "")
        if env_key:
            st.success("API key cargada desde .env", icon="🔑")
            api_key = env_key
        else:
            api_key = st.text_input("API key", type="password")
        if not api_key:
            st.warning("Sin API key el análisis fallará. Usa Demo o configura .env.")
    st.divider()
    st.caption("🔒 La cámara solo capta la bandeja. No se registran rostros ni datos personales; "
               "la bandeja se identifica con un código anónimo.")


def construir_detector(modo: str = "entrega"):
    if backend.startswith("Demo"):
        return DemoDetector(escenario)
    if backend.startswith("Visión"):
        return VisionLLMDetector(proveedor=proveedor, api_key=api_key or None, modo=modo)
    return YoloDetector()


def tarjeta_semaforo(res):
    st.markdown(f'<div class="semaforo {res.semaforo}">{SEMAFORO_TXT[res.semaforo]}</div>', unsafe_allow_html=True)


def lista_items(res):
    for it in res.items:
        st.markdown(f'<div class="item {it.estado}">{ESTADO_ICONO[it.estado]} <b>{it.nombre}</b> '
                    f'<span style="opacity:.7">({GRUPO_LABEL[it.grupo]})</span> — {it.mensaje}</div>', unsafe_allow_html=True)


def grafico_porciones(res):
    df = pd.DataFrame([{"Alimento": i.nombre, "Servido (g)": i.servido_g, "Meta (g)": i.meta_g} for i in res.items])
    fig = go.Figure()
    fig.add_bar(name="Meta", x=df["Alimento"], y=df["Meta (g)"], marker_color="#c9ccd1")
    fig.add_bar(name="Servido", x=df["Alimento"], y=df["Servido (g)"],
                marker_color=[{"ok": "#2ecc71", "bajo": "#f4b942", "alto": "#5dade2", "falta": "#e74c3c", "no_apto": "#8e44ad"}[i.estado] for i in res.items])
    fig.update_layout(barmode="group", height=280, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")


def medidor_kcal(kcal, meta, titulo="Energía servida"):
    fig = go.Figure(go.Indicator(mode="gauge+number", value=kcal, title={"text": f"{titulo} (meta {meta:.0f} kcal)"},
                                 gauge={"axis": {"range": [0, meta * 1.4]},
                                        "bar": {"color": "#1f77b4"},
                                        "steps": [{"range": [0, meta * 0.8], "color": "#fde3e1"},
                                                  {"range": [meta * 0.8, meta * 1.2], "color": "#e8f7ee"},
                                                  {"range": [meta * 1.2, meta * 1.4], "color": "#fff4d6"}]}))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=50, b=10))
    st.plotly_chart(fig, width="stretch")


# ================================================================== pestañas
st.title("🍽️ NutriPAE — Verificación nutricional con IA")
st.caption("Cada ración, cada día: completa, balanceada y en buen estado. Prototipo para el PAE de Neiva.")

tab_entrega, tab_devolucion, tab_tablero, tab_como = st.tabs(
    ["🟢 Estación de entrega", "🔄 Estación de devolución", "📊 Tablero de seguimiento", "ℹ️ Cómo funciona"])

# ------------------------------------------------------------------ ENTREGA
with tab_entrega:
    c1, c2 = st.columns([1, 1.15])
    with c1:
        st.subheader("1 · Bandeja en la estación")
        grado = st.selectbox("Grado del estudiante", list(GRADOS), format_func=GRADOS.get,
                             help="En producción se lee del carné/QR de la bandeja o de la fila por grado.")
        bandeja_id = st.text_input("Código de bandeja (anónimo)", value=f"B-{ss.contador:03d}")
        fuente = st.radio("Imagen", ["Bandeja sintética (demo)", "Cámara", "Subir foto"], horizontal=True)
        imagen = None
        if fuente == "Cámara":
            cap = st.camera_input("Capturar bandeja")
            if cap:
                imagen = Image.open(cap)
        elif fuente == "Subir foto":
            up = st.file_uploader("Foto de la bandeja", type=["jpg", "jpeg", "png"])
            if up:
                imagen = Image.open(up)
        analizar = st.button("🔍 Analizar ración", type="primary", width="stretch")

    with c2:
        st.subheader("2 · Veredicto de la IA")
        if analizar:
            try:
                det = construir_detector()
                with st.spinner("Analizando bandeja…"):
                    dets = det.detectar(imagen, minuta, grado, None)
                    peso = round(sum(d.gramos for d in dets), 1)  # peso estimado por IA
                    res = verificar(dets, minuta, grado)
                if imagen is None:
                    imagen = bandeja_sintetica(dets)
                ss.ultimo = dict(dets=dets, res=res, imagen=dibujar_overlay(imagen, dets, res.estados()),
                                 grado=grado, bandeja=bandeja_id, peso=peso, backend=det.nombre)
            except Exception as e:  # noqa: BLE001
                st.error(f"No se pudo analizar: {e}")
        if ss.get("ultimo"):
            u = ss.ultimo
            res = u["res"]
            tarjeta_semaforo(res)
            st.image(u["imagen"], caption=f"Bandeja {u['bandeja']} · peso estimado por IA: {u['peso']:.0f} g · motor: {u['backend']}", width="stretch")
            lista_items(res)
            colA, colB = st.columns(2)
            with colA:
                if st.button("💾 Registrar entrega", width="stretch", disabled=u.get("guardada", False)):
                    eid = storage.registrar_entrega(con, sede=sede, bandeja=u["bandeja"], grado=u["grado"], minuta=minuta.codigo,
                                                    peso_g=u["peso"], resultado=res, backend=u["backend"])
                    u["guardada"] = True
                    ss.contador += 1
                    st.success(f"Entrega #{eid} registrada. Bandeja {u['bandeja']} lista para devolución.")
            with colB:
                if res.semaforo != "verde" and st.button("🔁 Ración completada → re-analizar", width="stretch"):
                    ss.ultimo = None
                    st.rerun()

    if ss.get("ultimo"):
        st.divider()
        res = ss.ultimo["res"]
        g1, g2 = st.columns([1.3, 1])
        with g1:
            st.markdown("**Porción servida vs. meta por grado**")
            grafico_porciones(res)
        with g2:
            medidor_kcal(res.nutrientes["kcal"], res.kcal_meta)
        n = res.nutrientes
        cols = st.columns(len(n))
        for col, (k, v) in zip(cols, n.items()):
            col.metric(NUTRIENTE_LABEL[k], f"{v:g}")

# ------------------------------------------------------------------ DEVOLUCIÓN
with tab_devolucion:
    c1, c2 = st.columns([1, 1.15])
    with c1:
        st.subheader("1 · Bandeja devuelta")
        bandeja_dev = st.text_input("Código de bandeja", value=f"B-{max(1, ss.contador - 1):03d}", key="bdev")
        ent = storage.ultima_entrega_pendiente(con, bandeja_dev)
        if not ent:
            st.info("No hay una entrega pendiente para esa bandeja. Registra primero la entrega.")
        else:
            mnt = MINUTAS[ent["minuta"]]
            st.success(f"Entrega #{ent['id']} · {mnt.nombre} · {GRADOS[ent['grado']]}")
            fuente_d = st.radio("Imagen", ["Simular sobrante (demo)", "Cámara", "Subir foto"], horizontal=True, key="fdev")
            imagen_d = None
            if fuente_d == "Cámara":
                cap = st.camera_input("Capturar bandeja devuelta", key="camdev")
                if cap:
                    imagen_d = Image.open(cap)
            elif fuente_d == "Subir foto":
                up = st.file_uploader("Foto de la bandeja devuelta", type=["jpg", "jpeg", "png"], key="updev")
                if up:
                    imagen_d = Image.open(up)
            st.markdown("**Fracción que quedó en el plato** (modo demo)")
            sobr_frac = {}
            if fuente_d.startswith("Simular"):
                for comp in mnt.componentes:
                    base = {"verdura": 45, "tuberculo": 20, "cereal": 15, "fruta": 10, "proteina": 8, "bebida": 5}[comp.grupo]
                    sobr_frac[comp.alimento] = st.slider(comp.nombre, 0, 100, base, key=f"s_{comp.alimento}") / 100
            analizar_d = st.button("🔍 Analizar sobrante", type="primary", width="stretch")

    with c2:
        st.subheader("2 · Consumo real")
        if ent and analizar_d:
            servido = ent["porciones"]
            if fuente_d.startswith("Simular"):
                sobrante = {a: round(g * sobr_frac.get(a, 0), 1) for a, g in servido.items()}
                img_d = None
            else:
                try:
                    det = construir_detector("devolucion")
                    with st.spinner("Analizando sobrante…"):
                        dets = det.detectar(imagen_d, mnt, ent["grado"], None)
                    sobrante = {d.alimento: d.gramos for d in dets}
                    img_d = dibujar_overlay(imagen_d, dets) if imagen_d else None
                except Exception as e:  # noqa: BLE001
                    st.error(f"No se pudo analizar: {e}")
                    sobrante = None
            if sobrante is not None:
                cons = consumo(servido, sobrante)
                ss.devolucion = dict(servido=servido, sobrante=sobrante, cons=cons, nutr=sumar(cons), img=img_d, ent=ent, mnt=mnt)
        if ss.get("devolucion") and ent and ss.devolucion["ent"]["id"] == ent["id"]:
            dv = ss.devolucion
            tot_s, tot_c = sum(dv["servido"].values()), sum(dv["cons"].values())
            pct = 100 * tot_c / tot_s if tot_s else 0
            k1, k2, k3 = st.columns(3)
            k1.metric("Consumido", f"{tot_c:.0f} g", f"{pct:.0f} % de lo servido")
            k2.metric("Desperdicio", f"{tot_s - tot_c:.0f} g")
            k3.metric("Energía consumida", f"{dv['nutr']['kcal']:.0f} kcal",
                      f"{100 * dv['nutr']['kcal'] / KCAL_META[ent['grado']]:.0f} % de la meta")
            if dv["img"] is not None:
                st.image(dv["img"], width="stretch")
            df = pd.DataFrame({"Alimento": [TABLA[a].nombre if a in TABLA else a for a in dv["servido"]],
                               "Consumido": list(dv["cons"].values()),
                               "Sobrante": [dv["sobrante"].get(a, 0) for a in dv["servido"]]})
            fig = px.bar(df, x="Alimento", y=["Consumido", "Sobrante"], barmode="stack",
                         color_discrete_map={"Consumido": "#2ecc71", "Sobrante": "#e74c3c"})
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="g", legend_title="")
            st.plotly_chart(fig, width="stretch")
            if st.button("💾 Registrar devolución", width="stretch"):
                storage.registrar_devolucion(con, entrega_id=ent["id"], bandeja=bandeja_dev, peso_g=sum(dv["sobrante"].values()),
                                             sobrante=dv["sobrante"], consumido=dv["cons"], nutrientes=dv["nutr"])
                ss.devolucion = None
                st.success("Devolución registrada. Consumo real y nutrientes guardados.")
                st.rerun()

# ------------------------------------------------------------------ TABLERO
with tab_tablero:
    ent_df = storage.cargar_entregas(con)
    dev_df = storage.cargar_devoluciones(con)
    top = st.columns([3, 1, 1])
    top[0].subheader("Seguimiento del programa — cada comida, todos los días")
    if top[1].button("🧪 Generar datos de prueba (10 días)", width="stretch"):
        with st.spinner("Simulando raciones…"):
            simulate.generar(con, dias=10, raciones_por_dia=60)
        st.rerun()
    if top[2].button("🗑️ Vaciar registros", width="stretch"):
        storage.vaciar(con)
        st.rerun()

    if ent_df.empty:
        st.info("Aún no hay registros. Registra entregas o genera datos de prueba.")
    else:
        f1, f2 = st.columns(2)
        sedes_sel = f1.multiselect("Sedes", simulate.SEDES, default=simulate.SEDES)
        grados_sel = f2.multiselect("Grados", list(GRADOS), default=list(GRADOS), format_func=GRADOS.get)
        e = ent_df[ent_df.sede.isin(sedes_sel) & ent_df.grado.isin(grados_sel)]
        d = dev_df[dev_df.entrega_id.isin(e.id)] if not dev_df.empty else dev_df

        total = len(e)
        completas = int(e.aprobada.sum())
        rechazadas = int((e.semaforo == "rojo").sum())
        no_aptos = int(e.alertas.apply(lambda a: any("NO APTO" in x for x in a)).sum())
        kcal_serv = e.kcal.mean()
        kcal_cons = d.kcal_consumidas.mean() if not d.empty else 0
        desperdicio = (d.sobrante.apply(lambda s: sum(s.values())).sum() / 1000) if not d.empty else 0
        k = st.columns(6)
        for col, (l, v) in zip(k, [("Raciones verificadas", f"{total:,}"),
                                   ("Completas a la primera", f"{100 * completas / total:.0f} %"),
                                   ("Alertas rojas", f"{rechazadas:,}"),
                                   ("Alimentos no aptos", f"{no_aptos:,}"),
                                   ("kcal servidas / consumidas", f"{kcal_serv:.0f} / {kcal_cons:.0f}"),
                                   ("Desperdicio acumulado", f"{desperdicio:.1f} kg")]):
            col.markdown(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)

        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**Cumplimiento diario de raciones**")
            diario = e.groupby(["fecha", "semaforo"]).size().reset_index(name="n")
            fig = px.bar(diario, x="fecha", y="n", color="semaforo", barmode="stack",
                         color_discrete_map={"verde": "#2ecc71", "amarillo": "#f4b942", "rojo": "#e74c3c"},
                         category_orders={"semaforo": ["verde", "amarillo", "rojo"]})
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), legend_title="", yaxis_title="raciones")
            st.plotly_chart(fig, width="stretch")
        with g2:
            st.markdown("**Energía servida vs. consumida por grado (kcal, promedio)**")
            if not d.empty:
                m = e.merge(d[["entrega_id", "kcal_consumidas"]], left_on="id", right_on="entrega_id")
                por_grado = m.groupby("grado").agg(servida=("kcal", "mean"), consumida=("kcal_consumidas", "mean")).reset_index()
                por_grado["meta"] = por_grado.grado.map(KCAL_META)
                por_grado["grado"] = por_grado.grado.map(GRADOS)
                fig = px.bar(por_grado, x="grado", y=["meta", "servida", "consumida"], barmode="group",
                             color_discrete_map={"meta": "#c9ccd1", "servida": "#5dade2", "consumida": "#2ecc71"})
                fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), legend_title="", xaxis_title="", yaxis_title="kcal")
                st.plotly_chart(fig, width="stretch")

        g3, g4 = st.columns(2)
        with g3:
            st.markdown("**¿Qué dejan en el plato?** (% sobrante por alimento)")
            if not d.empty:
                m = e.merge(d[["entrega_id", "sobrante"]], left_on="id", right_on="entrega_id")
                filas = []
                for _, r in m.iterrows():
                    for a, g in r.porciones.items():
                        filas.append({"alimento": TABLA[a].nombre if a in TABLA else a, "grupo": TABLA[a].grupo if a in TABLA else "otro",
                                      "servido": g, "sobrante": r.sobrante.get(a, 0)})
                s = pd.DataFrame(filas).groupby(["alimento", "grupo"]).sum().reset_index()
                s["% sobrante"] = 100 * s.sobrante / s.servido
                s = s.sort_values("% sobrante", ascending=True)
                fig = px.bar(s, y="alimento", x="% sobrante", color="grupo", orientation="h")
                fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="", legend_title="")
                st.plotly_chart(fig, width="stretch")
        with g4:
            st.markdown("**Alertas por sede**")
            al = e[e.semaforo != "verde"].groupby(["sede", "semaforo"]).size().reset_index(name="n")
            if al.empty:
                st.success("Sin alertas en el periodo.")
            else:
                fig = px.bar(al, y="sede", x="n", color="semaforo", orientation="h",
                             color_discrete_map={"amarillo": "#f4b942", "rojo": "#e74c3c"})
                fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="", legend_title="", xaxis_title="alertas")
                st.plotly_chart(fig, width="stretch")

        st.markdown("**Nutrientes promedio por ración (servido vs. consumido)**")
        if not d.empty:
            ns = pd.DataFrame(list(e.nutrientes)).mean().round(1)
            nc = pd.DataFrame(list(d.nutrientes)).mean().round(1)
            tabla = pd.DataFrame({"Nutriente": [NUTRIENTE_LABEL[k] for k in ns.index], "Servido": ns.values, "Consumido": nc.reindex(ns.index).values})
            tabla["% consumido"] = (100 * tabla.Consumido / tabla.Servido).round(0)
            st.dataframe(tabla, hide_index=True, width="stretch")

        with st.expander("📋 Registro detallado de entregas"):
            vista = e[["ts", "sede", "bandeja", "grado", "minuta", "peso_g", "semaforo", "corregida", "kcal", "alertas"]].copy().rename(columns={"peso_g": "peso_estimado_g"})
            vista["alertas"] = vista.alertas.apply(lambda a: " | ".join(a))
            vista["grado"] = vista.grado.map(GRADOS)
            st.dataframe(vista.sort_values("ts", ascending=False), hide_index=True, width="stretch")
            st.download_button("⬇️ Exportar CSV", vista.to_csv(index=False).encode("utf-8"),
                               file_name=f"nutripae_entregas_{datetime.now():%Y%m%d}.csv", mime="text/csv")

# ------------------------------------------------------------------ CÓMO FUNCIONA
with tab_como:
    st.subheader("Flujo del sistema")
    st.markdown("""
```
   ESTACIÓN DE ENTREGA                                    ESTACIÓN DE DEVOLUCIÓN
   ┌──────────────┐      foto       ┌──────────────┐      ┌──────────────┐      foto
   │ Cámara       │ ──────────────▶ │ IA de visión │      │ Cámara       │ ──────────────▶ IA de visión
   │ Pantalla+LED │                 │ (reconoce,   │      │ Pantalla     │                 (detecta sobrante)
   └──────────────┘ ◀────────────── │  mide y pesa │      └──────────────┘                        │
                      🟢 / 🟡 / 🔴  │  cada uno)   │                                              ▼
                                    └──────┬───────┘                                   consumo = servido − sobrante
                                           ▼                                                      │
                                   verificación:                                                  ▼
                                   grupos ✔ porción ✔ aptitud ✔                        nutrientes reales ingeridos
                                           │                                                      │
                                           └────────────────▶  base de datos  ◀───────────────────┘
                                                                     │
                                                                     ▼
                                                 📊 Tablero: operador PAE · Secretaría de Educación · veedurías
```
""")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**🧠 IA**\n\n- Reconocimiento de alimentos y estimación de porción (modelo multimodal hoy, YOLO fine-tuned en producción).\n- Detección de mal aspecto (color, textura, cuerpos extraños).\n- Sin báscula: la IA estima los gramos a partir del área y la altura visible de cada porción, usando la bandeja (dimensiones conocidas) como referencia de escala y la densidad típica de cada alimento.")
    c2.markdown("**⚖️ Reglas**\n\n- Todos los grupos de la minuta presentes.\n- Porción dentro de ±20 % de la meta por grado.\n- Cualquier alimento no apto → ración rechazada.\n- Nutrientes con la Tabla de Composición de Alimentos Colombianos (ICBF).")
    c3.markdown("**🔒 Privacidad**\n\n- La cámara enfoca únicamente la bandeja (cenital).\n- No hay reconocimiento facial ni datos personales.\n- Identificación anónima por código de bandeja y grado.\n- Datos agregados para el tablero institucional.")
    st.markdown("**Metas de porción por grado (g)** — referencia parametrizable según la minuta patrón del PAE")
    mt = pd.DataFrame({GRADOS[g]: meta_gramos(g, minuta) for g in GRADOS})
    mt.index = [next(c.nombre for c in minuta.componentes if c.alimento == a) for a in mt.index]
    st.dataframe(mt, width="stretch")
