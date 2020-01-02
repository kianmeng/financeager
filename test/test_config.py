import unittest
from unittest import mock
import time
import tempfile

from financeager.config import Configuration, InvalidConfigError
from financeager import plugin


class ConfigTestCase(unittest.TestCase):
    def test_sections(self):
        config = Configuration()
        self.assertSetEqual(
            set(config._parser.sections()),
            {"SERVICE", "FRONTEND", "SERVICE:FLASK"})

    def test_load_custom_config_file(self):
        # create custom config file, modify service name
        filepath = "/tmp/{}".format(int(time.time()))
        with open(filepath, "w") as file:
            file.write("[SERVICE]\nname = flask\n")

        config = Configuration(filepath=filepath)
        self.assertEqual(config.get_option("SERVICE", "name"), "flask")

    @mock.patch("financeager.CONFIG_FILEPATH", "/tmp/non-existing-config")
    def test_get_option(self):
        config = Configuration()
        self.assertEqual(config.get_option("SERVICE", "name"), "none")
        self.assertDictEqual(config.get_option("SERVICE"), {"name": "none"})

    def test_invalid_config(self):
        filepath = "/tmp/{}".format(int(time.time()))

        for content in (
                "[SERVICE]\nname = sillyservice\n",
                "[FRONTEND]\ndefault_category = ",
                "[SERVICE:FLASK]\ntimeout = foo\n",
        ):
            with open(filepath, "w") as file:
                file.write(content)
            self.assertRaises(
                InvalidConfigError, Configuration, filepath=filepath)

    def test_nonexisting_config_filepath(self):
        filepath = "/tmp/{}".format(time.time())
        with self.assertRaises(InvalidConfigError) as cm:
            Configuration(filepath=filepath)
        self.assertTrue(
            cm.exception.args[0].endswith("Config filepath does not exist!"))


class TestPluginConfiguration(plugin.PluginConfiguration):
    def init_defaults(self, config_parser):
        config_parser["TESTSECTION"] = {
            "test": 42,
            "flag": "off",
            "number": 1.0
        }

    def init_option_types(self, option_types):
        option_types["TESTSECTION"] = {
            "test": "int",
            "flag": "boolean",
            "number": "float"
        }


class PluginConfigTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin = plugin.PluginBase(
            name="test-plugin", config=TestPluginConfiguration())

    def test_init_defaults(self):
        config = Configuration(plugins=[self.plugin])

        # Since creating the Configuration instance did not fail, validation was
        # successful
        self.assertEqual(config.get_option("TESTSECTION", "test"), 42)
        self.assertFalse(config.get_option("TESTSECTION", "flag"))
        self.assertEqual(config.get_option("TESTSECTION", "number"), 1.0)

        self.assertDictEqual(
            config.get_option("TESTSECTION"), {
                "test": 42,
                "flag": False,
                "number": 1.0
            })

    def test_load_custom_test_section(self):
        filepath = tempfile.mkstemp()[1]
        with open(filepath, "w") as file:
            file.write("[TESTSECTION]\ntest = 84\n")

        config = Configuration(filepath=filepath, plugins=[self.plugin])
        self.assertEqual(config.get_option("TESTSECTION", "test"), 84)

    def test_validate(self):
        filepath = tempfile.mkstemp()[1]
        with open(filepath, "w") as file:
            file.write("[TESTSECTION]\ntest = no-int\n")

        self.assertRaises(
            InvalidConfigError,
            Configuration,
            filepath=filepath,
            plugins=[self.plugin])

    def test_load_service_plugin_config(self):
        pl = plugin.ServicePlugin(
            name="test-plugin", config=TestPluginConfiguration(), client=None)
        filepath = tempfile.mkstemp()[1]
        with open(filepath, "w") as file:
            file.write("[SERVICE]\nname = {}\n".format(pl.name))

        config = Configuration(filepath=filepath, plugins=[pl])
        self.assertEqual(config.get_option("SERVICE", "name"), pl.name)


if __name__ == "__main__":
    unittest.main()
