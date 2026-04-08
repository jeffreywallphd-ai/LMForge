import os

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.config.settings.test")
django.setup()
