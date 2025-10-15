// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: [
    '@nuxtjs/tailwindcss',
  ],
  ssr: false,
  css: [
    '~/assets/css/main.css',
    'highlight.js/styles/atom-one-dark.css',
  ],
  runtimeConfig: {
    // 私有配置（仅在服务端可用）
    public: {},
  },
  app: {
    head: {
      title: 'LangGraph 可视化工具',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'LangGraph架构可视化和交互工具' },
      ],
    },
  },
})
