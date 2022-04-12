import logging
import os
import unittest

import mock

from catatom2osm import config
from catatom2osm.exceptions import CatConfigError

logging.disable(logging.WARNING)
os.environ["LANGUAGE"] = "C"
config.install_gettext("catato2osm", "")


class TestConfig(unittest.TestCase):
    @mock.patch("catatom2osm.config.os")
    @mock.patch("catatom2osm.config.print")
    def test_generate_default_user_config(self, m_print, m_os):
        m_os.path.exists.return_value = False
        m_open = mock.mock_open()
        with mock.patch("catatom2osm.config.open", m_open):
            config.generate_default_user_config()
        m_open.assert_called_once_with(config.default_config_file, "w")
        output = m_open().write.call_args_list[1][0][0]
        expect = f"warning_min_area: {config.default_warning_min_area}"
        self.assertIn(expect, output)
        self.assertIn("Config file saved", m_print.call_args_list[0][0][0])

    @mock.patch("catatom2osm.config.os")
    @mock.patch("catatom2osm.config.open")
    @mock.patch("catatom2osm.config.print")
    def test_generate_default_user_config_exists(self, m_print, m_open, m_os):
        m_os.path.exists.return_value = True
        config.generate_default_user_config()
        m_open.assert_not_called()
        self.assertIn("exists. Delete", m_print.call_args_list[0][0][0])

    @mock.patch("catatom2osm.config.logging")
    def test_get_user_config(self, m_logging):
        data = "warning_min_area: 1234\n"
        data += "foo: bar\n"
        m_open = mock.mock_open(read_data=data)
        with mock.patch("catatom2osm.config.open", m_open):
            config.get_user_config("taz")
        m_open.assert_called_once_with("taz", "r")
        self.assertEqual(config.warning_min_area, 1234)
        self.assertFalse(hasattr(config, "foo"))
        m_logging.getLogger().warning.assert_called_once_with(
            "Config key 'foo' is not valid"
        )

    def test_get_user_config_error(self):
        data = "foo: ["
        m_open = mock.mock_open(read_data=data)
        with self.assertRaises(CatConfigError) as e:
            with mock.patch("catatom2osm.config.open", m_open):
                config.get_user_config("taz")
        msg = str(e.exception)
        self.assertIn("Can't read 'taz'", msg)
        self.assertIn("found '<stream end>'", msg)

    @mock.patch("catatom2osm.config.logging")
    @mock.patch("catatom2osm.config.open")
    def test_get_user_config_not_found(self, m_open, m_logging):
        m_open.side_effect = FileNotFoundError()
        config.get_user_config("taz")
        m_logging.getLogger().warning.called_once_with(
            "Config file '%s' not found", "taz"
        )
