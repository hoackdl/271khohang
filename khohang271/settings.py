# khohang271/settings.py
# settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# ==============================================================#
# BASE DIR
# ==============================================================#
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env
load_dotenv(BASE_DIR / ".env")

# ==============================================================#
# ENVIRONMENT
# ==============================================================#
ENV = os.getenv("ENV", "dev").lower()  # dev / prod

import os
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
print("DEBUG =", DEBUG)
print("DB_NAME =", os.getenv("DB_NAME"))

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise Exception("SECRET_KEY không được tìm thấy trong .env!")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1").split(",")

# ==============================================================#
# DATABASE CONFIG
# ==============================================================#
if ENV == "dev":
    # LOCAL: SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / "khohang271db.sqlite3",
        }
    }
else:
    # PRODUCTION: PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv("DB_NAME"),
            'USER': os.getenv("DB_USER"),
            'PASSWORD': os.getenv("DB_PASSWORD"),
            'HOST': os.getenv("DB_HOST"),
            'PORT': os.getenv("DB_PORT", 5432),
        }
    }

# ==============================================================#
# INSTALLED APPS & MIDDLEWARE (giữ nguyên)
# ==============================================================#
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # App của bạn
    'invoice_reader_app',

    # Format số
    'django.contrib.humanize',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'khohang271.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "invoice_reader_app.context_processors.current_fiscal_year",
            ],
        },
    },
]

WSGI_APPLICATION = 'khohang271.wsgi.application'

# ==============================================================#
# STATIC & MEDIA
# ==============================================================#
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================#
# LOGIN CONFIG
# ==============================================================#
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inventory_summary'
LOGOUT_REDIRECT_URL = 'login'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================#
# TIPS:
# ==============================================================#
# 1. Trên server production:
#    - ENV=prod
#    - DEBUG=False
#    - Cấu hình DB PostgreSQL đúng
# 2. Trên local dev:
#    - ENV=dev
#    - DEBUG=True
#    - Sử dụng SQLitemport osfrom pathlib import Pat
