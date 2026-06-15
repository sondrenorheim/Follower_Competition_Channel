import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { cpSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'

const staticPublicAssets = [
  '404.html',
  'CNAME',
  'favicon.svg',
  'club_avatars',
]

const staticPublicDirectoryCopies = [
  ['api_slim', 'api'],
]

function copyStaticPublicAssets() {
  return {
    name: 'copy-static-public-assets',
    apply: 'build',
    writeBundle(options) {
      const outDir = options.dir || 'dist'
      for (const asset of staticPublicAssets) {
        const source = join('public', asset)
        if (!existsSync(source)) continue
        const target = join(outDir, asset)
        mkdirSync(dirname(target), { recursive: true })
        cpSync(source, target, { recursive: true })
      }
      for (const [sourceName, targetName] of staticPublicDirectoryCopies) {
        const source = join('public', sourceName)
        if (!existsSync(source)) continue
        const target = join(outDir, targetName)
        mkdirSync(dirname(target), { recursive: true })
        cpSync(source, target, { recursive: true })
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react(), copyStaticPublicAssets()],
  base: '/', // Custom domain - no subdirectory needed
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
  },
  publicDir: command === 'serve' ? 'public' : false,
}))
