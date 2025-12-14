# Gunicorn configuration for Render deployment
# Optimized for free tier cold start issues

import multiprocessing

# Worker configuration
workers = 2  # Free tier'da 2 worker yeterli, daha fazla memory kullanır
worker_class = "sync"  # Sync worker daha stabil
threads = 2  # Her worker için 2 thread

# Timeout configuration
timeout = 120  # Gemini API çağrıları uzun sürebilir
graceful_timeout = 30
keepalive = 5

# Preload app to speed up worker start
preload_app = True

# Binding
bind = "0.0.0.0:10000"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Memory optimization
max_requests = 1000  # Worker'ları periyodik olarak yeniden başlat (memory leak önleme)
max_requests_jitter = 50
