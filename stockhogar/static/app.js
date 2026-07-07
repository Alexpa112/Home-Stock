// Si la sesion caduca o se borra el usuario conectado, cualquier llamada a la
// API devolvera 401: mandamos a la pantalla de login en vez de dejar la app
// a medio cargar con errores silenciosos.
const fetchOriginal = window.fetch.bind(window);
window.fetch = async (...args) => {
  const res = await fetchOriginal(...args);
  if (res.status === 401) {
    window.location.href = "/login";
  }
  return res;
};

// Catalogo de iconos con palabras clave (para el buscador del selector).
// Deliberadamente son emoji (no SVGs a medida): cero peso extra para la
// Raspberry Pi y se ven bien en cualquier tema. Para que no resulten
// "pesados" visualmente, los mosaicos que los usan van sin fondo de color
// (ver .tile-compra en style.css).
const CATALOGO_ICONOS = [
  { icono: "🍎", palabras: ["manzana", "fruta"] },
  { icono: "🍏", palabras: ["manzana verde", "fruta"] },
  { icono: "🍌", palabras: ["platano", "fruta"] },
  { icono: "🍊", palabras: ["naranja", "fruta", "mandarina"] },
  { icono: "🍋", palabras: ["limon", "fruta"] },
  { icono: "🍉", palabras: ["sandia", "fruta"] },
  { icono: "🍇", palabras: ["uvas", "fruta"] },
  { icono: "🍓", palabras: ["fresa", "fruta"] },
  { icono: "🫐", palabras: ["arandanos", "fruta"] },
  { icono: "🍒", palabras: ["cerezas", "fruta"] },
  { icono: "🍑", palabras: ["melocoton", "fruta"] },
  { icono: "🥭", palabras: ["mango", "fruta"] },
  { icono: "🍍", palabras: ["piña", "fruta"] },
  { icono: "🥝", palabras: ["kiwi", "fruta"] },
  { icono: "🥑", palabras: ["aguacate", "fruta"] },
  { icono: "🍅", palabras: ["tomate", "verdura"] },
  { icono: "🥦", palabras: ["brocoli", "verdura"] },
  { icono: "🥬", palabras: ["lechuga", "verdura", "ensalada"] },
  { icono: "🥒", palabras: ["pepino", "verdura"] },
  { icono: "🌶️", palabras: ["pimiento", "picante", "verdura"] },
  { icono: "🫑", palabras: ["pimiento verde", "verdura"] },
  { icono: "🌽", palabras: ["maiz", "verdura"] },
  { icono: "🥕", palabras: ["zanahoria", "verdura"] },
  { icono: "🧄", palabras: ["ajo"] },
  { icono: "🧅", palabras: ["cebolla"] },
  { icono: "🥔", palabras: ["patata", "verdura"] },
  { icono: "🍠", palabras: ["boniato"] },
  { icono: "🥐", palabras: ["croissant", "bolleria", "pan"] },
  { icono: "🥖", palabras: ["pan", "barra"] },
  { icono: "🍞", palabras: ["pan", "molde"] },
  { icono: "🧀", palabras: ["queso"] },
  { icono: "🥚", palabras: ["huevo", "huevos"] },
  { icono: "🥩", palabras: ["carne", "filete"] },
  { icono: "🍗", palabras: ["pollo", "carne"] },
  { icono: "🍖", palabras: ["carne", "hueso"] },
  { icono: "🥓", palabras: ["bacon", "panceta"] },
  { icono: "🌭", palabras: ["salchicha"] },
  { icono: "🍔", palabras: ["hamburguesa"] },
  { icono: "🍕", palabras: ["pizza"] },
  { icono: "🐟", palabras: ["pescado"] },
  { icono: "🦐", palabras: ["gamba", "marisco"] },
  { icono: "🍱", palabras: ["comida preparada"] },
  { icono: "🍚", palabras: ["arroz"] },
  { icono: "🍜", palabras: ["pasta", "fideos", "sopa"] },
  { icono: "🥣", palabras: ["cereales", "sopa", "bol"] },
  { icono: "🥫", palabras: ["lata", "conserva"] },
  { icono: "🫙", palabras: ["tarro", "bote", "conserva"] },
  { icono: "🍫", palabras: ["chocolate"] },
  { icono: "🍬", palabras: ["caramelo", "dulce"] },
  { icono: "🍩", palabras: ["donut", "dulce"] },
  { icono: "🍪", palabras: ["galleta"] },
  { icono: "🎂", palabras: ["tarta", "pastel"] },
  { icono: "🍯", palabras: ["miel"] },
  { icono: "🥜", palabras: ["frutos secos", "cacahuete"] },
  { icono: "🧈", palabras: ["mantequilla"] },
  { icono: "🧂", palabras: ["sal"] },
  { icono: "🫒", palabras: ["aceituna", "aceite"] },
  { icono: "☕", palabras: ["cafe"] },
  { icono: "🍵", palabras: ["te", "infusion"] },
  { icono: "🧃", palabras: ["zumo", "brik"] },
  { icono: "🥤", palabras: ["refresco", "bebida"] },
  { icono: "🧋", palabras: ["bebida", "batido"] },
  { icono: "🍶", palabras: ["botella", "bebida"] },
  { icono: "🍾", palabras: ["cava", "champan"] },
  { icono: "🍷", palabras: ["vino"] },
  { icono: "🍺", palabras: ["cerveza"] },
  { icono: "🥛", palabras: ["leche"] },
  { icono: "💧", palabras: ["agua"] },
  { icono: "🧴", palabras: ["gel", "champu", "jabon liquido", "crema"] },
  { icono: "🧼", palabras: ["jabon"] },
  { icono: "🧽", palabras: ["esponja", "limpieza"] },
  { icono: "🪥", palabras: ["cepillo de dientes"] },
  { icono: "🦷", palabras: ["dientes", "dental"] },
  { icono: "🧻", palabras: ["papel higienico", "papel"] },
  { icono: "🧺", palabras: ["cesta", "colada"] },
  { icono: "🪣", palabras: ["cubo", "fregona"] },
  { icono: "🚽", palabras: ["wc", "bano"] },
  { icono: "🛁", palabras: ["bañera", "baño"] },
  { icono: "🚿", palabras: ["ducha"] },
  { icono: "🕯️", palabras: ["vela"] },
  { icono: "🔥", palabras: ["fuego", "gas"] },
  { icono: "🧯", palabras: ["extintor"] },
  { icono: "💊", palabras: ["pastilla", "medicina", "farmacia"] },
  { icono: "🩹", palabras: ["tirita", "botiquin"] },
  { icono: "🩺", palabras: ["salud", "medico"] },
  { icono: "🌡️", palabras: ["termometro", "fiebre"] },
  { icono: "👶", palabras: ["bebe"] },
  { icono: "🍼", palabras: ["biberon", "bebe"] },
  { icono: "🧸", palabras: ["peluche", "juguete"] },
  { icono: "🐶", palabras: ["perro", "mascota"] },
  { icono: "🐱", palabras: ["gato", "mascota"] },
  { icono: "🐹", palabras: ["hamster", "mascota"] },
  { icono: "🐟", palabras: ["pez", "mascota"] },
  { icono: "🦴", palabras: ["hueso", "mascota"] },
  { icono: "🐾", palabras: ["mascota", "huellas"] },
  { icono: "👕", palabras: ["ropa", "camiseta"] },
  { icono: "👖", palabras: ["pantalon", "ropa"] },
  { icono: "🧦", palabras: ["calcetines", "ropa"] },
  { icono: "🧣", palabras: ["bufanda", "ropa"] },
  { icono: "🧤", palabras: ["guantes", "ropa"] },
  { icono: "👗", palabras: ["vestido", "ropa"] },
  { icono: "👟", palabras: ["zapatillas", "calzado"] },
  { icono: "🧥", palabras: ["abrigo", "ropa"] },
  { icono: "🔧", palabras: ["llave inglesa", "herramienta", "bricolaje"] },
  { icono: "🔩", palabras: ["tornillo", "herramienta"] },
  { icono: "🔨", palabras: ["martillo", "herramienta"] },
  { icono: "🪛", palabras: ["destornillador", "herramienta"] },
  { icono: "🪜", palabras: ["escalera"] },
  { icono: "🖨️", palabras: ["impresora", "tinta"] },
  { icono: "📱", palabras: ["movil", "telefono"] },
  { icono: "💻", palabras: ["ordenador", "portatil"] },
  { icono: "🔌", palabras: ["enchufe", "cargador"] },
  { icono: "🔋", palabras: ["pila", "bateria"] },
  { icono: "💡", palabras: ["bombilla", "luz"] },
  { icono: "📷", palabras: ["camara", "foto"] },
  { icono: "🎧", palabras: ["auriculares"] },
  { icono: "⌚", palabras: ["reloj"] },
  { icono: "🔦", palabras: ["linterna"] },
  { icono: "🗝️", palabras: ["llave"] },
  { icono: "📓", palabras: ["cuaderno", "libreta"] },
  { icono: "✏️", palabras: ["lapiz", "oficina"] },
  { icono: "🖊️", palabras: ["boligrafo", "oficina"] },
  { icono: "📎", palabras: ["clip", "oficina"] },
  { icono: "✂️", palabras: ["tijeras"] },
  { icono: "📚", palabras: ["libros"] },
  { icono: "🌱", palabras: ["planta", "semilla"] },
  { icono: "🪴", palabras: ["maceta", "planta"] },
  { icono: "🌻", palabras: ["flor", "girasol"] },
  { icono: "🍀", palabras: ["trebol", "jardin"] },
  { icono: "🪵", palabras: ["madera", "leña"] },
  { icono: "⚽", palabras: ["futbol", "deporte"] },
  { icono: "🏀", palabras: ["baloncesto", "deporte"] },
  { icono: "🚴", palabras: ["bici", "bicicleta"] },
  { icono: "🎮", palabras: ["videojuego", "mando"] },
  { icono: "🎲", palabras: ["juego", "dados"] },
  { icono: "🧩", palabras: ["puzzle", "juego"] },
  { icono: "🚗", palabras: ["coche", "vehiculo"] },
  { icono: "⛽", palabras: ["gasolina", "combustible"] },
  { icono: "🎁", palabras: ["regalo"] },
  { icono: "🧳", palabras: ["maleta", "viaje"] },
  { icono: "🎈", palabras: ["globo", "fiesta"] },
  { icono: "📦", palabras: ["caja", "paquete"] },
  { icono: "🛒", palabras: ["carrito", "compra"] },
  { icono: "🗂️", palabras: ["carpeta", "otros", "varios"] },
];

const lista = document.getElementById("lista");
const vacio = document.getElementById("vacio");
const buscador = document.getElementById("buscador");
const filtros = document.getElementById("filtros");
const fab = document.getElementById("btnAbrirModal");
const modalFondo = document.getElementById("modal");
const form = document.getElementById("formProducto");
const btnCancelar = document.getElementById("btnCancelar");
const modalTitulo = document.getElementById("modalTitulo");
const campoCategoria = document.getElementById("campoCategoria");
const campoIcono = document.getElementById("campoIcono");
const selectorIconoProductoEl = document.getElementById("selectorIconoProducto");
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
const btnCancelarCompra = document.getElementById("btnCancelarCompra");
const compraModalTitulo = document.getElementById("compraModalTitulo");
const compraEditIdEl = document.getElementById("compraEditId");
const compraCampoCantidad = document.getElementById("compraCampoCantidad");
const compraCampoSubdescripcion = document.getElementById("compraCampoSubdescripcion");
const compraCampoCategoria = document.getElementById("compraCampoCategoria");
const compraCampoIcono = document.getElementById("compraCampoIcono");
const selectorIconoCompraEl = document.getElementById("selectorIconoCompra");
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
const btnCancelarAjustes = document.getElementById("btnCancelarAjustes");

const ajustesUsuarioActual = document.getElementById("ajustesUsuarioActual");
const btnCerrarSesion = document.getElementById("btnCerrarSesion");
const usuariosListaEl = document.getElementById("usuariosLista");
const usuarioCampoNombre = document.getElementById("usuarioCampoNombre");
const usuarioCampoPassword = document.getElementById("usuarioCampoPassword");
const btnAnadirUsuario = document.getElementById("btnAnadirUsuario");
const usuariosEstado = document.getElementById("usuariosEstado");

const btnEscanearTicket = document.getElementById("btnEscanearTicket");
const modalTicketFondo = document.getElementById("modalTicket");
const ticketPasoFoto = document.getElementById("ticketPasoFoto");
const ticketCargando = document.getElementById("ticketCargando");
const ticketPasoRevision = document.getElementById("ticketPasoRevision");
const ticketArchivo = document.getElementById("ticketArchivo");
const btnAnalizarTicket = document.getElementById("btnAnalizarTicket");
const btnCancelarTicket = document.getElementById("btnCancelarTicket");
const btnCancelarRevisionTicket = document.getElementById("btnCancelarRevisionTicket");
const btnAnadirLineaTicket = document.getElementById("btnAnadirLineaTicket");
const btnConfirmarTicket = document.getElementById("btnConfirmarTicket");
const ticketItemsEl = document.getElementById("ticketItems");

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

const barraEspacio = document.getElementById("barraEspacio");
const btnEspacios = document.getElementById("btnEspacios");
const espacioActualIconoEl = document.getElementById("espacioActualIcono");
const espacioActualNombreEl = document.getElementById("espacioActualNombre");
const vistaEspacios = document.getElementById("vistaEspacios");
const btnCerrarEspacios = document.getElementById("btnCerrarEspacios");
const btnEditarEspacios = document.getElementById("btnEditarEspacios");
const espaciosTarjetasEl = document.getElementById("espaciosTarjetas");

const modalEspacioFormFondo = document.getElementById("modalEspacioForm");
const formEspacio = document.getElementById("formEspacio");
const espacioFormTitulo = document.getElementById("espacioFormTitulo");
const espacioEditId = document.getElementById("espacioEditId");
const espacioBotonGuardar = document.getElementById("espacioBotonGuardar");
const espacioCampoNombre = document.getElementById("espacioCampoNombre");
const espacioCampoIcono = document.getElementById("espacioCampoIcono");
const espacioIconoElegido = document.getElementById("espacioIconoElegido");
const selectorIconoEspacioEl = document.getElementById("selectorIconoEspacio");
const paletaColorEspacioEl = document.getElementById("paletaColorEspacio");
const espacioCampoColor = document.getElementById("espacioCampoColor");
const espacioCampoColorPicker = document.getElementById("espacioCampoColorPicker");
const btnCancelarEspacio = document.getElementById("btnCancelarEspacio");

let productos = [];
let pendientesCompra = [];
let completadosCompra = [];
let categorias = [];
let espacios = [];
let espacioActualId = null;
let categoriaActiva = "todas";
let textoBusqueda = "";
let vistaActiva = "stock";

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

function aplicarTema(tema) {
  document.documentElement.dataset.theme = tema;
  localStorage.setItem("stockhogar-tema", tema);
  actualizarBotonTema();
}

btnTema.addEventListener("click", () => {
  aplicarTema(temaActual() === "dark" ? "light" : "dark");
});

actualizarBotonTema();

/* --- Categorias --- */

function iconoDeCategoria(nombre) {
  const cat = categorias.find((c) => c.nombre === nombre);
  return cat ? cat.icono : "🗂️";
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
  const res = await fetch("/api/historial");
  historialLista = await res.json();
  historialPorNombre = new Map(historialLista.map((h) => [h.nombre.toLowerCase(), h]));
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
function agregarPulsacion(elemento, alPulsarCorto, alPulsarLargo, duracion = 480) {
  let temporizador = null;
  let fueLarga = false;

  function empezar() {
    fueLarga = false;
    temporizador = setTimeout(() => {
      fueLarga = true;
      if (navigator.vibrate) navigator.vibrate(15);
      alPulsarLargo();
    }, duracion);
  }
  function cancelar() {
    clearTimeout(temporizador);
  }
  function terminar() {
    clearTimeout(temporizador);
    if (!fueLarga) alPulsarCorto();
  }

  elemento.addEventListener("pointerdown", empezar);
  elemento.addEventListener("pointerup", terminar);
  elemento.addEventListener("pointerleave", cancelar);
  elemento.addEventListener("pointercancel", cancelar);
  elemento.addEventListener("contextmenu", (e) => e.preventDefault());
}

async function cargarCategorias() {
  const res = await fetch("/api/categorias");
  categorias = await res.json();
  renderFiltros();
  poblarSelectCategoria(campoCategoria, campoCategoria.value);
}

function renderFiltros() {
  const categoriaPrevia = categoriaActiva;
  filtros.innerHTML = '<button class="chip activo" data-cat="todas">Todas</button>';
  for (const cat of categorias) {
    const btnCat = document.createElement("button");
    btnCat.className = "chip";
    btnCat.dataset.cat = cat.nombre;
    btnCat.textContent = `${cat.icono} ${cat.nombre}`;
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
    .map((c) => `<option value="${escapeHtml(c.nombre)}">${c.icono} ${escapeHtml(c.nombre)}</option>`)
    .join("");
  if (seleccionada) select.value = seleccionada;
}

function renderCategoriasLista() {
  categoriasListaEl.innerHTML = "";
  for (const cat of categorias) {
    const chip = document.createElement("div");
    chip.className = "categoria-chip";
    chip.innerHTML = `<span>${cat.icono} ${escapeHtml(cat.nombre)}</span>`;
    if (cat.nombre !== "Otros") {
      const btnBorrar = document.createElement("button");
      btnBorrar.type = "button";
      btnBorrar.title = "Borrar categoría";
      btnBorrar.textContent = "✕";
      btnBorrar.addEventListener("click", () => borrarCategoria(cat));
      chip.appendChild(btnBorrar);
    }
    categoriasListaEl.appendChild(chip);
  }
}

async function borrarCategoria(cat) {
  if (!confirm(`¿Borrar la categoría "${cat.nombre}"?`)) return;
  const res = await fetch(`/api/categorias/${cat.id}`, { method: "DELETE" });
  if (!res.ok) {
    const datos = await res.json().catch(() => ({}));
    alert(datos.error || "No se pudo borrar la categoría");
    return;
  }
  categorias = categorias.filter((c) => c.id !== cat.id);
  renderCategoriasLista();
  renderFiltros();
  poblarSelectCategoria(campoCategoria, campoCategoria.value);
  render();
}

/* Selector de iconos reutilizable: buscador + rejilla filtrable. Se usa en
   Categorías, en el formulario de producto y en el de la lista de la compra. */
function crearSelectorIconos(contenedor, seleccionado, alElegir) {
  contenedor.innerHTML = "";
  const buscador = document.createElement("input");
  buscador.type = "search";
  buscador.placeholder = "Buscar icono... (ej. leche, limpieza, mascota)";
  buscador.className = "buscador-iconos";

  const rejilla = document.createElement("div");
  rejilla.className = "selector-iconos";

  function pintar(filtro) {
    rejilla.innerHTML = "";
    const texto = filtro.trim().toLowerCase();
    const items = texto
      ? CATALOGO_ICONOS.filter((it) => it.palabras.some((p) => p.includes(texto)))
      : CATALOGO_ICONOS;
    for (const it of items) {
      const btnIcono = document.createElement("button");
      btnIcono.type = "button";
      btnIcono.textContent = it.icono;
      btnIcono.title = it.palabras[0] || "";
      btnIcono.className = it.icono === seleccionado ? "seleccionado" : "";
      btnIcono.addEventListener("click", () => {
        seleccionado = it.icono;
        rejilla.querySelectorAll("button").forEach((b) => b.classList.remove("seleccionado"));
        btnIcono.classList.add("seleccionado");
        alElegir(it.icono);
      });
      rejilla.appendChild(btnIcono);
    }
    if (items.length === 0) {
      const vacioAviso = document.createElement("p");
      vacioAviso.className = "aviso";
      vacioAviso.textContent = "Ningún icono coincide con esa búsqueda.";
      rejilla.appendChild(vacioAviso);
    }
  }

  buscador.addEventListener("input", () => pintar(buscador.value));
  pintar("");
  contenedor.append(buscador, rejilla);
}

function abrirModalCategorias() {
  renderCategoriasLista();
  formCategoria.reset();
  categoriaCampoIcono.value = "🗂️";
  categoriaIconoElegido.textContent = "🗂️";
  crearSelectorIconos(selectorIconosEl, "🗂️", (icono) => {
    categoriaCampoIcono.value = icono;
    categoriaIconoElegido.textContent = icono;
  });
  modalCategoriasFondo.hidden = false;
}

function cerrarModalCategorias() {
  modalCategoriasFondo.hidden = true;
}

btnCategorias.addEventListener("click", abrirModalCategorias);
btnCerrarCategorias.addEventListener("click", cerrarModalCategorias);
habilitarCierreSeguro(modalCategoriasFondo, cerrarModalCategorias);

formCategoria.addEventListener("submit", async (e) => {
  e.preventDefault();
  const nombre = categoriaCampoNombre.value.trim();
  if (!nombre) return;
  const icono = categoriaCampoIcono.value || "🗂️";

  const res = await fetch("/api/categorias", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre, icono }),
  });
  const datos = await res.json();
  if (!res.ok) {
    alert(datos.error || "No se pudo crear la categoría");
    return;
  }

  categorias.push(datos);
  categorias.sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  renderCategoriasLista();
  renderFiltros();
  poblarSelectCategoria(campoCategoria, campoCategoria.value);

  formCategoria.reset();
  categoriaCampoIcono.value = "🗂️";
  categoriaIconoElegido.textContent = "🗂️";
  crearSelectorIconos(selectorIconosEl, "🗂️", (icono) => {
    categoriaCampoIcono.value = icono;
    categoriaIconoElegido.textContent = icono;
  });
  categoriaCampoNombre.focus();
});

/* --- Espacios (varios stocks independientes: casa, oficina, etc.) --- */

const PALETA_COLOR_ESPACIOS = [
  "#B5551A", "#3E7C8C", "#7B6B9E", "#5B8C5A",
  "#C77B9E", "#C9A227", "#4A6FA5", "#B5473F",
];

let editandoEspacios = false;

function ajustarColor(hex, delta) {
  const num = parseInt(hex.slice(1), 16);
  const canal = (despl) => Math.max(0, Math.min(255, ((num >> despl) & 0xff) + delta));
  const r = canal(16), g = canal(8), b = canal(0);
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
}

function colorEsClaro(hex) {
  const num = parseInt(hex.slice(1), 16);
  const r = (num >> 16) & 0xff, g = (num >> 8) & 0xff, b = num & 0xff;
  return (0.299 * r + 0.587 * g + 0.114 * b) > 170;
}

function aplicarColorEspacio(color) {
  const raiz = document.documentElement.style;
  raiz.setProperty("--accent", color);
  raiz.setProperty("--accent-soft", ajustarColor(color, 95));
  raiz.setProperty("--accent-contrast", colorEsClaro(color) ? "#26211C" : "#FFFFFF");
}

async function cargarEspacios() {
  const [listaRes, actualRes] = await Promise.all([
    fetch("/api/espacios"),
    fetch("/api/espacios/actual"),
  ]);
  espacios = await listaRes.json();
  const actual = await actualRes.json();
  espacioActualId = actual.id;
  renderEspacioActual(actual);
}

function renderEspacioActual(actual) {
  espacioActualIconoEl.textContent = actual.icono;
  espacioActualNombreEl.textContent = actual.nombre;
  aplicarColorEspacio(actual.color);
}

function mostrarVistaEspacios() {
  editandoEspacios = false;
  renderTarjetasEspacios();
  barraEspacio.hidden = true;
  vistaEspacios.hidden = false;
  tabs.hidden = true;
  vistaStock.hidden = true;
  vistaCompra.hidden = true;
  fab.hidden = true;
}

function ocultarVistaEspacios() {
  barraEspacio.hidden = false;
  vistaEspacios.hidden = true;
  tabs.hidden = false;
  vistaStock.hidden = vistaActiva !== "stock";
  vistaCompra.hidden = vistaActiva !== "compra";
  fab.hidden = false;
}

function renderTarjetasEspacios() {
  btnEditarEspacios.textContent = editandoEspacios ? "Listo" : "Editar";
  espaciosTarjetasEl.innerHTML = "";

  for (const esp of espacios) {
    const tarjeta = document.createElement("button");
    tarjeta.type = "button";
    tarjeta.className = "tarjeta-espacio";
    tarjeta.style.background = `linear-gradient(135deg, ${ajustarColor(esp.color, 25)}, ${ajustarColor(esp.color, -25)})`;
    tarjeta.innerHTML = `
      <span class="tarjeta-espacio-icono">${esp.icono}</span>
      <p class="tarjeta-espacio-nombre">${escapeHtml(esp.nombre)}</p>
      ${esp.productos_count ? `<span class="tarjeta-espacio-contador">${esp.productos_count} producto${esp.productos_count === 1 ? "" : "s"}</span>` : ""}
      <span class="tarjeta-espacio-flecha">${editandoEspacios ? "✏️" : "›"}</span>
    `;
    tarjeta.addEventListener("click", () => {
      if (editandoEspacios) abrirFormEspacio(esp);
      else seleccionarEspacio(esp.id);
    });

    if (editandoEspacios && espacios.length > 1) {
      const btnBorrar = document.createElement("button");
      btnBorrar.type = "button";
      btnBorrar.className = "tarjeta-espacio-borrar";
      btnBorrar.title = "Borrar stock";
      btnBorrar.textContent = "✕";
      btnBorrar.addEventListener("click", (e) => {
        e.stopPropagation();
        borrarEspacio(esp);
      });
      tarjeta.appendChild(btnBorrar);
    }
    espaciosTarjetasEl.appendChild(tarjeta);
  }

  const btnNueva = document.createElement("button");
  btnNueva.type = "button";
  btnNueva.className = "tarjeta-espacio tarjeta-espacio-nueva";
  btnNueva.textContent = "+ Nuevo stock";
  btnNueva.addEventListener("click", () => abrirFormEspacio(null));
  espaciosTarjetasEl.appendChild(btnNueva);
}

async function seleccionarEspacio(id) {
  if (id !== espacioActualId) {
    const res = await fetch("/api/espacios/actual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ espacio_id: id }),
    });
    const actual = await res.json();
    espacioActualId = actual.id;
    renderEspacioActual(actual);
    await Promise.all([cargarProductos(), cargarListaCompra()]);
  }
  ocultarVistaEspacios();
}

async function borrarEspacio(esp) {
  if (!confirm(`¿Borrar el stock "${esp.nombre}"? Se borrará también todo su inventario y su lista de la compra.`)) return;
  const res = await fetch(`/api/espacios/${esp.id}`, { method: "DELETE" });
  if (!res.ok) {
    const datos = await res.json().catch(() => ({}));
    alert(datos.error || "No se pudo borrar el stock");
    return;
  }
  const eraElActual = esp.id === espacioActualId;
  espacios = espacios.filter((e) => e.id !== esp.id);
  renderTarjetasEspacios();
  if (eraElActual) {
    const actual = await (await fetch("/api/espacios/actual")).json();
    espacioActualId = actual.id;
    renderEspacioActual(actual);
    await Promise.all([cargarProductos(), cargarListaCompra()]);
  }
}

btnEspacios.addEventListener("click", mostrarVistaEspacios);
btnCerrarEspacios.addEventListener("click", ocultarVistaEspacios);
btnEditarEspacios.addEventListener("click", () => {
  editandoEspacios = !editandoEspacios;
  renderTarjetasEspacios();
});

/* --- Formulario de alta/edición de un stock (nombre, icono, color) --- */

function renderPaletaColorEspacio(seleccionado) {
  paletaColorEspacioEl.innerHTML = "";
  for (const color of PALETA_COLOR_ESPACIOS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.style.background = color;
    btn.className = color.toLowerCase() === seleccionado.toLowerCase() ? "seleccionado" : "";
    btn.title = color;
    btn.addEventListener("click", () => {
      espacioCampoColor.value = color;
      espacioCampoColorPicker.value = color;
      renderPaletaColorEspacio(color);
    });
    paletaColorEspacioEl.appendChild(btn);
  }
}

espacioCampoColorPicker.addEventListener("input", (e) => {
  espacioCampoColor.value = e.target.value;
  renderPaletaColorEspacio(e.target.value);
});

function abrirFormEspacio(esp) {
  formEspacio.reset();
  const esEdicion = Boolean(esp);
  espacioEditId.value = esEdicion ? esp.id : "";
  espacioFormTitulo.textContent = esEdicion ? "Editar stock" : "Nuevo stock";
  espacioBotonGuardar.textContent = esEdicion ? "Guardar" : "Añadir";

  espacioCampoNombre.value = esEdicion ? esp.nombre : "";
  const icono = esEdicion ? esp.icono : "🏠";
  const color = esEdicion ? esp.color : PALETA_COLOR_ESPACIOS[espacios.length % PALETA_COLOR_ESPACIOS.length];

  espacioCampoIcono.value = icono;
  espacioIconoElegido.textContent = icono;
  crearSelectorIconos(selectorIconoEspacioEl, icono, (nuevoIcono) => {
    espacioCampoIcono.value = nuevoIcono;
    espacioIconoElegido.textContent = nuevoIcono;
  });

  espacioCampoColor.value = color;
  espacioCampoColorPicker.value = color;
  renderPaletaColorEspacio(color);

  modalEspacioFormFondo.hidden = false;
  espacioCampoNombre.focus();
}

function cerrarFormEspacio() {
  modalEspacioFormFondo.hidden = true;
}

btnCancelarEspacio.addEventListener("click", cerrarFormEspacio);
habilitarCierreSeguro(modalEspacioFormFondo, cerrarFormEspacio);

formEspacio.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = espacioEditId.value;
  const payload = {
    nombre: espacioCampoNombre.value.trim(),
    icono: espacioCampoIcono.value || "🏠",
    color: espacioCampoColor.value,
  };
  if (!payload.nombre) return;

  const res = await fetch(id ? `/api/espacios/${id}` : "/api/espacios", {
    method: id ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const datos = await res.json();
  if (!res.ok) {
    alert(datos.error || "No se pudo guardar el stock");
    return;
  }

  if (id) {
    espacios = espacios.map((esp) => (esp.id === datos.id ? { ...esp, ...datos } : esp));
    if (Number(id) === espacioActualId) renderEspacioActual(datos);
  } else {
    espacios.push(datos);
  }
  espacios.sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));

  cerrarFormEspacio();
  renderTarjetasEspacios();
});

/* --- Stock --- */

async function cargarProductos() {
  const res = await fetch("/api/productos");
  productos = await res.json();
  render();
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
  const bajoStock = p.cantidad <= p.stock_minimo;
  div.className = "tarjeta" + (bajoStock ? " bajo" : "") + (p.revisar_caducidad ? " aviso-caducidad" : "");

  const avisos = [];
  if (bajoStock) avisos.push("¡Pocas unidades!");
  if (p.revisar_caducidad) avisos.push("⏰ Revisar caducidad");

  div.innerHTML = `
    <div class="icono">${iconoEfectivo(p)}</div>
    <div class="info">
      <div class="nombre">${escapeHtml(p.nombre)}</div>
      <div class="detalle">${escapeHtml(p.categoria)}${avisos.length ? " · " + avisos.join(" · ") : ""}</div>
    </div>
    <div class="contador">
      <button data-accion="restar" title="Quitar uno">−</button>
      <span class="cantidad">${p.cantidad} ${escapeHtml(p.unidad)}</span>
      <button data-accion="sumar" title="Añadir uno">+</button>
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
  const res = await fetch(`/api/productos/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ delta }),
  });
  const actualizado = await res.json();
  productos = productos.map((p) => (p.id === id ? actualizado : p));
  render();
  cargarListaCompra();
}

async function borrarProducto(id) {
  if (!confirm("¿Eliminar este producto del stock?")) return;
  await fetch(`/api/productos/${id}`, { method: "DELETE" });
  productos = productos.filter((p) => p.id !== id);
  render();
}

let iconoProductoTocado = false;

function actualizarSelectorIconoProducto() {
  btnQuitarIconoProducto.hidden = !campoIcono.value;
  crearSelectorIconos(selectorIconoProductoEl, campoIcono.value, (icono) => {
    campoIcono.value = icono;
    iconoProductoTocado = true;
    btnQuitarIconoProducto.hidden = false;
  });
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
    modalTitulo.textContent = "Editar producto";
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
    modalTitulo.textContent = `Añadir "${producto.nombre}" al stock`;
    document.getElementById("campoNombre").value = producto.nombre || "";
    poblarSelectCategoria(campoCategoria, producto.categoria || null);
    document.getElementById("campoCantidad").value = producto.cantidad || 1;
    document.getElementById("campoUnidad").value = producto.unidad || "ud";
    campoIcono.value = producto.icono || "";
    iconoProductoTocado = Boolean(producto.icono);
  } else {
    modalTitulo.textContent = "Nuevo producto";
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
  const payload = {
    nombre: document.getElementById("campoNombre").value.trim(),
    categoria: campoCategoria.value,
    icono: campoIcono.value || "",
    cantidad: Number(document.getElementById("campoCantidad").value),
    unidad: document.getElementById("campoUnidad").value.trim() || "ud",
    stock_minimo: Number(document.getElementById("campoMinimo").value),
    dias_aviso: Number(document.getElementById("campoDiasAviso").value),
  };
  if (!payload.nombre) return;

  if (id) {
    const res = await fetch(`/api/productos/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const actualizado = await res.json();
    productos = productos.map((p) => (p.id === actualizado.id ? actualizado : p));
  } else {
    const res = await fetch("/api/productos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const creado = await res.json();
    productos.push(creado);
  }

  cerrarModal();
  render();
  cargarListaCompra();
  cargarHistorial();
});

btnCancelar.addEventListener("click", cerrarModal);
habilitarCierreSeguro(modalFondo, cerrarModal);

buscador.addEventListener("input", (e) => {
  textoBusqueda = e.target.value;
  render();
});

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
  const res = await fetch("/api/lista-compra");
  const datos = await res.json();
  pendientesCompra = datos.pendientes;
  completadosCompra = datos.completados;
  renderListaCompra();
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
    titulo.textContent = `${iconoDeCategoria(nombreCategoria)} ${nombreCategoria}`;
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
    <span class="tile-compra-icono">${iconoEfectivo(item)}</span>
    <span class="tile-compra-nombre">${escapeHtml(item.nombre)}</span>
    ${item.cantidad > 1 ? `<span class="tile-compra-cantidad">×${item.cantidad}</span>` : ""}
  `;
  if (completado) {
    btn.addEventListener("click", () => restaurarItemCompra(item.id));
  } else {
    agregarPulsacion(
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
    await fetch(`/api/lista-compra/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activo: false }),
    });
    cargarListaCompra();
  }, 280);
}

async function restaurarItemCompra(id) {
  await fetch(`/api/lista-compra/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ activo: true }),
  });
  cargarListaCompra();
}

btnToggleCompletados.addEventListener("click", () => {
  seccionCompletadosEl.classList.toggle("plegada");
});

let iconoCompraTocado = false;

function actualizarSelectorIconoCompra() {
  btnQuitarIconoCompra.hidden = !compraCampoIcono.value;
  crearSelectorIconos(selectorIconoCompraEl, compraCampoIcono.value, (icono) => {
    compraCampoIcono.value = icono;
    iconoCompraTocado = true;
    btnQuitarIconoCompra.hidden = false;
  });
}

// item === undefined/null -> alta en blanco.
// item sin "id" (una entrada del catálogo) -> alta prellenada con esos datos.
// item con "id" (una fila real de la lista) -> edición de ese artículo.
function abrirModalCompra(item) {
  formCompra.reset();
  const esEdicion = Boolean(item && item.id !== undefined);
  compraEditIdEl.value = esEdicion ? item.id : "";
  compraModalTitulo.textContent = esEdicion
    ? "Editar artículo"
    : item
    ? `Añadir "${item.nombre}"`
    : "Añadir a la lista de la compra";
  compraBotonGuardar.textContent = esEdicion ? "Guardar" : "Añadir";

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
  const payload = {
    nombre: document.getElementById("compraCampoNombre").value.trim(),
    cantidad: Number(compraCampoCantidad.value) || 1,
    unidad: document.getElementById("compraCampoUnidad").value.trim() || "ud",
    categoria: compraCampoCategoria.value,
    icono: compraCampoIcono.value || "",
    sub_descripcion: compraCampoSubdescripcion.value.trim(),
  };
  if (!payload.nombre) return;

  await fetch(id ? `/api/lista-compra/${id}` : "/api/lista-compra", {
    method: id ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  cerrarModalCompra();
  cargarListaCompra();
  cargarHistorial();
});

btnCancelarCompra.addEventListener("click", cerrarModalCompra);
habilitarCierreSeguro(modalCompraFondo, cerrarModalCompra);

/* --- Catálogo (navegar y añadir a la lista por categorías) --- */

let catalogoModo = "compra"; // "compra" (lista de la compra) o "stock" (alta directa de producto)

function abrirModalCatalogo(modo = "compra") {
  catalogoModo = modo;
  if (modo === "stock") {
    catalogoTitulo.textContent = "Añadir al stock";
    catalogoAyuda.textContent = "Toca un producto para indicar su cantidad y añadirlo al stock.";
    btnCrearDesdeCatalogo.textContent = "+ Crear producto nuevo";
  } else {
    catalogoTitulo.textContent = "Añadir a la lista";
    catalogoAyuda.textContent = "Toca un producto para añadirlo. Mantén pulsado para ajustar cantidad, unidad, sub-descripción o icono antes de añadirlo.";
    btnCrearDesdeCatalogo.textContent = "+ Crear artículo nuevo";
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
    titulo.textContent = `${iconoDeCategoria(nombreCategoria)} ${nombreCategoria}`;
    const rejilla = document.createElement("div");
    rejilla.className = "tiles-grid";
    for (const item of porCategoria.get(nombreCategoria)) {
      rejilla.appendChild(crearTileCatalogo(item));
    }
    grupo.append(titulo, rejilla);
    catalogoGruposEl.appendChild(grupo);
  }
}

function crearTileCatalogo(entry) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "tile-compra";
  const detalle = [entry.unidad, entry.sub_descripcion].filter(Boolean).join(" · ");
  btn.innerHTML = `
    <span class="tile-compra-icono">${entry.icono || iconoDeCategoria(entry.categoria)}</span>
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

  btn.title = `Toca para añadir · mantén pulsado para personalizar${detalle ? " · " + detalle : ""}`;
  agregarPulsacion(
    btn,
    () => anadirDesdeCatalogo(entry),
    () => {
      cerrarModalCatalogo();
      volverAlCatalogoTrasCompra = true;
      abrirModalCompra({ ...entry, cantidad: 1 });
    }
  );
  return btn;
}

async function anadirDesdeCatalogo(entry) {
  await fetch("/api/lista-compra", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      nombre: entry.nombre,
      categoria: entry.categoria,
      icono: entry.icono,
      unidad: entry.unidad,
      sub_descripcion: entry.sub_descripcion,
    }),
  });
  cargarListaCompra();
}

catalogoBuscadorEl.addEventListener("input", (e) => renderCatalogo(e.target.value));

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

btnCerrarCatalogo.addEventListener("click", cerrarModalCatalogo);
habilitarCierreSeguro(modalCatalogoFondo, cerrarModalCatalogo);

/* --- Ajustes --- */

function abrirModalAjustes() {
  cargarUsuarios();
  modalAjustesFondo.hidden = false;
}

function cerrarModalAjustes() {
  modalAjustesFondo.hidden = true;
}

btnAjustes.addEventListener("click", abrirModalAjustes);
btnCancelarAjustes.addEventListener("click", cerrarModalAjustes);
habilitarCierreSeguro(modalAjustesFondo, cerrarModalAjustes);

/* --- Sesion y usuarios --- */

async function cargarEstadoAuth() {
  const res = await fetch("/api/auth/estado");
  const datos = await res.json();
  ajustesUsuarioActual.textContent = datos.usuario || "-";
}

async function cargarUsuarios() {
  const res = await fetch("/api/usuarios");
  const usuarios = await res.json();
  usuariosListaEl.innerHTML = "";
  for (const u of usuarios) {
    const chip = document.createElement("div");
    chip.className = "categoria-chip";
    chip.innerHTML = `<span>👤 ${escapeHtml(u.nombre_usuario)}</span>`;
    if (usuarios.length > 1) {
      const btnBorrar = document.createElement("button");
      btnBorrar.type = "button";
      btnBorrar.title = "Borrar usuario";
      btnBorrar.textContent = "✕";
      btnBorrar.addEventListener("click", () => borrarUsuario(u));
      chip.appendChild(btnBorrar);
    }
    usuariosListaEl.appendChild(chip);
  }
}

async function borrarUsuario(u) {
  if (!confirm(`¿Borrar el usuario "${u.nombre_usuario}"?`)) return;
  const res = await fetch(`/api/usuarios/${u.id}`, { method: "DELETE" });
  if (!res.ok) {
    const datos = await res.json().catch(() => ({}));
    alert(datos.error || "No se pudo borrar el usuario");
    return;
  }
  cargarUsuarios();
}

btnAnadirUsuario.addEventListener("click", async () => {
  usuariosEstado.hidden = true;
  const usuario = usuarioCampoNombre.value.trim();
  const password = usuarioCampoPassword.value;
  if (!usuario || password.length < 4) {
    usuariosEstado.textContent = "Pon un nombre y una contraseña de al menos 4 caracteres";
    usuariosEstado.hidden = false;
    return;
  }
  const res = await fetch("/api/auth/registrar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario, password }),
  });
  const datos = await res.json();
  if (!res.ok) {
    usuariosEstado.textContent = datos.error || "No se pudo crear el usuario";
    usuariosEstado.hidden = false;
    return;
  }
  usuarioCampoNombre.value = "";
  usuarioCampoPassword.value = "";
  cargarUsuarios();
});

btnCerrarSesion.addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

/* --- Escaneo de tickets --- */

function abrirModalTicket() {
  ticketArchivo.value = "";
  ticketPasoFoto.hidden = false;
  ticketCargando.hidden = true;
  ticketPasoRevision.hidden = true;
  ticketItemsEl.innerHTML = "";
  modalTicketFondo.hidden = false;
}

function cerrarModalTicket() {
  modalTicketFondo.hidden = true;
}

function opcionesVincular(nombreDetectado) {
  const coincidencia = productos.find(
    (p) => p.nombre.trim().toLowerCase() === (nombreDetectado || "").trim().toLowerCase()
  );
  let html = '<option value="nuevo">➕ Crear producto nuevo</option>';
  html += productos
    .map(
      (p) =>
        `<option value="${p.id}" ${coincidencia && coincidencia.id === p.id ? "selected" : ""}>Sumar a: ${escapeHtml(p.nombre)} (${p.cantidad} ${escapeHtml(p.unidad)})</option>`
    )
    .join("");
  return html;
}

function crearFilaTicket(item) {
  const li = document.createElement("li");
  li.className = "ticket-item";
  li.innerHTML = `
    <div class="fila-superior">
      <input type="text" name="nombre" value="${escapeHtml(item.nombre || "")}" placeholder="Nombre">
      <input type="number" name="cantidad" min="1" value="${item.cantidad || 1}">
      <input type="text" name="unidad" value="${escapeHtml(item.unidad || "ud")}" maxlength="10">
      <button type="button" title="Quitar línea">🗑️</button>
    </div>
    <select name="vincular">${opcionesVincular(item.nombre)}</select>
    <select name="categoria"></select>
  `;

  const selectVincular = li.querySelector('select[name="vincular"]');
  const selectCategoria = li.querySelector('select[name="categoria"]');
  poblarSelectCategoria(selectCategoria, "Otros");
  const actualizarVisibilidadCategoria = () => {
    selectCategoria.hidden = selectVincular.value !== "nuevo";
  };
  selectVincular.addEventListener("change", actualizarVisibilidadCategoria);
  actualizarVisibilidadCategoria();

  li.querySelector("button").addEventListener("click", () => li.remove());
  return li;
}

btnEscanearTicket.addEventListener("click", abrirModalTicket);
btnCancelarTicket.addEventListener("click", cerrarModalTicket);
btnCancelarRevisionTicket.addEventListener("click", cerrarModalTicket);
habilitarCierreSeguro(modalTicketFondo, cerrarModalTicket);

btnAnadirLineaTicket.addEventListener("click", () => {
  ticketItemsEl.appendChild(crearFilaTicket({ nombre: "", cantidad: 1, unidad: "ud" }));
});

btnAnalizarTicket.addEventListener("click", async () => {
  const archivo = ticketArchivo.files[0];
  if (!archivo) {
    alert("Elige antes una foto del ticket");
    return;
  }

  ticketPasoFoto.hidden = true;
  ticketCargando.hidden = false;

  const formData = new FormData();
  formData.append("foto", archivo);

  try {
    const res = await fetch("/api/tickets/analizar", { method: "POST", body: formData });
    const datos = await res.json();
    if (!res.ok) {
      alert(datos.error || "No se pudo analizar el ticket");
      ticketPasoFoto.hidden = false;
      ticketCargando.hidden = true;
      return;
    }

    ticketItemsEl.innerHTML = "";
    if (datos.length === 0) {
      ticketItemsEl.appendChild(crearFilaTicket({ nombre: "", cantidad: 1, unidad: "ud" }));
    } else {
      for (const item of datos) {
        ticketItemsEl.appendChild(crearFilaTicket(item));
      }
    }
    ticketCargando.hidden = true;
    ticketPasoRevision.hidden = false;
  } catch (err) {
    alert("No se pudo analizar el ticket");
    ticketPasoFoto.hidden = false;
    ticketCargando.hidden = true;
  }
});

btnConfirmarTicket.addEventListener("click", async () => {
  const filas = [...ticketItemsEl.querySelectorAll(".ticket-item")];
  const items = filas
    .map((fila) => {
      const nombre = fila.querySelector('[name="nombre"]').value.trim();
      const cantidad = Number(fila.querySelector('[name="cantidad"]').value) || 1;
      const unidad = fila.querySelector('[name="unidad"]').value.trim() || "ud";
      const vincular = fila.querySelector('[name="vincular"]').value;
      const categoria = fila.querySelector('[name="categoria"]').value;
      if (!nombre) return null;
      return vincular === "nuevo"
        ? { nombre, cantidad, unidad, categoria }
        : { nombre, cantidad, unidad, producto_id: Number(vincular) };
    })
    .filter(Boolean);

  if (items.length === 0) {
    cerrarModalTicket();
    return;
  }

  btnConfirmarTicket.disabled = true;
  try {
    await fetch("/api/tickets/confirmar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items }),
    });
    await cargarProductos();
    await cargarListaCompra();
    cerrarModalTicket();
  } finally {
    btnConfirmarTicket.disabled = false;
  }
});

cargarEspacios();
cargarCategorias().then(() => {
  cargarProductos();
  cargarListaCompra();
});
cargarHistorial();
cargarEstadoAuth();
