from django.conf import settings

from . import constants as c

# Where the data, primarily the weights, are stored.
settings.ASKLET_BACKEND = getattr(
    settings,
    'ASKLET_BACKEND',
    c.SQL)

# What mechanism we use to calculate ranks.
# Dependent on backend.
settings.ASKLET_RANKER = getattr(
    settings,
    'ASKLET_RANKER',
    #c.PYTHON,
    c.SQL,#Only available with SQL backend.
)
