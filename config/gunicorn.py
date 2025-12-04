from os import environ

bind = environ.get("GUNICORN_BIND", "0.0.0.0:8000")

workers = int(environ.get("GUNICORN_WORKERS", 2))
threads = int(environ.get("GUNICORN_THREADS", 1))

reload = bool(environ.get("GUNICORN_RELOAD", 0))

# https://docs.gunicorn.org/en/latest/faq.html#blocking-os-fchmod
# place tmp dir in tmpfs location - instead of overlay - to avoid delays
worker_tmp_dir = "/dev/shm"
