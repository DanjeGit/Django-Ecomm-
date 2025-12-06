"""
Django settings for resource_loop project.
"""
from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# 1. BASE_DIR & ENV
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file for local development
load_dotenv(BASE_DIR / '.env')

# 2. SECURITY
# Try to get the key from Environment (Render), fallback to insecure key ONLY for local dev
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-k4ao826m*h$mhn$0_p66s54vw7t%xlt^2_62erftgx+35ub+xj')

# Detect if running on Render
IS_RENDER = 'RENDER' in os.environ

# Debug: True locally, False on Render
DEBUG = not IS_RENDER

ALLOWED_HOSTS = [
    '.onrender.com',    # Allow Render
    '.ngrok-free.app',  # Allow Ngrok
    '.ngrok-free.dev',
    '127.0.0.1',
    'localhost'
]

# Avoid CSRF issues on Render and Ngrok
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://*.ngrok-free.app',
    'https://*.ngrok-free.dev',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# 3. APPLICATION DEFINITION
INSTALLED_APPS = [
    # Cloudinary Storage must be BEFORE django.contrib.staticfiles
    'cloudinary_storage', 
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    'marketplace',
    # 'mpesa', # Uncomment if you have an mpesa app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Whitenoise enabled
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'resource_loop.urls'

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
                'marketplace.context_processors.cart_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'resource_loop.wsgi.application'


# 4. DATABASE
if IS_RENDER:
    # Production: Using PostgreSQL via Render's URL
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
else:
    # Local: Use SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# 5. PASSWORD VALIDATION
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# 6. INTERNATIONALIZATION
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi' # Updated for M-Pesa
USE_I18N = True
USE_TZ = True


# 7. STATIC & MEDIA FILES (Hybrid Setup with Compatibility)

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'

if IS_RENDER:
    # --- PRODUCTION (Render) ---
    # 1. Modern Configuration (Django 4.2+)
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            # ✅ FIX: Using CompressedStaticFilesStorage (Non-Strict) to prevent crashes
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    
    # 2. Legacy Configuration (For Django 5 compatibility with older libs)
    STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

    # Cloudinary Config
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
        'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
        'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
    }
else:
    # --- LOCAL (Laptop) ---
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    MEDIA_ROOT = BASE_DIR / 'media'
    
    # Legacy Fallbacks for Local
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"


# 8. AUTHENTICATION & REDIRECTS
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'

AUTHENTICATION_BACKENDS = [
    'marketplace.backends.EmailOrPhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# 9. M-PESA SETTINGS
CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
SHORTCODE = os.environ.get('SHORTCODE', '174379')
PASSKEY = os.environ.get('PASSKEY')
CALLBACK_URL = os.environ.get('CALLBACK_URL', '')