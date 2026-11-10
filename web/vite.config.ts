import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: Number(process.env.MP_WEB_PORT ?? 5173), strictPort: true, proxy: { '/api': { target: `http://127.0.0.1:${process.env.MP_API_PORT ?? 8000}`, headers: { 'X-MP-Token': process.env.MP_ADMIN_TOKEN ?? '' } } } },
})
