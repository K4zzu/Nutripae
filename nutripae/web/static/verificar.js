/* Pantalla de verificación: cámara, lectura del QR en el navegador y veredicto en dos capas. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const local = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* sin almacenamiento */ } },
  };

  // ------------------------------------------------------------------ modo de la pantalla
  const params = new URLSearchParams(location.search);
  if (params.has("estacion")) local.set("np.estacion", params.get("estacion") === "1" ? "1" : "0");
  const ESTACION = local.get("np.estacion", "0") === "1";

  const INTERVALO_QR = 300;      // ms entre lecturas del QR
  const QR_ESTABLE = 1000;       // ms que el mismo QR debe verse antes de capturar
  const ESPERA_VEREDICTO = 8000; // ms que el veredicto queda en pantalla en la estación
  const SIN_TARJETA = 5000;      // ms sin QR antes de pedir "Acerca tu tarjeta"
  const INACTIVA = 120000;       // ms sin veredictos ni tarjetas antes de volver a la pantalla de inicio
  const QR_RECIENTE = 2000;      // ms en que un QR visto en vivo aún vale para la toma
  const REINTENTOS_OCUPADO = 3;

  const ICONO = { verde: "✓", amarillo: "!", rojo: "✕" };
  const ESTADO = {
    ok: ["✓", "Bien"], corto: ["!", "Corto"], excedido: ["!", "Excedido"],
    falta: ["✕", "Falta"], no_apto: ["—", "No apto"],
  };
  const NUTRIENTE = {
    kcal: ["Calorías", "kcal"], proteina_g: ["Proteína", "g"], carbohidratos_g: ["Carbohidratos", "g"],
    grasa_g: ["Grasa", "g"], fibra_g: ["Fibra", "g"], hierro_mg: ["Hierro", "mg"], calcio_mg: ["Calcio", "mg"],
  };

  const el = {
    pantalla: $("pantalla"), video: $("video"), foto: $("foto"), toques: $("toques"), lienzo: $("lienzo"),
    aviso: $("camara-aviso"), semaforo: $("semaforo"), icono: $("icono"), titulo: $("titulo"), detalle: $("detalle"),
    lectura: $("lectura"), capturar: $("btn-capturar"), siguiente: $("btn-siguiente"), corregir: $("btn-corregir"),
    buscar: $("btn-buscar"), porciones: $("porciones"), nutrientes: $("nutrientes"), total: $("total"),
    practica: $("practica"), situacion: $("situacion"), grado: $("grado-sin-estudiante"),
    panelBuscar: $("panel-buscar"), buscarQ: $("buscar-q"), buscarGrado: $("buscar-grado"), buscarLista: $("buscar-lista"),
    panelCorregir: $("panel-corregir"), corregirLista: $("corregir-lista"), inicio: $("inicio"),
  };
  const token = (nombre) => getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
  const iconoEspera = el.icono.innerHTML;

  const s = {
    estado: "esperando",   // esperando | analizando | veredicto | aviso
    camara: false,
    qrVisto: null, qrDesde: 0, ultimoQR: Date.now(),
    qrLeido: null,         // último QR visto en vivo
    qrLeidoEn: 0,          // cuándo se vio por última vez
    qrUsado: null,         // QR del último veredicto: no vuelve a disparar mientras siga a la vista
    elegido: null,         // estudiante elegido con Buscar
    veredicto: null, alimentos: null, temporizador: null,
    actividad: Date.now(), // último veredicto, tarjeta vista o toque
  };

  // ------------------------------------------------------------------ preferencias guardadas
  el.practica.checked = local.get("np.practica", "0") === "1";
  el.situacion.value = local.get("np.situacion", "completa");
  el.grado.value = local.get("np.grado", "primaria");
  el.buscarGrado.value = el.grado.value;
  el.practica.addEventListener("change", () => { local.set("np.practica", el.practica.checked ? "1" : "0"); ajustarBotones(); });
  el.situacion.addEventListener("change", () => local.set("np.situacion", el.situacion.value));
  el.grado.addEventListener("change", () => { local.set("np.grado", el.grado.value); el.buscarGrado.value = el.grado.value; });

  function ajustarBotones() {
    // En la estación no hay botón de captura, salvo en práctica (no hay tarjeta que dispare la toma).
    el.capturar.hidden = ESTACION && !el.practica.checked;
  }
  ajustarBotones();
  el.pantalla.classList.toggle("np-v-es-estacion", ESTACION);
  // en la estación la barra superior (con "Salir") se oculta; queda un "Salir" discreto abajo a la derecha
  document.body.classList.toggle("np-estacion", ESTACION);

  // ------------------------------------------------------------------ cámara
  async function iniciarCamara() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return avisoCamara();
    try {
      const flujo = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      el.video.srcObject = flujo;
      await el.video.play().catch(() => {});
      s.camara = true;
      s.ultimoQR = Date.now();
      el.aviso.hidden = true;
    } catch (e) {
      avisoCamara();
    }
  }
  function avisoCamara() {
    s.camara = false;
    el.aviso.textContent = "Permite el acceso a la cámara";
    el.aviso.hidden = false;
  }
  const videoListo = () => s.camara && el.video.readyState >= 2 && el.video.videoWidth > 0;

  function qrEn(canvas) {
    if (typeof jsQR !== "function") return null;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    const r = jsQR(ctx.getImageData(0, 0, canvas.width, canvas.height).data, canvas.width, canvas.height,
      { inversionAttempts: "dontInvert" });
    return r && r.data ? r.data.trim() : null;
  }

  function leerQR() {
    if (!videoListo()) return null;
    const v = el.video, escala = Math.min(1, 640 / v.videoWidth);
    const c = el.lienzo;
    c.width = Math.round(v.videoWidth * escala); c.height = Math.round(v.videoHeight * escala);
    c.getContext("2d", { willReadFrequently: true }).drawImage(v, 0, 0, c.width, c.height);
    return qrEn(c);
  }

  // Tarjeta para la toma: la del propio fotograma; si no, una vista hace menos de QR_RECIENTE ms.
  function tarjetaParaToma(qrDelFotograma) {
    if (qrDelFotograma) return qrDelFotograma;
    return s.qrLeido && Date.now() - s.qrLeidoEn <= QR_RECIENTE ? s.qrLeido : null;
  }

  function cicloQR() {
    const codigo = leerQR();
    const ahora = Date.now();
    if (codigo) {
      s.ultimoQR = ahora;
      s.actividad = ahora;
      if (!el.inicio.hidden) ocultarInicio(); // una tarjeta también despierta la estación
      if (codigo !== s.qrVisto) { s.qrVisto = codigo; s.qrDesde = ahora; }
    } else {
      s.qrVisto = null;
      if (s.qrUsado && s.estado === "esperando") s.qrUsado = null; // la tarjeta salió de la vista
    }
    if (codigo && s.estado !== "analizando") {
      const cambio = codigo !== s.qrLeido;
      s.qrLeido = codigo; s.qrLeidoEn = ahora;
      if (cambio && !ESTACION) mostrarLectura();
    } else if (!ESTACION && s.qrLeido && ahora - s.qrLeidoEn > QR_RECIENTE && s.estado !== "analizando") {
      s.qrLeido = null; // la tarjeta ya no está a la vista: no se usará al capturar
      mostrarLectura();
    }

    if (!ESTACION) return;
    if (!el.inicio.hidden) return; // en la pantalla de inicio no se pide tarjeta ni se captura
    if (s.estado === "esperando" && ahora - s.actividad > INACTIVA) { mostrarInicio(); return; }
    if (s.estado === "esperando") {
      if (codigo && codigo !== s.qrUsado && ahora - s.qrDesde >= QR_ESTABLE) {
        capturar();
      } else if (!codigo && videoListo() && ahora - s.ultimoQR > SIN_TARJETA) {
        pedirTarjeta();
      } else if (codigo) {
        quitarPedido();
      }
    } else if (s.estado === "veredicto" && codigo && codigo !== s.qrUsado) {
      volver();
    }
  }

  function pedirTarjeta() {
    if (el.pantalla.classList.contains("np-v-pide-tarjeta")) return;
    el.pantalla.classList.add("np-v-pide-tarjeta");
    el.titulo.textContent = "Acerca tu tarjeta";
    el.detalle.textContent = "Ponla cerca de la cámara. Si no tienes tarjeta, avisa a tu profe.";
  }
  function quitarPedido() {
    if (!el.pantalla.classList.contains("np-v-pide-tarjeta")) return;
    el.pantalla.classList.remove("np-v-pide-tarjeta");
    textosEspera();
  }

  // ------------------------------------------------------------------ captura y envío
  function fotoGris() {
    const c = document.createElement("canvas"); c.width = 640; c.height = 480;
    const ctx = c.getContext("2d"); ctx.fillStyle = "#808080"; ctx.fillRect(0, 0, 640, 480);
    return new Promise((ok) => c.toBlob(ok, "image/jpeg", 0.8));
  }
  function fotoCamara() {
    const v = el.video, escala = Math.min(1, 1280 / Math.max(v.videoWidth, v.videoHeight));
    const c = document.createElement("canvas");
    c.width = Math.round(v.videoWidth * escala); c.height = Math.round(v.videoHeight * escala);
    c.getContext("2d", { willReadFrequently: true }).drawImage(v, 0, 0, c.width, c.height);
    const qr = qrEn(c);
    return new Promise((ok) => c.toBlob((blob) => ok({ blob, qr }), "image/jpeg", 0.85));
  }

  async function capturar(intento = 0) {
    if (s.estado === "analizando" && intento === 0) return;
    const practica = el.practica.checked;
    if (!practica && !videoListo()) { avisoCamara(); return; }
    cambiarEstado("analizando");
    el.semaforo.dataset.semaforo = "espera";
    el.icono.innerHTML = '<span class="np-v-girando"></span>';
    el.titulo.textContent = "Revisando tu plato…";
    el.detalle.textContent = "Quédate quieto un momento.";

    const datos = new FormData();
    const toma = practica ? { blob: await fotoGris(), qr: null } : await fotoCamara();
    const tarjeta = s.elegido ? null : tarjetaParaToma(toma.qr);
    datos.append("foto", toma.blob, "bandeja.jpg");
    datos.append("modo", practica ? "demo" : "camara");
    if (practica) datos.append("escenario", el.situacion.value);
    datos.append("grado", el.grado.value);
    if (s.elegido) datos.append("estudiante_id", String(s.elegido.id));
    else if (tarjeta) datos.append("tarjeta", tarjeta);
    s.qrUsado = tarjeta;

    let r;
    try {
      r = await fetch("/api/verificar", { method: "POST", body: datos, credentials: "same-origin" });
    } catch (e) {
      return mostrarAviso("No hay conexión. Intenta de nuevo.");
    }
    if (r.redirected || r.status === 401) { location.href = "/entrar"; return; }
    let j = null;
    try { j = await r.json(); } catch (e) { /* respuesta sin cuerpo */ }
    if (!r.ok) {
      if (j && j.error === "ocupado" && intento < REINTENTOS_OCUPADO) {
        el.titulo.textContent = j.mensaje;
        setTimeout(() => capturar(intento + 1), 1500);
        return;
      }
      return mostrarAviso(j && j.mensaje ? j.mensaje : "No se pudo leer la bandeja. Intenta de nuevo.");
    }
    s.qrLeido = null; // cada veredicto consume la tarjeta, en ambos modos
    s.elegido = null;
    mostrarVeredicto(j);
  }

  // ------------------------------------------------------------------ estados de la pantalla
  function cambiarEstado(e) {
    s.estado = e;
    el.pantalla.dataset.estado = e;
    clearTimeout(s.temporizador);
  }

  function textosEspera() {
    el.titulo.textContent = "Coloca la bandeja";
    el.detalle.textContent = ESTACION ? "Pon tu tarjeta sobre la bandeja." : "Apunta la cámara a la bandeja y a la tarjeta.";
  }

  function volver() {
    cambiarEstado("esperando");
    el.pantalla.classList.remove("np-v-pide-tarjeta");
    s.veredicto = null; s.ultimoQR = Date.now();
    s.qrLeido = null;
    s.elegido = null;
    el.semaforo.dataset.semaforo = "espera";
    el.icono.innerHTML = iconoEspera;
    textosEspera();
    el.foto.hidden = true; el.toques.hidden = true; el.video.hidden = false;
    el.porciones.replaceChildren(fila(["Esperando una bandeja."], 4));
    el.nutrientes.replaceChildren(); el.total.textContent = "";
    el.corregir.disabled = true;
    el.panelCorregir.hidden = true;
    mostrarLectura();
  }

  function mostrarAviso(mensaje) {
    cambiarEstado("aviso");
    el.semaforo.dataset.semaforo = "aviso";
    el.icono.textContent = "!";
    el.titulo.textContent = mensaje;
    el.detalle.textContent = "";
    s.qrUsado = null;
    s.temporizador = setTimeout(volver, 3500);
  }

  function mostrarVeredicto(j) {
    cambiarEstado("veredicto");
    s.veredicto = j;
    s.actividad = Date.now();
    el.pantalla.classList.remove("np-v-pide-tarjeta");
    el.semaforo.dataset.semaforo = j.semaforo;
    el.icono.textContent = ICONO[j.semaforo] || "!";
    el.titulo.textContent = j.titulo;
    el.detalle.textContent = j.detalle;
    if (j.foto_url) el.foto.src = j.foto_url;
    el.foto.hidden = false; el.toques.hidden = false; el.video.hidden = true;
    pintarDocente(j);
    if (!ESTACION) el.semaforo.scrollIntoView({ behavior: "smooth", block: "start" });
    if (ESTACION) s.temporizador = setTimeout(volver, ESPERA_VEREDICTO);
  }

  function mostrarLectura() {
    const t = (icono, texto, clase) => {
      const i = document.createElement("span"); i.setAttribute("aria-hidden", "true"); i.textContent = icono;
      el.lectura.replaceChildren(i, document.createTextNode(" " + texto));
      el.lectura.className = "np-v-lectura" + (clase ? " " + clase : "");
    };
    const j = s.veredicto;
    if (j && j.tarjeta_invalida) return t("✕", "Tarjeta no válida: no se guardó a nombre de nadie.", "np-v-mal");
    if (j && j.estudiante) return t("✓", `${j.estudiante.nombre} · ${j.estudiante.grado}`, "np-v-bien");
    if (j) return t("▢", "Sin estudiante: no se guardó a nombre de nadie.");
    if (s.elegido) return t("✓", `Elegido: ${s.elegido.nombre}`, "np-v-bien");
    if (s.qrLeido) return t("▣", `Tarjeta leída: ${s.qrLeido}`, "np-v-bien");
    t("▢", "Sin tarjeta leída");
  }

  // ------------------------------------------------------------------ capa de la docente
  function fila(celdas, colspan) {
    const tr = document.createElement("tr");
    celdas.forEach((c) => {
      const td = document.createElement("td");
      if (colspan) { td.colSpan = colspan; td.className = "np-sub"; }
      if (c instanceof Node) td.append(c); else td.textContent = c;
      tr.append(td);
    });
    return tr;
  }

  function pintarDocente(j) {
    mostrarLectura();
    el.porciones.replaceChildren(...j.porciones.map((p) => {
      const nombre = document.createElement("span");
      nombre.className = "np-v-alimento";
      const punto = document.createElement("i"); punto.style.background = p.color; punto.setAttribute("aria-hidden", "true");
      nombre.append(punto, document.createTextNode(p.nombre + (p.aproximado ? " (aprox.)" : "")));
      const [icono, texto] = ESTADO[p.estado] || ["!", p.estado];
      const estado = document.createElement("span");
      estado.className = "np-v-estado np-v-estado-" + p.estado;
      estado.textContent = `${icono} ${texto}`;
      const tr = fila([nombre, p.grupo_label, p.estado === "falta" ? "—" : `${p.gramos} g`, estado]);
      tr.dataset.indice = p.indice;
      return tr;
    }));
    el.nutrientes.replaceChildren(...Object.entries(NUTRIENTE).flatMap(([k, [nombre, unidad]]) => {
      if (!(k in (j.nutrientes || {}))) return [];
      const dt = document.createElement("dt"); dt.textContent = nombre;
      const dd = document.createElement("dd"); dd.textContent = `${Math.round(j.nutrientes[k] * 10) / 10} ${unidad}`;
      return [dt, dd];
    }));
    el.total.textContent = `Peso estimado del plato: ${j.total_g} g`;
    el.corregir.disabled = !j.porciones.some((p) => p.estado !== "falta");
    if (!el.panelCorregir.hidden) abrirCorregir();
  }

  // Toque sobre la foto: resalta la porción y abre Corregir en ella.
  function puntoEnPoligono(x, y, pol) {
    let dentro = false;
    for (let i = 0, k = pol.length - 1; i < pol.length; k = i++) {
      const [xi, yi] = pol[i], [xk, yk] = pol[k];
      if ((yi > y) !== (yk > y) && x < ((xk - xi) * (y - yi)) / (yk - yi) + xi) dentro = !dentro;
    }
    return dentro;
  }
  function resaltar(p) {
    // el lienzo de toques cubre exactamente la foto mostrada
    const c = el.toques, f = el.foto;
    c.width = f.clientWidth; c.height = f.clientHeight;
    c.style.left = f.offsetLeft + "px"; c.style.top = f.offsetTop + "px";
    c.style.width = f.clientWidth + "px"; c.style.height = f.clientHeight + "px";
    const ctx = c.getContext("2d");
    ctx.clearRect(0, 0, c.width, c.height);
    if (!p || !p.poligono) return;
    ctx.lineWidth = 6; ctx.strokeStyle = token("--surf") || "white"; ctx.setLineDash([10, 6]);
    ctx.beginPath();
    p.poligono.forEach(([x, y], i) => (i ? ctx.lineTo : ctx.moveTo).call(ctx, x * c.width, y * c.height));
    ctx.closePath(); ctx.stroke();
  }
  el.toques.addEventListener("click", (ev) => {
    if (!s.veredicto) return;
    const r = el.toques.getBoundingClientRect();
    const x = (ev.clientX - r.left) / r.width, y = (ev.clientY - r.top) / r.height;
    const p = s.veredicto.porciones.find((q) => q.estado !== "falta" && q.poligono && puntoEnPoligono(x, y, q.poligono));
    resaltar(p);
    if (p) { pausarRetorno(); abrirCorregir(p.indice); }
  });
  el.foto.addEventListener("load", () => resaltar(null));
  window.addEventListener("resize", () => { if (!el.foto.hidden) resaltar(null); });

  function pausarRetorno() { clearTimeout(s.temporizador); }

  // ------------------------------------------------------------------ Corregir
  async function cargarAlimentos() {
    if (s.alimentos) return s.alimentos;
    const r = await fetch("/api/alimentos", { credentials: "same-origin" });
    if (!r.ok) throw new Error("sin lista");
    s.alimentos = await r.json();
    return s.alimentos;
  }

  async function abrirCorregir(foco) {
    const j = s.veredicto;
    if (!j) return;
    pausarRetorno();
    el.panelCorregir.hidden = false;
    let lista;
    try { lista = await cargarAlimentos(); } catch (e) {
      el.corregirLista.replaceChildren(item("No se pudo cargar la lista de alimentos."));
      return;
    }
    el.corregirLista.replaceChildren(...j.porciones.filter((p) => p.estado !== "falta").map((p) => {
      const li = document.createElement("li");
      li.className = "np-v-corregir-item" + (p.indice === foco ? " np-v-foco" : "");
      const etiqueta = document.createElement("label");
      etiqueta.htmlFor = `corregir-${p.indice}`;
      etiqueta.textContent = `${p.nombre} · ${p.grupo_label}`;
      const sel = document.createElement("select");
      sel.id = `corregir-${p.indice}`;
      sel.append(new Option("Cambiar por…", ""), ...lista.map((a) => new Option(a.nombre, a.clave)));
      sel.addEventListener("change", () => sel.value && enviarCorreccion(p.indice, sel.value, sel));
      li.append(etiqueta, sel);
      return li;
    }));
    const enfoque = foco !== undefined && $(`corregir-${foco}`);
    if (enfoque) { enfoque.scrollIntoView({ block: "nearest" }); enfoque.focus(); }
  }

  async function enviarCorreccion(indice, alimento, sel) {
    sel.disabled = true;
    const j = s.veredicto;
    const r = await fetch(`/api/verificaciones/${j.id}/corregir`, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ indice, alimento }),
    }).catch(() => null);
    const nuevo = r ? await r.json().catch(() => null) : null;
    if (!r || !r.ok || !nuevo) {
      sel.disabled = false;
      sel.after(item(nuevo && nuevo.mensaje ? nuevo.mensaje : "No se pudo guardar la corrección."));
      return;
    }
    // la foto anotada no cambia; las demás partes del veredicto se rehacen
    nuevo.tarjeta_invalida = j.tarjeta_invalida;
    s.veredicto = nuevo;
    el.semaforo.dataset.semaforo = nuevo.semaforo;
    el.icono.textContent = ICONO[nuevo.semaforo] || "!";
    el.titulo.textContent = nuevo.titulo;
    el.detalle.textContent = nuevo.detalle;
    pintarDocente(nuevo);
  }

  function item(texto) {
    const li = document.createElement("li"); li.className = "np-sub"; li.textContent = texto; return li;
  }

  // ------------------------------------------------------------------ Buscar
  let esperaBusqueda = null;

  async function pedir(url) {
    const r = await fetch(url, { credentials: "same-origin" });
    if (r.status === 404) throw new Error("no disponible");
    if (!r.ok) throw new Error("fallo");
    return r.json();
  }

  function botonEstudiante(e, sugerido) {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.className = "np-v-estudiante" + (sugerido ? " np-v-sugerido" : "");
    b.textContent = (sugerido ? "Siguiente en lista: " : "") + e.nombre + (e.grupo ? ` · ${e.grupo}` : "");
    b.addEventListener("click", () => elegir(e));
    li.append(b);
    return li;
  }

  async function buscar() {
    const grado = el.buscarGrado.value, q = el.buscarQ.value.trim();
    const qs = (o) => new URLSearchParams(o).toString();
    try {
      const [siguiente, lista] = await Promise.all([
        pedir(`/api/estudiantes/siguiente?${qs({ grado, grupo: "" })}`).catch((e) => { if (e.message === "no disponible") throw e; return null; }),
        pedir(`/api/estudiantes/buscar?${qs({ q, grado })}`),
      ]);
      const filas = [];
      if (siguiente && siguiente.id) filas.push(botonEstudiante(siguiente, true));
      (Array.isArray(lista) ? lista : []).forEach((e) => { if (!siguiente || e.id !== siguiente.id) filas.push(botonEstudiante(e)); });
      el.buscarLista.replaceChildren(...(filas.length ? filas : [item("No hay estudiantes con ese nombre.")]));
    } catch (e) {
      el.buscarLista.replaceChildren(item(e.message === "no disponible"
        ? "Búsqueda no disponible todavía" : "No se pudo buscar. Intenta de nuevo."));
    }
  }

  function elegir(e) {
    el.panelBuscar.hidden = true;
    if (s.estado === "veredicto" || s.estado === "aviso") volver();
    s.elegido = e;
    s.qrLeido = null;
    mostrarLectura();
    if (ESTACION) capturar();
  }

  el.buscarQ.addEventListener("input", () => { clearTimeout(esperaBusqueda); esperaBusqueda = setTimeout(buscar, 250); });
  el.buscarGrado.addEventListener("change", buscar);

  // ------------------------------------------------------------------ botones
  el.capturar.addEventListener("click", () => capturar());
  el.siguiente.addEventListener("click", volver);
  el.corregir.addEventListener("click", () => (el.panelCorregir.hidden ? abrirCorregir() : (el.panelCorregir.hidden = true)));
  el.buscar.addEventListener("click", () => {
    el.panelBuscar.hidden = !el.panelBuscar.hidden;
    if (!el.panelBuscar.hidden) { pausarRetorno(); el.buscarQ.focus(); buscar(); }
  });
  document.querySelectorAll("[data-cerrar]").forEach((b) =>
    b.addEventListener("click", () => { $(b.dataset.cerrar).hidden = true; }));

  // ------------------------------------------------------------------ pantalla de inicio (solo estación)
  function mostrarInicio() {
    el.inicio.hidden = false;
    el.inicio.focus({ preventScroll: true });
  }
  function ocultarInicio() {
    el.inicio.hidden = true;
    s.actividad = Date.now();
    s.ultimoQR = Date.now();
    quitarPedido();
  }
  function tocarInicio() {
    ocultarInicio();
    if (!s.camara) iniciarCamara(); // getUserMedia dentro del gesto del toque
  }
  el.inicio.addEventListener("click", tocarInicio);
  el.inicio.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); tocarInicio(); }
  });
  // la docente usando la pantalla también cuenta como actividad
  el.pantalla.addEventListener("pointerdown", () => { s.actividad = Date.now(); });

  // ------------------------------------------------------------------ arranque
  textosEspera();
  mostrarLectura();
  if (ESTACION) mostrarInicio();
  else iniciarCamara();
  setInterval(cicloQR, INTERVALO_QR);
})();
