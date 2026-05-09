import os
from pathlib import Path
from decouple import config  # type: ignore
# =========================================================
# BASE DIRECTORY
# =========================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================
# SECURITY
# =========================================================
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    ".ngrok-free.dev",
]

# =========================================================
# APPLICATIONS
# =========================================================
INSTALLED_APPS = [
    # DJANGO DEFAULT
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',

    # LOCAL APPS
    'shop.apps.ShopConfig',

    # DJANGO ALLAUTH
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # PROVIDERS
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
]

SITE_ID = 2

# =========================================================
# MIDDLEWARE
# =========================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# =========================================================
# URLS
# =========================================================
ROOT_URLCONF = 'core.urls'

# =========================================================
# TEMPLATES
# =========================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# =========================================================
# DATABASE
# =========================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
    }
}

# =========================================================
# AUTHENTICATION
# =========================================================
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# =========================================================
# ALLAUTH CONFIGURATION
# =========================================================

# LOGIN / LOGOUT
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# LOGIN METHOD
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = [
    'email*',
    'password1*',
    'password2*',
]

ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGOUT_ON_GET = True

# SOCIAL LOGIN
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_QUERY_EMAIL = True

# PROVIDERS
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'SCOPE': [
            'user',
            'user:email'
        ],
    },

    'google': {
        'SCOPE': [
            'profile',
            'email'
        ],
        'AUTH_PARAMS': {
            'access_type': 'online'
        },
    }
}

# OPTIONAL CUSTOM TEMPLATES
ACCOUNT_LOGIN_TEMPLATE = 'socialaccount/login.html'
ACCOUNT_SIGNUP_TEMPLATE = 'socialaccount/signup.html'

# ADAPTERS
ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'allauth.socialaccount.adapter.DefaultSocialAccountAdapter'

# =========================================================
# INTERNATIONALIZATION
# =========================================================
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Pontianak'
USE_I18N = True
USE_TZ = True

# =========================================================
# STATIC FILES
# =========================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# =========================================================
# MEDIA FILES
# =========================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =========================================================
# DEFAULT PRIMARY KEY
# =========================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =========================================================
# EMAIL CONFIGURATION
# =========================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = 'AF Promotion <afpromotion9000@gmail.com>'

# =========================================================
# MIDTRANS CONFIGURATION
# =========================================================
MIDTRANS_CLIENT_KEY = config("MIDTRANS_CLIENT_KEY")
MIDTRANS_SERVER_KEY = config("MIDTRANS_SERVER_KEY")
MIDTRANS_IS_PRODUCTION = config(
    "MIDTRANS_IS_PRODUCTION",
    cast=bool
)

# =========================================================
# SECURITY (BASIC PRODUCTION READY)
# =========================================================
CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.app",
    "https://*.ngrok-free.dev",
]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'
FONNTE_TOKEN = config("FONNTE_TOKEN")
RAJAONGKIR_API_KEY = config("RAJAONGKIR_API_KEY")
ORIGIN_SUBDISTRICT_ID = int(
    config('ORIGIN_SUBDISTRICT_ID', default=0)
)
DEFAULT_COURIER = config(
    "DEFAULT_COURIER",
    default="JNE"
)
