export default defineNuxtConfig({
  compatibilityDate: '2026-10-17',
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],
  typescript: { strict: true, typeCheck: true },
  runtimeConfig: {
    public: { apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000/api/v1' }
  },
  app: { head: { title: 'MülkAnaliz | Gayrimenkul Yönetimi', meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }, { name: 'theme-color', content: '#f5f7fb' }] } }
})
