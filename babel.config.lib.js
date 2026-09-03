// Config de Babel exclusiva para los tests de lib/*.ts bajo Jest (ver
// jest.config.lib.js). No se usa en build (Next.js compila con SWC);
// solo permite a Jest transformar TypeScript en __tests__lib__/*.test.ts.
module.exports = {
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' } }],
    '@babel/preset-typescript',
  ],
}
