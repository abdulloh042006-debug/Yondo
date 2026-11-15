import logging
import sys

import structlog

_SECRET_KEYS = frozenset(
    {'password', 'current_password', 'new_password', 'password_hash', 'code', 'otp', 'token'}
)


def _drop_secrets(_logger, _method, event_dict):
    """Guard: never write a password, code or token field into a log line."""
    for key in _SECRET_KEYS.intersection(event_dict):
        event_dict[key] = '[redacted]'
    return event_dict


def configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(format='%(message)s', stream=sys.stdout, level=level, force=True)
    # httpx/httpcore log every request URL at INFO. The Telegram Bot API puts the bot token in the
    # URL path (/bot<token>/...), so those loggers must never go below WARNING.
    for name in ('httpx', 'httpcore'):
        logging.getLogger(name).setLevel(max(level, logging.WARNING))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _drop_secrets,
            structlog.processors.TimeStamper(fmt='iso', utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

