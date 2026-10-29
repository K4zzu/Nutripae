# NutriPAE — Material de postulación · Neiva Fest Reto Innova 2026

**Cierre de inscripciones: 22 de octubre de 2026, 11:59 p. m.** · Finalistas: 27 oct · Pitch & demo (15 min): 30 oct 2:00–4:00 p. m. · Premiación: 30 oct 6:00 p. m., San Pedro Plaza.

Entregables obligatorios: Documento técnico (≤15 páginas, Anexo 2) · Pitch (≤10 diapositivas, guía oficial) · Anexos 3, 4 y 5 firmados · copia de cédula del representante. Opcionales (pero suman en "Demostración en vivo"): enlace al repositorio/demo y video ≤3 min.

Ámbito sugerido: **Social** (educación, inclusión de población vulnerable). Alternativa: Institucional & Gobierno (control de un programa público).

---

## 1. Nombre de la iniciativa

**NutriPAE — El plato balanceado, explicado a cada niño del Programa de Alimentación Escolar de Neiva con inteligencia artificial**

## 2. Resumen ejecutivo (máx. 200 palabras)

NutriPAE es una app web con inteligencia artificial que acompaña a cada estudiante del Programa de Alimentación Escolar (PAE) de Neiva en un solo momento: entre "me sirvieron" y "me siento a comer". El niño pone su tarjeta QR junto a la bandeja y una cámara, en el celular de la docente o en una estación fija, lee la tarjeta y el plato en una sola toma. En menos de 10 segundos la pantalla muestra un veredicto pensado para un niño de 6 a 12 años: un semáforo con color e ícono, su nombre y una sola razón ("Te falta verdura. La verdura te ayuda a crecer fuerte."), sobre la foto de su plato con cada alimento coloreado por grupo. Si el plato no está balanceado, vuelve a la fila y se lo completan. La IA segmenta la bandeja, identifica cada alimento, estima sus gramos sin báscula, detecta mal aspecto y evalúa el plato con el método del plato balanceado. Con el consentimiento de la familia, cada verificación queda guardada a nombre del niño: el colegio tiene el registro de lo que se le sirvió y la nutricionista entrega a los padres un informe en PDF cuando lo piden.

## 3. Problema específico de Neiva que aborda (máx. 250 palabras)

Cerca de 32.000 estudiantes de 167 sedes educativas oficiales de Neiva dependen del Programa de Alimentación Escolar para alimentarse durante la jornada. La alimentación escolar incide directamente en la asistencia, la concentración y el aprendizaje, sobre todo en los estudiantes de hogares más vulnerables, para quienes la ración del colegio es con frecuencia la comida principal del día.

En los últimos años el programa en Neiva ha presentado fallas reiteradas: interrupciones del servicio durante semanas, almuerzos incompletos o con porciones inferiores a la minuta, alimentos sin registro sanitario y denuncias sobre las condiciones de las cocinas. El problema de fondo es la ausencia de un mecanismo de verificación continua. Hoy el control se hace mediante visitas de supervisión puntuales, planillas diligenciadas a mano y conteos de raciones que no permiten saber, de manera objetiva, si cada bandeja llegó completa y en buen estado, qué consumieron realmente los estudiantes ni qué aporte nutricional recibieron.

Sin esa información, la administración municipal no puede exigir cumplimiento al operador con evidencia, los rectores y padres no pueden reclamar con datos, y las decisiones sobre menús y presupuesto se toman a ciegas. Además, el alimento que se bota y los grupos que los estudiantes rechazan pasan desapercibidos.

Y a los niños nadie les explica, con el plato delante, qué es comer balanceado: la educación alimentaria se queda en el aula, lejos del momento en que se decide qué se sirven.

NutriPAE ataca ese vacío en el instante exacto: verifica cada plato antes de que el niño se siente, le explica en su lenguaje qué le falta y por qué importa, y deja el registro de lo que se le sirvió, de modo que la alimentación adecuada de los estudiantes de Neiva deje de depender de la buena fe y pase a depender de datos.

## 4. Población beneficiaria y alcance estimado (máx. 200 palabras)

**Beneficiarios directos:** los cerca de 32.000 niños, niñas y adolescentes de las 167 sedes oficiales de Neiva atendidos por el PAE, en su mayoría de estratos 1 y 2, población víctima, migrante y rural. Aprenden, plato a plato, qué es comer balanceado, y reciben platos verificados, completos y en buen estado antes de sentarse.

**Beneficiarios indirectos:** sus familias, que reciben a pedido el informe de lo que se le sirvió a su hijo; los rectores y docentes, que obtienen evidencia para reclamar; la Secretaría de Educación de Neiva, que gana un instrumento de interventoría continua sobre un contrato de miles de millones de pesos al año; el operador del PAE, que puede demostrar cumplimiento y reducir desperdicio; y las veedurías ciudadanas y entes de control, que acceden a datos agregados.

**Alcance por fases:** piloto en 2 sedes (≈1.500 raciones diarias) durante el primer semestre de 2027; expansión a las 20 sedes de mayor matrícula (≈12.000 raciones diarias) en 12 meses; cobertura municipal gradual. Impacto esperado, con base en experiencias comparables de escaneo de bandejas en Corea del Sur: reducción del desperdicio entre 13 % y 60 %, detección inmediata del 100 % de raciones incompletas en los puntos instalados, y datos reales de los grupos de alimentos que más faltan, por sede y grado, para rediseñar las minutas.

---

## 5. Cómo responde a la rúbrica (70 pts técnicos + 30 pts pitch)

| Criterio | Pts | Qué debe decir el documento técnico / demo |
|---|---|---|
| Pertinencia y delimitación del problema | 10 | Cifras de Neiva (32.000 estudiantes, 167 sedes), fallas documentadas con fuentes (noticias, informes de la Contraloría/Personería), vacío de verificación ración por ración. |
| Impacto y potencial de transformación | 12 | Educación alimentaria en el momento del plato, todos los días; registro por niño de lo servido; menús basados en datos. Indicadores: % de platos verdes a la primera por sede y grado, grupo que más falta, alimentos no aptos detectados, informes entregados a familias. |
| Calidad del componente de IA | 14 | Segmentación real con FastSAM (contornos de cada alimento, en CPU en 1–2 s) + IA de visión multimodal que nombra cada alimento, estima gramos sin báscula (bandeja de dimensiones conocidas como escala + altura visible + densidad) y marca mal aspecto; cruce contorno ↔ alimento y evaluación con el método del plato. Las correcciones de la docente quedan registradas como etiquetas humanas. Ruta: hoy segmentación general + IA de visión → fase 2 YOLO-seg propio entrenado con la muestra de fotos del piloto, en la estación y sin internet. Métricas a reportar: mAP por clase, error de gramaje frente a pesaje de validación, exactitud del semáforo frente a la nutricionista, tasa de correcciones. |
| Innovación y diferenciación | 8 | Primera aplicación en Colombia del escaneo de bandejas (referente Nuvilab, Corea) orientada a **educar al niño en el momento del plato**, no solo a medir desperdicio. Veredicto en dos capas (niño / docente) que corrige el plato antes de que se siente; tarjeta QR que solo lleva un código. |
| Viabilidad técnica y operativa | 8 | App web sin instalar nada: el celular de la docente o un PC con webcam (≈1 millón/estación, sin báscula ni sensores); veredicto en menos de 10 s; un servidor Lightsail de 12 USD/mes con HTTPS. Carga de estudiantes desde el Excel del colegio y tarjetas QR impresas por curso. Prototipo funcional ya operativo. |
| IA responsable, privacidad y ética | 10 | El sistema **sí guarda datos personales de menores** y lo dice: consentimiento informado de la familia antes de registrar a un niño (sin consentimiento recibe el veredicto, pero nada se guarda a su nombre ni se le da tarjeta); el QR lleva solo un código; el documento de identidad se guarda como huella irreversible; cámara cenital solo a la bandeja y toma descartada si aparece una persona; fotos reducidas a 1024 px y borradas al cerrar el año escolar; muestra de entrenamiento limitada (50 bandejas por día y sede); acceso por usuario y sede, con registro de quién consulta o genera un informe; Ley 1581 de 2012 y protección reforzada de menores; sesgo controlado con alimentos locales (plátano, yuca, arepa). Explicabilidad: cada veredicto da una razón y la docente ve alimento, grupo, gramos y estado. |
| Sostenibilidad y escalabilidad | 8 | Costo marginal por sede bajo; modelo de financiación: inclusión como requisito en el contrato PAE (operador paga la estación) o inversión municipal; el ahorro por desperdicio y por raciones no entregadas supera el costo. Escalable a Huila y a otros municipios. |
| Demostración en vivo | 12 | Demo: un "niño" pone su tarjeta QR junto a una bandeja sin verdura → la cámara lee tarjeta y plato → rojo con su nombre y "Te falta verdura…"; se completa el plato → verde "¡Listo!". La docente corrige un alimento y busca a un niño sin tarjeta. Cierre: carga del Excel con la columna de consentimiento, hoja de tarjetas QR y el PDF del historial para la familia. Respaldo sin internet: *Práctica sin cámara* con plato simulado (sus registros no entran a ningún historial). |
| Validación de impacto y usuarios | 6 | Antes del 30 oct: entrevistas con un rector, una manipuladora de alimentos y un padre de familia; si es posible, prueba de 1 hora en un comedor con fotos reales. Documentar en 1 slide. |
| Dominio técnico | 4 | Conocer límites: estimación visual de gramos con error esperado ±15–20 % (suficiente para el método del plato con tolerancia amplia); sopas y alimentos mezclados se estiman por nivel del recipiente; oclusiones y bandejas no estándar requieren calibración; umbrales del plato pendientes de validar con la nutricionista; el análisis es de a uno por servidor (dos sedes caben en 2 GB con swap). |
| Claridad del pitch | 4 | Estructura: problema → un niño con su plato y su veredicto → cómo funciona (30 s de demo) → privacidad y consentimiento → datos → plan → equipo. |
| Plan 6–12 meses | 4 | Ver sección 6. |

## 6. Plan de implementación 6–12 meses

| Mes | Hito |
|---|---|
| 1–2 | Acuerdo con Secretaría de Educación y operador; selección de 2 sedes piloto; consentimientos informados de las familias; carga de estudiantes y entrega de tarjetas QR plastificadas; validación de los umbrales del plato con la nutricionista. |
| 3–4 | Piloto en operación diaria con estaciones fijas y celulares de docentes; calibración de la estimación de gramos pesando 300 bandejas de referencia con nutricionista; recolección de la muestra de fotos y de las correcciones de las docentes. |
| 5–6 | Medición de línea base vs. piloto (platos verdes a la primera, grupo que más falta); ajuste de mensajes y umbrales; entrenamiento del modelo YOLO-seg propio con las fotos del piloto. |
| 7–9 | Modelo propio en la estación, sin internet; informe de resultados para la Secretaría; propuesta de inclusión en pliegos del contrato PAE 2027. |
| 10–12 | Expansión a 20 sedes; borrado de las fotos del año escolar según la política de retención; apertura de datos agregados a veedurías. |

## 7. Guion sugerido de video (≤3 min)

0:00–0:30 El problema: un niño se sirve, se sienta y nadie le explica qué le faltó. Cifras de Neiva.
0:30–1:30 El momento: tarjeta QR junto a la bandeja → rojo "Te falta verdura. La verdura te ayuda a crecer fuerte." → vuelve a la fila → verde "¡Listo!".
1:30–2:10 La docente: alimentos, gramos y nutrientes; Corregir y Buscar; el celular como estación.
2:10–2:45 El registro: historial del niño y el PDF que recibe la familia; resumen por sede para la nutricionista.
2:45–3:00 Consentimiento y privacidad, costo por estación y plan 12 meses.

## 8. Fuentes a citar en el documento técnico (verificar y completar)

- Resolución 335 de 2021 del Ministerio de Educación Nacional — Lineamientos Técnico-Administrativos del PAE (minuta patrón, gramajes por grupo de edad).
- ICBF (2018). Tabla de Composición de Alimentos Colombianos (TCAC).
- Ley 1581 de 2012 y Decreto 1377 de 2013 — protección de datos personales; Código de Infancia y Adolescencia (Ley 1098 de 2006).
- KOCIS / Ministerio de Cultura de Corea (2024). "Using A.I. food scanners to reduce food garbage" — resultados de Nuvilab en 29 colegios (reducción de desperdicio promedio 13 %, hasta 60 %).
- Informes de la Secretaría de Educación de Neiva y de los entes de control sobre el PAE 2024–2026 (cifras de 32.000 estudiantes / 167 sedes y denuncias).
