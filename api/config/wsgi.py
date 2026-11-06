import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Started here, not in an AppConfig, so management commands and tests never run it.
# The server runs a single worker process, so there is exactly one sweeper.
from reviews import sweeper

sweeper.start()
