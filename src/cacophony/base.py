"""Cacophony base classes."""
import os

from . import helpers, log


class CacophonyError(Exception):
    """Base exception class for cacophony related errors."""


class ProfileNotFoundError(CacophonyError):
    """Exception thrown when the profile's configuration is not found."""


class Application:
    """Base application class."""

    def __init__(self, logger=None, name="cacophony", load_conf=True,
                 *args, **kwargs):
        """Construct an application class."""

        self.name = name
        self.base_dir = os.path.expanduser("~/.config/cacophony-discord")

        if logger is not None:
            self.logger = logger
        else:
            self._make_default_logger()

        self.conf = {}
        if load_conf:
            self._load_conf()
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

    def _load_conf(self):
        """Private. Load the configuration from the profile's YAML file.

        Raises:
            ProfileNotFoundError: The configuration file according to the
                application's name has not been found.

        """
        base_dir = os.path.join(self.base_dir, self.name)

        if not os.path.exists(base_dir):
            raise ProfileNotFoundError(
                f"The profile '{self.name}' could not be found. Create it "
                f"by launching 'cacophony create --profile {self.name}'")

        self.info("Will load config from %s...", base_dir)
        try:
            self.conf = helpers.load_yaml_file(
                os.path.join(base_dir, "config.yml"))
        except FileNotFoundError:
            raise ProfileNotFoundError(
                "Could not file 'config.yml' file into profile "
                f"'{self.name}'. You can re-create the config file "
                f"by launching 'cacophony create --profile {self.name}'")

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


class Cacophony:
    def __init__(self, logger, name, markov_brain, channels=None,
                 chattyness=0.1, *args, **kwargs):
        self.chattyness = chattyness
        self._name = name
        self._brain = markov_brain
        self._is_mute = False
        self._channels = channels or list()  # Should be a list

    def mute(self):
        self._is_mute = True

    def unmute(self):
        self._is_mute = False

    @property
    def is_mute(self):
        return self._is_mute

    @property
    def brain(self):
        return self._brain

    @property
    def name(self):
        return self._name

    @property
    def channels(self):
        return self._channels
