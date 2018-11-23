import base64
import os
import shutil
import sys

import dj_database_url
import environ
import saml2.saml

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Set up .env
ENV_FILE = os.path.join(BASE_DIR, '.env')
if os.path.exists(ENV_FILE):
    environ.Env.read_env(ENV_FILE)
env = environ.Env(
    DEBUG=(bool, False),
    RESTRICT_ADMIN=(bool, False),
    RESTRICT_ADMIN_BY_IPS=(str,'127.0.0.1'),
    XMLSEC1=(str, shutil.which('xmlsec1'))
)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG', default=False)
ENV_NAME = env('ENV_NAME', default='test')  # 'test', 'staging' or 'prod' (maches config/saml/x/)

ALLOWED_HOSTS = env('ALLOWED_HOSTS', default='localhost').split(',')

# Application definition

INSTALLED_APPS = [
    'admin_tools',
    'admin_tools.theming',
    'admin_tools.menu',
    'admin_tools.dashboard',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djangosaml2',
    'govuk_template',
    'oauth2_provider',
    'rest_framework',
    'axes',
    'raven.contrib.django.raven_compat',

    'sso.core',
    'sso.user',
    'sso.samlauth',
    'sso.localauth',
    'sso.oauth2',
    'sso.emailauth',
]

MIDDLEWARE = [
    'sso.user.middleware.UpdatedLastAccessedMiddleware',
    'sso.healthcheck.middleware.HealthCheckMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'sso.core.middleware.NeverCacheMiddleware',
    'admin_ip_restrictor.middleware.AdminIPRestrictorMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'sso', 'templates'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'sso.core.context_processors.template_settings',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'admin_tools.template_loaders.Loader',
            ]
        }
    }
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

SAML_USER_MODEL = 'user.user'

# Allows us to use the NameID field for some IdPs
SAML_IDPS_USE_NAME_ID_AS_USERNAME = [
    'http://adfsmobile.azurecore.com/adfs/services/trust',
    'https://adfs.mobile.ukti.gov.uk/adfs/services/trust'
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'sso.samlauth.backends.MultiEmailSaml2Backend',
)

SAML_DJANGO_USER_MAIN_ATTRIBUTE = 'email'
SAML_DJANGO_USER_MAIN_ATTRIBUTE_LOOKUP = ''

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
    with open(SAML_PRIVATE_KEY_PATH, 'wb') as f:
        f.write(base64.b64decode(env('SAML_PRIVATE_KEY')))

    with open(SAML_PUBLIC_CERT_PATH, 'wb') as f:
        f.write(base64.b64decode(env('SAML_PUBLIC_CERT')))

# domain the metadata will refer to
SAML_REDIRECT_RETURN_HOST = env('SAML_REDIRECT_RETURN_HOST')
SAML_ACS_URL = SAML_REDIRECT_RETURN_HOST + '/saml2/acs/'
XMLSEC1 = env('XMLSEC1')

SAML_CONFIG = {
    # full path to the xmlsec1 binary, latter is where it ends up in Heroku
    # on ubuntu install with `apt-get install xmlsec`
    # to get this into Heroku, add the following buildpack on settings page:
    # https://github.com/uktrade/heroku-buildpack-xmlsec
    'xmlsec_binary': XMLSEC1,

    # note not a real url, just a global identifier per SAML recommendations
    'entityid': 'https://sso.staff.service.trade.gov.uk/sp',

    # directory with attribute mapping
    'attribute_map_dir': os.path.join(SAML_CONFIG_DIR, 'attribute_maps'),

    'service': {
        'sp': {
            'allow_unsolicited': False,
            'authn_requests_signed': True,
            'want_assertions_signed': True,
            'want_response_signed': False,
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
            'name_id_format': saml2.saml.NAMEID_FORMAT_UNSPECIFIED,
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


if ENV_NAME == 'staging':
    SAML_CONFIG['metadata']['local'] = [
        os.path.join(SAML_CONFIG_DIR, 'idp_metadata_okta.xml'),
        os.path.join(SAML_CONFIG_DIR, 'idp_metadata_ukef.xml'),
        os.path.join(SAML_CONFIG_DIR, 'idp_metadata_google.xml'),
        os.path.join(SAML_CONFIG_DIR, 'idp_metadata.xml')
    ]

    SAML_CONFIG['entityid'] = 'https://sso.uat.staff.service.trade.gov.uk/sp'

elif ENV_NAME == 'prod':
    SAML_CONFIG['metadata']['local'] = [
        os.path.join(SAML_CONFIG_DIR, 'idp_metadata_cirrus.xml'),
        os.path.join(SAML_CONFIG_DIR, 'idp_metadata_ukef.xml'),
        os.path.join(SAML_CONFIG_DIR, 'idp_metadata_google.xml'),
        os.path.join(SAML_CONFIG_DIR, 'idp_metadata.xml')
    ]


SAML_ATTRIBUTE_MAPPING = {
    'email': ('email',),
    'first_name': ('first_name',),
    'last_name': ('last_name',),
}


REST_FRAMEWORK = {
    'UNAUTHENTICATED_USER': None,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication'
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ]
}

# Include the local auth page?
LOCAL_AUTH_PAGE = env('LOCAL_AUTH_PAGE', default=False)

OAUTH2_PROVIDER = {
    'SCOPES': {
        'read': 'Read scope',
        'write': 'Write scope',
        'introspection': 'introspect scope',
        'data-hub:internal-front-end': 'A datahub specific scope'
    },
    'DEFAULT_SCOPES': ['read', 'write', 'data-hub:internal-front-end'],
}

OAUTH2_PROVIDER_APPLICATION_MODEL = 'oauth2.Application'

LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARN'
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'axes_cache': {
        # See - https://github.com/jazzband/django-axes/blob/master/docs/configuration.rst#cache-problems
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

AXES_CACHE = 'axes_cache'

# admin ip restriction
RESTRICT_ADMIN_BY_IPS = env('RESTRICT_ADMIN_BY_IPS')

# sentry config
RAVEN_CONFIG = {
    'dsn': env('SENTRY_DSN', default=None)
}

# email auth
EMAIL_TOKEN_DOMAIN_WHITELIST = env.tuple('EMAIL_TOKEN_DOMAIN_WHITELIST')

EMAIL_TOKEN_TTL = 3600

# email settings
EMAIL_USE_TLS = env('EMAIL_USE_TLS', default=True)
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_PORT = env('EMAIL_PORT', default=587)
EMAIL_FROM = env('EMAIL_FROM', default='test@example.com')

# admin config
ADMIN_TOOLS_INDEX_DASHBOARD = 'sso.core.dashboard.CustomIndexDashboard'

# session settings
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 24 * 60 * 60

# google analytics
GOOGLE_ANALYTICS_CODE = env('GOOGLE_ANALYTICS_CODE', default=None)
GOOGLE_TAG_CODE = env('GOOGLE_TAG_CODE', default=None)

# This is used to determine a users primary email and should be set to a comma separated list
# e.g: 'mobile.ukti.gov.uk, digital.trade.gov.uk'
DEFAULT_EMAIL_ORDER = env('DEFAULT_EMAIL_ORDER', default='')

ZENPY_CREDENTIALS = {
    'email': env('ZENDESK_EMAIL', default=''),
    'token': env('ZENDESK_TOKEN', default=''),
    'subdomain': env('ZENDESK_SUBDOMAIN', default=''),
}

ZENDESK_TICKET_SUBJECT = 'AuthBroker: Support request'

SECURE_BROWSER_XSS_FILTER = env.bool('SECURE_BROWSER_XSS_FILTER', True)
SECURE_CONTENT_TYPE_NOSNIFF = env.bool('SECURE_CONTENT_TYPE_NOSNIFF', True)
