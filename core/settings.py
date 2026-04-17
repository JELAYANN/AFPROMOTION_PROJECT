import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
SECRET_KEY = 'django-insecure-i45e((k=xf$!=!l+vjn^ink$)g*=pea=d%x32s9*^o=tukf5_7'
DEBUG = True
ALLOWED_HOSTS = []

# --- APPS ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites', 

    'shop', # App Lokal

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
]

SITE_ID = 2

# --- MIDDLEWARE ---
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

ROOT_URLCONF = 'core.urls'

# --- TEMPLATES ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # Kita paksa Django melihat folder templates di ROOT secara absolut
            os.path.join(BASE_DIR, 'templates'), 
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
# --- DATABASE ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'af_promotion_db',
        'USER': 'root',
        'PASSWORD': 'admin1234',#admin1234
        'HOST': '127.0.0.1',
        'PORT': '3306',#3306 #8889
    }
}
# git push origin main     
# git commit -m "Update Fitur Notif WA"
# git add .      
# --- AUTHENTICATION ---
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Pontianak'
USE_I18N = True
USE_TZ = True

# --- STATIC & MEDIA ---
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# --- DJANGO ALLAUTH CONFIGURATION (THE SECRETS TO SEAMLESS LOGIN) ---

# 1. URL Redirects (Gunakan URL name yang tepat untuk Beranda)
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'  
LOGOUT_REDIRECT_URL = '/accounts/login/'

# 2. Bypass Halaman Perantara (PENTING!)
SOCIALACCOUNT_LOGIN_ON_GET = True   # Klik tombol langsung ke Provider
SOCIALACCOUNT_AUTO_SIGNUP = True    # Buat user otomatis tanpa form tambahan
ACCOUNT_LOGOUT_ON_GET = True        # Logout tanpa konfirmasi halaman putih

# 3. Pengaturan Email & Verifikasi
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_EMAIL_REQUIRED = False
SOCIALACCOUNT_QUERY_EMAIL = True    # Paksa ambil email dari GitHub/Google

# 4. Pengaturan Username & Login
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_USERNAME_REQUIRED = False   # User bisa daftar hanya dengan email
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_REQUIRED = True

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email' # Login menggunakan email
ACCOUNT_EMAIL_VERIFICATION = "none" # Set 'none' agar tidak kirim email verifikasi saat testing
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
# 6. Provider Scope
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'SCOPE': ['user', 'user:email'],
    },
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}
ACCOUNT_LOGIN_TEMPLATE = 'socialaccount/login.html'
ACCOUNT_SIGNUP_TEMPLATE = 'socialaccount/signup.html'

ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email', 'password1*', 'password2*']

ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'allauth.socialaccount.adapter.DefaultSocialAccountAdapter'

# --- EMAIL CONFIGURATION ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True  
EMAIL_USE_SSL = False   
EMAIL_HOST_USER = 'afpromotion9000@gmail.com'
EMAIL_HOST_PASSWORD = 'hhnytwkzvoztdwgw' 
DEFAULT_FROM_EMAIL = 'AF Promotion <afpromotion9000@gmail.com>'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'