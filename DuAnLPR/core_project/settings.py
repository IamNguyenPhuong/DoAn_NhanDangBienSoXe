import os
from pathlib import Path
LANGUAGE_CODE = 'vi-vn'  # Đặt mã ngôn ngữ là tiếng Việt

TIME_ZONE = 'Asia/Ho_Chi_Minh' # Đây là múi giờ cho Việt Nam (GMT+7)

USE_I18N = True

USE_L10N = True # Django 4.0 trở lên dùng USE_L10N, nếu bạn dùng Django cũ hơn có thể là USE_TZ

USE_TZ = True # Rất quan trọng: Bật hỗ trợ múi giờ trong Django

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
LOGIN_URL = 'parking_management:login_user' # URL sẽ chuyển hướng đến nếu người dùng chưa đăng nhập và cố truy cập trang yêu cầu đăng nhập
LOGIN_REDIRECT_URL = 'parking_management:user_dashboard' # URL sẽ chuyển hướng đến sau khi đăng nhập thành công
LOGOUT_REDIRECT_URL = 'parking_management:login_user' # URL sẽ chuyển hướng đến sau khi đăng xuất thành công

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-ixsg3j1mv64y1tiq%9xmjtazco#&h%@+=(6-)(-pr7dikf_zfw'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
'django.contrib.humanize',
    'parking_management',
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

ROOT_URLCONF = 'core_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates'),], # Nếu bạn có thư mục templates chung
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media', # <<<--- ĐẢM BẢO CÓ DÒNG NÀY
            ],
        },
    },
]

WSGI_APPLICATION = 'core_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'db_ancu_parking',  # Tên CSDL bạn đã tạo trong phpMyAdmin
        'USER': 'root',             # Username của MySQL (mặc định của XAMPP thường là 'root')
        'PASSWORD': '',             # Password của MySQL (mặc định của XAMPP thường là để trống)
        'HOST': 'localhost',        # Hoặc '127.0.0.1'
        'PORT': '3306',             # Cổng mặc định của MySQL
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES',time_zone='+07:00'",
            'charset': 'utf8mb4',

        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/




# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# Cấu hình cho Media Files (User-uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
