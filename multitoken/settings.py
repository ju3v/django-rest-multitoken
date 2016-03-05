from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured


TOKEN_TIMEOUT_IN_DAYS = 14


def get(key):
    from django.conf import settings
    defaults = {
        'TOKEN_TIMEOUT': timedelta(days=TOKEN_TIMEOUT_IN_DAYS)
    }
    defaults.update(getattr(settings, 'REST_MULTITOKEN', {}))
    try:
        return defaults[key]
    except KeyError:
        raise ImproperlyConfigured(
            'Missing settings: REST_MULTITOKEN[\'{}\']'.format(key))
