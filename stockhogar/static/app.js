/**
 * APP.JS - Orquestador Principal (Frontend)
 *
 * Patrón: Orquestador limpio
 * Responsabilidad: Inicializar managers y conectarlos
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

// ===== 2. CUANDO DOM ESTÁ LISTO =====

document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 Inicializando aplicación...');

  // Verificar que singletons base estén disponibles
  if (!window.API || !window.DOM) {
    console.error('❌ Error: window.API o window.DOM no disponibles');
    return;
  }

  // Instanciar managers AQUÍ, dentro de DOMContentLoaded
  const managers = {
    categorias: new CategoriasManager(window.API, window.DOM),
    productos: new ProductosManager(window.API, window.DOM),
    compra: new CompraManager(window.API, window.DOM),
    espacios: new EspaciosManager(window.API, window.DOM),
    tickets: new TicketsManager(window.API, window.DOM),
    ui: new UIManager(window.API, window.DOM),
    listas: new ListasManager(window.API, window.DOM),
    usuarios: new UsuariosManager(window.API, window.DOM),
    historial: new HistorialManager(window.API, window.DOM),
  };

  // Hacer managers disponibles globalmente
  window.productosManager = managers.productos;
  window.compraManager = managers.compra;
  window.categoriasManager = managers.categorias;
  window.espaciosManager = managers.espacios;
  window.ticketsManager = managers.tickets;
  window.uiManager = managers.ui;
  window.listasManager = managers.listas;
  window.usuariosManager = managers.usuarios;
  window.historialManager = managers.historial;

  // ===== 3. WIREADO DE EVENTOS =====

  // ProductosManager
  managers.productos.suscribir((evento) => {
    if (['productos-cargados', 'producto-creado', 'producto-actualizado', 'producto-borrado', 'filtro-cambiado'].includes(evento)) {
      managers.productos.render();
    }
  });

  // CompraManager
  managers.compra.suscribir((evento) => {
    if (['articulos-cargados', 'articulo-creado', 'articulo-actualizado', 'articulo-borrado'].includes(evento)) {
      managers.compra.render();
    }
  });

  // CategoriasManager
  managers.categorias.suscribir((evento) => {
    if (['categorias-cargadas', 'categoria-creada', 'categoria-borrada'].includes(evento)) {
      managers.categorias.render();
      managers.productos.render();
    }
  });

  // EspaciosManager
  managers.espacios.suscribir((evento) => {
    if (['espacios-cargados', 'espacio-creado', 'espacio-actualizado', 'espacio-borrado', 'espacio-seleccionado'].includes(evento)) {
      managers.espacios.render();
      if (evento === 'espacio-seleccionado') {
        managers.productos.cargar();
      }
    }
  });

  // UIManager
  managers.ui.suscribir((evento) => {
    if (['modal-abierto', 'modal-cerrado', 'tema-cambiado'].includes(evento)) {
      managers.ui.render();
    }
  });

  // ===== 4. EVENT LISTENERS DE BOTONES =====

  // Botón tema
  const btnTema = window.DOM.get('btnTema');
  if (btnTema) {
    btnTema.addEventListener('click', () => managers.ui.toggleTema());
  }

  // Botón categorías
  const btnCategorias = window.DOM.get('btnCategorias');
  if (btnCategorias) {
    btnCategorias.addEventListener('click', () => managers.categorias.abrirModal?.());
  }

  // Botón crear producto (+)
  const btnCrear = document.querySelector('.fab-button');
  if (btnCrear) {
    btnCrear.addEventListener('click', () => managers.productos.abrirModalCrear());
  }

  // Botón selector listas
  const btnCambiarLista = window.DOM.get('btnCambiarLista');
  if (btnCambiarLista) {
    btnCambiarLista.addEventListener('click', () => managers.listas.abrirModal());
  }

  // Botón ajustes/usuarios
  const btnAjustes = window.DOM.get('btnAjustes');
  if (btnAjustes) {
    btnAjustes.addEventListener('click', () => managers.usuarios.cargar());
  }

  // Botón escanear tickets
  const btnEscanear = window.DOM.get('btnEscanearTicket');
  if (btnEscanear) {
    btnEscanear.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) managers.tickets.procesarArchivo?.(file);
      });
      input.click();
    });
  }

  // Formulario productos
  const formProducto = window.DOM.get('formProducto');
  if (formProducto) {
    formProducto.addEventListener('submit', (e) => managers.productos.guardarProducto?.(e));
  }

  // Formulario compra
  const formCompra = window.DOM.get('formCompra');
  if (formCompra) {
    formCompra.addEventListener('submit', (e) => managers.compra.guardarArticulo?.(e));
  }

  // ===== 5. CARGAR DATOS INICIALES =====

  async function inicializarApp() {
    try {
      console.log('📦 Cargando datos iniciales...');
      await managers.categorias.cargar();
      await managers.productos.cargar();
      await managers.espacios.cargar();
      console.log('✅ Aplicación lista');
    } catch (error) {
      console.error('❌ Error inicializando:', error);
    }
  }

  inicializarApp();

  // ===== 6. DEBUG =====

  window.__DEBUG__ = {
    managers,
    CATALOGO_ICONOS,
    escapeHtml,
    normalizarTexto,
  };

  console.log('💡 Tip: window.__DEBUG__.managers para inspeccionar');
});
