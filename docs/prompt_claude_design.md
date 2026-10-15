# Prompt para Claude Design — Sistema NutriPAE

Diseña el sistema de interfaces de **NutriPAE**, una plataforma de verificación nutricional con inteligencia artificial para los comedores escolares del Programa de Alimentación Escolar (PAE) de Neiva, Colombia. Es un proyecto para el concurso Neiva Fest Reto Innova 2026 y se presentará en vivo ante un jurado; el diseño debe verse profesional, cívico y claro, no como un juguete ni como un dashboard corporativo genérico.

## Contexto del problema
Cerca de 32.000 estudiantes de 167 sedes oficiales de Neiva dependen del PAE. Ha habido raciones incompletas, alimentos en mal estado e interrupciones del servicio, y no existe un sistema que verifique ración por ración. NutriPAE instala en cada comedor dos estaciones (entrega y devolución) con cámara cenital, pantalla y luz LED (sin báscula). Un modelo de visión reconoce cada alimento de la bandeja, estima los gramos por el tamaño de la porción usando la bandeja como referencia de escala, los compara con la minuta y con la porción que corresponde al grado del estudiante, detecta mal aspecto y enciende un semáforo. Al devolver la bandeja, detecta el sobrante y calcula el consumo real y los nutrientes ingeridos. Todo alimenta un tablero para el operador, la Secretaría de Educación y las veedurías. Nunca se captan rostros ni datos personales: la bandeja se identifica con un código anónimo y el grado.

## Usuarios
1. **Manipuladora de alimentos / auxiliar del comedor** (estación de entrega): mira la pantalla a 1–2 m, con ruido y fila de niños; tiene 5 segundos por bandeja. Necesita un veredicto enorme e inequívoco y saber qué falta.
2. **Estudiante** (estación de devolución): ve en una pantalla cuánto comió y cuánto dejó; debe ser amable y motivador, no punitivo.
3. **Nutricionista / supervisor del operador PAE** y **funcionario de la Secretaría de Educación** (tablero web): seguimiento diario por sede, alertas, nutrientes servidos vs. consumidos, desperdicio, exportación.
4. **Rector / veeduría** (vista pública simplificada): cumplimiento del programa en su sede.

## Pantallas a diseñar
1. **Estación de entrega (kiosco, pantalla 7–10", horizontal, uso a distancia)**
   - Imagen en vivo de la bandeja con cuadros y etiquetas por alimento ("Pollo guisado · 68 g").
   - Semáforo gigante: VERDE "Ración completa", AMARILLO "Completar porción" (indica qué y cuánto falta: "Arroz: faltan 25 g"), ROJO "Ración rechazada" (falta un grupo o alimento no apto).
   - Peso total estimado por la IA, grado del estudiante, código de bandeja, minuta del día, contador de raciones del turno.
   - Botones grandes: "Ración completada → reanalizar", "Registrar".
2. **Estación de devolución (kiosco)**
   - Bandeja devuelta con el sobrante resaltado; barras consumido/sobrante por alimento; mensaje para el estudiante ("Hoy comiste el 82 % de tu almuerzo 💪").
3. **Tablero de seguimiento (web, escritorio y tablet)**
   - KPIs: raciones verificadas, % completas a la primera, alertas rojas, alimentos no aptos, kcal servidas vs. consumidas, kg de desperdicio.
   - Gráficos: cumplimiento diario (apilado verde/amarillo/rojo), energía servida vs. consumida vs. meta por grado, % sobrante por alimento (qué dejan en el plato), alertas por sede, tabla de nutrientes (energía, proteína, carbohidratos, grasa, fibra, hierro, calcio) servidos vs. consumidos.
   - Filtros por sede, grado y rango de fechas; registro detallado de entregas con exportación CSV; detalle de una alerta con la foto anotada.
4. **Vista pública por sede (móvil)**: tarjeta simple con el cumplimiento de la semana para rectores y padres.
5. **Pantalla "Cómo funciona"** con el diagrama del flujo: cámara → IA de visión → verificación (grupos ✔ porción ✔ aptitud ✔) → base de datos → tablero; y los principios de privacidad.

## Datos y reglas que debe reflejar el diseño
- Grupos de alimentos de una ración completa: proteína, cereal, tubérculo/plátano, verdura, fruta, bebida.
- Grados: preescolar (meta 450 kcal almuerzo), primaria (550 kcal), secundaria (700 kcal). Porción dentro de ±20 % de la meta = cumple; menos del 80 % = incompleta; grupo ausente o alimento no apto = rechazada.
- Minutas típicas: pollo guisado con arroz y papa; carne molida con lentejas; huevo con arroz y plátano maduro; pescado con yuca. Alimentos colombianos (plátano, yuca, arepa, guayaba, mango) en las ilustraciones.
- Estados: ok ✅, porción baja ⚠️, falta ❌, no apto ⛔.

## Dirección visual
- Tono: institucional-cálido, confiable, colombiano; evocar comedor escolar y salud pública, no fintech.
- Paleta sugerida: verde salud como primario, ámbar y rojo semáforo solo para estados (accesible, con iconos además del color), fondo claro cálido; modo oscuro opcional para el tablero.
- Tipografía legible a distancia en los kioscos (tamaños muy grandes para el veredicto), compacta pero clara en el tablero.
- Componentes: tarjeta de semáforo, chip de estado por alimento, tarjeta KPI, barra servido vs. meta, medidor de kcal, tarjeta de alerta con foto anotada, tabla de nutrientes, filtros de sede/grado.
- Incluir un logo/isotipo simple para NutriPAE (bandeja + check) y una versión monocroma.
- Entregar: sistema de diseño (colores, tipografía, espaciado, componentes y sus estados) + las 5 pantallas en alta fidelidad + una versión de la estación de entrega en cada estado del semáforo.

## Restricciones
- Español de Colombia en todos los textos.
- Nada de rostros de niños en las ilustraciones: solo bandejas, manos y comedor.
- Las pantallas de kiosco deben funcionar sin mouse (táctil, botones ≥ 64 px) y verse bien a 2 metros.
- El prototipo real está hecho en Python/Streamlit; el diseño servirá como referencia visual para ajustarlo y para el pitch, así que mantén layouts implementables con componentes estándar (tarjetas, columnas, gráficos de barras y medidores).
