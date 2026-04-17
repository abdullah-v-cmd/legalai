module.exports = {
  apps: [
    {
      name: 'legalai',
      script: 'python',
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info',
      cwd: '/home/user/legalai',
      env: {
        PYTHONPATH: '/home/user/legalai',
        PORT: 8000
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork',
      error_file: '/home/user/legalai/logs/error.log',
      out_file: '/home/user/legalai/logs/out.log',
    }
  ]
}
