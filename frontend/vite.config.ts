import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // Lets us write `@/components/...` instead of long `../../` paths.
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    fs: {
      // Phase 1 only: the frontend reads the seed guide JSON files from
      // ../seed_data. Phase 2 replaces this with API calls to the backend.
      allow: ['..'],
    },
  },
})
