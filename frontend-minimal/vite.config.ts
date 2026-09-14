import { defineConfig } from 'vite';

// 构建产物由后端挂载到 /m（见 server.py），base 用相对路径以适配任意挂载点
export default defineConfig({
  base: './',
  server: {
    port: 5173,
    proxy: {
      '/client-ws': {
        target: 'http://localhost:12393',
        ws: true,
      },
      '/live2d-models': 'http://localhost:12393',
      '/avatars': 'http://localhost:12393',
      '/libs': 'http://localhost:12393',
    },
  },
  build: {
    target: 'es2020',
  },
});
