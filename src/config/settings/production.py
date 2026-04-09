from .base import *
from django.core.exceptions import ImproperlyConfigured

DEBUG = False
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='',
    cast=lambda value: [host.strip() for host in value.split(',') if host.strip()],
)

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must be configured in production.')
if '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured('Wildcard ALLOWED_HOSTS is not allowed in production.')

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='',
    cast=lambda value: [origin.strip() for origin in value.split(',') if origin.strip()],
)
