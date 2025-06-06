import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  root: '.',
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html')
      }
    },
    outDir: 'static/dist',
    assetsDir: 'assets',
    sourcemap: false
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/submit': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/status': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/tasks': {
        target: 'http://localhost:5001',
        changeOrigin: true
      }
    }
  }
})
