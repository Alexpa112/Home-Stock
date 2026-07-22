module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testMatch: ['**/__tests__/**/*.js', '**/?(*.)+(spec|test).js'],
  testPathIgnorePatterns: ['/node_modules/', '/.claude/worktrees/'],
  collectCoverageFrom: [
    'stockhogar/static/modules/**/*.js',
    'stockhogar/static/core/**/*.js',
    '!**/*.test.js',
    '!**/node_modules/**'
  ],
  coveragePathIgnorePatterns: [
    'node_modules',
    'deprecated',
    '.claude/worktrees'
  ],
  coverageReporters: ['text', 'lcov', 'html'],
  // Umbral realista a partir de la cobertura real actual (ver npm run
  // test:coverage): api-client.js, dom-manager.js, form-builder.js y
  // ui-components.js están bien cubiertos; drawer-listas.js (1300+ líneas)
  // solo cubre lo más crítico. Subir estos números a medida que se amplíe
  // la cobertura, no bajarlos para que pase un cambio puntual.
  coverageThreshold: {
    global: {
      branches: 50,
      functions: 50,
      lines: 65,
      statements: 60
    }
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/stockhogar/static/$1'
  },
  testTimeout: 10000,
  verbose: true
};
