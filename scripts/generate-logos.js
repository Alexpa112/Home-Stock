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

    console.log('\n✅ All logos generated successfully!');
  } catch (err) {
    console.error('❌ Error generating logos:', err);
    process.exit(1);
  }
}

generateLogos();
