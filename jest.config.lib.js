// Única config de Jest del proyecto: cubre las funciones puras de lib/*.ts.
// Antes convivía con jest.config.js (+ jest.setup.js), que apuntaba a los
// módulos JS vanilla de stockhogar/static; esa carpeta desapareció en la
// migración a Next y no quedaba ni un .test.js, así que se han borrado. Con
// ellos se fue la dependencia jest-environment-jsdom: aquí el entorno es
// 'node' y los tests que necesitan window/localStorage los simulan a mano
// (ver lib/__tests__/dataCache.test.ts).
const path = require('path')

module.exports = {
  testEnvironment: 'node',
  rootDir: __dirname,
  testMatch: ['<rootDir>/lib/__tests__/**/*.test.ts'],
  transform: {
    '^.+\\.tsx?$': ['babel-jest', { configFile: path.join(__dirname, 'babel.config.lib.js') }],
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testTimeout: 10000,
};
