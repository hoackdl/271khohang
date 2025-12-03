import os
from dotenv import load_dotenv

load_dotenv(r"E:\My Drive\Python Web\XML\271khohang\.env")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # vì DATABASE_URL là postgres
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT"),
    }
}


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