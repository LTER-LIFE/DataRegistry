import logging

from application import create_app

logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.WARNING)

application = create_app()

if __name__ == '__main__':
    application.run(debug=True)

