import unittest

import mock

from catatom2osm.geo.aux import merge_groups


class TestAux(unittest.TestCase):

    def test_merge_groups(self):
        groups = [[1, 1, 2, 3], [2, 4], [4, 5, 6], [7, 8, 9], [8, 9]]
        result = merge_groups(groups)
        self.assertEqual(len(result), 2)
        g1 = result[0]
        g2 = result[1]
        self.assertTrue(all([g not in g1 for g in g2]))
