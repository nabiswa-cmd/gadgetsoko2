from pathlib import Path
from dotenv import load_dotenv
import os
from decimal import Decimal

# Define BASE_DIR first, then load .env
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, ".env"))

# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-xmv2^pwsqiljxgn^$9fc3l&jy0)_9+f!ppalvsa_cwmyo3$-4f')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    '.vercel.app',
    '.onrender.com',
    'localhost',
    '127.0.0.1',
    '187.127.164.196',
    'gadgetsoko.com',
    'www.gadgetsoko.com'
]

# DISABLE STRICT SSL (Allows site to run on both HTTP and HTTPS)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Helps Django recognize HTTPS behind a proxy (like Vercel/Nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    'https://gadgetsoko.vercel.app',
    'https://gadgetsoko.com',
    'https://www.gadgetsoko.com',
    'https://127.0.0.1:8000',
    'https://187.127.164.196',
    'http://187.127.164.196',
    'https://accounts.google.com',
]

CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False

# ---------------------------------------------------------------------------
# APPLICATION
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'app',
    'django.contrib.sitemaps',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'proj.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'app' / 'templates1',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'app.context_processors.cart_count',
                'app.context_processors.active_orders',
                'app.context_processors.google_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'proj.wsgi.application'
SITE_ID = 1

# ---------------------------------------------------------------------------
# DATABASE (PostgreSQL)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {   
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'gadgetsoko_db',
        'USER': 'admin',
        'PASSWORD': 'admin@123',
        'HOST': '187.127.164.196',
        'PORT': '5432',
    }
}

# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

LOGIN_REDIRECT_URL = '/index/'
LOGIN_URL = 'userlog'
LOGOUT_REDIRECT_URL = 'index'

# ---------------------------------------------------------------------------
# INTERNATIONALISATION
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# STATIC & MEDIA FILES
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# M-PESA & API KEYS
# ---------------------------------------------------------------------------
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_ENV = os.getenv('MPESA_ENV', 'sandbox')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL')
SITE_DOMAIN = os.getenv('SITE_DOMAIN', 'https://gadgetsoko.com')

GEMINI_API_KEY = "AIzaSyBvuzWyutF1NItMRXNx7F6B7ExF_V3ReS8"
GOOGLE_CLIENT_ID = os.getenv("CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# ---------------------------------------------------------------------------
# GOOGLE OAUTH
# ---------------------------------------------------------------------------
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True
LOGIN_REDIRECT_URL = '/index/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/index/'
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
            'prompt': 'select_account',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}

# ---------------------------------------------------------------------------
# EMAIL
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'Gadget Soko <sammytings2@gmail.com>'

# ---------------------------------------------------------------------------
# LOGGING (SAFE FOR UBUNTU & WINDOWS)
# ---------------------------------------------------------------------------
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
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django.log'),
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}