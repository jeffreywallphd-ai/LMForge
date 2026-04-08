"""Base settings for the standalone src-based Django project."""

import os
import sys
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')
DEBUG = config('DEBUG', cast=bool, default=True)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

INSTALLED_APPS = [
    'rest_framework',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'src.studio',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'src.config.urls'
WSGI_APPLICATION = 'src.config.wsgi.application'
ASGI_APPLICATION = 'src.config.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'src', 'studio', 'presentation', 'web', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'src', 'studio', 'presentation', 'web', 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1',
    'http://localhost',
]
CORS_ALLOW_CREDENTIALS = True

DB_NAME = config('DATABASE_NAME', default='')
DB_USER = config('DATABASE_USER', default='')
DB_PASSWORD = config('DATABASE_PASSWORD', default='')
DB_HOST = config('DATABASE_HOST', default='')
DB_PORT = config('DATABASE_PORT', default='3306')

def _looks_placeholder(v: str) -> bool:
    v = (v or '').strip().lower()
    return v in {'', 'password', 'changeme', 'your_db', 'your_user', 'localhost'}

RUNNING_DEV_SERVER = 'runserver' in sys.argv
MISSING_OR_PLACEHOLDER = (
    _looks_placeholder(DB_NAME)
    or _looks_placeholder(DB_USER)
    or _looks_placeholder(DB_HOST)
    or DB_PASSWORD.strip() == ''
)

USE_SQLITE_FALLBACK = DEBUG and (RUNNING_DEV_SERVER or 'migrate' in sys.argv) and MISSING_OR_PLACEHOLDER

if USE_SQLITE_FALLBACK:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
        }
    }
