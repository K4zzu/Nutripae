# 🍽️ NutriPAE — Verificación nutricional con IA para el PAE de Neiva

Sistema que revisa **cada ración, cada día** en los comedores escolares con solo una cámara: al entregar la bandeja
verifica que esté completa, con la porción del grado y en buen estado; al devolverla mide qué se
consumió realmente y calcula los nutrientes ingeridos. Todo sin captar rostros ni datos personales.

Prototipo para el **Neiva Fest · Reto Innova 2026** (Convocatoria Pública No. 001 de 2026).

## Ejecutar en local (venv)

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt anthropic
cp .env.example .env             # pega tu ANTHROPIC_API_KEY (o GEMINI_API_KEY)
streamlit run app.py
```

Se abre en el navegador (`http://localhost:8501`). Sin cámara ni API funciona en **modo demo**:
1. Pestaña **Estación de entrega** → *Analizar ración* → aparece el semáforo 🟢/🟡/🔴 con la bandeja anotada.
2. *Registrar entrega* → pestaña **Estación de devolución** → *Analizar sobrante* → consumo real y nutrientes.
3. Pestaña **Tablero** → *Generar datos de prueba (10 días)* → KPIs, gráficos y exportación CSV.

En la barra lateral se cambia el **escenario de demo** (`completa`, `incompleta`, `no_apto`) para mostrar cada caso en vivo.

## Usar IA real sobre fotos de bandejas

En la barra lateral elige **Visión LLM** y pega una API key (o define `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`):

```bash
pip install anthropic            # o: pip install google-genai
```

Luego toma la foto con la cámara del portátil (`Cámara`) o sube una imagen. El modelo devuelve los alimentos
reconocidos, los gramos estimados (sin báscula: usa la bandeja de tamaño conocido como referencia de escala, la altura visible y la densidad típica de cada alimento), cuadros y si algo tiene mal aspecto.

Para producción (sin internet, en un mini-PC o Raspberry Pi/Jetson): `pip install ultralytics` y poner el modelo
fine-tuned en `modelos/nutripae_yolo.pt` (ver `nutripae/detector.py::YoloDetector`).

## Desplegar en AWS Lightsail (plan 12 USD, Ubuntu)

```bash
# en la instancia
git clone <tu-repo> /home/ubuntu/nutripae && cd /home/ubuntu/nutripae
chmod +x deploy/setup_lightsail.sh
sudo deploy/setup_lightsail.sh TU_IP_O_DOMINIO
nano .env                        # API key
sudo systemctl restart nutripae
```
Abre el puerto 80 (y 443) en el firewall de Lightsail. El script crea el venv, el servicio `nutripae` (systemd)
y el proxy Nginx con WebSockets. Para HTTPS con dominio: `sudo certbot --nginx -d tu-dominio`.
La cámara del navegador (`st.camera_input`) solo funciona bajo HTTPS o en `localhost`; con IP sin certificado, usa "Subir foto".

## Estructura

```
app.py                  interfaz Streamlit (3 estaciones: entrega, devolución, tablero)
nutripae/menu.py        minutas PAE, grupos de alimentos, metas de porción por grado, metas kcal
nutripae/nutrition.py   tabla de composición (ICBF/TCAC, por 100 g) y cálculo de nutrientes
nutripae/detector.py    backends de visión: Demo · Visión LLM (Claude/Gemini) · YOLO; overlay visual
nutripae/verifier.py    reglas: grupos completos, porción ±20 %, aptitud → semáforo
nutripae/storage.py     SQLite: entregas y devoluciones
nutripae/simulate.py    datos sintéticos para el tablero
docs/                   textos de postulación, mapeo a la rúbrica, capturas
```

## Hardware de una estación (estimado)

| Componente | Opción | Costo aprox. (COP) |
|---|---|---|
| Cámara cenital | Webcam 1080p / cámara Pi | 80.000 – 150.000 |
| Cómputo | Raspberry Pi 5 / mini-PC | 400.000 – 700.000 |
| Pantalla + LED | Pantalla 7" + tira LED | 150.000 – 250.000 |
| Estructura | Soporte y caja | 100.000 |
| **Total por estación** | | **≈ 0,7 – 1,2 millones** |

Dos estaciones por comedor (entrega + devolución). Una sede puede verificar 300–500 raciones/hora por estación
(≈ 5 segundos por bandeja).

## Licencia
MIT — equipo NutriPAE, Neiva 2026.
