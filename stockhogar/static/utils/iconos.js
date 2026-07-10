// Helper único para renderizar iconos (nombre de símbolo -> HTML <svg><use>).
// Todo el código que hoy asigna un icono al DOM debe pasar por aquí en vez
// de usar el emoji/nombre directamente, para que el punto de renderizado
// esté centralizado.
const ICONO_POR_DEFECTO = "h-folder";

let spriteListo = fetch("/static/icons/sprite.svg")
  .then((res) => res.text())
  .then((svg) => {
    document.body.insertAdjacentHTML("afterbegin", svg);
  })
  .catch((error) => {
    console.error("No se pudo cargar el sprite de iconos:", error);
  });

function renderIcono(nombre, { tamano = 20, clase = "" } = {}) {
  const seguro = nombre || ICONO_POR_DEFECTO;
  return `<svg class="icono-svg ${clase}" width="${tamano}" height="${tamano}" aria-hidden="true"><use href="#icon-${seguro}"></use></svg>`;
}
