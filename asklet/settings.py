from django.conf import settings

settings.ASKLET_BACKEND = getattr(
    settings,
    'ASKLET_BACKEND',
    'SQL')
