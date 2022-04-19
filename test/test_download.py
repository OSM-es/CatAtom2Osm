import unittest

import mock

from catatom2osm import config
from catatom2osm.download import chunk_size, get_response, wget

config.install_gettext("catato2osm", "")


class TestGetResponse(unittest.TestCase):
    @mock.patch("catatom2osm.download.requests")
    def test_get_response_ok(self, mock_requests):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_requests.codes.ok = 200
        mock_requests.get.return_value = mock_response
        r = get_response("foo", "bar")
        self.assertEqual(r, mock_response)
        mock_requests.get.assert_called_once_with("foo", stream="bar", timeout=30)

    @mock.patch("catatom2osm.download.requests")
    def test_get_response_bad(self, mock_requests):
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_requests.codes.ok = 200
        mock_requests.get.return_value = mock_response
        get_response("foo", "bar")
        self.assertEqual(mock_requests.get.call_count, 3)
        mock_response.raise_for_status.assert_called_once_with()


class TestWget(unittest.TestCase):
    @mock.patch("catatom2osm.download.progressbar", mock.MagicMock())
    @mock.patch("catatom2osm.download.get_response")
    @mock.patch("catatom2osm.download.open")
    def test_wget(self, mock_open, mock_gr):
        mock_gr.return_value = mock.MagicMock()
        mock_gr.return_value.iter_content = range
        mock_gr.return_value.headers = {"Content-Length": "99999"}
        file_mock = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = file_mock
        wget("foo", "bar")
        self.assertEqual(file_mock.write.call_count, chunk_size)

    @mock.patch("catatom2osm.download.progressbar", mock.MagicMock())
    @mock.patch("catatom2osm.download.get_response")
    @mock.patch("catatom2osm.download.open")
    def test_wget0(self, mock_open, mock_gr):
        mock_gr.return_value = mock.MagicMock()
        mock_gr.return_value.iter_content = range
        mock_gr.return_value.headers = {}
        file_mock = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = file_mock
        wget("foo", "bar")
        self.assertEqual(file_mock.write.call_count, chunk_size)
