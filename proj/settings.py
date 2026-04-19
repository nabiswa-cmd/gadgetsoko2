from pathlib import Path
from dotenv import load_dotenv
import os

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
    '187.124.210.223',
    'gadgetsoko.com',
    'www.gadgetsoko.com'
]

#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    'https://gadgetsoko.vercel.app','https://gadgetsoko.com','https://gadgetsoko.com','https://www.gadgetsoko.com','https://127.0.0.1:8000/'
]

# Production security settings (active when DEBUG=False)
# --- This line must have ZERO spaces at the start ---
# settings.py

# Only force HTTPS if we are NOT in debug mode (i.e., in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    # Ensure these are False locally
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# ---------------------------------------------------------------------------
# APPLICATION
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    
    # 2. Staticfiles only appears ONCE
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
            ],
        },
    },
]


WSGI_APPLICATION = 'proj.wsgi.application'
SITE_ID = 1

# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

#DATABASES = {
 #    'default': {
   #      'ENGINE': 'django.db.backends.sqlite3',
  #
 #@        'NAME': BASE_DIR / 'db.sqlite3',
   #  }
#}
DATABASES = {
    'default':{   
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'gadgetsoko_db',
        'USER': 'admin',
        'PASSWORD': 'admin@123',
        'HOST': '187.124.210.223',
        'PORT': '5432',
    }
    }

# To switch to PostgreSQL in production, set DATABASE_URL in .env and uncomment:
# import dj_database_url
# DATABASES = {'default': dj_database_url.config(default=os.getenv('DATABASE_URL'), conn_max_age=600)}

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
# M-PESA
# ---------------------------------------------------------------------------

MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_ENV = os.getenv('MPESA_ENV', 'sandbox')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL')
SITE_DOMAIN = os.getenv('SITE_DOMAIN', 'https://gadgetsoko.com')

# ---------------------------------------------------------------------------
# GOOGLE OAUTH
# ---------------------------------------------------------------------------

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
# Force the login to happen immediately on the GET/POST request
SOCIALACCOUNT_LOGIN_ON_GET = True


# Ensure users go straight to the account picker
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'AUTH_PARAMS': {
            'access_type': 'online',
            'prompt': 'select_account',  # This forces the "Choose an Account" screen
        }
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



SOCIALACCOUNT_LOGIN_ON_GET = True