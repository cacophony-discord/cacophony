"""Cacophony base classes."""
from enum import Enum

from . import log


class Hook(Enum):
    """Describe different hook kinds for cacophony."""
    ON_MESSAGE = 1
    ON_ANSWER = 2
    ON_SERVER_JOIN = 3


class CacophonyError(Exception):
    """Base exception class for cacophony related errors."""


class Application:
    """Base application class."""

    def __init__(self, logger=None, name="cacophony", load_conf=True,
                 *args, **kwargs):
        """Construct an application class."""

        self.name = name
        if logger is not None:
            self.logger = logger
        else:
            self._make_default_logger()

        self.conf = {}
        if load_conf:
            self._reconfigure_logging()
            self.debug("Loaded configuration: %s", self.conf)

    def _reconfigure_logging(self):
        """Reconfigure logging according to application's config."""
        log_dict = self.conf.get('logging')
        if log_dict is not None:
            log.load_dict_config(log_dict)
            self.logger = log.get_logger(self.name)

    def _make_default_logger(self):
        """Private. Load a default configuration for bsol and return
        a default logger."""
        log.load_default_config(self.name)
        self.logger = log.get_logger(self.name)

    def run(self):
        """Run the application."""

    def debug(self, msg, *fmt):
        """Wrapper around self.logger.debug(...)"""
        return self.logger.debug(msg, *fmt)

    def info(self, msg, *fmt):
        """Wrapper around self.logger.info(...)"""
        return self.logger.info(msg, *fmt)

    def warning(self, msg, *fmt):
        """Wrapper around self.logger.warn(...)"""
        return self.logger.warning(msg, *fmt)

    def error(self, msg, *fmt):
        """Wrapper around self.logger.error(...)"""
        return self.logger.error(msg, *fmt)

    def critical(self, msg, *fmt):
        """Wrapper around self.logger.error(...)"""


class Plugin:
    """Base class for cacophony plugins."""

    def __init__(self, bot, *args, **kwargs):
        """Instantiate a plug-in being loaded by `bot`.

        Args:
            bot: The bot loading the plugin.

        """
        self._bot = bot

    @property
    def bot(self):
        """Return the bot instance."""
        return self._bot

    async def on_load(self):
        """Hook called when the plugin is being loaded."""

    async def on_ready(self):
        """Hook called when the bot is ready to deal with discord servers."""
