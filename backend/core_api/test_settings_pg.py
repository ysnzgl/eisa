"""
PostgreSQL integration test settings.

Usage:
    pytest -m postgresql --ds=core_api.test_settings_pg
"""
from .test_settings import *  # noqa: F403, F401

# PostgreSQL connection (docker-compose.test-pg.yml)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'eisa_test',
        'USER': 'eisa_test_user',
        'PASSWORD': 'eisa_test_pass',
        'HOST': 'localhost',
        'PORT': '5433',  # docker-compose port mapping
        'ATOMIC_REQUESTS': False,
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 10,
        },
        'TEST': {
            'NAME': 'eisa_test_integration',
            'CHARSET': 'UTF8',
            'COLLATION': None,
            'CREATE_DB': True,
            'USER': 'eisa_test_user',
            'PASSWORD': 'eisa_test_pass',
        },
    }
}

# PostgreSQL specific: gerçek transaction isolation testleri için
# select_for_update() nowait/skip_locked/of gerçek davranış gösterir
USE_TZ = True
