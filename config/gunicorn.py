from os import environ

bind = f"{environ.get("GUNICORN_HOST", "0.0.0.0")}:{environ.get("PORT", "8000")}"

workers = int(environ.get("GUNICORN_WORKERS", 2))
threads = int(environ.get("GUNICORN_THREADS", 1))

reload = bool(environ.get("GUNICORN_RELOAD", 0))

# https://docs.gunicorn.org/en/latest/faq.html#blocking-os-fchmod
# place tmp dir in tmpfs location - instead of overlay - to avoid delays
worker_tmp_dir = "/dev/shm"
