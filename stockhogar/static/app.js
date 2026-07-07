const ICONOS = {
  Alimentacion: "🍎",
  Limpieza: "🧴",
  Higiene: "🧼",
  Bebidas: "🥤",
  Otros: "🗂️",
};

const lista = document.getElementById("lista");
const vacio = document.getElementById("vacio");
const buscador = document.getElementById("buscador");
const filtros = document.getElementById("filtros");
const fab = document.getElementById("btnAbrirModal");
const modalFondo = document.getElementById("modal");
const form = document.getElementById("formProducto");
const btnCancelar = document.getElementById("btnCancelar");
const modalTitulo = document.getElementById("modalTitulo");

const tabs = document.getElementById("tabs");
const vistaStock = document.getElementById("vistaStock");
const vistaCompra = document.getElementById("vistaCompra");
const listaCompraEl = document.getElementById("listaCompra");
const compraVacia = document.getElementById("compraVacia");
const btnSincronizarBring = document.getElementById("btnSincronizarBring");

const modalCompraFondo = document.getElementById("modalCompra");
const formCompra = document.getElementById("formCompra");
const btnCancelarCompra = document.getElementById("btnCancelarCompra");

const btnAjustes = document.getElementById("btnAjustes");
const modalAjustesFondo = document.getElementById("modalAjustes");
const formAjustes = document.getElementById("formAjustes");
const btnCancelarAjustes = document.getElementById("btnCancelarAjustes");
const btnProbarBring = document.getElementById("btnProbarBring");
const ajustesEstado = document.getElementById("ajustesEstado");
const ajustesLista = document.getElementById("ajustesLista");

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

const CATEGORIAS_DISPONIBLES = [...document.getElementById("campoCategoria").options].map((o) => o.value);

let productos = [];
let listaCompra = [];
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
    <div class="icono">${ICONOS[p.categoria] || "🗂️"}</div>
    <div class="info">
      <div class="nombre">${escapeHtml(p.nombre)}</div>
      <div class="detalle">${p.categoria}${avisos.length ? " · " + avisos.join(" · ") : ""}</div>
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

function escapeHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
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

function abrirModal(producto) {
  form.reset();
  document.getElementById("productoId").value = "";
  document.getElementById("campoCantidad").value = 1;
  document.getElementById("campoUnidad").value = "ud";
  document.getElementById("campoMinimo").value = 1;
  document.getElementById("campoDiasAviso").value = 30;

  if (producto) {
    modalTitulo.textContent = "Editar producto";
    document.getElementById("productoId").value = producto.id;
    document.getElementById("campoNombre").value = producto.nombre;
    document.getElementById("campoCategoria").value = producto.categoria;
    document.getElementById("campoCantidad").value = producto.cantidad;
    document.getElementById("campoUnidad").value = producto.unidad;
    document.getElementById("campoMinimo").value = producto.stock_minimo;
    document.getElementById("campoDiasAviso").value = producto.dias_aviso;
  } else {
    modalTitulo.textContent = "Nuevo producto";
  }

  modalFondo.hidden = false;
  document.getElementById("campoNombre").focus();
}

function cerrarModal() {
  modalFondo.hidden = true;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("productoId").value;
  const payload = {
    nombre: document.getElementById("campoNombre").value.trim(),
    categoria: document.getElementById("campoCategoria").value,
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
  if (vistaActiva === "compra") {
    abrirModalCompra();
  } else {
    abrirModal(null);
  }
});

/* --- Lista de la compra --- */

async function cargarListaCompra() {
  const res = await fetch("/api/lista-compra");
  listaCompra = await res.json();
  renderListaCompra();
}

function renderListaCompra() {
  listaCompraEl.innerHTML = "";
  compraVacia.hidden = listaCompra.length !== 0;
  btnSincronizarBring.hidden = !bringActivado || listaCompra.length === 0;

  for (const item of listaCompra) {
    listaCompraEl.appendChild(crearItemCompra(item));
  }
}

function crearItemCompra(item) {
  const li = document.createElement("li");
  li.className = "item-compra";
  li.innerHTML = `
    <input type="checkbox" title="Marcar como comprado">
    <div class="info">
      <div class="nombre">${escapeHtml(item.nombre)}</div>
      <div class="detalle">${item.unidad} · ${item.origen === "auto" ? "Repuesto automático" : "Añadido a mano"}</div>
    </div>
    ${item.sincronizado_bring ? '<span class="badge-sincronizado">✅ En Bring!</span>' : ""}
  `;
  li.querySelector('input[type="checkbox"]').addEventListener("change", () => marcarComprado(item.id));
  return li;
}

async function marcarComprado(id) {
  await fetch(`/api/lista-compra/${id}`, { method: "DELETE" });
  listaCompra = listaCompra.filter((i) => i.id !== id);
  renderListaCompra();
}

function abrirModalCompra() {
  formCompra.reset();
  document.getElementById("compraCampoUnidad").value = "ud";
  modalCompraFondo.hidden = false;
  document.getElementById("compraCampoNombre").focus();
}

function cerrarModalCompra() {
  modalCompraFondo.hidden = true;
}

formCompra.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    nombre: document.getElementById("compraCampoNombre").value.trim(),
    unidad: document.getElementById("compraCampoUnidad").value.trim() || "ud",
  };
  if (!payload.nombre) return;

  const res = await fetch("/api/lista-compra", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const creado = await res.json();
  listaCompra.push(creado);
  cerrarModalCompra();
  renderListaCompra();
});

btnCancelarCompra.addEventListener("click", cerrarModalCompra);
habilitarCierreSeguro(modalCompraFondo, cerrarModalCompra);

btnSincronizarBring.addEventListener("click", async () => {
  btnSincronizarBring.disabled = true;
  btnSincronizarBring.textContent = "Sincronizando...";
  try {
    const res = await fetch("/api/bring/sincronizar", { method: "POST" });
    const datos = await res.json();
    if (!res.ok) {
      alert(datos.error || "No se pudo sincronizar con Bring!");
    } else {
      await cargarListaCompra();
    }
  } finally {
    btnSincronizarBring.disabled = false;
    btnSincronizarBring.textContent = "🔄 Sincronizar con Bring!";
  }
});

/* --- Ajustes / Bring! --- */

let bringActivado = false;

async function cargarAjustes() {
  const res = await fetch("/api/ajustes");
  const ajustes = await res.json();
  bringActivado = ajustes.activado;
  document.getElementById("ajustesActivado").checked = ajustes.activado;
  document.getElementById("ajustesEmail").value = ajustes.email;
  if (ajustes.lista_uuid) {
    ajustesLista.innerHTML = `<option value="${ajustes.lista_uuid}">${escapeHtml(ajustes.lista_nombre)}</option>`;
  }
  renderListaCompra();
}

function abrirModalAjustes() {
  ajustesEstado.textContent = "";
  modalAjustesFondo.hidden = false;
}

function cerrarModalAjustes() {
  modalAjustesFondo.hidden = true;
}

btnAjustes.addEventListener("click", abrirModalAjustes);
btnCancelarAjustes.addEventListener("click", cerrarModalAjustes);
habilitarCierreSeguro(modalAjustesFondo, cerrarModalAjustes);

btnProbarBring.addEventListener("click", async () => {
  const email = document.getElementById("ajustesEmail").value.trim();
  const password = document.getElementById("ajustesPassword").value;
  if (!email) {
    ajustesEstado.textContent = "Introduce primero el email de Bring!";
    return;
  }
  ajustesEstado.textContent = "Conectando con Bring!...";
  btnProbarBring.disabled = true;
  try {
    const res = await fetch("/api/bring/listas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const datos = await res.json();
    if (!res.ok) {
      ajustesEstado.textContent = datos.error || "No se pudo conectar con Bring!";
      return;
    }
    ajustesLista.innerHTML = datos
      .map((l) => `<option value="${l.uuid}">${escapeHtml(l.nombre)}</option>`)
      .join("");
    ajustesEstado.textContent = "Conexión correcta. Elige la lista y guarda los ajustes.";
  } catch (err) {
    ajustesEstado.textContent = "No se pudo conectar con Bring!";
  } finally {
    btnProbarBring.disabled = false;
  }
});

formAjustes.addEventListener("submit", async (e) => {
  e.preventDefault();
  const listaSeleccionada = ajustesLista.options[ajustesLista.selectedIndex];
  const payload = {
    activado: document.getElementById("ajustesActivado").checked,
    email: document.getElementById("ajustesEmail").value.trim(),
    password: document.getElementById("ajustesPassword").value,
    lista_uuid: listaSeleccionada ? listaSeleccionada.value : "",
    lista_nombre: listaSeleccionada ? listaSeleccionada.textContent : "",
  };
  const res = await fetch("/api/ajustes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const ajustes = await res.json();
  bringActivado = ajustes.activado;
  cerrarModalAjustes();
  renderListaCompra();
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

function opcionesCategoria(seleccionada) {
  return CATEGORIAS_DISPONIBLES
    .map((c) => `<option value="${c}" ${c === seleccionada ? "selected" : ""}>${c}</option>`)
    .join("");
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
    <select name="categoria">${opcionesCategoria("Otros")}</select>
  `;

  const selectVincular = li.querySelector('select[name="vincular"]');
  const selectCategoria = li.querySelector('select[name="categoria"]');
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

cargarProductos();
cargarListaCompra();
cargarAjustes();
