"""
bsol log facilities
"""
import logging
import logging.config


def load_dict_config(dict_config):
    logging.config.dictConfig(dict_config)


def load_default_config(name='cacophony'):
    """Configure logging facility with basic configuration."""
    config_dict = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s '
                          '%(process)d %(thread)d %(message)s'
            },
            'simple': {
                'format': '[%(levelname)s] %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            name: {
                'level': 'DEBUG',
                'handlers': ['console']
            }
        }
    }
    logging.config.dictConfig(config_dict)


def get_logger(logger_name):
    """Simple snake_case wrapper around logging.getLogger()"""
    return logging.getLogger(logger_name)
