# 🧪 Testing Guide - Home-Stock

Guía completa para ejecutar y escribir tests en el proyecto.

## 📦 Instalación de Node.js

Antes de ejecutar tests, necesitas Node.js (que incluye npm):

### Windows
1. Descarga desde: https://nodejs.org/
2. Usa la versión LTS (Long Term Support)
3. Instala con opciones por defecto
4. Verifica en PowerShell:
   ```powershell
   node --version
   npm --version
   ```

### macOS
```bash
brew install node
```

### Linux
```bash
sudo apt install nodejs npm
```

---

## 🚀 Ejecutar Tests

### Instalación de dependencias (primera vez)
```bash
npm install
```

### Ejecutar todos los tests
```bash
npm test
```

### Ejecutar tests en modo watch (recarga automática)
```bash
npm run test:watch
```

### Ejecutar con coverage (cobertura)
```bash
npm run test:coverage
```

---

## 📊 Cobertura Actual

| Manager | Archivo | Tests | Estado |
|---------|---------|-------|--------|
| **ProductosManager** | `modules/productos-manager.test.js` | 13 | ✅ |
| **CompraManager** | `modules/compra-manager.test.js` | 10 | ✅ |
| **CategoriasManager** | `modules/categorias-manager.test.js` | 10 | ✅ |
| **EspaciosManager** | `modules/espacios-manager.test.js` | 11 | ✅ |
| **APIClient** | `core/api-client.test.js` | 16 | ✅ |
| **DOMManager** | `core/dom-manager.test.js` | 11 | ✅ |

**Total tests**: 71  
**Coverage objetivo**: >80%

---

## 🏗️ Estructura de Tests

```
stockhogar/
├── static/
│   ├── core/
│   │   ├── api-client.js
│   │   ├── api-client.test.js     ← Tests
│   │   ├── dom-manager.js
│   │   └── dom-manager.test.js    ← Tests
│   └── modules/
│       ├── productos-manager.js
│       ├── productos-manager.test.js  ← Tests
│       ├── compra-manager.js
│       ├── compra-manager.test.js     ← Tests
│       ├── categorias-manager.js
│       ├── categorias-manager.test.js ← Tests
│       ├── espacios-manager.js
│       └── espacios-manager.test.js   ← Tests
├── jest.config.js        ← Configuración Jest
├── jest.setup.js         ← Setup global
├── package.json          ← Dependencies
└── TESTING.md           ← Este archivo
```

---

## 🧬 Anatomía de un Test

### Estructura básica
```javascript
describe('NombreDelManager', () => {
  let manager;
  let mockDOM;
  let mockAPI;

  beforeEach(() => {
    // Setup antes de cada test
    mockAPI = {
      obtenerDatos: jest.fn().mockResolvedValue([])
    };
    mockDOM = {
      get: jest.fn(() => ({ innerHTML: '' }))
    };
    manager = new NombreDelManager(mockAPI, mockDOM);
  });

  test('descripción del test', async () => {
    // Arrange
    const datos = { nombre: 'Test' };

    // Act
    const resultado = await manager.crear(datos);

    // Assert
    expect(resultado).toEqual(expect.objectContaining({ nombre: 'Test' }));
  });
});
```

### Patrones comunes

**Mock de función async**:
```javascript
mockAPI.obtenerDatos = jest.fn().mockResolvedValue([
  { id: 1, nombre: 'Test' }
]);

const datos = await manager.cargar();
expect(datos).toHaveLength(1);
```

**Mock de función síncrona**:
```javascript
mockDOM.get = jest.fn(() => ({ innerHTML: '' }));

manager.render();
expect(mockDOM.get).toHaveBeenCalledWith('lista');
```

**Mock de error**:
```javascript
mockAPI.cargar = jest.fn().mockRejectedValue(new Error('Network error'));

await expect(manager.cargar()).rejects.toThrow('Network error');
```

---

## 📋 Checklist para nuevos tests

Antes de escribir un test:
- [ ] ¿Qué estoy testeando? (método, comportamiento)
- [ ] ¿Cuáles son las inputs y outputs?
- [ ] ¿Qué errores pueden ocurrir?
- [ ] ¿Necesito mocks? (API, DOM, localStorage)
- [ ] ¿Es determinístico? (no depende de tiempo aleatorio)

---

## 🔍 Debugging Tests

### Ver logs de un test específico
```bash
npm test -- --testNamePattern="ProductosManager CRUD"
```

### Debug en VS Code
1. Abre `.vscode/launch.json`
2. Añade configuración:
```json
{
  "type": "node",
  "request": "launch",
  "name": "Jest Debug",
  "program": "${workspaceFolder}/node_modules/.bin/jest",
  "args": ["--runInBand"],
  "console": "integratedTerminal"
}
```
3. Presiona F5 para iniciar debugger

### Modo watch con debugging
```bash
npm test -- --watch --runInBand
```

---

## 🎯 Próximos Tests a Implementar

### UIManager Tests
```javascript
// TODO: tests para toggleTema(), abrirModal(), cerrarModal()
```

### TicketsManager Tests
```javascript
// TODO: tests para procesarArchivo(), confirmarItems()
```

### Integración Tests
```javascript
// TODO: tests de flujos end-to-end
// Ej: crear producto → render() → verificar DOM
```

---

## 📈 Coverage Report

Después de ejecutar `npm run test:coverage`:
- Archivo HTML: `coverage/index.html`
- Líneas cubiertas: verde ✅
- Líneas no cubiertas: rojo ❌
- Cobertura por archivo mostrada en tabla

**Meta**: >80% en líneas, funciones y branches

---

## ⚠️ Errores Comunes

### Error: "Cannot find module 'jest'"
**Solución**: Ejecuta `npm install`

### Error: "window is not defined"
**Solución**: Jest está configurado con `testEnvironment: 'jsdom'`, pero verifica `jest.setup.js`

### Error: "API is not defined"
**Solución**: Mock correctamente en `beforeEach()`:
```javascript
global.window.API = {
  obtenerProductos: jest.fn().mockResolvedValue([])
};
```

### Tests lentos
**Solución**: 
- Aumenta timeout: `jest.setTimeout(15000)`
- Verifica que no hay console.log() sin capturar
- Evita setTimeout innecesarios

---

## 📚 Referencias

- Jest docs: https://jestjs.io/
- Testing Library: https://testing-library.com/
- Mock functions: https://jestjs.io/docs/mock-functions
- Async testing: https://jestjs.io/docs/asynchronous

---

**Última actualización**: 2026-07-08  
**Versión**: 1.0  
**Estado**: ✅ Activo (necesita Node.js para ejecutar)
