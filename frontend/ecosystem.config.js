module.exports = {
  apps: [{
    name: 'nuxt-frontend',
    script: 'node_modules/.bin/nuxt',
    args: 'dev --host 0.0.0.0 --port 3001',
    cwd: '/opt/webapp/patrol_/frontend',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'development',
      HOST: '0.0.0.0',
      PORT: 3001
    },
    output: '/var/log/pm2/nuxt-out.log',
    error: '/var/log/pm2/nuxt-error.log',
    log: '/var/log/pm2/nuxt-combined.log',
    time: true,
    interpreter: 'none',
    
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
