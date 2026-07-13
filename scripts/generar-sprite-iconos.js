// Script de desarrollo (no se ejecuta en producción). Genera
// stockhogar/static/icons/sprite.svg a partir de los iconos usados en
// stockhogar/static/icons/catalogo-iconos.js.
//
// Tres fuentes posibles por icono (mismo catálogo, todas de trazo/línea, no
// relleno sólido, para que el estilo sea consistente):
//   - "nombre"   -> node_modules/lucide-static/icons/nombre.svg    (comida/bebida)
//   - "h-nombre" -> node_modules/heroicons/24/outline/nombre.svg   (hogar/utilidad)
//   - "c-nombre" -> stockhogar/static/icons/custom/nombre.svg      (diseño propio,
//     para conceptos que no existen en ninguna de las dos librerías)
//
// Ejecutar con: node scripts/generar-sprite-iconos.js
// cada vez que se añada/quite un icono en catalogo-iconos.js.
const fs = require("fs");
const path = require("path");

const RAIZ = path.join(__dirname, "..");
const CATALOGO_PATH = path.join(RAIZ, "stockhogar/static/icons/catalogo-iconos.js");
const ICONOS_LUCIDE_DIR = path.join(RAIZ, "node_modules/lucide-static/icons");
const ICONOS_HEROICONS_DIR = path.join(RAIZ, "node_modules/heroicons/24/outline");
const ICONOS_CUSTOM_DIR = path.join(RAIZ, "stockhogar/static/icons/custom");
const SALIDA_PATH = path.join(RAIZ, "stockhogar/static/icons/sprite.svg");

// Atributos de presentación que Lucide/Heroicons ponen en la etiqueta <svg>
// raíz (fill="none", stroke="currentColor"...) y que los <path> internos
// heredan. Si se pierden al extraer solo el contenido interno, el icono se
// pinta como una mancha sólida en vez del trazo de línea fina pretendido.
const ATRIBUTOS_A_CONSERVAR = ["fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"];

function extraerNombresIconos(contenidoCatalogo) {
  const nombres = new Set();
  const regex = /icono:\s*"([a-z0-9-]+)"/g;
  let match;
  while ((match = regex.exec(contenidoCatalogo)) !== null) {
    nombres.add(match[1]);
  }
  return [...nombres];
}

function rutaFuente(nombre) {
  if (nombre.startsWith("h-")) {
    return path.join(ICONOS_HEROICONS_DIR, `${nombre.slice(2)}.svg`);
  }
  if (nombre.startsWith("c-")) {
    return path.join(ICONOS_CUSTOM_DIR, `${nombre.slice(2)}.svg`);
  }
  return path.join(ICONOS_LUCIDE_DIR, `${nombre}.svg`);
}

function convertirASimbolo(svgOriginal, nombre) {
  const aperturaSvg = svgOriginal.match(/<svg[^>]*>/)[0];
  const atributosHeredables = ATRIBUTOS_A_CONSERVAR.map((attr) => {
    const m = aperturaSvg.match(new RegExp(`${attr}="([^"]*)"`));
    return m ? `${attr}="${m[1]}"` : "";
  })
    .filter(Boolean)
    .join(" ");

  const contenidoInterno = svgOriginal
    .replace(/^[\s\S]*?<svg[^>]*>/, "")
    .replace(/<\/svg>\s*$/, "");
  return `<symbol id="icon-${nombre}" viewBox="0 0 24 24" ${atributosHeredables}>${contenidoInterno}</symbol>`;
}

function main() {
  const catalogo = fs.readFileSync(CATALOGO_PATH, "utf8");
  const nombres = extraerNombresIconos(catalogo);

  const simbolos = [];
  const faltantes = [];
  for (const nombre of nombres) {
    const rutaSvg = rutaFuente(nombre);
    if (!fs.existsSync(rutaSvg)) {
      faltantes.push(nombre);
      continue;
    }
    const svgOriginal = fs.readFileSync(rutaSvg, "utf8");
    simbolos.push(convertirASimbolo(svgOriginal, nombre));
  }

  if (faltantes.length > 0) {
    console.error("Iconos no encontrados:", faltantes.join(", "));
    process.exitCode = 1;
    return;
  }

  const sprite = `<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n${simbolos.join("\n")}\n</svg>\n`;
  fs.writeFileSync(SALIDA_PATH, sprite, "utf8");
  console.log(`Sprite generado con ${simbolos.length} iconos en ${SALIDA_PATH}`);
}

main();
