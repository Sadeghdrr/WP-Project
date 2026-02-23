import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  // Read .env from the repo root (WP-Project/) so both Django and Vite share
  // the same WP-Project/.env file.
  // Variables must be prefixed with VITE_ to be exposed to client-side code.
  // Usage: import.meta.env.VITE_API_BASE_URL
  envDir: path.resolve(__dirname, '..'),
})
