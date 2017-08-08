"""
bsol core application
"""
import os


from . import helpers, log


class Application:
    """Application class."""

    def __init__(self, logger=None, name="bsol", load_conf=True,
                 *args, **kwargs):
        """Construct an application class."""

        self.name = name
        self.bsol_base_dir = os.path.expanduser("~/.bsol")

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
        if log_dict:
            log.load_dict_config(log_dict)
            self.logger = log.get_logger(self.name)

    def _make_default_logger(self):
        """Private. Load a default configuration for bsol and return
        a default logger."""
        log.load_default_config()
        self.logger = log.get_logger('bsol')

    def _load_conf(self):
        base_dir = os.path.join(self.bsol_base_dir, self.name)

        if not os.path.exists(base_dir):
            self.info("Directory {} does not exist. Creating it...".format(
                base_dir))
            os.makedirs(base_dir)
            return  # No config at all

        self.info("Will load config from %s...", base_dir)
        try:
            self.conf = helpers.load_yaml_file(
                os.path.join(base_dir, "config.yml"))
        except FileNotFoundError:
            self.warning("Config file was not found. Skipping...")

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
        return self.logger.critical(msg, *fmt)
