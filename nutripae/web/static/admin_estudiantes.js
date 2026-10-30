// Arrastrar y soltar la lista de estudiantes sobre la zona de carga.
(function () {
  const zona = document.getElementById("zona-arrastre");
  const entrada = document.getElementById("archivo");
  const nombre = document.getElementById("archivo-nombre");
  if (!zona || !entrada) return;

  function mostrar() {
    const f = entrada.files && entrada.files[0];
    nombre.hidden = !f;
    nombre.textContent = f ? `Archivo listo: ${f.name}` : "";
  }

  ["dragenter", "dragover"].forEach((ev) => zona.addEventListener(ev, (e) => {
    e.preventDefault();
    zona.classList.add("np-arrastrando");
  }));
  ["dragleave", "drop"].forEach((ev) => zona.addEventListener(ev, () => zona.classList.remove("np-arrastrando")));
  zona.addEventListener("drop", (e) => {
    e.preventDefault();
    const archivos = e.dataTransfer && e.dataTransfer.files;
    if (!archivos || !archivos.length) return;
    const f = archivos[0];
    if (!/\.xlsx$/i.test(f.name)) {
      nombre.hidden = false;
      nombre.textContent = "Solo se aceptan archivos de Excel (.xlsx).";
      return;
    }
    const dt = new DataTransfer();
    dt.items.add(f);
    entrada.files = dt.files;
    mostrar();
  });
  entrada.addEventListener("change", mostrar);
})();
