import os
import shutil

import dj_database_url
import environ
import saml2
import saml2.saml

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Set up .env
ENV_FILE = os.path.join(BASE_DIR, '.env')
if os.path.exists(ENV_FILE):
    environ.Env.read_env(ENV_FILE)
env = environ.Env(
    DEBUG=(bool, False),
)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG', default=False)
ENV_NAME = env('ENV_NAME', default='test')  # 'test', 'staging' or 'prod' (maches config/saml/x/)

ALLOWED_HOSTS = env('ALLOWED_HOSTS', default='localhost').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djangosaml2',
    'oauth2_provider',
    'rest_framework',

    'sso.user',
    'sso.samlauth'
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'sso', 'templates'),
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

WSGI_APPLICATION = 'config.wsgi.application'


# Database

DATABASES = {
    'default': dj_database_url.config()
}


# Password validation
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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Auth / SAML
AUTH_USER_MODEL = 'user.user'
LOGIN_URL = 'saml2_login'
LOGOUT_REDIRECT_URL = '/saml2/logged-out/'
LOGIN_REDIRECT_URL = '/saml2/logged-in/'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SAML_USER_MODEL = 'user.user'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'djangosaml2.backends.Saml2Backend',
)

SAML_DJANGO_USER_MAIN_ATTRIBUTE = 'email'

SAML_CONFIG_DIR = os.path.join(
    BASE_DIR,
    'config',
    'saml',
    ENV_NAME
)

SAML_PRIVATE_KEY_PATH = os.path.join(SAML_CONFIG_DIR, 'sp.private.key')
SAML_PUBLIC_CERT_PATH = os.path.join(SAML_CONFIG_DIR, 'sp.public.crt')

if env('SAML_PRIVATE_KEY', default=None) and env('SAML_PUBLIC_CERT', default=None):
    # if the key/crt are passed in as env vars => save it to a file
    with open(SAML_PRIVATE_KEY_PATH, 'w') as f:
        f.write(env('SAML_PRIVATE_KEY'))

    with open(SAML_PUBLIC_CERT_PATH, 'w') as f:
        f.write(env('SAML_PUBLIC_CERT'))

SAML_PRIVATE_KEY_PATH = os.path.join(SAML_CONFIG_DIR, 'sp.private.key')
SAML_PUBLIC_CERT_PATH = os.path.join(SAML_CONFIG_DIR, 'sp.public.crt')

# domain the metadata will refer to
SAML_REDIRECT_RETURN_HOST = env('SAML_REDIRECT_RETURN_HOST')
SAML_ACS_URL = SAML_REDIRECT_RETURN_HOST + '/saml2/acs/'

SAML_CONFIG = {
    # full path to the xmlsec1 binary, latter is where it ends up in Heroku
    # on ubuntu install with `apt-get install xmlsec`
    # to get this into Heroku, add the following buildpack on settings page:
    # https://github.com/uktrade/heroku-buildpack-xmlsec
    'xmlsec_binary': shutil.which('xmlsec1'),

    # note not a real url, just a global identifier per SAML recommendations
    'entityid': 'https://sso.staff.service.trade.gov.uk/sp',

    # directory with attribute mapping
    'attribute_map_dir': os.path.join(SAML_CONFIG_DIR, 'attribute_maps'),

    'service': {
        'sp': {
            'allow_unsolicited': False,
            'authn_requests_signed': True,
            'want_assertions_signed': True,
            'name': 'DIT SP',
            'endpoints': {
                'assertion_consumer_service': [
                    (SAML_ACS_URL, saml2.BINDING_HTTP_POST),
                ],
                'single_logout_service': [
                    (SAML_REDIRECT_RETURN_HOST + '/saml2/ls/post/', saml2.BINDING_HTTP_POST),
                ]
            },
            # this is the name id format Core responds with
            'name_id_format': saml2.saml.NAMEID_FORMAT_UNSPECIFIED1,
        },
    },

    'valid_for': 1,  # hours the metadata is valid

    # Created with: `openssl req -new -x509 -days 3652 -nodes -sha256 -out sp.crt -keyout saml.key`
    'key_file': SAML_PRIVATE_KEY_PATH,  # private part, loaded via env var (see above)
    'cert_file': SAML_PUBLIC_CERT_PATH,  # public part

    'encryption_keypairs': [{
        'key_file': SAML_PRIVATE_KEY_PATH,  # private part
        'cert_file': SAML_PUBLIC_CERT_PATH  # public part
    }],

    # remote metadata
    'metadata': {
        'local': [
            os.path.join(SAML_CONFIG_DIR, 'idp_metadata.xml')
        ],
    },
}

SAML_ATTRIBUTE_MAPPING = {
    'email': ('email', ),
}


# DRF
REST_FRAMEWORK = {
    'UNAUTHENTICATED_USER': None,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication'
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
}
