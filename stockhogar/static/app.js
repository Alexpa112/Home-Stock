/**
 * APP.JS - Orquestador Principal (Frontend)
 *
 * Patrón: Orquestador limpio
 * Responsabilidad: Inicializar managers y conectarlos
 *
 * Estructura:
 * 1. Constantes globales (iconos, etc.)
 * 2. Funciones helper reutilizables
 * 3. Instanciación de managers
 * 4. Wireado de eventos inter-managers
 */

// ===== 1. CONSTANTES GLOBALES =====

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

// ===== 2. FUNCIONES HELPER =====

function escapeHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

function normalizarTexto(texto) {
  const SIN_ACENTOS = new RegExp("[̀-ͯ]", "g");
  return (texto || "")
    .normalize("NFD")
    .replace(SIN_ACENTOS, "")
    .toLowerCase()
    .trim();
}

// ===== 3. INSTANCIACIÓN DE MANAGERS =====

console.log('🚀 Inicializando Frontend OOP...');

// Verificar que singletons base estén disponibles
if (!window.API || !window.DOM) {
  console.error('❌ Error: window.API o window.DOM no disponibles');
  throw new Error('Core singletons not loaded');
}

// Instanciar managers en orden de dependencia
const managers = {
  categorias: window.categoriasManager,
  productos: window.productosManager,
  compra: window.compraManager,
  espacios: window.espaciosManager,
  tickets: window.ticketsManager,
  ui: window.uiManager,
};

// ===== 4. CARGA INICIAL =====

async function inicializarApp() {
  try {
    // Cargar datos base
    console.log('📦 Cargando categorías...');
    await managers.categorias.cargar();

    console.log('📦 Cargando productos...');
    await managers.productos.cargar();

    console.log('📦 Cargando espacios...');
    await managers.espacios.cargar();

    console.log('✅ Aplicación inicializada correctamente');
  } catch (error) {
    console.error('❌ Error inicializando aplicación:', error);
  }
}

// ===== 5. WIREADO DE EVENTOS =====

// Cuando se crea un producto, refrescar sugerencias en compra
managers.productos.suscribir((evento, datos) => {
  if (evento === 'producto-creado' || evento === 'productos-cargados') {
    // Actualizar sugerencias en el manager de compra si es necesario
    console.log('📝 Productos actualizados, notificando...');
  }
});

// Cuando se cambia de espacio, recargar productos
managers.espacios.suscribir((evento, datos) => {
  if (evento === 'espacio-seleccionado') {
    console.log('🏠 Espacio cambiado, recargar productos...');
    managers.productos.cargar();
  }
});

// Cuando se cargan categorías, actualizar renderizado de productos
managers.categorias.suscribir((evento, datos) => {
  if (evento === 'categorias-cargadas') {
    console.log('🏷️ Categorías cargadas, actualizar filtros...');
  }
});

// ===== 6. HANDLERS DE PÁGINA =====

// Cuando carga la página
window.addEventListener('load', () => {
  console.log('📄 Página cargada, iniciando app...');
  inicializarApp();
});

// ===== 7. EXPORTAR PARA DEBUGGING =====

window.__DEBUG__ = {
  managers,
  CATALOGO_ICONOS,
  escapeHtml,
  normalizarTexto,
};

console.log('💡 Tip: window.__DEBUG__.managers para inspeccionar');
