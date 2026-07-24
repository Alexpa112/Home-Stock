console.log(
  "%c" +
    " _____                              _ \n" +
    "|  __ \\                            | |\n" +
    "| |  | |_ __ ___  __ _ _ __ ___   __| |\n" +
    "| |  | | '__/ _ \\/ _` | '_ ` _ \\ / _` |\n" +
    "| |__| | | |  __/ (_| | | | | | | (_| |\n" +
    "|_____/|_|  \\___|\\__,_|_| |_| |_|\\__,_|\n" +
    "                                     ! ",
  "color:#2e8b57;font-weight:bold;font-family:monospace"
);

// Si la sesion caduca o se borra el usuario conectado, cualquier llamada a la
// API devolvera 401: mandamos a la pantalla de login en vez de dejar la app
// a medio cargar con errores silenciosos.
const fetchOriginal = window.fetch.bind(window);
window.fetch = async (input, init = {}) => {
  const metodo = (init.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(metodo)) {
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    if (token) {
      init = { ...init, headers: { ...(init.headers || {}), "X-CSRFToken": token } };
    }
  }
  const res = await fetchOriginal(input, init);
  if (res.status === 401) {
    window.location.href = "/login";
  } else if (res.status === 503) {
    const cuerpo = await res.clone().json().catch(() => null);
    if (cuerpo?.mantenimiento) {
      window.location.reload();
    }
  }
  return res;
};

// El antes-de-cada-peticion del servidor bloquea llamadas nuevas al activar el
// modo mantenimiento, pero si el usuario se queda quieto en una pantalla sin
// pedir nada no se entera. Comprobamos el estado cada minuto (y al recuperar
// el foco) para sacarlo aunque no esté interactuando con la app.
function iniciarComprobacionMantenimiento() {
  const comprobar = () => {
    if (document.visibilityState === "hidden") return;
    fetch("/api/auth/estado", { headers: { "X-Comprobacion-Mantenimiento": "1" } }).catch(() => {});
  };
  setInterval(comprobar, 60000);
  document.addEventListener("visibilitychange", comprobar);
}
iniciarComprobacionMantenimiento();

// Función auxiliar para fetch con timeout y manejo de errores
async function fetchConTimeout(url, options = {}, timeoutMs = 10000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timeoutId);

    if (!res.ok) {
      const cuerpo = await res.clone().json().catch(() => null);
      const error = new Error(cuerpo?.error || `Error del servidor (${res.status})`);
      error.status = res.status;
      throw error;
    }

    return res;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === "AbortError") {
      const timeoutError = new Error("La petición ha tardado demasiado. Comprueba tu conexión e inténtalo de nuevo.");
      console.error(`Fetch timeout for ${url}`);
      throw timeoutError;
    }
    console.error(`Fetch error for ${url}:`, error);
    throw error;
  }
}

// Catálogo de iconos (CATALOGO_ICONOS) e icono por defecto ("h-folder") ahora
// viven en static/icons/catalogo-iconos.js y se renderizan como SVG vía
// renderIcono() (static/utils/iconos.js), cargados antes de este script.

const lista = document.getElementById("lista");
const vacio = document.getElementById("vacio");
const buscador = document.getElementById("buscador");
const filtros = document.getElementById("filtros");
const fab = document.getElementById("btnAbrirModal");
const modalFondo = document.getElementById("modal");
const form = document.getElementById("formProducto");
const botonesEnviarProducto = [
  ...form.querySelectorAll('button[type="submit"]'),
  ...document.querySelectorAll(`button[form="${form.id}"]`),
];
const btnCancelar = document.getElementById("btnCancelar");
const modalTitulo = document.getElementById("modalTitulo");
const campoCategoria = document.getElementById("campoCategoria");
const campoIcono = document.getElementById("campoIcono");
const btnSeleccionarIconoProducto = document.getElementById("btnSeleccionarIconoProducto");
const iconoProductoDisplay = document.getElementById("iconoProductoDisplay");
const btnQuitarIconoProducto = document.getElementById("btnQuitarIconoProducto");

const tabs = document.getElementById("tabs");
const vistaStock = document.getElementById("vistaStock");
const vistaCompra = document.getElementById("vistaCompra");
const gruposCompraEl = document.getElementById("gruposCompra");
const compraVacia = document.getElementById("compraVacia");
const seccionCompletadosEl = document.getElementById("seccionCompletados");
const tilesCompletadosEl = document.getElementById("tilesCompletados");
const btnToggleCompletados = document.getElementById("btnToggleCompletados");

const modalCompraFondo = document.getElementById("modalCompra");
const formCompra = document.getElementById("formCompra");
const botonesEnviarCompra = [
  ...formCompra.querySelectorAll('button[type="submit"]'),
  ...document.querySelectorAll(`button[form="${formCompra.id}"]`),
];
const btnCancelarCompra = document.getElementById("btnCancelarCompra");
const compraModalTitulo = document.getElementById("compraModalTitulo");
const compraEditIdEl = document.getElementById("compraEditId");
const compraCampoCantidad = document.getElementById("compraCampoCantidad");
const compraCampoSubdescripcion = document.getElementById("compraCampoSubdescripcion");
const compraCampoCategoria = document.getElementById("compraCampoCategoria");
const compraCampoIcono = document.getElementById("compraCampoIcono");
const btnSeleccionarIconoCompra = document.getElementById("btnSeleccionarIconoCompra");
const iconoCompraDisplay = document.getElementById("iconoCompraDisplay");
const btnQuitarIconoCompra = document.getElementById("btnQuitarIconoCompra");
const compraBotonGuardar = document.getElementById("compraBotonGuardar");

const modalCatalogoFondo = document.getElementById("modalCatalogo");
const catalogoTitulo = document.getElementById("catalogoTitulo");
const catalogoAyuda = document.getElementById("catalogoAyuda");
const catalogoBuscadorEl = document.getElementById("catalogoBuscador");
const catalogoGruposEl = document.getElementById("catalogoGrupos");
const catalogoVacioEl = document.getElementById("catalogoVacio");
const btnCrearDesdeCatalogo = document.getElementById("btnCrearDesdeCatalogo");
const btnCerrarCatalogo = document.getElementById("btnCerrarCatalogo");

const btnAjustes = document.getElementById("btnAjustes");
const modalAjustesFondo = document.getElementById("modalAjustes");

const btnCerrarSesion = document.getElementById("btnCerrarSesion");

const btnConsumo = document.getElementById("btnConsumo");
const modalConsumoFondo = document.getElementById("modalConsumo");
const btnCerrarConsumo = document.getElementById("btnCerrarConsumo");
const consumoPorProductoEl = document.getElementById("consumoPorProducto");
const consumoVacioEl = document.getElementById("consumoVacio");

const btnTema = document.getElementById("btnTema");
const btnCategorias = document.getElementById("btnCategorias");
const modalCategoriasFondo = document.getElementById("modalCategorias");
const categoriasListaEl = document.getElementById("categoriasLista");
const formCategoria = document.getElementById("formCategoria");
const categoriaCampoNombre = document.getElementById("categoriaCampoNombre");
const categoriaCampoIcono = document.getElementById("categoriaCampoIcono");
const categoriaIconoElegido = document.getElementById("categoriaIconoElegido");
const selectorIconosEl = document.getElementById("selectorIconos");
const btnCerrarCategorias = document.getElementById("btnCerrarCategorias");
const botonesEnviarCategoria = [
  ...formCategoria.querySelectorAll('button[type="submit"]'),
  ...document.querySelectorAll(`button[form="${formCategoria.id}"]`),
];

let productos = [];
// Productos con un PATCH de cantidad en curso: evita que clics rápidos en +/-
// disparen peticiones concurrentes para el mismo producto (que pueden llegar
// desordenadas y dejar la cantidad mostrada desincronizada del backend).
const productosEnProceso = new Set();
let pendientesCompra = [];
let completadosCompra = [];
let categorias = [];
let categoriaActiva = "todas";
let textoBusqueda = "";
let vistaActiva = "stock";
let tecladoOffset = 0;

function sincronizarEstadoModal() {
  const hayModalAbierto = Array.from(document.querySelectorAll('.modal-fondo')).some((modal) => !modal.hidden);
  document.body.classList.toggle('modal-open', hayModalAbierto);
  document.documentElement.classList.toggle('modal-open', hayModalAbierto);
}

const observerModales = new MutationObserver(() => {
  sincronizarEstadoModal();
});
observerModales.observe(document.documentElement, {
  subtree: true,
  attributes: true,
  attributeFilter: ['hidden'],
});

function ajustarViewportMovil() {
  // Mientras el teclado virtual propio está abierto, es él quien fija
  // --keyboard-height/--keyboard-offset (su altura es conocida, no
  // estimada) - no dejar que este tracker del teclado nativo la pise.
  if (document.body.dataset.tecladoVirtualActivo === '1') return;
  if (!window.visualViewport) {
    document.documentElement.style.setProperty("--keyboard-offset", "0px");
    document.body.classList.remove("keyboard-open");
    tecladoOffset = 0;
    return;
  }

  const viewport = window.visualViewport;
  const offset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
  const offsetEfectivo = offset > 32 ? offset : 0;
  const hayModalAbierto = Array.from(document.querySelectorAll('.modal-fondo')).some((modal) => !modal.hidden);
  tecladoOffset = offsetEfectivo;
  document.documentElement.style.setProperty("--keyboard-offset", `${offsetEfectivo}px`);
  // --keyboard-height y la clase is-keyboard-open son leídos por ui-components.js
  // (TicketModal/CatalogModal.getMaxHeight() y responsive.css). Se fijan aquí
  // también para que exista una única fuente de verdad: antes KeyboardManager
  // (ui-components.js) los calculaba de forma independiente vía focusin/focusout
  // y un umbral distinto, pudiendo desincronizarse del alto real del teclado.
  document.documentElement.style.setProperty("--keyboard-height", `${offsetEfectivo}px`);
  // Aplicar clase SOLO cuando el teclado esté abierto y NO haya modales abiertos
  // para que los modales se adapten correctamente al teclado
  document.body.classList.toggle("keyboard-open", offsetEfectivo > 0);
  document.body.classList.toggle("is-keyboard-open", offsetEfectivo > 0 && !hayModalAbierto);
  sincronizarEstadoModal();

  if (offsetEfectivo > 0 && !hayModalAbierto && document.activeElement instanceof HTMLElement && document.activeElement !== document.body) {
    window.requestAnimationFrame(() => {
      document.activeElement.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
    });
  }
}

if (window.visualViewport) {
  window.visualViewport.addEventListener("resize", ajustarViewportMovil);
  window.visualViewport.addEventListener("scroll", ajustarViewportMovil);
}
window.addEventListener("resize", ajustarViewportMovil);
window.addEventListener("orientationchange", ajustarViewportMovil);
document.addEventListener("focusin", (event) => {
  const target = event.target;
  if (target instanceof HTMLElement && target.matches("input, select, textarea")) {
    window.setTimeout(() => {
      if (document.activeElement === target) {
        ajustarViewportMovil();
        target.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
      }
    }, 120);
  }
});
window.addEventListener("load", () => {
  ajustarViewportMovil();
  sincronizarEstadoModal();
});

if (window.VirtualKeyboard) {
  const preferenciaInicial = (window.__TECLADO_VIRTUAL_INICIAL__ ?? localStorage.getItem('stockhogar-teclado-virtual') ?? 'on') === 'on';
  window.tecladoVirtualController = new window.VirtualKeyboard.VirtualKeyboardController();
  window.tecladoVirtualController.init(preferenciaInicial);
}

/* --- Cierre seguro de modales: solo si el clic empieza y termina en el fondo --- */
function habilitarCierreSeguro(fondo, alCerrar) {
  let iniciadoEnFondo = false;
  fondo.addEventListener("mousedown", (e) => {
    iniciadoEnFondo = e.target === fondo;
  });
  fondo.addEventListener("click", (e) => {
    if (e.target === fondo && iniciadoEnFondo) alCerrar();
  });
}

/* --- Cierre de modales por drag-down (solo móvil, sin interferir con el scroll interno) --- */
function habilitarDragDown(modal, alCerrar) {
  const ZONA_ARRASTRE_PX = 32;
  let startY = 0;
  let currentY = 0;
  let isDragging = false;

  function scrollTopContenido() {
    const scrollable = modal.querySelector("form, .modal-content") || modal;
    return scrollable.scrollTop || 0;
  }

  modal.addEventListener("touchstart", (e) => {
    if (!window.matchMedia("(max-width: 767px)").matches) return;
    const toqueY = e.touches[0].clientY;
    const zonaSuperior = modal.getBoundingClientRect().top + ZONA_ARRASTRE_PX;
    if (toqueY > zonaSuperior && scrollTopContenido() > 0) return;
    startY = toqueY;
    currentY = startY;
    isDragging = true;
  }, { passive: true });

  // { passive: false } + preventDefault(): sin esto, en un dispositivo real
  // el navegador interpreta el mismo touchmove como un intento de scroll
  // nativo/rebote de .modal-content (que tiene overflow-y:auto) y se lo
  // queda para sí, compitiendo con el transform que aplicamos aquí; el
  // resultado es que el arrastre nunca "se siente" como un cierre y solo
  // queda la X como forma de cerrar (bug real reportado, invisible al
  // simular el toque por JS porque dispatchEvent no reproduce el
  // reconocimiento de gestos nativo del navegador).
  modal.addEventListener("touchmove", (e) => {
    if (!isDragging) return;
    currentY = e.touches[0].clientY;
    const diff = currentY - startY;
    if (diff > 0) {
      e.preventDefault();
      modal.style.transform = `translateY(${diff}px)`;
    }
  }, { passive: false });

  modal.addEventListener("touchend", () => {
    if (!isDragging) return;
    const diff = currentY - startY;
    isDragging = false;

    if (diff > 80) {
      modal.style.transform = "";
      alCerrar();
    } else {
      modal.style.transform = "";
    }
  });
}

/* --- Bottom sheet completo: cierre por fondo + arrastre seguro --- */
function habilitarBottomSheet(fondo, contenedor, alCerrar) {
  habilitarCierreSeguro(fondo, alCerrar);
  if (contenedor) habilitarDragDown(contenedor, alCerrar);
}
window.habilitarCierreSeguro = habilitarCierreSeguro;
window.habilitarDragDown = habilitarDragDown;
window.habilitarBottomSheet = habilitarBottomSheet;

function escapeHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

/* --- Tema claro/oscuro --- */

function temaActual() {
  return (
    document.documentElement.dataset.theme ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
  );
}

function actualizarBotonTema() {
  btnTema.textContent = temaActual() === "dark" ? "☀️" : "🌙";
}

/* Guarda la preferencia de tema ('light' | 'dark' | 'auto'), la aplica
   visualmente y la persiste tanto en localStorage (efecto inmediato en
   este navegador) como en BD (para que se recuerde en cualquier otro
   dispositivo donde el usuario inicie sesión). */
function guardarTemaPreferido(preferencia) {
  localStorage.setItem("stockhogar-tema", preferencia);
  const aplicado = preferencia === "auto"
    ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    : preferencia;
  document.documentElement.dataset.theme = aplicado;
  actualizarBotonTema();

  fetch("/api/auth/tema", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tema: preferencia })
  }).catch((error) => console.error("Error guardando tema:", error));
}

/* Alias usado por el toggle rápido de la cabecera: fuerza un tema explícito. */
function aplicarTema(tema) {
  guardarTemaPreferido(tema);
}

/* Guarda la preferencia de teclado virtual propio ('on'/'off'), igual patrón
   que guardarTemaPreferido(): localStorage para efecto inmediato + BD para
   que se recuerde en otros dispositivos. */
function guardarPreferenciaTecladoVirtual(activo) {
  const valor = activo ? 'on' : 'off';
  localStorage.setItem('stockhogar-teclado-virtual', valor);
  window.tecladoVirtualController?.setEnabled(activo);

  fetch('/api/auth/teclado-virtual', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ teclado_virtual_activo: valor })
  }).catch((error) => console.error('Error guardando preferencia de teclado virtual:', error));
}

btnTema.addEventListener("click", () => {
  aplicarTema(temaActual() === "dark" ? "light" : "dark");
});

actualizarBotonTema();

/* Escucha cambios del tema del sistema mientras la preferencia sea "auto",
   para que la app reaccione en caliente si el usuario cambia el tema del
   móvil sin necesidad de recargar la página. */
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
  const preferencia = localStorage.getItem("stockhogar-tema") || "auto";
  if (preferencia !== "auto") return;
  document.documentElement.dataset.theme = e.matches ? "dark" : "light";
  actualizarBotonTema();
});

/* --- Categorias --- */

function iconoDeCategoria(nombre) {
  const cat = categorias.find((c) => c.nombre === nombre);
  return cat ? cat.icono : "h-folder";
}

// Icono a mostrar para un producto o articulo de la compra: el suyo propio
// si se le asigno uno, si no el de su categoria.
function iconoEfectivo(item) {
  return item.icono || iconoDeCategoria(item.categoria);
}

/* --- Historial / catalogo de articulos (nombre -> icono/categoria/unidad) --- */

let historialLista = [];
let historialPorNombre = new Map();

async function cargarHistorial() {
  try {
    const res = await fetchConTimeout("/api/historial", {}, 8000);
    historialLista = await res.json();
    historialPorNombre = new Map(historialLista.map((h) => [h.nombre.toLowerCase(), h]));
  } catch (error) {
    console.error("Error cargando historial:", error);
    historialLista = [];
    historialPorNombre = new Map();
  }
}

// Retrasa la ejecución hasta que paren de llegar llamadas: evita reconstruir
// listas/grids completos en cada pulsación mientras se escribe (con el
// teclado virtual propio esto se notaba como escritura lenta/no fluida, al
// bloquear el hilo principal entre tecla y tecla).
function debounce(fn, esperaMs) {
  let temporizador;
  return (...args) => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => fn(...args), esperaMs);
  };
}

// Quita acentos para que buscar "platano" encuentre "Plátanos".
function normalizarTexto(texto) {
  const SIN_ACENTOS = new RegExp("[̀-ͯ]", "g");
  return (texto || "")
    .normalize("NFD")
    .replace(SIN_ACENTOS, "")
    .toLowerCase()
    .trim();
}

// Pulsacion corta vs. mantener pulsado, unificando raton y tactil.
// Implementación en modules/gestures.js (testeada en gestures.test.js).
// Nombre distinto al de la función global de gestures.js (agregarPulsacion):
// WebKit/Safari lanza SyntaxError "Can't create duplicate variable that
// shadows a global property" si un script declara aquí un const/let con el
// mismo nombre que una function de nivel superior de otro script previo
// (Chrome/V8 lo permite, Safari no); ese error de parseo rompe app.js entero
// y deja la app en blanco (bug real reportado).
const agregarPulsacionGesto = window.Gestures.agregarPulsacion;

async function cargarCategorias() {
  try {
    const res = await fetchConTimeout("/api/categorias", {}, 8000);
    categorias = await res.json();
    renderFiltros();
    poblarSelectCategoria(campoCategoria, campoCategoria.value);
  } catch (error) {
    console.error("Error cargando categorías:", error);
    Toast.error((window.i18n && window.i18n.t('error_cargar_categorias')) || "No se pudieron cargar las categorías. Comprueba tu conexión.");
    categorias = [];
  }
}

function renderFiltros() {
  const categoriaPrevia = categoriaActiva;
  const textoTodas = (window.i18n && window.i18n.t('todas')) || "Todas";
  filtros.innerHTML = `<button class="chip activo" data-cat="todas">${textoTodas}</button>`;
  for (const cat of categorias) {
    const btnCat = document.createElement("button");
    btnCat.className = "chip";
    btnCat.dataset.cat = cat.nombre;
    btnCat.innerHTML = `${renderIcono(cat.icono)} ${escapeHtml(cat.nombre)}`;
    filtros.appendChild(btnCat);
  }
  categoriaActiva = "todas";
  if (categoriaPrevia !== "todas" && categorias.some((c) => c.nombre === categoriaPrevia)) {
    categoriaActiva = categoriaPrevia;
  }
  filtros.querySelectorAll(".chip").forEach((c) => {
    c.classList.toggle("activo", c.dataset.cat === categoriaActiva);
  });
}

function poblarSelectCategoria(select, seleccionada) {
  select.innerHTML = categorias
    .map((c) => {
      const nombreTrad = (window.i18n && window.i18n.t(window.i18n.claveCategoria(c.nombre))) || c.nombre;
      return `<option value="${escapeHtml(c.nombre)}">${escapeHtml(nombreTrad)}</option>`;
    })
    .join("");
  if (seleccionada) select.value = seleccionada;
}

function renderCategoriasLista() {
  categoriasListaEl.innerHTML = "";
  for (const cat of categorias) {
    const chip = document.createElement("div");
    chip.className = "categoria-chip";
    const nombreCategoriaTrad = (window.i18n && window.i18n.t(window.i18n.claveCategoria(cat.nombre))) || cat.nombre;
    chip.innerHTML = `<span>${renderIcono(cat.icono)} ${escapeHtml(nombreCategoriaTrad)}</span>`;
    if (cat.nombre !== "Otros") {
      const btnBorrar = document.createElement("button");
      btnBorrar.type = "button";
      btnBorrar.title = (window.i18n && window.i18n.t('borrar_categoria_titulo')) || "Borrar categoría";
      btnBorrar.textContent = "✕";
      btnBorrar.addEventListener("click", () => borrarCategoria(cat));
      chip.appendChild(btnBorrar);
    }
    categoriasListaEl.appendChild(chip);
  }
}

async function borrarCategoria(cat) {
  const msjBorrarCategoria = (window.i18n && window.i18n.t('confirmar_borrar_categoria')) || '¿Borrar la categoría "{nombre}"?';
  if (!confirm(msjBorrarCategoria.replace('{nombre}', cat.nombre))) return;

  try {
    const res = await fetchConTimeout(`/api/categorias/${cat.id}`, { method: "DELETE" }, 8000);
    categorias = categorias.filter((c) => c.id !== cat.id);
    renderCategoriasLista();
    renderFiltros();
    poblarSelectCategoria(campoCategoria, campoCategoria.value);
    render();
  } catch (error) {
    console.error("Error borrando categoría:", error);
    Toast.error(error.message || (window.i18n && window.i18n.t('error_borrar_categoria')) || "No se pudo borrar la categoría. Inténtalo de nuevo.");
  }
}

// Modal superpuesta para seleccionar icono: única implementación del
// selector, reutilizada por categorías, producto, compra y espacio.
const modalSelectorIconos = document.getElementById("modalSelectorIconos");
const contenedorIconos = document.getElementById("contenedorIconos");
const buscadorIconos = document.getElementById("buscadorIconos");
const btnCerrarSelectorIconos = document.getElementById("btnCerrarSelectorIconos");

let callbackIconoSeleccionado = null;
let iconoActualmentSeleccionado = null;

function renderizarIconosGrid(filtro = "") {
  contenedorIconos.innerHTML = "";
  const texto = filtro.trim().toLowerCase();
  const items = texto
    ? CATALOGO_ICONOS.filter((it) => it.palabras.some((p) => p.includes(texto)))
    : CATALOGO_ICONOS;

  for (const it of items) {
    const btnIcono = document.createElement("button");
    btnIcono.type = "button";
    btnIcono.innerHTML = renderIcono(it.icono, { tamano: 28 });
    btnIcono.title = it.palabras[0] || "";
    btnIcono.className = it.icono === iconoActualmentSeleccionado ? "seleccionado" : "";
    btnIcono.addEventListener("click", (e) => {
      e.preventDefault();
      if (callbackIconoSeleccionado) {
        callbackIconoSeleccionado(it.icono);
      }
      cerrarModalSelectorIconos();
    });
    contenedorIconos.appendChild(btnIcono);
  }

  if (items.length === 0) {
    const vacioAviso = document.createElement("p");
    vacioAviso.className = "aviso";
    vacioAviso.textContent = (window.i18n && window.i18n.t('sin_iconos_coincidentes')) || "Ningún icono coincide con esa búsqueda.";
    contenedorIconos.appendChild(vacioAviso);
  }
}

function abrirModalSelectorIconos(iconoSeleccionado, callback) {
  callbackIconoSeleccionado = callback;
  iconoActualmentSeleccionado = iconoSeleccionado;
  buscadorIconos.value = "";
  renderizarIconosGrid("");
  modalSelectorIconos.hidden = false;
  buscadorIconos.focus();
}

function cerrarModalSelectorIconos() {
  modalSelectorIconos.hidden = true;
  contenedorIconos.innerHTML = "";
  buscadorIconos.value = "";
  callbackIconoSeleccionado = null;
  iconoActualmentSeleccionado = null;
}

// Event listener para el buscador
buscadorIconos.addEventListener(
  "input",
  debounce(() => {
    renderizarIconosGrid(buscadorIconos.value);
  }, 150)
);

btnCerrarSelectorIconos.addEventListener("click", cerrarModalSelectorIconos);

habilitarBottomSheet(modalSelectorIconos, modalSelectorIconos.querySelector(".modal"), cerrarModalSelectorIconos);

function abrirModalCategorias() {
  renderCategoriasLista();
  formCategoria.reset();
  categoriaCampoIcono.value = "h-folder";
  categoriaIconoElegido.innerHTML = renderIcono("h-folder");
  modalCategoriasFondo.hidden = false;
  modalCategoriasFondo.scrollTop = 0;
  const contenido = modalCategoriasFondo.querySelector(".modal-content");
  if (contenido) contenido.scrollTop = 0;
}

function cerrarModalCategorias() {
  modalCategoriasFondo.hidden = true;
}

btnCategorias.addEventListener("click", abrirModalCategorias);
btnCerrarCategorias.addEventListener("click", cerrarModalCategorias);
habilitarBottomSheet(modalCategoriasFondo, modalCategoriasFondo.querySelector(".modal"), cerrarModalCategorias);

// Botón para seleccionar icono en categorías
const btnSeleccionarIconoCategoria = document.getElementById("btnSeleccionarIconoCategoria");
if (btnSeleccionarIconoCategoria) {
  btnSeleccionarIconoCategoria.addEventListener("click", (e) => {
    e.preventDefault();
    abrirModalSelectorIconos(categoriaCampoIcono.value, (icono) => {
      categoriaCampoIcono.value = icono;
      categoriaIconoElegido.innerHTML = renderIcono(icono);
    });
  });
}

formCategoria.addEventListener("submit", async (e) => {
  e.preventDefault();
  const nombre = categoriaCampoNombre.value.trim();
  if (!nombre) return;
  if (categorias.some((c) => c.nombre.localeCompare(nombre, "es", { sensitivity: "base" }) === 0)) {
    Toast.error("Ya existe una categoría con ese nombre");
    return;
  }
  const icono = categoriaCampoIcono.value || "h-folder";

  botonesEnviarCategoria.forEach((btn) => (btn.disabled = true));
  let datos;
  try {
    const res = await fetch("/api/categorias", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, icono }),
    });
    datos = await res.json();
    if (!res.ok) {
      Toast.error(datos.error || "No se pudo crear la categoría");
      return;
    }
  } catch (error) {
    console.error("Error creando categoría:", error);
    Toast.error("No se pudo crear la categoría. Comprueba tu conexión e inténtalo de nuevo.");
    return;
  } finally {
    botonesEnviarCategoria.forEach((btn) => (btn.disabled = false));
  }

  categorias.push(datos);
  categorias.sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  renderCategoriasLista();
  renderFiltros();
  poblarSelectCategoria(campoCategoria, campoCategoria.value);

  cerrarModalCategorias();
  formCategoria.reset();
  categoriaCampoIcono.value = "h-folder";
  categoriaIconoElegido.innerHTML = renderIcono("h-folder");
  categoriaCampoNombre.focus();
});

/* --- Stock --- */

async function cargarProductos() {
  try {
    const res = await fetchConTimeout("/api/productos", {}, 10000);
    productos = await res.json();
    render();
  } catch (error) {
    console.error("Error cargando productos:", error);
    Toast.error("No se pudo cargar el stock. Comprueba tu conexión.");
    productos = [];
    render();
  }
}

function render() {
  const filtrados = productos.filter((p) => {
    const pasaCategoria = categoriaActiva === "todas" || p.categoria === categoriaActiva;
    const pasaTexto = p.nombre.toLowerCase().includes(textoBusqueda.toLowerCase());
    return pasaCategoria && pasaTexto;
  });

  lista.innerHTML = "";
  vacio.hidden = filtrados.length !== 0;

  for (const p of filtrados) {
    lista.appendChild(crearTarjeta(p));
  }
}

function crearTarjeta(p) {
  const div = document.createElement("div");
  // <= (no <): igual que el aviso automático del backend (revisar_stock_bajo),
  // así la tarjeta se marca "pocas unidades" exactamente cuando ese aviso se dispara.
  const bajoStock = p.cantidad <= p.stock_minimo;
  div.className = "tarjeta" + (bajoStock ? " bajo" : "") + (p.revisar_caducidad ? " aviso-caducidad" : "");

  const avisos = [];
  if (bajoStock) avisos.push("¡Pocas unidades!");
  if (p.revisar_caducidad) avisos.push("⏰ Revisar caducidad");

  div.innerHTML = `
    <div class="icono">${renderIcono(iconoEfectivo(p), { tamano: 26 })}</div>
    <div class="info">
      <div class="nombre">${escapeHtml(p.nombre)}</div>
      <div class="detalle" data-categoria-original="${escapeHtml(p.categoria)}">${escapeHtml(p.categoria)}${avisos.length ? " · " + avisos.join(" · ") : ""}</div>
    </div>
    <div class="contador">
      <button data-accion="restar" title="Quitar uno" ${productosEnProceso.has(p.id) ? "disabled" : ""}>−</button>
      <span class="cantidad">${p.cantidad} ${escapeHtml(p.unidad)}</span>
      <button data-accion="sumar" title="Añadir uno" ${productosEnProceso.has(p.id) ? "disabled" : ""}>+</button>
    </div>
    <div class="acciones">
      <button data-accion="editar" title="Editar">✏️</button>
      <button data-accion="borrar" title="Eliminar">🗑️</button>
    </div>
  `;

  div.querySelector('[data-accion="sumar"]').addEventListener("click", () => cambiarCantidad(p.id, 1));
  div.querySelector('[data-accion="restar"]').addEventListener("click", () => cambiarCantidad(p.id, -1));
  div.querySelector('[data-accion="editar"]').addEventListener("click", () => abrirModal(p));
  div.querySelector('[data-accion="borrar"]').addEventListener("click", () => borrarProducto(p.id));

  return div;
}

async function cambiarCantidad(id, delta) {
  if (productosEnProceso.has(id)) return;
  productosEnProceso.add(id);

  let actualizado;
  try {
    // fetchConTimeout ya lanza (con el mensaje del servidor si lo hay) si la
    // respuesta no es res.ok, así que aquí solo queda validar el cuerpo.
    const res = await fetchConTimeout(`/api/productos/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ delta }),
    }, 8000);
    const datos = await res.json().catch(() => null);
    if (!datos || !datos.id) {
      console.error("Respuesta inválida del servidor", datos);
      Toast.error("Respuesta inválida del servidor al cambiar la cantidad");
      return;
    }
    actualizado = datos;
  } catch (error) {
    console.error("Error cambiando cantidad:", error);
    Toast.error(error.message || "No se pudo cambiar la cantidad. Comprueba tu conexión e inténtalo de nuevo.");
    return;
  } finally {
    productosEnProceso.delete(id);
  }

  productos = productos.map((p) => (p.id === id ? actualizado : p));
  render();
  cargarListaCompra();
}

async function borrarProducto(id) {
  if (!confirm((window.i18n && window.i18n.t('confirmar_eliminar_producto_stock')) || "¿Eliminar este producto del stock?")) return;
  try {
    const res = await fetch(`/api/productos/${id}`, { method: "DELETE" });
    if (!res.ok) {
      const datos = await res.json().catch(() => null);
      Toast.error(datos?.error || "No se pudo eliminar el producto");
      return;
    }
  } catch (error) {
    console.error("Error borrando producto:", error);
    Toast.error("No se pudo eliminar el producto. Comprueba tu conexión e inténtalo de nuevo.");
    return;
  }
  productos = productos.filter((p) => p.id !== id);
  render();
}

let iconoProductoTocado = false;

function actualizarSelectorIconoProducto() {
  btnQuitarIconoProducto.hidden = !campoIcono.value;
  // Mostrar el icono actual en el botón
  iconoProductoDisplay.innerHTML = campoIcono.value ? renderIcono(campoIcono.value) : "Elegir icono";
}

// producto === undefined/null -> alta en blanco.
// producto sin "id" (una entrada del catálogo) -> alta prellenada con esos datos.
// producto con "id" (un producto real del stock) -> edición de ese producto.
function abrirModal(producto) {
  form.reset();
  document.getElementById("productoId").value = "";
  document.getElementById("campoCantidad").value = 1;
  document.getElementById("campoUnidad").value = "ud";
  document.getElementById("campoMinimo").value = 1;
  document.getElementById("campoDiasAviso").value = 30;
  poblarSelectCategoria(campoCategoria, null);
  campoIcono.value = "";
  iconoProductoTocado = false;

  const esEdicion = Boolean(producto && producto.id !== undefined);
  if (esEdicion) {
    modalTitulo.textContent = (window.i18n && window.i18n.t('editar_producto')) || "Editar producto";
    document.getElementById("productoId").value = producto.id;
    document.getElementById("campoNombre").value = producto.nombre;
    campoCategoria.value = producto.categoria;
    document.getElementById("campoCantidad").value = producto.cantidad;
    document.getElementById("campoUnidad").value = producto.unidad;
    document.getElementById("campoMinimo").value = producto.stock_minimo;
    document.getElementById("campoDiasAviso").value = producto.dias_aviso;
    campoIcono.value = producto.icono || "";
    iconoProductoTocado = true;
  } else if (producto) {
    const plantillaAñadirStock = (window.i18n && window.i18n.t('añadir_x_al_stock')) || 'Añadir "{nombre}" al stock';
    modalTitulo.textContent = plantillaAñadirStock.replace('{nombre}', producto.nombre);
    document.getElementById("campoNombre").value = producto.nombre || "";
    poblarSelectCategoria(campoCategoria, producto.categoria || null);
    document.getElementById("campoCantidad").value = producto.cantidad || 1;
    document.getElementById("campoUnidad").value = producto.unidad || "ud";
    campoIcono.value = producto.icono || "";
    iconoProductoTocado = Boolean(producto.icono);
  } else {
    modalTitulo.textContent = (window.i18n && window.i18n.t('nuevo_producto')) || "Nuevo producto";
  }

  actualizarSelectorIconoProducto();
  modalFondo.hidden = false;
  if (esEdicion || !producto) {
    document.getElementById("campoNombre").focus();
  } else {
    // Viene precargado desde el catálogo: la cantidad es lo unico que hay
    // que confirmar obligatoriamente antes de guardar.
    const campoCantidad = document.getElementById("campoCantidad");
    campoCantidad.focus();
    campoCantidad.select();
  }
}

function cerrarModal() {
  modalFondo.hidden = true;
}

// Botón para seleccionar icono en el formulario de producto
btnSeleccionarIconoProducto.addEventListener("click", (e) => {
  e.preventDefault();
  abrirModalSelectorIconos(campoIcono.value, (icono) => {
    campoIcono.value = icono;
    iconoProductoTocado = true;
    actualizarSelectorIconoProducto();
  });
});

btnQuitarIconoProducto.addEventListener("click", () => {
  campoIcono.value = "";
  iconoProductoTocado = true;
  actualizarSelectorIconoProducto();
});

document.getElementById("campoNombre").addEventListener("input", (e) => {
  if (document.getElementById("productoId").value || iconoProductoTocado) return;
  const recuerdo = historialPorNombre.get(e.target.value.trim().toLowerCase());
  if (recuerdo) {
    campoIcono.value = recuerdo.icono;
    actualizarSelectorIconoProducto();
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("productoId").value;
  const cantidadRaw = document.getElementById("campoCantidad").value;
  const minimoRaw = document.getElementById("campoMinimo").value;
  const cantidad = Number(cantidadRaw);
  const stockMinimo = Number(minimoRaw);

  if (!Number.isInteger(cantidad) || cantidad < 0 || !Number.isInteger(stockMinimo) || stockMinimo < 0) {
    Toast.error("La cantidad y el stock mínimo deben ser números enteros y no negativos.");
    return;
  }

  const payload = {
    nombre: document.getElementById("campoNombre").value.trim(),
    categoria: campoCategoria.value,
    icono: campoIcono.value || "",
    cantidad,
    unidad: document.getElementById("campoUnidad").value.trim() || "ud",
    stock_minimo: stockMinimo,
    dias_aviso: Number(document.getElementById("campoDiasAviso").value),
  };
  if (!payload.nombre) return;

  botonesEnviarProducto.forEach((btn) => (btn.disabled = true));
  try {
    if (id) {
      const res = await fetch(`/api/productos/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        Toast.error(error.error || "No se pudo guardar los cambios.");
        return;
      }
      const actualizado = await res.json();
      productos = productos.map((p) => (p.id === actualizado.id ? actualizado : p));
    } else {
      const res = await fetch("/api/productos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        Toast.error(error.error || "No se pudo crear el producto.");
        return;
      }
      const creado = await res.json();
      productos.push(creado);

      // Traducir automáticamente el nombre del producto a todos los idiomas
      // (en background, sin bloquear la UI)
      fetch("/api/productos/traducir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: payload.nombre,
          producto_id: creado.id
        })
      }).catch(err => console.warn('Traducción automática fallida:', err));
    }
  } finally {
    botonesEnviarProducto.forEach((btn) => (btn.disabled = false));
  }

  cerrarModal();
  render();
  cargarListaCompra();
  cargarHistorial();
});

btnCancelar.addEventListener("click", cerrarModal);
habilitarBottomSheet(modalFondo, modalFondo.querySelector(".modal"), cerrarModal);

buscador.addEventListener(
  "input",
  debounce((e) => {
    textoBusqueda = e.target.value;
    render();
  }, 150)
);

filtros.addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  categoriaActiva = btn.dataset.cat;
  filtros.querySelectorAll(".chip").forEach((c) => c.classList.remove("activo"));
  btn.classList.add("activo");
  render();
});

/* --- Pestañas --- */

tabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  vistaActiva = btn.dataset.vista;
  tabs.querySelectorAll(".tab").forEach((t) => t.classList.remove("activo"));
  btn.classList.add("activo");
  vistaStock.hidden = vistaActiva !== "stock";
  vistaCompra.hidden = vistaActiva !== "compra";
});

fab.addEventListener("click", () => {
  abrirModalCatalogo(vistaActiva === "compra" ? "compra" : "stock");
});

/* --- Lista de la compra --- */

async function cargarListaCompra() {
  const listaId = localStorage.getItem('lista-actual');
  if (!listaId) return;

  try {
    const res = await fetchConTimeout(`/api/articulos?lista_id=${listaId}`, {}, 8000);
    const datos = await res.json();
    pendientesCompra = datos.data?.pendientes || datos.pendientes || [];
    completadosCompra = datos.data?.completados || datos.completados || [];
    renderListaCompra();
  } catch (error) {
    console.error("Error cargando lista de compra:", error);
    Toast.error("No se pudo cargar la lista de la compra. Comprueba tu conexión.");
    pendientesCompra = [];
    completadosCompra = [];
    renderListaCompra();
  }
}

function ordenGrupos(nombresCategorias) {
  // Mismo orden que las categorias (alfabetico), con cualquier categoria
  // huerfana (borrada despues de crear el articulo) al final.
  const orden = categorias.map((c) => c.nombre);
  return [...nombresCategorias].sort((a, b) => {
    const posA = orden.indexOf(a);
    const posB = orden.indexOf(b);
    if (posA === -1 && posB === -1) return a.localeCompare(b, "es");
    if (posA === -1) return 1;
    if (posB === -1) return -1;
    return posA - posB;
  });
}

function renderListaCompra() {
  gruposCompraEl.innerHTML = "";
  compraVacia.hidden = pendientesCompra.length !== 0;

  const porCategoria = new Map();
  for (const item of pendientesCompra) {
    if (!porCategoria.has(item.categoria)) porCategoria.set(item.categoria, []);
    porCategoria.get(item.categoria).push(item);
  }

  for (const nombreCategoria of ordenGrupos([...porCategoria.keys()])) {
    const grupo = document.createElement("div");
    grupo.className = "grupo-compra";
    const titulo = document.createElement("h3");
    titulo.className = "grupo-compra-titulo";
    titulo.innerHTML = `${renderIcono(iconoDeCategoria(nombreCategoria))} ${escapeHtml(nombreCategoria)}`;
    const rejilla = document.createElement("div");
    rejilla.className = "tiles-grid";
    for (const item of porCategoria.get(nombreCategoria)) {
      rejilla.appendChild(crearTileCompra(item, false));
    }
    grupo.append(titulo, rejilla);
    gruposCompraEl.appendChild(grupo);
  }

  tilesCompletadosEl.innerHTML = "";
  seccionCompletadosEl.hidden = completadosCompra.length === 0;
  for (const item of completadosCompra) {
    tilesCompletadosEl.appendChild(crearTileCompra(item, true));
  }
}

function crearTileCompra(item, completado) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "tile-compra" + (completado ? " completado" : "");
  const detalle = [item.unidad, item.sub_descripcion].filter(Boolean).join(" · ");
  btn.title = completado
    ? `Volver a añadir a la lista${detalle ? " · " + detalle : ""}`
    : `Mantén pulsado para editar${detalle ? " · " + detalle : ""}`;
  btn.innerHTML = `
    <span class="tile-compra-icono">${renderIcono(iconoEfectivo(item), { tamano: 30 })}</span>
    <span class="tile-compra-nombre">${escapeHtml(item.nombre)}</span>
    ${item.cantidad > 1 ? `<span class="tile-compra-cantidad">×${item.cantidad}</span>` : ""}
  `;
  if (completado) {
    btn.addEventListener("click", () => restaurarItemCompra(item.id));
  } else {
    agregarPulsacionGesto(
      btn,
      () => completarItemCompra(item.id, btn),
      () => {
        volverAlCatalogoTrasCompra = false;
        abrirModalCompra(item);
      }
    );
  }
  return btn;
}

async function completarItemCompra(id, elemento) {
  elemento.classList.add("completando");
  elemento.disabled = true;
  setTimeout(async () => {
    try {
      const res = await fetch(`/api/articulos/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activo: false }),
      });
      if (!res.ok) {
        const datos = await res.json().catch(() => null);
        Toast.error(datos?.error || "No se pudo marcar como comprado.");
      }
    } catch (error) {
      console.error("Error completando artículo:", error);
      Toast.error("No se pudo marcar como comprado. Comprueba tu conexión.");
    } finally {
      // Siempre recargar: si falló, esto también deshace el estado
      // "completando"/disabled dejado por el bloque de arriba.
      await cargarListaCompra();
    }
  }, 280);
}

async function restaurarItemCompra(id) {
  await fetch(`/api/articulos/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ activo: true }),
  });
  await cargarListaCompra();
}

btnToggleCompletados.addEventListener("click", () => {
  seccionCompletadosEl.classList.toggle("plegada");
});

let iconoCompraTocado = false;

function actualizarSelectorIconoCompra() {
  btnQuitarIconoCompra.hidden = !compraCampoIcono.value;
  // Mostrar el icono actual en el botón
  iconoCompraDisplay.innerHTML = compraCampoIcono.value ? renderIcono(compraCampoIcono.value) : "Elegir icono";
}

// item === undefined/null -> alta en blanco.
// item sin "id" (una entrada del catálogo) -> alta prellenada con esos datos.
// item con "id" (una fila real de la lista) -> edición de ese artículo.
function abrirModalCompra(item) {
  formCompra.reset();
  const esEdicion = Boolean(item && item.id !== undefined);
  compraEditIdEl.value = esEdicion ? item.id : "";
  // Establecer ID de artículo personalizado si existe
  const articuloPersonalizadoId = item && item.articulo_personalizado_id;
  document.getElementById("compraArticuloPersonalizadoId").value = articuloPersonalizadoId || "";
  
  const t = (clave, fallback) => (window.i18n ? window.i18n.t(clave) : fallback);
  compraModalTitulo.textContent = esEdicion
    ? t("editar_articulo", "Editar artículo")
    : item
    ? t("añadir_x", 'Añadir "{nombre}"').replace("{nombre}", item.nombre)
    : t("añadir_a_lista_compra", "Añadir a la lista de la compra");
  compraBotonGuardar.textContent = esEdicion ? t("guardar", "Guardar") : t("añadir", "Añadir");
  document.getElementById("btnBorrarArticulo").hidden = !esEdicion;
  // Mostrar botón de edición avanzada solo si es artículo personalizado
  const btnEdicionAvanzada = document.getElementById("btnEdicionAvanzada");
  if (btnEdicionAvanzada) {
    btnEdicionAvanzada.hidden = !articuloPersonalizadoId;
  }

  document.getElementById("compraCampoNombre").value = item ? item.nombre : "";
  compraCampoCantidad.value = (item && item.cantidad) || 1;
  document.getElementById("compraCampoUnidad").value = (item && item.unidad) || "ud";
  compraCampoSubdescripcion.value = (item && item.sub_descripcion) || "";
  poblarSelectCategoria(compraCampoCategoria, item ? item.categoria : null);

  compraCampoIcono.value = (item && item.icono) || "";
  iconoCompraTocado = Boolean(compraCampoIcono.value);
  actualizarSelectorIconoCompra();

  modalCompraFondo.hidden = false;
  document.getElementById("compraCampoNombre").focus();
}

let volverAlCatalogoTrasCompra = false;

function cerrarModalCompra() {
  modalCompraFondo.hidden = true;
  if (volverAlCatalogoTrasCompra) {
    volverAlCatalogoTrasCompra = false;
    abrirModalCatalogo();
  }
}

// Botón para seleccionar icono en el formulario de compra
btnSeleccionarIconoCompra.addEventListener("click", (e) => {
  e.preventDefault();
  abrirModalSelectorIconos(compraCampoIcono.value, (icono) => {
    compraCampoIcono.value = icono;
    iconoCompraTocado = true;
    actualizarSelectorIconoCompra();
  });
});

btnQuitarIconoCompra.addEventListener("click", () => {
  compraCampoIcono.value = "";
  iconoCompraTocado = true;
  actualizarSelectorIconoCompra();
});

document.getElementById("compraCampoNombre").addEventListener("input", (e) => {
  if (iconoCompraTocado) return;
  const recuerdo = historialPorNombre.get(e.target.value.trim().toLowerCase());
  if (recuerdo) {
    compraCampoIcono.value = recuerdo.icono;
    actualizarSelectorIconoCompra();
  }
});

formCompra.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = compraEditIdEl.value;
  const listaId = localStorage.getItem('lista-actual');
  if (!listaId) {
    Toast.error("Selecciona una lista primero");
    return;
  }

  const payload = {
    nombre: document.getElementById("compraCampoNombre").value.trim(),
    cantidad: Number(compraCampoCantidad.value) || 1,
    unidad: document.getElementById("compraCampoUnidad").value.trim() || "ud",
    categoria: compraCampoCategoria.value,
    icono: compraCampoIcono.value || "",
    sub_descripcion: compraCampoSubdescripcion.value.trim(),
  };
  if (!payload.nombre) return;

  if (!id) {
    payload.lista_id = parseInt(listaId);
  }

  botonesEnviarCompra.forEach((btn) => (btn.disabled = true));
  try {
    // Si es una edición y el artículo tiene ID personalizado, usar API de artículos personalizados
    const articuloPersonalizadoId = document.getElementById("compraArticuloPersonalizadoId")?.value;
    let catalogoPersonalizadoActualizado = false;
    if (id && articuloPersonalizadoId) {
      try {
        const articuloActualizado = await editarArticuloPersonalizado(articuloPersonalizadoId, payload);
        console.log("Artículo personalizado actualizado:", articuloActualizado);
        catalogoPersonalizadoActualizado = true;
      } catch (error) {
        console.error("Error actualizando artículo personalizado:", error);
        Toast.error(error.message || "No se pudo actualizar el artículo personalizado. Inténtalo de nuevo.");
        return;
      }
    }

    let articulo;
    try {
      const res = await fetch(id ? `/api/articulos/${id}` : "/api/articulos", {
        method: id ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      articulo = await res.json();
      if (!res.ok) {
        // Si el catálogo personalizado ya se actualizó por encima, el estado
        // ha quedado parcialmente aplicado: avisar de eso en vez de un error
        // generico que sugiere que no se guardó nada.
        if (catalogoPersonalizadoActualizado) {
          Toast.error(
            "El artículo del catálogo se actualizó, pero no se pudo guardar en esta lista: " +
            (articulo?.error || "inténtalo de nuevo")
          );
          cargarListaCompra();
        } else {
          Toast.error(articulo?.error || "No se pudo guardar el artículo");
        }
        return;
      }
    } catch (error) {
      console.error("Error guardando artículo:", error);
      if (catalogoPersonalizadoActualizado) {
        Toast.error("El artículo del catálogo se actualizó, pero no se pudo guardar en esta lista. Comprueba tu conexión e inténtalo de nuevo.");
        cargarListaCompra();
      } else {
        Toast.error("No se pudo guardar el artículo. Comprueba tu conexión e inténtalo de nuevo.");
      }
      return;
    }

    // Traducir automáticamente el nombre del artículo a todos los idiomas
    // (en background, sin bloquear la UI)
    if (!id && articulo && articulo.id) {
      fetch("/api/productos/traducir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: payload.nombre,
          descripcion: payload.sub_descripcion || "",
          articulo_id: articulo.id
        })
      }).catch(err => console.warn('Traducción automática fallida:', err));
    }

    cerrarModalCompra();
    cargarListaCompra();
    cargarHistorial();
  } finally {
    botonesEnviarCompra.forEach((btn) => (btn.disabled = false));
  }
});

btnCancelarCompra.addEventListener("click", cerrarModalCompra);

const btnBorrarArticuloEl = document.getElementById("btnBorrarArticulo");
if (btnBorrarArticuloEl) {
  btnBorrarArticuloEl.addEventListener("click", async () => {
    const id = compraEditIdEl.value;
    if (!id || !confirm((window.i18n && window.i18n.t('confirmar_borrar_articulo_lista')) || "¿Borrar este artículo de la lista?")) return;

    try {
      await fetchConTimeout(`/api/articulos/${id}`, { method: "DELETE" }, 8000);
      cerrarModalCompra();
      await cargarListaCompra();
    } catch (error) {
      console.error("Error eliminando artículo:", error);
      Toast.error(error.message || "No se pudo eliminar el artículo. Inténtalo de nuevo.");
    }
  });
}

habilitarBottomSheet(modalCompraFondo, modalCompraFondo.querySelector(".modal"), cerrarModalCompra);

// Botón de edición avanzada para artículos personalizados
const btnEdicionAvanzadaEl = document.getElementById("btnEdicionAvanzada");
if (btnEdicionAvanzadaEl) {
  btnEdicionAvanzadaEl.addEventListener("click", () => {
    const articuloPersonalizadoId = document.getElementById("compraArticuloPersonalizadoId").value;
    if (!articuloPersonalizadoId) {
      Toast.info("Este artículo no es personalizado, no tiene edición avanzada.");
      return;
    }
    // Abrir modal de edición avanzada (por ahora solo alerta)
    const plantillaEdicionAvanzada = (window.i18n && window.i18n.t('edicion_avanzada_articulo')) || 'Edición avanzada para artículo personalizado ID {id}. Esta funcionalidad puede extenderse en el futuro.';
    alert(plantillaEdicionAvanzada.replace('{id}', articuloPersonalizadoId));
    // En el futuro: abrir un modal específico para traducciones y detalles avanzados
  });
}

// ===== FUNCIONES PARA ARTÍCULOS PERSONALIZADOS =====

/**
 * Edita un artículo personalizado
 */
async function editarArticuloPersonalizado(articuloId, datos) {
  try {
    const res = await fetch(`/api/articulos/personalizados/${articuloId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos)
    });

    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.error || 'Error al actualizar');
    }

    return await res.json();
  } catch (error) {
    console.error('Error editando artículo personalizado:', error);
    throw error;
  }
}

/**
 * Elimina un artículo personalizado
 */
async function eliminarArticuloPersonalizado(articuloId) {
  try {
    const res = await fetch(`/api/articulos/personalizados/${articuloId}`, {
      method: "DELETE"
    });

    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.error || 'Error al eliminar');
    }

    return true;
  } catch (error) {
    console.error('Error eliminando artículo personalizado:', error);
    throw error;
  }
}

/**
 * Obtiene traducciones de un artículo personalizado
 */
async function obtenerTraduccionesArticulo(articuloId, idioma) {
  try {
    const res = await fetch(`/api/articulos/personalizados/${articuloId}/traducciones/${idioma}`);

    if (!res.ok) {
      return null;
    }

    const data = await res.json();
    return data.data || null;
  } catch (error) {
    console.warn(`No hay traducciones para artículo ${articuloId}:`, error);
    return null;
  }
}

/* --- Catálogo (navegar y añadir a la lista por categorías) --- */

let catalogoModo = "compra"; // "compra" (lista de la compra) o "stock" (alta directa de producto)

function abrirModalCatalogo(modo = "compra") {
  catalogoModo = modo;
  const botonesAccion = document.querySelector("#accionesModalCatalogo");
  if (modo === "stock") {
    catalogoTitulo.textContent = (window.i18n && window.i18n.t('añadir_al_stock')) || "Añadir al stock";
    catalogoAyuda.textContent = (window.i18n && window.i18n.t('ayuda_stock_catalogo')) || "Toca un producto para indicar su cantidad y añadirlo al stock.";
    if (btnCrearDesdeCatalogo) btnCrearDesdeCatalogo.textContent = "+";
    if (botonesAccion) botonesAccion.style.display = "flex";
  } else {
    catalogoTitulo.textContent = (window.i18n && window.i18n.t('añadir_a_la_lista')) || "Añadir a la lista";
    catalogoAyuda.textContent = (window.i18n && window.i18n.t('ayuda_lista_catalogo')) || "Toca un producto para añadirlo (el fondo se resaltará cuando esté en tu lista).";
    if (botonesAccion) botonesAccion.style.display = "none";
  }
  catalogoBuscadorEl.value = "";
  renderCatalogo("");
  modalCatalogoFondo.hidden = false;
  catalogoBuscadorEl.focus();
}

function cerrarModalCatalogo() {
  modalCatalogoFondo.hidden = true;
}

function renderCatalogo(filtro) {
  const texto = normalizarTexto(filtro);
  const items = texto
    ? historialLista.filter((h) => normalizarTexto(h.nombre).includes(texto))
    : historialLista;

  catalogoGruposEl.innerHTML = "";
  catalogoVacioEl.hidden = items.length !== 0;
  if (items.length === 0) {
    catalogoVacioEl.textContent = filtro
      ? `Ningún producto coincide con "${filtro}". Puedes crearlo como nuevo.`
      : "Todavía no hay ningún producto en el catálogo.";
  }

  const porCategoria = new Map();
  for (const item of items) {
    const cat = item.categoria || "Otros";
    if (!porCategoria.has(cat)) porCategoria.set(cat, []);
    porCategoria.get(cat).push(item);
  }

  for (const nombreCategoria of ordenGrupos([...porCategoria.keys()])) {
    const grupo = document.createElement("div");
    grupo.className = "grupo-compra";
    const titulo = document.createElement("h3");
    titulo.className = "grupo-compra-titulo";
    titulo.innerHTML = `${renderIcono(iconoDeCategoria(nombreCategoria))} ${escapeHtml(nombreCategoria)}`;
    const rejilla = document.createElement("div");
    rejilla.className = "tiles-grid";
    for (const item of porCategoria.get(nombreCategoria)) {
      rejilla.appendChild(crearTileCatalogo(item));
    }
    grupo.append(titulo, rejilla);
    catalogoGruposEl.appendChild(grupo);
  }
}

function articuloEnLista(nombre) {
  return pendientesCompra.some((a) => a.nombre === nombre);
}

function crearTileCatalogo(entry) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "tile-compra";
  const detalle = [entry.unidad, entry.sub_descripcion].filter(Boolean).join(" · ");
  btn.innerHTML = `
    <span class="tile-compra-icono">${renderIcono(entry.icono || iconoDeCategoria(entry.categoria), { tamano: 30 })}</span>
    <span class="tile-compra-nombre">${escapeHtml(entry.nombre)}</span>
  `;

  if (catalogoModo === "stock") {
    btn.title = `Toca para indicar la cantidad y añadir al stock${detalle ? " · " + detalle : ""}`;
    btn.addEventListener("click", () => {
      cerrarModalCatalogo();
      abrirModal({ ...entry, cantidad: entry.cantidad_defecto || 1 });
    });
    return btn;
  }

  // Modo compra: toggle añadir/quitar de lista
  const enLista = articuloEnLista(entry.nombre);
  if (enLista) {
    btn.classList.add("tile-en-lista");
  }
  btn.title = `Toca para ${enLista ? "quitar de" : "añadir a"} la lista${detalle ? " · " + detalle : ""}`;
  btn.addEventListener("click", () => toggleArticuloEnLista(entry, btn));
  return btn;
}

async function anadirDesdeCatalogo(entry) {
  const listaId = localStorage.getItem('lista-actual');
  if (!listaId) {
    Toast.error("Selecciona una lista primero");
    return;
  }

  await fetch("/api/articulos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      lista_id: parseInt(listaId),
      nombre: entry.nombre,
      categoria: entry.categoria,
      icono: entry.icono,
      unidad: entry.unidad,
      sub_descripcion: entry.sub_descripcion,
    }),
  });
  cargarListaCompra();
}

async function toggleArticuloEnLista(entry, btn) {
  // Evita que un doble-tap dispare dos peticiones antes de que la primera
  // termine (ambas verían pendientesCompra desactualizado y duplicarían el alta).
  if (btn.disabled) return;

  const listaId = localStorage.getItem('lista-actual');
  if (!listaId) {
    Toast.error("Selecciona una lista primero");
    return;
  }

  btn.disabled = true;
  try {
    const enLista = articuloEnLista(entry.nombre);
    if (enLista) {
      const articulo = pendientesCompra.find((a) => a.nombre === entry.nombre);
      if (articulo) {
        await fetch(`/api/articulos/${articulo.id}`, { method: "DELETE" });
      }
    } else {
      await fetch("/api/articulos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lista_id: parseInt(listaId),
          nombre: entry.nombre,
          categoria: entry.categoria,
          icono: entry.icono,
          unidad: entry.unidad,
          sub_descripcion: entry.sub_descripcion,
        }),
      });
    }
    await cargarListaCompra();

    // Solo actualizar el color del botón, sin regenerar todo el catálogo
    const ahora_enLista = articuloEnLista(entry.nombre);
    if (ahora_enLista) {
      btn.classList.add("tile-en-lista");
      btn.title = `Toca para quitar de la lista`;
    } else {
      btn.classList.remove("tile-en-lista");
      btn.title = `Toca para añadir a la lista`;
    }
  } finally {
    btn.disabled = false;
  }
}

catalogoBuscadorEl.addEventListener(
  "input",
  debounce((e) => renderCatalogo(e.target.value), 150)
);

if (btnCrearDesdeCatalogo) {
  btnCrearDesdeCatalogo.addEventListener("click", () => {
    const nombrePrevio = catalogoBuscadorEl.value.trim();
    cerrarModalCatalogo();
    if (catalogoModo === "stock") {
      abrirModal(nombrePrevio ? { nombre: nombrePrevio, cantidad: 1 } : null);
    } else {
      volverAlCatalogoTrasCompra = true;
      abrirModalCompra(nombrePrevio ? { nombre: nombrePrevio, cantidad: 1 } : null);
    }
  });
}

if (btnCerrarCatalogo) {
  btnCerrarCatalogo.addEventListener("click", cerrarModalCatalogo);
}
habilitarBottomSheet(modalCatalogoFondo, modalCatalogoFondo.querySelector(".modal"), cerrarModalCatalogo);

/* --- Ajustes --- */

function abrirModalAjustes() {
  modalAjustesFondo.hidden = false;
}

function cerrarModalAjustes() {
  modalAjustesFondo.hidden = true;
}

// Event listeners for settings modal are added during late initialization

/* --- Consumo --- */

async function abrirModalConsumo() {
  modalConsumoFondo.hidden = false;
  consumoPorProductoEl.innerHTML = "";
  consumoVacioEl.hidden = true;

  try {
    const res = await fetch("/api/consumo/resumen?dias=30");
    const datos = await res.json();
    if (!res.ok) {
      Toast.error(datos.error || "No se pudo cargar el consumo");
      return;
    }

    const porProducto = datos.por_producto || [];
    if (porProducto.length === 0) {
      consumoVacioEl.hidden = false;
      return;
    }

    const maximo = Math.max(...porProducto.map((p) => p.consumo));
    consumoPorProductoEl.innerHTML = porProducto
      .map((p) => {
        const porcentaje = maximo > 0 ? Math.round((p.consumo / maximo) * 100) : 0;
        return `
          <li class="consumo-fila">
            <span class="consumo-nombre">${escapeHtml(p.nombre)}</span>
            <div class="consumo-barra-fondo"><div class="consumo-barra" style="width: ${porcentaje}%"></div></div>
            <span class="consumo-cantidad">${p.consumo}</span>
          </li>
        `;
      })
      .join("");
  } catch (err) {
    console.error("Error cargando consumo:", err);
    Toast.error("No se pudo cargar el consumo. Comprueba tu conexión.");
  }
}

function cerrarModalConsumo() {
  modalConsumoFondo.hidden = true;
}

if (btnConsumo) btnConsumo.addEventListener("click", abrirModalConsumo);
if (btnCerrarConsumo) btnCerrarConsumo.addEventListener("click", cerrarModalConsumo);
if (modalConsumoFondo) habilitarBottomSheet(modalConsumoFondo, modalConsumoFondo.querySelector(".modal"), cerrarModalConsumo);

/* --- Escaneo de tickets --- */

if (typeof TicketsManager !== "undefined") {
  window.ticketsManager = new TicketsManager({
    fetchImpl: (...args) => fetch(...args),
    toast: Toast,
    escapeHtml,
    renderIcon: renderIcono,
    populateCategorySelect: poblarSelectCategoria,
    getProducts: () => productos,
    onConfirmed: async () => {
      await cargarProductos();
      await cargarListaCompra();
    },
    habilitarBottomSheet,
  });
}

// ============ KEYBOARD MANAGEMENT ============

// KeyboardManager se define en ui-components.js, se instancia ahí
// No se redeclara aquí para evitar conflictos

// ============ SCROLL & ZOOM PREVENTION ============

class ScrollManager {
  constructor() {
    this.init();
  }

  init() {
    let startX = 0;
    let startY = 0;
    let dentroDeScrollHorizontal = null; // se calcula una vez por gesto, no en cada touchmove

    document.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      dentroDeScrollHorizontal = null;
    }, { passive: true });

    document.addEventListener('touchmove', (e) => {
      const currentX = e.touches[0].clientX;
      const diffX = Math.abs(currentX - startX);
      const diffY = Math.abs(e.touches[0].clientY - startY);

      if (diffX > 20) {
        if (dentroDeScrollHorizontal === null) {
          dentroDeScrollHorizontal = false;
          let el = e.target;
          while (el && el !== document.body) {
            if (el.scrollWidth > el.clientWidth) {
              dentroDeScrollHorizontal = true;
              break;
            }
            el = el.parentElement;
          }
        }
        if (dentroDeScrollHorizontal) return;

        if (diffX > 50 && diffY < 20) {
          e.preventDefault();
        }
      }
    }, { passive: false });
  }
}

const scrollManager = new ScrollManager();

// ============ ZOOM PREVENTION ============

class ZoomManager {
  constructor() {
    this.init();
  }

  init() {
    document.addEventListener('gesturestart', (e) => {
      e.preventDefault();
    }, { passive: false });

    let lastTap = 0;
    document.addEventListener('touchend', (e) => {
      const now = Date.now();
      const timesince = now - lastTap;

      if (timesince < 300 && timesince > 0) {
        if (!this.isInteractive(e.target)) {
          e.preventDefault();
        }
      }
      lastTap = now;
    }, { passive: false });
  }

  isInteractive(el) {
    const interactive = ['INPUT', 'TEXTAREA', 'BUTTON', 'A', 'SELECT'];
    return interactive.includes(el.tagName) || el.closest('button, a, input, textarea, select');
  }
}

const zoom = new ZoomManager();

// ============ LISTAS COMPARTIDAS ============

async function cargarMisListas() {
  try {
    const response = await fetch('/api/listas');
    const data = await response.json();

    // Descartar 'lista-actual' guardada en localStorage si no pertenece a este
    // usuario (p.ej. quedó de una sesión anterior de otro usuario en el mismo
    // navegador) para evitar 403 en cascada y la pantalla atascada en "Cargando...".
    const idsValidos = new Set([...(data.propias || []), ...(data.compartidas || [])].map(l => String(l.id)));
    const listaGuardada = localStorage.getItem('lista-actual');
    if (listaGuardada && !idsValidos.has(String(listaGuardada))) {
      localStorage.removeItem('lista-actual');
    }

    // FASE 2: Mostrar banner si no hay listas (ANTES de actualizarListaActual)
    const totalListas = (data.propias?.length || 0) + (data.compartidas?.length || 0);
    const banner = document.getElementById('bannerSinListas');
    if (banner) {
      if (totalListas === 0) {
        banner.hidden = false;
        console.log('⚠️ Usuario sin listas - Banner visible');
        // Configurar evento del botón del banner (una sola vez; el modal puede
        // no estar listo aún porque drawer-listas.js lo inicializa con delay)
        const btnBannerCrearLista = document.getElementById('btnBannerCrearLista');
        if (btnBannerCrearLista && !btnBannerCrearLista.dataset.listenerAttached) {
          btnBannerCrearLista.dataset.listenerAttached = 'true';
          btnBannerCrearLista.addEventListener('click', () => {
            if (window.crearListaModal) {
              window.crearListaModal.open();
            } else {
              console.error('crearListaModal no está inicializado todavía');
            }
          });
        }
      } else {
        banner.hidden = true;
      }
    }

    renderizarSelectorListas(data.propias, data.compartidas);
    await actualizarListaActual(data.propias);
  } catch (error) {
    console.error('Error cargando listas:', error);
    Toast.error('No se pudieron cargar tus listas. Comprueba tu conexión.');
  }
}

function renderizarSelectorListas(propias, compartidas) {
  const containerPropias = document.getElementById('listasPropias');
  const containerCompartidas = document.getElementById('listasCompartidas');
  const seccionCompartidas = document.getElementById('seccionListasCompartidas');

  // Los elementos ya no existen (modalCambiarLista fue eliminado)
  // Solo renderizar si los contenedores existen
  if (!containerPropias || !containerCompartidas) {
    return;
  }

  containerPropias.innerHTML = '';
  containerCompartidas.innerHTML = '';

  propias.forEach(lista => {
    const item = crearItemLista(lista);
    containerPropias.appendChild(item);
  });

  if (compartidas.length > 0 && seccionCompartidas) {
    seccionCompartidas.style.display = 'block';
    compartidas.forEach(lista => {
      const item = crearItemLista(lista);
      containerCompartidas.appendChild(item);
    });
  } else if (seccionCompartidas) {
    seccionCompartidas.style.display = 'none';
  }
}

function crearItemLista(lista) {
  const div = document.createElement('div');
  div.style.cssText = `
    padding: 12px;
    background: var(--surface);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 56px;
    margin-bottom: 8px;
    transition: all 0.15s ease;
  `;

  const icono = document.createElement('span');
  icono.innerHTML = renderIcono(lista.icono || 'h-clipboard-document-list', { tamano: 19 });

  const info = document.createElement('div');
  info.style.cssText = 'flex: 1;';
  info.innerHTML = `
    <div style="font-weight: 600; font-size: 0.95rem;">${escapeHtml(lista.nombre)}</div>
    <div style="font-size: 0.75rem; color: var(--text-soft);">${escapeHtml(lista.mi_rol ? lista.mi_rol.toUpperCase() : 'VER')}</div>
  `;

  div.appendChild(icono);
  div.appendChild(info);

  div.addEventListener('click', () => {
    cambiarLista(lista.id);
  });

  div.addEventListener('mousedown', () => {
    div.style.background = 'var(--surface-2)';
  });

  div.addEventListener('mouseup', () => {
    div.style.background = 'var(--surface)';
  });

  return div;
}

async function actualizarListaActual(listas = null) {
  let listaId = localStorage.getItem('lista-actual');

  // Si no hay lista seleccionada, usar la primera del parámetro
  if (!listaId && listas && listas.length > 0) {
    listaId = listas[0].id;
    localStorage.setItem('lista-actual', listaId);
  }

  if (!listaId) {
    console.warn('No hay lista disponible para actualizar');
    return;
  }

  // Actualizar el selector visible
  try {
    const res = await fetch(`/api/listas/${listaId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const lista = await res.json();

    const nombreEl = document.getElementById('listaActualNombre');
    const iconoEl = document.getElementById('listaActualIcono');
    const rolEl = document.getElementById('listaActualRol');

    if (nombreEl) nombreEl.textContent = lista.nombre;
    if (iconoEl) iconoEl.innerHTML = renderIcono(lista.icono || 'h-clipboard-document-list');
    if (rolEl) rolEl.textContent = (lista.mi_rol || 'ver').toUpperCase();
  } catch (error) {
    console.error('Error actualizando lista actual:', error);
    Toast.error('No se pudo cargar la información de la lista actual.');
  }
}

async function cambiarLista(listaId) {
  // Fuente única de verdad: primero confirma con el backend (sesión) que el
  // usuario tiene acceso a la lista, y solo entonces persiste en localStorage.
  // Antes había una segunda implementación (DrawerListasManager.cambiarLista)
  // que sí llamaba a /seleccionar; esta no lo hacía y dejaba la sesión del
  // backend desincronizada con localStorage, mostrando stock de otra lista.
  try {
    const res = await fetch(`/api/listas/${listaId}/seleccionar`, { method: 'POST' });
    if (!res.ok) {
      const datos = await res.json().catch(() => ({}));
      console.error('Error cambiando lista:', res.status);
      Toast.error(datos.error || 'No se pudo cambiar la lista');
      return;
    }
  } catch (error) {
    console.error('Error en cambiarLista:', error);
    Toast.error('No se pudo cambiar de lista. Comprueba tu conexión e inténtalo de nuevo.');
    return;
  }

  localStorage.setItem('lista-actual', listaId);

  // Cerrar modal
  const modalMisListas = document.getElementById('modalMisListas');
  if (modalMisListas) {
    modalMisListas.hidden = true;
    document.body.classList.remove('modal-open');
  }

  // Recargar datos
  await cargarProductos();
  await cargarListaCompra();

  // Actualizar selector visible
  await cargarMisListas();
}
window.cambiarLista = cambiarLista;

// ============ INICIALIZACIONES ============

// Se espera a cargarMisListas() antes de cargar productos/compra porque esa
// función valida y limpia 'lista-actual' en localStorage; si no, otras
// llamadas pueden usar un lista_id obsoleto y recibir 403 en cascada.
const misListasPromise = cargarMisListas();
misListasPromise.then(() => {
  cargarCategorias().then(() => {
    cargarProductos();
    cargarListaCompra();
  });
});
cargarHistorial();

// Si venimos de aceptar una invitación de lista compartida (?lista=<id>),
// seleccionarla automáticamente en vez de dejar la lista propia activa.
(function() {
  const params = new URLSearchParams(window.location.search);
  const listaId = params.get('lista');
  if (listaId) {
    misListasPromise.then(() => {
      window.cambiarLista(listaId);
      window.history.replaceState({}, document.title, window.location.pathname);
    });
  }
})();

// ============ EVENTOS DE UI ============

const btnCambiarListaEl = document.getElementById('btnCambiarLista');
if (btnCambiarListaEl) {
  btnCambiarListaEl.addEventListener('click', () => {
    if (window.drawerListasManager) {
      window.drawerListasManager.abrirModal();
    }
  });
}

const listaActualBtnEl = document.getElementById('listaActualBtn');
if (listaActualBtnEl) {
  listaActualBtnEl.addEventListener('click', () => {
    if (window.drawerListasManager) {
      window.drawerListasManager.abrirModal();
    }
  });
}

// ============ CREAR PRIMERA LISTA (NUEVO USUARIO) ============
// Selector de Tema y Perfil en Modal de Ajustes
(function() {
  function setupAjustesModal() {
    const modalAjustes = document.getElementById('modalAjustes');
    const selectTema = document.getElementById('selectTema');
    const checkTecladoVirtual = document.getElementById('checkTecladoVirtual');
    const btnGuardarPerfil = document.getElementById('btnGuardarPerfil');
    const inputNombre = document.getElementById('ajustesNombreUsuario');
    const inputEmail = document.getElementById('ajustesEmailUsuario');
    const inputPassword = document.getElementById('ajustesPasswordUsuario');
    const spanEstado = document.getElementById('ajustesEstado');

    if (!modalAjustes || !selectTema || !btnGuardarPerfil) return;

    // Cargar datos del usuario cuando se abre el modal. Se comprueba
    // "!inputNombre.value" para no pisar lo que el usuario esté editando
    // si el foco cambia entre campos del propio modal (focusin reentra).
    modalAjustes.addEventListener('focusin', async () => {
      const temaGuardado = localStorage.getItem('stockhogar-tema') || 'auto';
      selectTema.value = temaGuardado;

      if (checkTecladoVirtual) {
        checkTecladoVirtual.checked = (localStorage.getItem('stockhogar-teclado-virtual') || 'on') === 'on';
      }

      if ((inputNombre && !inputNombre.value) || (inputEmail && !inputEmail.value)) {
        try {
          const res = await fetch('/api/auth/estado');
          const datos = await res.json();
          if (inputNombre && !inputNombre.value) inputNombre.value = datos.usuario || '';
          if (inputEmail && !inputEmail.value) inputEmail.value = datos.email || '';
        } catch (error) {
          console.error('Error cargando datos del perfil:', error);
        }
      }
    });

    // Cambiar tema al seleccionar
    selectTema.addEventListener('change', (e) => {
      guardarTemaPreferido(e.target.value);
    });

    if (checkTecladoVirtual) {
      checkTecladoVirtual.addEventListener('change', (e) => {
        guardarPreferenciaTecladoVirtual(e.target.checked);
      });
    }

    // Guardar perfil
    btnGuardarPerfil.addEventListener('click', async () => {
      const nombre = inputNombre?.value.trim() || '';
      const password = inputPassword?.value || '';

      if (!nombre) {
        mostrarEstado('El nombre no puede estar vacío', 'error');
        return;
      }

      if (password && password.length < 4) {
        mostrarEstado('La contraseña debe tener mínimo 4 caracteres', 'error');
        return;
      }

      try {
        btnGuardarPerfil.disabled = true;
        mostrarEstado('Guardando...', 'info');

        const body = { nombre };
        if (password) {
          body.password = password;
        }

        const res = await fetch('/api/auth/perfil', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });

        if (!res.ok) {
          const error = await res.json();
          mostrarEstado(error.error || 'Error al guardar', 'error');
          return;
        }

        if (inputPassword) {
          inputPassword.value = '';
        }

        mostrarEstado('Perfil guardado correctamente', 'exito');
      } catch (error) {
        console.error('Error guardando perfil:', error);
        mostrarEstado('Error de conexión', 'error');
      } finally {
        btnGuardarPerfil.disabled = false;
      }
    });

    function mostrarEstado(mensaje, tipo) {
      if (!spanEstado) return;
      spanEstado.textContent = mensaje;
      spanEstado.hidden = false;
      spanEstado.className = 'aviso';
      if (tipo === 'exito') {
        spanEstado.style.color = 'var(--success)';
      } else if (tipo === 'error') {
        spanEstado.style.color = 'var(--danger)';
      }
      setTimeout(() => {
        spanEstado.hidden = true;
      }, 4000);
    }
  }

  // Esperar a que el DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupAjustesModal);
  } else {
    setupAjustesModal();
  }
})();

// ========== HANDLERS PARA CREAR NUEVA LISTA ==========
(function() {
  const formCrearLista = document.getElementById('formCrearLista');
  const modalCrearLista = document.getElementById('modalCrearLista');
  const btnCerrarCrearLista = document.getElementById('btnCerrarCrearLista');
  const iconoSeleccionadoNuevaLista = document.getElementById('iconoSeleccionadoNuevaLista');
  const crearListaColor = document.getElementById('crearListaColor');
  const colorPreviewCrear = document.getElementById('colorPreviewCrear');

  if (!formCrearLista || !modalCrearLista) return;

  // Abrir modal de crear lista
  const btnCrearNuevaLista = document.getElementById('btnCrearNuevaLista');
  if (btnCrearNuevaLista) {
    btnCrearNuevaLista.addEventListener('click', () => {
      formCrearLista.reset();
      iconoSeleccionadoNuevaLista.innerHTML = renderIcono('h-clipboard-document-list');
      formCrearLista.querySelector('input[name="icono"]').value = 'h-clipboard-document-list';
      crearListaColor.value = '#B5551A';
      if (colorPreviewCrear) colorPreviewCrear.style.backgroundColor = '#B5551A';
      modalCrearLista.hidden = false;
      document.body.classList.add('modal-open');
      setTimeout(() => {
        const inputNombre = formCrearLista.querySelector('input[name="nombre"]');
        if (inputNombre) inputNombre.focus();
      }, 100);
    });
  }

  // Cerrar modal
  function cerrarModalCrearLista() {
    modalCrearLista.hidden = true;
    document.body.classList.remove('modal-open');
  }
  if (btnCerrarCrearLista) {
    btnCerrarCrearLista.addEventListener('click', cerrarModalCrearLista);
  }

  window.habilitarBottomSheet(modalCrearLista, modalCrearLista.querySelector('.modal'), cerrarModalCrearLista);

  // NOTA: El botón "Cambiar icono" NO se enlaza aquí: FormBuilder.inyectarFormularioEnModal
  // recrea ese botón cada vez que se abre el modal (ver CrearListaModal.onOpen en
  // drawer-listas.js), así que un listener añadido una sola vez aquí, al cargar la página,
  // queda enganchado al nodo original y deja de funcionar tras la primera apertura.
  // El handler real vive en CrearListaModal.setupIconoSelector (drawer-listas.js),
  // que se reejecuta cada vez que el botón se regenera.

  // Preview de color
  if (crearListaColor) {
    crearListaColor.addEventListener('change', (e) => {
      if (colorPreviewCrear) {
        colorPreviewCrear.style.backgroundColor = e.target.value;
      }
    });
  }

  // NOTA: El handler del formulario está en drawer-listas.js (CrearListaModal.onSubmit)
  // No duplicar aquí para evitar conflictos
})();

// Detectar si es un usuario nuevo y mostrar modal de creación
(function() {
  const params = new URLSearchParams(window.location.search);
  if (params.has('crear_primera_lista')) {
    // Esperar a que carguen las listas
    setTimeout(() => {
      const modal = document.getElementById('modalMisListas');
      const btnCrearNuevaLista = document.getElementById('btnCrearNuevaLista');

      if (modal && btnCrearNuevaLista) {
        // Abrir modal de crear lista
        modal.hidden = false;
        document.body.classList.add('modal-open');

        // Focus en input de nombre
        setTimeout(() => {
          const inputNombre = document.getElementById('formCrearLista')?.querySelector('input[name="nombre"]');
          if (inputNombre) {
            inputNombre.focus();
            inputNombre.placeholder = (window.i18n && window.i18n.t('ej_mi_lista_compra')) || 'Ej: Mi lista de compra...';
          }
        }, 100);

        // Limpiar URL
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }, 500);
  }
})();

// Inicialización tardía - asegurar que los listeners se agregan después de que el DOM esté listo
(function() {
  function initializeEventListeners() {
    // Settings modal
    const btnAjustesInit = document.getElementById('btnAjustes');
    const modalAjustesFondoInit = document.getElementById('modalAjustes');
    if (btnAjustesInit && modalAjustesFondoInit) {
      btnAjustesInit.addEventListener("click", abrirModalAjustes);
      habilitarBottomSheet(modalAjustesFondoInit, modalAjustesFondoInit.querySelector(".modal"), cerrarModalAjustes);
    }

    // Close session button
    const btnCerrarSesionInit = document.getElementById('btnCerrarSesion');
    if (btnCerrarSesionInit) {
      btnCerrarSesionInit.addEventListener("click", async () => {
        await fetch("/api/auth/logout", { method: "POST" });
        window.location.href = "/login";
      });
    }

  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeEventListeners);
  } else {
    initializeEventListeners();
  }
})();
