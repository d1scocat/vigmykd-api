import logging.config
import sys


config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s | [%(levelname)s] %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'level': 'INFO',
            'formatter': 'detailed'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'app.log',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'encoding': 'utf-8'
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO'
    },
    'loggers': {
        'vigmykd': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}


def setup():
    logging.config.dictConfig(config)
