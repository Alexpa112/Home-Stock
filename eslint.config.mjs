// Configuración de ESLint (formato "flat config", el único que admite ESLint 9).
//
// Hasta ahora el proyecto no tenía linter de frontend: `npm run lint` invocaba
// `next lint`, que Next 16 eliminó, así que el script fallaba y nadie lo
// notaba. Se parte del preset de Next (reglas de React, hooks y del propio
// framework) y se dejan como aviso —no como error— las reglas que hoy no se
// cumplen en todo el código, para que el linter sea utilizable desde el primer
// día en vez de escupir cientos de errores y acabar ignorado.
import coreWebVitals from 'eslint-config-next/core-web-vitals'
import typescriptConfig from 'eslint-config-next/typescript'

export default [
  {
    ignores: [
      'node_modules/**',
      '.next/**',
      'out/**',
      'build/**',
      'coverage/**',
      'stockhogar/**',
      'scripts/**',
      // Copia generada de translations.json (ver
      // scripts/generar_traducciones_base.py): no se edita a mano.
      'lib/traduccionesBase.ts',
    ],
  },
  ...(Array.isArray(coreWebVitals) ? coreWebVitals : [coreWebVitals]),
  ...(Array.isArray(typescriptConfig) ? typescriptConfig : [typescriptConfig]),
  {
    // Ficheros de configuración de Node (CommonJS): require() es lo correcto
    // aquí, no un descuido.
    files: ['*.js', '*.cjs', 'jest.config*.js', 'babel.config*.js', 'postcss.config.js'],
    rules: { '@typescript-eslint/no-require-imports': 'off' },
  },
  {
    rules: {
      // `any` está muy extendido en las respuestas de la API (lib/api.ts
      // devuelve any a propósito). Queda como aviso para no bloquear, pero
      // visible para ir tipándolo.
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      // El proyecto usa <img> en sitios donde next/image no aporta (iconos
      // embebidos, previsualización de recibos ya redimensionada).
      '@next/next/no-img-element': 'warn',
      'react-hooks/exhaustive-deps': 'warn',
      // Reglas nuevas del compilador de React (Next 16). Señalan patrones
      // mejorables —setState dentro de un efecto, escribir un ref durante el
      // render— repartidos por casi todos los hooks del proyecto. Corregirlos
      // es un refactor en sí mismo, así que se dejan como aviso: el linter
      // arranca en verde y los avisos quedan a la vista para ir saldándolos.
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/refs': 'warn',
      'react-hooks/purity': 'warn',
      'react-hooks/immutability': 'warn',
      'react-hooks/preserve-manual-memoization': 'warn',
      'react-hooks/static-components': 'warn',
      'react-hooks/incompatible-library': 'warn',
    },
  },
]
