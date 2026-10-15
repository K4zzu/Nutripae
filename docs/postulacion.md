# NutriPAE — Material de postulación · Neiva Fest Reto Innova 2026

**Cierre de inscripciones: 22 de octubre de 2026, 11:59 p. m.** · Finalistas: 27 oct · Pitch & demo (15 min): 30 oct 2:00–4:00 p. m. · Premiación: 30 oct 6:00 p. m., San Pedro Plaza.

Entregables obligatorios: Documento técnico (≤15 páginas, Anexo 2) · Pitch (≤10 diapositivas, guía oficial) · Anexos 3, 4 y 5 firmados · copia de cédula del representante. Opcionales (pero suman en "Demostración en vivo"): enlace al repositorio/demo y video ≤3 min.

Ámbito sugerido: **Social** (educación, inclusión de población vulnerable). Alternativa: Institucional & Gobierno (control de un programa público).

---

## 1. Nombre de la iniciativa

**NutriPAE — Verificación nutricional con inteligencia artificial para el Programa de Alimentación Escolar de Neiva**

## 2. Resumen ejecutivo (máx. 200 palabras)

NutriPAE es un sistema de visión artificial que verifica, ración por ración, la alimentación que reciben los estudiantes del Programa de Alimentación Escolar (PAE) en Neiva. En el comedor, cada bandeja pasa por una estación con cámara cenital y pantalla. Un modelo de inteligencia artificial reconoce los alimentos servidos, estima el peso de cada porción por su tamaño, la contrasta con la minuta y con el gramaje que corresponde al grado del estudiante, y detecta alimentos con mal aspecto. Si la ración cumple, se enciende una luz verde; si falta algo, una alerta permite completarla de inmediato y el evento queda registrado. Al devolver la bandeja, una segunda estación identifica qué quedó en el plato y calcula el consumo real y los nutrientes efectivamente ingeridos, usando la Tabla de Composición de Alimentos Colombianos. Toda la información alimenta un tablero para el operador, la Secretaría de Educación y las veedurías: raciones entregadas, cumplimiento diario, alimentos rechazados, nutrientes servidos frente a consumidos y desperdicio por alimento. La IA es el núcleo: convierte una sola foto en evidencia nutricional verificable en segundos, todos los días, sin depender de visitas de supervisión esporádicas y sin captar rostros ni datos personales.

## 3. Problema específico de Neiva que aborda (máx. 250 palabras)

Cerca de 32.000 estudiantes de 167 sedes educativas oficiales de Neiva dependen del Programa de Alimentación Escolar para alimentarse durante la jornada. La alimentación escolar incide directamente en la asistencia, la concentración y el aprendizaje, sobre todo en los estudiantes de hogares más vulnerables, para quienes la ración del colegio es con frecuencia la comida principal del día.

En los últimos años el programa en Neiva ha presentado fallas reiteradas: interrupciones del servicio durante semanas, almuerzos incompletos o con porciones inferiores a la minuta, alimentos sin registro sanitario y denuncias sobre las condiciones de las cocinas. El problema de fondo es la ausencia de un mecanismo de verificación continua. Hoy el control se hace mediante visitas de supervisión puntuales, planillas diligenciadas a mano y conteos de raciones que no permiten saber, de manera objetiva, si cada bandeja llegó completa y en buen estado, qué consumieron realmente los estudiantes ni qué aporte nutricional recibieron.

Sin esa información, la administración municipal no puede exigir cumplimiento al operador con evidencia, los rectores y padres no pueden reclamar con datos, y las decisiones sobre menús y presupuesto se toman a ciegas. Además, el alimento que se bota y los grupos que los estudiantes rechazan pasan desapercibidos.

NutriPAE ataca exactamente ese vacío: instala en el comedor un verificador objetivo, automático y diario que genera evidencia ración por ración, de modo que garantizar la alimentación adecuada de los estudiantes de Neiva deje de depender de la buena fe y pase a depender de datos.

## 4. Población beneficiaria y alcance estimado (máx. 200 palabras)

**Beneficiarios directos:** los cerca de 32.000 niños, niñas y adolescentes de las 167 sedes oficiales de Neiva atendidos por el PAE, en su mayoría de estratos 1 y 2, población víctima, migrante y rural. Reciben raciones verificadas, completas y en buen estado, y menús ajustados a lo que realmente consumen.

**Beneficiarios indirectos:** sus familias; los rectores y docentes, que obtienen evidencia para reclamar; la Secretaría de Educación de Neiva, que gana un instrumento de interventoría continua sobre un contrato de miles de millones de pesos al año; el operador del PAE, que puede demostrar cumplimiento y reducir desperdicio; y las veedurías ciudadanas y entes de control, que acceden a datos agregados.

**Alcance por fases:** piloto en 2 sedes (≈1.500 raciones diarias) durante el primer semestre de 2027; expansión a las 20 sedes de mayor matrícula (≈12.000 raciones diarias) en 12 meses; cobertura municipal gradual. Impacto esperado, con base en experiencias comparables de escaneo de bandejas en Corea del Sur: reducción del desperdicio entre 13 % y 60 %, detección inmediata del 100 % de raciones incompletas en los puntos instalados, y datos nutricionales reales para rediseñar las minutas.

---

## 5. Cómo responde a la rúbrica (70 pts técnicos + 30 pts pitch)

| Criterio | Pts | Qué debe decir el documento técnico / demo |
|---|---|---|
| Pertinencia y delimitación del problema | 10 | Cifras de Neiva (32.000 estudiantes, 167 sedes), fallas documentadas con fuentes (noticias, informes de la Contraloría/Personería), vacío de verificación ración por ración. |
| Impacto y potencial de transformación | 12 | Evidencia diaria para la interventoría; nutrientes reales; menos desperdicio; menús basados en datos. Indicadores: % raciones completas, kcal consumidas vs. meta, kg de desperdicio. |
| Calidad del componente de IA | 14 | Visión artificial para reconocer alimentos, estimar gramos sin báscula (bandeja de dimensiones conocidas como referencia de escala + altura visible + densidad por alimento) y detectar mal aspecto; comparación antes/después para consumo. Ruta: modelo multimodal (hoy) → YOLO fine-tuned con dataset propio de bandejas PAE (producción, edge). Métricas a reportar: mAP por clase, error de gramaje frente a pesaje de validación (se pesan bandejas solo durante la calibración), exactitud del semáforo. |
| Innovación y diferenciación | 8 | Primera aplicación en Colombia del escaneo de bandejas (referente Nuvilab, Corea) orientada a **verificación de cumplimiento del PAE**, no solo a desperdicio. Semáforo en tiempo real que corrige la ración antes de que el niño se siente. |
| Viabilidad técnica y operativa | 8 | Solo cámara + pantalla (≈1 millón/estación, sin báscula ni sensores), 5 s por bandeja, se integra al flujo actual del comedor. Prototipo funcional en Python ya operativo. |
| IA responsable, privacidad y ética | 10 | Cámara cenital solo a la bandeja; sin reconocimiento facial; identificador anónimo de bandeja + grado; datos agregados; cumplimiento Ley 1581 de 2012 (habeas data) y protección reforzada de menores; sesgo controlado con dataset de alimentos locales (plátano, yuca, arepa). Explicabilidad: cada alerta muestra el alimento, la porción y la regla incumplida. |
| Sostenibilidad y escalabilidad | 8 | Costo marginal por sede bajo; modelo de financiación: inclusión como requisito en el contrato PAE (operador paga la estación) o inversión municipal; el ahorro por desperdicio y por raciones no entregadas supera el costo. Escalable a Huila y a otros municipios. |
| Demostración en vivo | 12 | Demo: bandeja real + webcam → semáforo; luego bandeja con sobrante → consumo; cierre con tablero de 10 días. Preparar escenarios `completa`, `incompleta`, `no_apto`. |
| Validación de impacto y usuarios | 6 | Antes del 30 oct: entrevistas con un rector, una manipuladora de alimentos y un padre de familia; si es posible, prueba de 1 hora en un comedor con fotos reales. Documentar en 1 slide. |
| Dominio técnico | 4 | Conocer límites: estimación visual de gramos con error esperado ±15–20 % (suficiente para detectar porciones <80 %); sopas y alimentos mezclados se estiman por nivel del recipiente; oclusiones y bandejas no estándar requieren calibración. |
| Claridad del pitch | 4 | Estructura: problema → niño con bandeja incompleta → cómo funciona (30 s de demo) → datos → plan → equipo. |
| Plan 6–12 meses | 4 | Ver sección 6. |

## 6. Plan de implementación 6–12 meses

| Mes | Hito |
|---|---|
| 1–2 | Acuerdo con Secretaría de Educación y operador; selección de 2 sedes piloto; captura de 3.000 fotos de bandejas PAE reales (dataset propio, etiquetado). |
| 3–4 | Entrenamiento YOLO fine-tuned con alimentos locales; ensamble de 4 estaciones (2 por sede); calibración de la estimación de gramos pesando 300 bandejas de referencia con nutricionista. |
| 5–6 | Piloto en operación diaria; medición de línea base vs. piloto (raciones completas, desperdicio, kcal consumidas); ajuste de reglas con la minuta patrón oficial. |
| 7–9 | Tablero institucional conectado para interventoría; informe de resultados; propuesta de inclusión en pliegos del contrato PAE 2027. |
| 10–12 | Expansión a 20 sedes; alertas automáticas a rectores y Secretaría; apertura de datos agregados a veedurías. |

## 7. Guion sugerido de video (≤3 min)

0:00–0:30 El problema: un estudiante, una bandeja incompleta, nadie lo registró. Cifras de Neiva.
0:30–1:30 Demo entrega: foto → semáforo rojo → se completa → verde.
1:30–2:10 Demo devolución: lo que quedó en el plato → consumo y nutrientes reales.
2:10–2:45 Tablero: 10 días, 6 sedes, qué se rechaza, cuánto se bota, kcal consumidas por grado.
2:45–3:00 Privacidad, costo por estación y plan 12 meses.

## 8. Fuentes a citar en el documento técnico (verificar y completar)

- Resolución 335 de 2021 del Ministerio de Educación Nacional — Lineamientos Técnico-Administrativos del PAE (minuta patrón, gramajes por grupo de edad).
- ICBF (2018). Tabla de Composición de Alimentos Colombianos (TCAC).
- Ley 1581 de 2012 y Decreto 1377 de 2013 — protección de datos personales; Código de Infancia y Adolescencia (Ley 1098 de 2006).
- KOCIS / Ministerio de Cultura de Corea (2024). "Using A.I. food scanners to reduce food garbage" — resultados de Nuvilab en 29 colegios (reducción de desperdicio promedio 13 %, hasta 60 %).
- Informes de la Secretaría de Educación de Neiva y de los entes de control sobre el PAE 2024–2026 (cifras de 32.000 estudiantes / 167 sedes y denuncias).
