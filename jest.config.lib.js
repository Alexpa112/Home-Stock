// Config de Jest para las funciones puras de lib/*.ts (Next.js/TSX), separada
// de jest.config.js (que cubre los módulos JS vanilla legacy de
// stockhogar/static). Se ejecuta con `npm run test:lib`; `npm test` corre
// ambos proyectos.
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
