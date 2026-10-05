module.exports = {
  apps: [
    {
      name: 'AI-RECRUIT-BE',
      script: 'pnpm prod',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
    },
  ],
};
