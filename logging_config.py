"""Centralized logging setup.

`configure_logging()` is called once at process startup from `app.py`. It
attaches a stdout `StreamHandler` plus a `RotatingFileHandler` writing to
`logs/rssfedder.log` (5 MB per file, 3 rotations kept). Every module then
uses `logging.getLogger(__name__)` and inherits this configuration.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = 'logs'
LOG_FILE = 'rssfedder.log'
LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUPS = 3


def configure_logging(level=logging.INFO):
    os.makedirs(LOG_DIR, exist_ok=True)
    root = logging.getLogger()
    if any(getattr(h, '_rssfedder', False) for h in root.handlers):
        return
    root.setLevel(level)
    fmt = logging.Formatter(LOG_FORMAT)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh._rssfedder = True
    root.addHandler(sh)

    fh = RotatingFileHandler(
        os.path.join(LOG_DIR, LOG_FILE),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUPS,
        encoding='utf-8',
    )
    fh.setFormatter(fmt)
    fh._rssfedder = True
    root.addHandler(fh)
