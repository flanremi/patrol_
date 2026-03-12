module.exports = {
  apps: [{
    name: 'nuxt-frontend',
    // 使用生产构建后的输出
    script: './.output/server/index.mjs',
    cwd: '/opt/webapp/patrol_/frontend',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      HOST: '0.0.0.0',
      PORT: 3001,
      NUXT_PUBLIC_API_BASE_URL: 'http://123.151.89.76:8001'
    },
    output: '/var/log/pm2/nuxt-out.log',
    error: '/var/log/pm2/nuxt-error.log',
    log: '/var/log/pm2/nuxt-combined.log',
    time: true,
    
    // 性能监控
    exec_mode: 'fork',
    merge_logs: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    
    // 启动相关
    min_uptime: '10s',
    max_restarts: 10,
    restart_delay: 5000
  }]
};
