# NutriPAE v2 — Diseño

Fecha: 2026-10-29 · Estado: revisado por un constructor; pendiente de aprobación

## 1. Intención

NutriPAE v2 es un sistema para que cada niño del Programa de Alimentación Escolar (PAE) de Neiva aprenda,
plato a plato, qué es comer balanceado, y para que el colegio tenga el registro de qué se le sirvió a cada uno.

Cambia el centro del proyecto. La v1 (la app Streamlit actual) estaba pensada para el interventor: minutas,
gramajes por grado, tablero de cumplimiento, estación de devolución. La v2 vive en un solo momento, el paso
entre "me sirvieron" y "me siento a comer", y su usuario principal es el niño. Todo lo demás (historial,
PDF, administración) existe para servir ese momento o para dejar constancia de él.

Por qué: la educación alimentaria se enseña mejor en el instante en que el niño tiene el plato delante, con
un veredicto inmediato y una razón ("la verdura te ayuda a crecer fuerte"). Y como a veces el niño se sirve
solo, el veredicto debe medir "plato balanceado", no "minuta oficial".

## 1.1 Relación con la v1

La presentación del Reto Innova con la v1 ya pasó. **La v2 se construye en el mismo repositorio, reemplazando a la
v1**: `app.py` (Streamlit), `menu.py` como regla, `simulate.py`, la devolución y el tablero se retiran cuando la
v2 los sustituye. El orden del plan es el del piloto: primero lo que hace funcionar el momento del plato
(verificación, segmentación, veredicto), luego listas de estudiantes, tarjetas QR e historial, y por último
administración y PDF. El modo demostración se mantiene desde el principio para poder mostrar el sistema sin
cámara.

## 2. El momento (flujo principal)

1. Al niño le sirven (o se sirve) la bandeja.
2. Antes de sentarse pasa por la **verificación**. Hay dos formas, con la misma página web:
   - **Estación fija**: un PC con webcam cenital y pantalla, abierto en el navegador. La docente está al lado
     vigilando; no tiene que tocar nada en el caso normal.
   - **Celular de la docente**: abre la misma página, entra con su usuario y apunta la cámara.
3. El niño pone su **tarjeta QR** sobre la bandeja (o al lado). La cámara lee el QR y el plato en una sola toma.
   El sistema ya sabe quién es, grado, sede.
   - Si el niño no tiene tarjeta: la docente toca **Buscar**, elige el nombre en la lista del grado (el
     siguiente en orden de lista aparece sugerido arriba) y continúa.
4. La IA **identifica, segmenta y clasifica** cada alimento del plato por grupo, estima gramos y detecta mal
   aspecto. Evalúa el plato contra el **plato balanceado** (sección 4).
5. En pantalla aparece el veredicto en **dos capas** (sección 5):
   - **Verde**: "¡Listo, Juan! Tu plato está balanceado." El niño sigue al comedor.
   - **Amarillo o rojo**: "Te falta verdura. La verdura te ayuda a crecer fuerte." El niño vuelve a la fila a
     que le completen o balanceen el plato, y pasa de nuevo por la verificación.
6. Cada verificación queda **guardada a nombre del niño**: foto anotada, alimentos, gramos, grupos, veredicto,
   hora, sede, quién verificó. Si el mismo niño pasa varias veces en el mismo almuerzo, se guardan todas y la
   última es la que cuenta como "lo que se le sirvió"; las anteriores quedan como intentos.

Objetivo de tiempo: del plato bajo la cámara al veredicto, **menos de 10 segundos**. Nada de clics en el
caso normal en la estación fija; en el celular, un toque para capturar.

## 3. Personas y roles

| Rol | Quién | Qué hace |
|---|---|---|
| **Niño** | Estudiante del PAE | Pone la tarjeta y el plato; lee el veredicto. No tiene cuenta. |
| **Docente** | Docente a cargo del comedor (o manipuladora) | Entra con usuario y contraseña; verifica platos (celular o estación); busca al niño sin tarjeta; puede abrir el historial de un niño de su sede. |
| **Nutricionista** | Nutricionista del operador o de la Secretaría | Ve el historial de cualquier niño de sus sedes; genera el **PDF** cuando un padre lo pide; ve resúmenes por sede y grado. |
| **Administrador** | Quien instala y mantiene el sistema | Carga la lista de estudiantes desde Excel; imprime las hojas de tarjetas QR; crea usuarios y asigna sedes; da de baja estudiantes. |

Los padres **no entran al sistema**. Reciben el PDF impreso o por WhatsApp de manos del colegio.

Un usuario puede tener varios roles (p. ej. nutricionista + administrador).

## 4. Qué significa "plato balanceado"

La regla deja de ser la minuta del día con gramos por grado. Pasa a ser una idea general de plato balanceado,
basada en el **método del plato** adaptado al almuerzo del PAE:

- **Grupos que deben estar**: proteína, cereal o tubérculo (vale uno de los dos; si hay ambos se suman como
  "energéticos"), verdura, fruta. La bebida se registra pero no decide el semáforo.
- **Proporciones** (sobre el peso estimado del plato sin bebida), con tolerancia amplia:
  - verdura + fruta: alrededor de la mitad
  - proteína: alrededor de un cuarto
  - cereal/tubérculo: alrededor de un cuarto
- **Semáforo**:
  - **Verde**: están los cuatro grupos y ninguna proporción se sale mucho.
  - **Amarillo**: están los cuatro grupos pero alguna porción está claramente corta (p. ej. proteína muy pequeña) o
    muy excedida (un plato que es casi todo arroz).
  - **Rojo**: falta un grupo entero, o algún alimento tiene mal aspecto (se marca "no apto" y el plato se cambia).
- El **grado** ya no fija gramos. Se usa para el tamaño esperado del plato (preescolar come menos) y para el tono
  del mensaje.

**Pendiente de validación**: los umbrales exactos (qué tan corta es "claramente corta") los debe validar la
nutricionista del proyecto. El diseño los deja como parámetros editables, con valores iniciales razonables
que el constructor propone y documenta.

Se conserva la **tabla de composición** (ICBF) para mostrar calorías y nutrientes del plato servido en la capa
de la docente y en el historial.

## 5. La pantalla del veredicto

Dos capas en la misma pantalla, a la vez:

**Capa del niño (arriba, grande, legible a dos metros)**
- Semáforo con color e ícono (nunca solo color), nombre del niño, frase corta.
- Si falta o sobra algo: qué, en una frase, y por qué importa ("la verdura te ayuda a crecer fuerte"). Una sola
  razón, la del grupo que más falta; no una lista.
- La foto del plato con cada alimento **coloreado por grupo** (contornos de segmentación, no cuadros), con su
  nombre encima.
- Con verde, un refuerzo variado ("¡Hoy sí tienes fruta!"), no siempre la misma frase.

**Capa de la docente (abajo, pequeña)**
- Alimento por alimento: nombre, grupo, gramos estimados, estado (ok / corto / excedido / falta / no apto).
- Calorías y nutrientes del plato.
- Botones: **Siguiente** (vuelve a esperar bandeja; en la estación fija pasa solo tras unos segundos),
  **Corregir** (si la IA nombró mal un alimento, la docente lo cambia de una lista; queda registrado como
  corrección humana) y **Buscar** (niño sin tarjeta).

En el celular las dos capas son la misma pantalla, desplazable; la capa del niño es la que ve el niño cuando
la docente le gira el teléfono.

Lenguaje: todo en español, para un niño de 6 a 12 años en la capa de arriba; para un adulto en la de abajo.
No aparecen palabras técnicas (modelo, API, segmentación) en ninguna de las dos.

## 6. Identificación: tarjetas QR

- Al cargar la lista de estudiantes, el sistema genera un **código único** por estudiante y un **PDF por curso**
  con las tarjetas listas para imprimir y plastificar (nombre, grado, sede y el QR).
- **El QR contiene solo el código**, no el nombre ni datos del niño. Una tarjeta perdida no expone nada; el
  administrador puede anularla y generar otra.
- Lectura del QR **en el navegador** (cámara del celular o webcam), sin pasar por el servidor. La misma toma
  sirve para el QR y para el plato cuando la tarjeta está sobre la bandeja; si el QR no se lee en la toma, la
  pantalla pide "acerca la tarjeta" y sigue intentando en vivo.
- **Respaldo sin tarjeta**: buscar por nombre dentro del grado, con el siguiente en orden de lista sugerido.

## 7. Historial y PDF

- Por niño: lista de días con el plato servido (foto anotada, alimentos, grupos, gramos, calorías, semáforo),
  frecuencia con que faltó cada grupo en el periodo, intentos por día.
- Por sede y grado (nutricionista): porcentaje de platos verdes por día, grupo que más falta, alimentos
  no aptos.
- **PDF del niño** a pedido de un padre: periodo elegido, resumen en lenguaje de padres (sin jerga), tabla de
  días, calorías y grupos, una o dos fotos de ejemplo. Lo genera la nutricionista o la docente desde el
  historial; el sistema no lo envía a nadie.

## 8. Administración

- Cargar estudiantes desde **Excel**. Columnas: **código** (el que use el colegio: número de lista con grado, o
  código interno; si el colegio solo tiene el documento de identidad, se usa como clave pero se guarda
  **cifrado de forma irreversible**, nunca en claro), **nombre**, **grado**, **grupo** (opcional: 3-A, 3-B; si
  no viene, todo el grado es un grupo), **sede**, **consentimiento** (sí/no; si falta la columna, se asume no).
  Volver a cargar actualiza por código, no duplica. El "orden de lista" es el orden de las filas del Excel
  dentro de cada grupo; si el administrador lo pide, se reordena alfabéticamente por apellido. *(Decisión del
  diseño, no del solicitante.)*
- **Consentimiento**: se marca en la carga o después, estudiante por estudiante, en administración. Un niño
  **sin consentimiento** recibe igual el veredicto educativo en pantalla, pero no se guarda nada a su nombre y no
  se le genera tarjeta QR hasta que el consentimiento quede marcado. *(Decisión del diseño.)*
- Generar e imprimir hojas de tarjetas QR por curso; anular y regenerar una tarjeta.
- Usuarios: crear, asignar rol y sedes, desactivar.
- Parámetros: umbrales del plato balanceado, lista de alimentos conocidos y su grupo.

## 9. La IA

Para el piloto, sin entrenar ningún modelo:

1. **Segmentación: FastSAM** (viene en el paquete `ultralytics`). Recorta la bandeja en regiones con sus contornos,
   sin saber qué son. Funciona con cualquier comida, incluida la colombiana. Corre en CPU en 1–2 s.
2. **Identificación y estimación: IA de visión por API**, con la clave de OpenAI existente (el código ya soporta
   también Claude y Gemini). Nombra cada alimento, lo ubica, estima gramos (con la bandeja como escala, como hoy)
   y marca mal aspecto.
3. **Cruce**: cada contorno recibe el nombre y grupo del alimento que la IA ubicó en esa zona; contornos sin
   alimento (bandeja, sombras) se descartan; alimentos sin contorno se muestran con su cuadro.

Justificación para la presentación: "segmentamos con un modelo general y clasificamos con IA de visión
mientras entrenamos el modelo propio con las fotos del piloto".

**Fase 2 (fuera de este diseño)**: modelo YOLO-seg propio entrenado con las fotos anónimas del piloto (con
autorización de las sedes y revisión de nutricionistas), corriendo en el PC de la estación sin internet. La
plataforma de Ultralytics sirve para ese entrenamiento.

## 10. Datos y privacidad

Este diseño **sí guarda datos personales de menores** (nombre, grado, sede, foto del plato, qué se le sirvió). Eso
obliga a:

- Consentimiento informado de padres o acudientes antes de registrar a un niño (lo gestiona el colegio; el
  sistema solo registra si el consentimiento está marcado al cargar la lista).
- La foto es solo de la bandeja, cenital. No se guardan rostros; si la IA detecta una persona en la foto, se
  descarta la toma y se pide repetir.
- Acceso por usuario y contraseña; cada usuario solo ve sus sedes. Registro de quién consultó o generó un PDF.
- Retención: las fotos se conservan el año escolar y luego se borran; los datos tabulares se conservan mientras
  el niño esté en el programa.
- **Qué foto se guarda** *(decisión del diseño)*: para el historial, una versión reducida y anotada (lado mayor
  1024 px, unos 100–150 KB), suficiente para que un padre o la nutricionista vean el plato. Para el entrenamiento
  de la fase 2, además, el original sin anotar de una **muestra configurable por día y sede** (valor inicial:
  50 bandejas), nunca de todas. Así un año de piloto en dos sedes cabe en el disco de la instancia; si la muestra
  crece, se pasa a almacenamiento de objetos.
- El documento de identidad, si el colegio lo usa como código, no se guarda en claro (ver sección 8).
- El servidor está en Colombia o, si no es posible, se documenta dónde está.

Los textos actuales de "sin datos personales, código anónimo" se retiran de la app y de la documentación.

## 11. Cómo se construye (decisiones tomadas)

- **App web propia**, sin instalar nada: se abre desde un enlace en el navegador del celular o del PC, pide
  usuario y contraseña. Reemplaza a Streamlit, que no puede leer QR en vivo ni mostrar la cámara con los
  alimentos coloreados encima.
- **Servidor en Python**, reutilizando lo que ya existe y sirve: `detector.py` (IA de visión por API, prompt de
  estimación de gramos), `nutrition.py` (tabla ICBF), partes de `storage.py`. Se retiran `menu.py` como regla,
  `verifier.py` (se reescribe para el plato balanceado), `simulate.py`, la devolución y el tablero v1.
- **Base de datos**: SQLite sigue sirviendo para el piloto (pocas sedes, pocos usuarios a la vez).
- **Despliegue**: la instancia Lightsail de 12 USD (2 GB RAM) que ya existe, con **dominio y HTTPS obligatorios**
  (sin HTTPS el navegador no permite la cámara) y **2 GB de swap** porque `torch` + FastSAM usan cerca de 1 GB al
  analizar. Si en el piloto se queda corta, se sube al plan de 4 GB.
- **Sistema de diseño**: se reemplaza el de la v1 por la identidad visual del equipo (abajo). Se conservan las reglas
  de producto: semáforo con ícono además de color, botones de kiosco de 88 px, texto del veredicto legible a dos metros.

**Identidad visual NutriPAE (2026-10-29, recursos del equipo en `docs/identidad/` y `nutripae/web/static/img/`)**
- Logotipo: "NutriPAE" con lápiz y sonrisa (`logo.png` sin fondo para la app; `docs/identidad/logo-fondo-blanco.png` para PDF). Icono: el lápiz (`icono.png`, `favicon.png`).
- Paleta: morado `#4C17C1` (principal, títulos, botones), verde `#23D098`, amarillo `#FAC344`, rojo lápiz `#EE3B5A`, azul `#1C3F9E`; tinta `#1F1A3D`, tinta secundaria `#5A557A`, línea `#E6E2F5`, fondo blanco `#FFFFFF` con superficie suave `#F7F5FF`. Tonos oscuros para texto sobre blanco: verde `#13A676`, amarillo `#B8820A`, rojo `#B81F3C`; tonos claros para fondos de estado: `#DFF8EE`, `#FFF4D6`, `#FFE1E6`, morado claro `#EEE8FB`.
- Semáforo (siempre con ícono): verde = fondo `#23D098` con texto tinta; amarillo = fondo `#FAC344` con texto tinta; rojo = fondo `#E02E4D` con texto blanco. No apto: `#B81F3C`.
- Grupos sobre la foto: proteína `#EE3B5A`, energéticos `#FAC344`, verdura `#23D098`, fruta `#4C17C1`, bebida `#1C3F9E`, otro `#9A96B3`.
- Tipografía (Google Fonts): **Fredoka** 500–700 para títulos, veredicto y botones; **Nunito** 400–800 para el cuerpo.
- Forma: esquinas muy redondeadas (tarjetas 24 px, botones y chips 999 px), manchas orgánicas amarillas y verdes en las esquinas de las pantallas de inicio, sin bordes duros ni grises fríos.
- Estación: pantalla de inicio a pantalla completa con el logotipo y "Toca para comenzar" (el toque pide el permiso de cámara); vuelve a ella tras 2 min sin actividad.

- **Modo demostración**: se mantiene para presentar sin cámara ni internet (plato simulado), elegible por el
  usuario; nunca visible al niño como "demo". Los registros del modo demostración se marcan y no entran en el
  historial de ningún niño real.
- **Concurrencia** *(decisión del diseño)*: el piloto son dos sedes. El análisis (FastSAM 1–2 s + IA de visión
  4–8 s) se ejecuta de a uno por servidor, con una cola corta; si dos estaciones verifican a la vez, la segunda
  ve "un momento…" y espera unos segundos. Si en el piloto la espera se vuelve habitual, se sube al plan de 4 GB
  (2 vCPU) antes que complicar el software.

## 12. Objetivos, no-objetivos, anti-objetivos

**Objetivos**
- Veredicto claro y educativo para el niño en menos de 10 s, sin clics en la estación fija.
- Segmentación real (contornos) desde el día uno.
- Registro por niño de lo servido; historial y PDF para padres a pedido.
- Funciona igual en el celular de la docente y en el PC de la estación, sin instalar nada.

**No-objetivos (esta versión)**
- Medir lo que el niño comió (devolución, consumo real, desperdicio).
- Tablero de interventoría, vista pública, cumplimiento de minuta y gramaje oficial.
- Modelo propio entrenado; funcionamiento sin internet.
- Acceso de padres al sistema; envío automático de mensajes.

**Anti-objetivos (sería un fracaso aunque funcione)**
- Atribuir un plato al niño equivocado (por eso QR y no orden de lista).
- Que el niño vea jerga, regaños o solo color sin ícono.
- Que la pantalla muestre configuración técnica (claves, proveedores, modelos).
- Guardar fotos con rostros.

## 13. Lo que queda al constructor

- Elección concreta del framework web y de la librería de lectura de QR en el navegador.
- Qué tanto se conserva de `storage.py` y `detector.py` frente a reescribirlos.
- Formato interno del cruce contorno ↔ alimento y cómo se dibuja la capa coloreada.
- Valores iniciales de los umbrales del plato balanceado (documentados y editables).
- Diseño de las tablas, migración de lo útil de la v1, estructura del PDF.
- Cómo se pasa "solo" a la siguiente bandeja en la estación fija (temporizador, detección de bandeja nueva).
- Textos exactos de los mensajes al niño (una lista variada por grupo y por semáforo), revisables por la
  nutricionista.
