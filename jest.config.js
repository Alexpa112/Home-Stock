module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testMatch: ['**/__tests__/**/*.js', '**/?(*.)+(spec|test).js'],
  collectCoverageFrom: [
    'stockhogar/static/modules/**/*.js',
    'stockhogar/static/core/**/*.js',
    '!**/*.test.js',
    '!**/node_modules/**'
  ],
  coveragePathIgnorePatterns: [
    'node_modules',
    'deprecated'
  ],
  coverageReporters: ['text', 'lcov', 'html'],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/stockhogar/static/$1'
  },
  testTimeout: 10000,
  verbose: true
};
