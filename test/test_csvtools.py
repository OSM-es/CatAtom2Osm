import io
import unittest
from tempfile import mkstemp

from catatom2osm import csvtools
from catatom2osm.config import delimiter, encoding
from catatom2osm.exceptions import CatIOError


class TestCsvTools(unittest.TestCase):
    def test_csv2dict(self):
        _, tmp_path = mkstemp()
        with io.open(tmp_path, "w", encoding=encoding) as csv_file:
            csv_file.write("á%sx\né%sy\n" % (delimiter, delimiter))
        a_dict = csvtools.csv2dict(tmp_path, {})
        self.assertEqual(a_dict, {"á": "x", "é": "y"})

    def test_csv2dict_bad_delimiter(self):
        _, tmp_path = mkstemp()
        with io.open(tmp_path, "w", encoding=encoding) as csv_file:
            csv_file.write("a;1\nb;2")
        with self.assertRaises(CatIOError):
            csvtools.csv2dict(tmp_path, {})

    def test_dict2csv(self):
        _, tmp_path = mkstemp()
        a_dict = {"á": "x", "é": "y"}
        items = list(a_dict.items())
        exp = "%s%s%s\n%s%s%s\n" % (
            items[0][0],
            delimiter,
            items[0][1],
            items[1][0],
            delimiter,
            items[1][1],
        )
        csvtools.dict2csv(tmp_path, a_dict)
        with io.open(tmp_path, "r", encoding=encoding) as csv_file:
            text = csv_file.read()
        self.assertEqual(text, exp)

    def test_dict2csv_sort(self):
        _, tmp_path = mkstemp()
        csvtools.dict2csv(tmp_path, {"b": "1", "a": "3", "c": "2"}, sort=1)
        with io.open(tmp_path, "r", encoding=encoding) as csv_file:
            text = csv_file.read()
        self.assertEqual(text, "b%s1\nc%s2\na%s3\n" % (delimiter, delimiter, delimiter))

    def test_search_mun(self):
        def query(row, args):
            return row[0] == args[0]

        fn = "test/fixtures/municipalities.csv"
        output = csvtools.search(fn, "05001", query=query)
        self.assertEqual(output, ["05001", "339910", "Adanero"])

    def test_filter_prov(self):
        def query(row, args):
            return row[0].startswith(args[0])

        fn = "test/fixtures/municipalities.csv"
        output = csvtools.filter(fn, "02", query=query)
        self.assertTrue(all([row[0].startswith("02") for row in output]))
        self.assertEqual(len(output), 87)
