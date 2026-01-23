"""
Gunicorn configuration for production deployment.
"""
import os

# Bind to PORT environment variable (Render sets this)
bind = f"0.0.0.0:{os.getenv('PORT', '5001')}"

# Workers
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
worker_class = "sync"
threads = int(os.getenv("GUNICORN_THREADS", "4"))

# Timeout (increase for large file processing and AI summarization)
timeout = 300  # 5 minutes

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# Restart workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50
