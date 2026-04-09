from .base import *

DEBUG = True
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-only-key')
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,[::1]',
    cast=lambda value: [host.strip() for host in value.split(',') if host.strip()],
)
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1,http://localhost',
    cast=lambda value: [origin.strip() for origin in value.split(',') if origin.strip()],
)
