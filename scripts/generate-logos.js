const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const publicDir = path.join(__dirname, '../public');

async function generateLogos() {
  try {
    // Read SVG
    const svgBuffer = fs.readFileSync(path.join(publicDir, 'icon.svg'));

    const sizes = [
      { name: 'icon.png', size: 256 },
      { name: 'apple-icon.png', size: 192 },
      { name: 'apple-touch-icon.png', size: 180 },
      { name: 'favicon-32x32.png', size: 32 },
      { name: 'favicon-16x16.png', size: 16 },
      { name: 'icon-192x192.png', size: 192 },
      { name: 'icon-512x512.png', size: 512 },
    ];

    // Generate all sizes
    for (const { name, size } of sizes) {
      await sharp(svgBuffer)
        .resize(size, size, { fit: 'contain', background: { r: 240, g: 244, b: 248, alpha: 1 } })
        .png()
        .toFile(path.join(publicDir, name));
      console.log(`✓ Generated ${name} (${size}x${size})`);
    }

    // Generate maskable versions (same as regular but indicate as maskable)
    await sharp(svgBuffer)
      .resize(192, 192, { fit: 'contain', background: { r: 240, g: 244, b: 248, alpha: 1 } })
      .png()
      .toFile(path.join(publicDir, 'icon-maskable-192x192.png'));
    console.log('✓ Generated icon-maskable-192x192.png');

    await sharp(svgBuffer)
      .resize(512, 512, { fit: 'contain', background: { r: 240, g: 244, b: 248, alpha: 1 } })
      .png()
      .toFile(path.join(publicDir, 'icon-maskable-512x512.png'));
    console.log('✓ Generated icon-maskable-512x512.png');

    // favicon.ico: navegadores lo piden directamente (p.ej. al añadir a
    // pantalla de inicio) sin mirar los <link rel="icon">. Formato ICO
    // moderno (Vista+): PNG crudo embebido en el contenedor ICO, sin
    // dependencias externas de conversión.
    const pngFor32 = await sharp(svgBuffer)
      .resize(32, 32, { fit: 'contain', background: { r: 240, g: 244, b: 248, alpha: 1 } })
      .png()
      .toBuffer();
    const icoHeader = Buffer.alloc(6);
    icoHeader.writeUInt16LE(0, 0); // reserved
    icoHeader.writeUInt16LE(1, 2); // type: icon
    icoHeader.writeUInt16LE(1, 4); // image count
    const icoEntry = Buffer.alloc(16);
    icoEntry.writeUInt8(32, 0); // width
    icoEntry.writeUInt8(32, 1); // height
    icoEntry.writeUInt8(0, 2); // color count
    icoEntry.writeUInt8(0, 3); // reserved
    icoEntry.writeUInt16LE(1, 4); // planes
    icoEntry.writeUInt16LE(32, 6); // bit count
    icoEntry.writeUInt32LE(pngFor32.length, 8); // bytes in resource
    icoEntry.writeUInt32LE(22, 12); // offset (6 header + 16 entry)
    fs.writeFileSync(path.join(publicDir, 'favicon.ico'), Buffer.concat([icoHeader, icoEntry, pngFor32]));
    console.log('✓ Generated favicon.ico (32x32)');

    console.log('\n✅ All logos generated successfully!');
  } catch (err) {
    console.error('❌ Error generating logos:', err);
    process.exit(1);
  }
}

generateLogos();
