import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 本地可设 VITE_API_TARGET 环境变量覆盖后端端口，默认 8001（ALMT 独立端口，与 ALMD 8000/IALMD 8002 并存）
const apiTarget = process.env.VITE_API_TARGET || 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [react()],
  base: '/almt/',
  server: {
    port: 5174,
    proxy: {
      '/almt/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/almt/, ''),
      },
    },
  },
  build: {
    emptyOutDir: false,
  },
})
