// Script de desarrollo (no se ejecuta en producción). Genera los PNG del
// icono de la app (favicon, manifest, apple-touch-icon) a partir de
// stockhogar/static/icons/favicon.svg, para máxima compatibilidad con
// navegadores/plataformas que no soportan iconos SVG en el manifest o
// en apple-touch-icon (iOS Safari, Android antiguos, etc).
//
// Ejecutar con: node scripts/generar-iconos-png.js
// cada vez que cambie el diseño del icono en favicon.svg.
const fs = require("fs");
const path = require("path");
const sharp = require("sharp");

const RAIZ = path.join(__dirname, "..");
const ICONS_DIR = path.join(RAIZ, "stockhogar/static/icons");
const FUENTE_SVG = path.join(ICONS_DIR, "favicon.svg");

const ACCENT = "#B5551A";

// Icono "any": el mismo diseño a distintos tamaños, a sangre (sin margen extra).
const TAMANOS_ANY = [16, 32, 48, 180, 192, 512];

// Icono "maskable": el sistema recorta un círculo/superelipse desde el borde,
// así que el contenido debe vivir en la "safe zone" central (~80% del lienzo).
const TAMANOS_MASKABLE = [192, 512];

function svgMaskable(tamano) {
  const escala = 0.7; // deja margen de seguridad para el recorte del SO
  const offset = ((1 - escala) / 2) * 24;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${tamano}" height="${tamano}" viewBox="0 0 24 24">
<rect width="24" height="24" fill="${ACCENT}"/>
<g transform="translate(${offset} ${offset}) scale(${escala})">
<path d="M2 13 12 3.5 22 13Z" fill="#FFFFFF"/>
<rect x="4" y="10.5" width="16" height="10" rx="3" fill="#FFFFFF"/>
<path d="M16.3 7.6a2.3 2.3 0 1 0 0 4.6 2.9 2.9 0 0 1 0-4.6Z" fill="${ACCENT}"/>
<rect x="10.2" y="15" width="3.6" height="5.5" rx="1.2" fill="${ACCENT}"/>
<path d="M19.2 2.2 19.8 3.7 21.3 4.3 19.8 4.9 19.2 6.4 18.6 4.9 17.1 4.3 18.6 3.7Z" fill="#FFFFFF"/>
</g>
</svg>`;
}

async function main() {
  const svgOriginal = fs.readFileSync(FUENTE_SVG, "utf8");

  for (const tamano of TAMANOS_ANY) {
    const salida = path.join(ICONS_DIR, `icon-${tamano}.png`);
    await sharp(Buffer.from(svgOriginal), { density: 384 })
      .resize(tamano, tamano)
      .png()
      .toFile(salida);
    console.log(`Generado ${salida}`);
  }

  for (const tamano of TAMANOS_MASKABLE) {
    const salida = path.join(ICONS_DIR, `icon-maskable-${tamano}.png`);
    await sharp(Buffer.from(svgMaskable(tamano)), { density: 384 })
      .resize(tamano, tamano)
      .png()
      .toFile(salida);
    console.log(`Generado ${salida}`);
  }

  // Favicon multiresolución para navegadores que no soportan SVG (Safari legacy).
  fs.copyFileSync(path.join(ICONS_DIR, "icon-32.png"), path.join(ICONS_DIR, "favicon-32.png"));
  fs.copyFileSync(path.join(ICONS_DIR, "icon-16.png"), path.join(ICONS_DIR, "favicon-16.png"));
  fs.copyFileSync(path.join(ICONS_DIR, "icon-180.png"), path.join(ICONS_DIR, "apple-touch-icon.png"));
  console.log("Copias de favicon-16/32.png y apple-touch-icon.png listas.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
