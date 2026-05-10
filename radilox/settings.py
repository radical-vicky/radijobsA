"""
Django settings for radilox project.
"""

from pathlib import Path
import os
from decouple import config
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Create logs directory if it doesn't exist
logs_dir = BASE_DIR / 'logs'
if not logs_dir.exists():
    logs_dir.mkdir()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-2#j5s79hw!-90=pa&5r&rx&g(jwk51aoncc84dwt%wy1^vbpjk')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,.ngrok.io,.onrender.com').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    
    # AllAuth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
    
    # Third-party apps
    'crispy_forms',
    'crispy_tailwind',
    'django_htmx',
    'widget_tweaks',
    'corsheaders',
    'cloudinary',
    'cloudinary_storage',
    
    # Local apps
    'home',
    'accounts',
    'jobs',
    'application',
    'tasks',
    'payments',
    'wallet',
    'zoom_integration',
    'notifications',
    'public',
    'api',
    'subscriptions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'radilox.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'radilox.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary Configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

cloudinary.config(
    cloud_name=config('CLOUDINARY_CLOUD_NAME', default=''),
    api_key=config('CLOUDINARY_API_KEY', default=''),
    api_secret=config('CLOUDINARY_API_SECRET', default=''),
    secure=True
)

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============ ALLAUTH CONFIGURATION ============
SITE_ID = 1

# Authentication URLs
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'

# Account Settings
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email', 'username*', 'password1*', 'password2*']
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_UNIQUE_EMAIL = True

# Rate limiting
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/300s',
}

# Social account providers
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    },
    'github': {
        'SCOPE': ['user:email'],
    }
}

# ============ EMAIL CONFIGURATION (Gmail - Production) ============
# Use these settings for sending real emails via Gmail
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'entreprenuerridicular@gmail.com'
EMAIL_HOST_PASSWORD = 'fxug ewew mwkt vvsb'  # App password, not regular password
DEFAULT_FROM_EMAIL = 'RadiloxRemoteJobs <entreprenuerridicular@gmail.com>'

# If you want to use console for development (emails appear in terminal), comment the above and uncomment below:
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============ RADILOXREMOTEJOBS CUSTOM SETTINGS ============

# Subscription & Payments
SUBSCRIPTION_PRICE_USD = 19
SUBSCRIPTION_PRICE_KES = 2000
WITHDRAWAL_FEE_PERCENTAGE = 3
MINIMUM_WITHDRAWAL_USD = 20
MAX_WITHDRAWAL_USD = 5000




# Zoom API Configuration
ZOOM_ACCOUNT_ID = 'YBECS6bwQnuVAvErJjRLrg'
ZOOM_CLIENT_ID = 'mE0t2iCsQ6BKDWCisHZcw'
ZOOM_CLIENT_SECRET = 'WMDoifDJr7iijmcMNPXq1ohcokqNQQN0'  # You need to get this from Zoom
ZOOM_MEETING_DURATION_INTERVIEW = 60
ZOOM_MEETING_DURATION_ONBOARDING = 45

# Payment Gateways
BINANCE_API_KEY = config('BINANCE_API_KEY', default='')
BINANCE_API_SECRET = config('BINANCE_API_SECRET', default='')

OKX_API_KEY = config('OKX_API_KEY', default='')
OKX_API_SECRET = config('OKX_API_SECRET', default='')
OKX_PASSPHRASE = config('OKX_PASSPHRASE', default='')

PAYPAL_MODE = 'sandbox' if DEBUG else 'live'
PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET', default='')

# M-Pesa Configuration
MPESA_CONSUMER_KEY = 'Atscmk0CWUCHXl9FGdUVZnOf7Co3XXggR3kXbEcDdnrdRb41'
MPESA_CONSUMER_SECRET = 'TgBdlhu7ZlAFnatiwsqCIvr5WdCbU0athFlK75pUWrMmsas3yuPut5tuRLbFUXAb'
MPESA_SHORTCODE = '174379'
MPESA_SHORTCODE_TYPE = 'paybill'
MPESA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
MPESA_CALLBACK_URL = 'https://cyptconsult.onrender.com/payments/mpesa-callback/'
MPESA_ENVIRONMENT = 'sandbox'
MPESA_INITIATOR_NAME = 'testapi'
MPESA_INITIATOR_PASSWORD = 'Safaricom123!!'

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600
SESSION_COOKIE_SECURE = False if DEBUG else True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF Settings
CSRF_COOKIE_SECURE = False if DEBUG else True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'payments': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# Celery settings for async tasks
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Security Headers for Production
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True