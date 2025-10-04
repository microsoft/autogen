import { defineConfig } from 'tsup'

export default defineConfig([
  {
    dts: true,
    entry: ['src/index.ts'],
    format: ['cjs', 'esm'],
    sourcemap: true,
  },
])