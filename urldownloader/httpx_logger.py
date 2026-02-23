import contextlib
import logging
from copy import deepcopy


def __log_httpx_on(logfile):
    fileHandler = logging.FileHandler(logfile)
    fileHandler.setLevel(logging.DEBUG)
    fileHandler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    )

    httpx_log = logging.getLogger("httpx")
    httpx_log.setLevel(logging.DEBUG)
    httpx_handlers = deepcopy(httpx_log.handlers)
    httpx_log.addHandler(fileHandler)

    httpcore_log = logging.getLogger("httpcore")
    httpcore_log.setLevel(logging.DEBUG)
    httpcore_handlers = deepcopy(httpcore_log.handlers)
    httpcore_log.addHandler(fileHandler)

    return httpx_handlers, httpcore_handlers


def __log_httpx_off(httpx_handlers, httpcore_handlers):
    httpx_log = logging.getLogger("httpx")
    httpx_log.setLevel(logging.WARNING)
    if httpx_handlers is not None:
        httpx_log.handlers = httpx_handlers

    httpcore_log = logging.getLogger("httpcore")
    httpcore_log.setLevel(logging.WARNING)
    if httpcore_handlers is not None:
        httpcore_log.handlers = httpcore_handlers


@contextlib.contextmanager
def log_httpx(logfile):
    """Use with 'with'!"""
    httpx_handlers, httpcore_handlers = __log_httpx_on(logfile)
    try:
        yield
    finally:
        __log_httpx_off(httpx_handlers, httpcore_handlers)
