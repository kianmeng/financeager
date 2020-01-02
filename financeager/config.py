"""Configuration of the financeager application."""
import os.path
from configparser import ConfigParser, NoSectionError, NoOptionError

import financeager
from financeager import plugin
from .entries import CategoryEntry, BaseEntry
from .exceptions import InvalidConfigError
from . import DEFAULT_HOST, DEFAULT_TIMEOUT, init_logger

logger = init_logger(__name__)


class Configuration:
    """Wrapper around a ConfigParser object holding configuration. The default
    configuration can be customized by settings specified in a config file.
    """

    def __init__(self, filepath=None, plugins=None):
        """Initialize the default configuration, overwrite with custom
        configuration from file if available, and eventually validate the loaded
        configuration.
        If plugins are given, their configuration is taken into account.

        :type plugins: list[plugin.PluginBase]

        :raises: InvalidConfigError if validation fails
        """
        if filepath is None and os.path.exists(financeager.CONFIG_FILEPATH):
            self._filepath = financeager.CONFIG_FILEPATH
        else:
            self._filepath = filepath

        self._plugins = plugins or []
        self._parser = ConfigParser()
        self._option_types = {}

        self._init_defaults()
        self._init_option_types()

        self._load_custom_config()
        self._validate()

    def _init_defaults(self):
        self._parser["SERVICE"] = {
            "name": "none",
        }
        self._parser["FRONTEND"] = {
            "default_category": CategoryEntry.DEFAULT_NAME,
            "date_format": BaseEntry.DATE_FORMAT.replace("%", "%%"),
        }
        self._parser["SERVICE:FLASK"] = {
            "host": DEFAULT_HOST,
            "timeout": DEFAULT_TIMEOUT,
            "username": "",
            "password": "",
        }

        for p in self._plugins:
            p.config.init_defaults(self._parser)

    def _init_option_types(self):
        self._option_types = {
            "SERVICE:FLASK": {
                "timeout": "int",
            },
        }

        for p in self._plugins:
            p.config.init_option_types(self._option_types)

    def _load_custom_config(self):
        """Update config values according to customization in config file."""
        if self._filepath is None:
            return

        logger.debug("Loading custom config from {}".format(self._filepath))

        custom_config = ConfigParser()
        # read() silently ignores non-existing paths but returns list of paths
        # that were successfully read
        used_filepaths = custom_config.read(self._filepath)
        if len(used_filepaths) < 1 or used_filepaths[0] != self._filepath:
            raise InvalidConfigError("Config filepath does not exist!")

        for section in self._parser.sections():
            for item in self._parser.options(section):
                try:
                    # read raw value to avoid issues when reading date format
                    # containing percent-characters
                    custom_value = custom_config.get(section, item, raw=True)
                except (NoSectionError, NoOptionError):
                    # section or option not specified by user
                    continue
                self._parser[section][item] = custom_value

    def get_section(self, section):
        """Return a dictionary of options of the requested section.
        If an option is typed, a converted value is returned.
        """
        return {
            o: self.get_option(section, o)
            for o in self._parser.options(section)
        }

    def get_option(self, section, option):
        """Return the requested option of the configuration.
        If an option is typed, a converted value is returned.
        """
        try:
            option_type = self._option_types[section][option]
        except KeyError:
            # Option type not specified, assuming str
            option_type = None

        if option_type in ("int", "float", "boolean"):
            get = getattr(self._parser, "get{}".format(option_type))
        else:
            get = self._parser.get

        return get(section, option)

    def _validate(self):
        """Validate certain options of the configuration. Typed options are
        validated for possible conversion.

        :raises: InvalidConfigError
        """
        valid_services = ["none", "flask"]
        for p in self._plugins:
            if isinstance(p, plugin.ServicePlugin):
                valid_services.append(p.name)

        if self.get_option("SERVICE", "name") not in valid_services:
            raise InvalidConfigError("Unknown service name!")

        if len(self.get_option("FRONTEND", "default_category")) < 1:
            raise InvalidConfigError("Default category name too short!")

        for section in self._option_types:
            for option in self._option_types[section]:
                try:
                    self.get_option(section, option)
                except ValueError:
                    raise InvalidConfigError(
                        "Wrong type for option {} in section {}.".format(
                            option, section))

        for p in self._plugins:
            p.config.validate(self)
