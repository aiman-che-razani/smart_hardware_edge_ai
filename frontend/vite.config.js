import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Point the dev proxy at a non-default backend, e.g. `sentinel api --port 8001`:
// VITE_API_PROXY=http://localhost:8001 npm run dev
const apiTarget = process.env.VITE_API_PROXY || process.env.SENTINEL_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': apiTarget,
    },
  },
})
