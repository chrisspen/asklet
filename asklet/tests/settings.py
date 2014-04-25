import os, sys
PROJECT_DIR = os.path.dirname(__file__)
DEBUG = True
SITE_ID = 1
DATABASES = {
    'default':{
        'ENGINE': 'django.db.backends.sqlite3',
    }
}
ROOT_URLCONF = 'asklet.tests.urls'
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'south',
    'asklet',
    'asklet.tests',
]
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')
STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    #'django.middleware.gzip.GZipMiddleware',
    #'pipeline.middleware.MinifyHTMLMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',#should come after gzip/minify
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'middleware.usercontext.UserContextMiddleware',
)

ADMIN_MEDIA_PREFIX = '/media/admin/'
STATIC_URL = '/static/' # Cannot be absolute on dev?
SOUTH_TESTS_MIGRATE = False
USE_TZ = True

TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

USE_I18N = True

AUTH_USER_MODEL = 'auth.User'

SECRET_KEY = '-a-nku-@g0ig9_%(r2_o+fabjf-knwaeujwfs@rt!z^ox=7$2d'

try:
    from .settings_local import *
except ImportError:
    raise
