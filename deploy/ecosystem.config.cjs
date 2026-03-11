module.exports = {
  apps: [
    {
      name: 'clawsec-api',
      cwd: '/srv/clawsec/backend',
      script: 'dist/index.js',
      instances: 1,
      exec_mode: 'fork',
      env: {
        NODE_ENV: 'production',
        PORT: 3005,
        FRONTEND_URLS: 'https://your-domain.com',
      },
    },
  ],
};
