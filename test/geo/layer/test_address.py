import logging
import unittest

import mock
from osgeo import gdal
from qgis.core import QgsField, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant

from catatom2osm import osm
from catatom2osm.app import QgsSingleton
from catatom2osm.geo.layer.address import AddressLayer
from catatom2osm.geo.layer.highway import HighwayLayer
from catatom2osm.geo.layer.polygon import PolygonLayer

gdal.PushErrorHandler("CPLQuietErrorHandler")
qgs = QgsSingleton()
m_log = mock.MagicMock()
m_log.app_level = logging.INFO


class TestAddressLayer(unittest.TestCase):
    def setUp(self):
        fn = "test/fixtures/address.gml"
        self.address_gml = QgsVectorLayer(fn, "address", "ogr")
        self.assertTrue(self.address_gml.isValid(), "Loading address")
        self.tn_gml = QgsVectorLayer(fn + "|layername=thoroughfarename", "tn", "ogr")
        self.assertTrue(self.tn_gml.isValid(), "Loading thoroughfarename")
        self.pd_gml = QgsVectorLayer(fn + "|layername=postaldescriptor", "pd", "ogr")
        self.assertTrue(self.pd_gml.isValid(), "Loading address")
        self.au_gml = QgsVectorLayer(fn + "|layername=adminUnitname", "au", "ogr")
        self.assertTrue(self.au_gml.isValid(), "Loading address")
        fn = "test_layer.shp"
        AddressLayer.create_shp(fn, self.address_gml.crs())
        self.layer = AddressLayer(fn, "address", "ogr")
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.dataProvider().addAttributes(
            [QgsField("TN_text", QVariant.String, len=254)]
        )
        self.layer.updateFields()

    def tearDown(self):
        del self.layer
        AddressLayer.delete_shp("test_layer.shp")

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.progressbar", mock.MagicMock())
    def test_append(self):
        self.layer.append(self.address_gml)
        feat = next(self.layer.getFeatures())
        attrs = ["localId", "PD_id", "TN_id", "AU_id"]
        values = [
            "38.012.1.12.0295603CS6109N",
            "ES.SDGC.PD.38.012.38570",
            "ES.SDGC.TN.38.012.1",
            "ES.SDGC.AU.38.012",
        ]
        for (attr, value) in zip(attrs, values):
            self.assertEqual(feat[attr], value)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.progressbar", mock.MagicMock())
    def test_join_field(self):
        self.layer.append(self.address_gml)
        self.layer.join_field(self.tn_gml, "TN_id", "gml_id", ["text"], "TN_")
        self.layer.join_field(self.au_gml, "AU_id", "gml_id", ["text"], "AU_")
        self.layer.join_field(self.pd_gml, "PD_id", "gml_id", ["postCode"])
        feat = next(self.layer.getFeatures())
        attrs = ["TN_text", "AU_text", "postCode"]
        values = ["MC ABASTOS (RESTO)", "FASNIA", 38570]
        for (attr, value) in zip(attrs, values):
            self.assertEqual(feat[attr], value)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.progressbar", mock.MagicMock())
    def test_join_field_size(self):
        layer = PolygonLayer("Point", "test", "memory")
        layer.dataProvider().addAttributes([QgsField("A", QVariant.String, len=255)])
        layer.updateFields()
        self.layer.append(self.address_gml)
        self.layer.join_field(layer, "TN_id", "gml_id", ["A"], "TN_")
        self.assertEqual(self.layer.fields().field("TN_A").length(), 254)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.progressbar", mock.MagicMock())
    def test_join_void(self):
        self.layer.join_field(self.tn_gml, "TN_id", "gml_id", ["text"], "TN_")
        self.assertEqual(self.layer.featureCount(), 0)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.progressbar", mock.MagicMock())
    def test_to_osm(self):
        self.layer.append(self.address_gml)
        self.layer.join_field(self.tn_gml, "TN_id", "gml_id", ["text"], "TN_")
        self.layer.join_field(self.au_gml, "AU_id", "gml_id", ["text"], "AU_")
        self.layer.join_field(self.pd_gml, "PD_id", "gml_id", ["postCode"])
        self.layer.source_date = "foobar"
        data = osm.Osm(upload="ifyoudare")
        data.Node(0, 0)
        data = self.layer.to_osm(data=data)
        self.assertEqual(data.upload, "ifyoudare")
        self.assertEqual(data.tags["source:date"], "foobar")
        self.assertEqual(len(data.elements), self.layer.featureCount() + 1)
        address = {
            n.tags["ref"]: n.tags["addr:street"] + n.tags["addr:housenumber"]
            for n in data.nodes
            if "ref" in n.tags
        }
        for feat in self.layer.getFeatures():
            t = address[feat["localId"].split(".")[-1]]
            self.assertEqual(feat["TN_text"] + feat["designator"], t)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.progressbar", mock.MagicMock())
    def test_conflate(self):
        self.layer.append(self.address_gml)
        self.layer.join_field(self.tn_gml, "TN_id", "gml_id", ["text"], "TN_")
        self.layer.join_field(self.au_gml, "AU_id", "gml_id", ["text"], "AU_")
        self.layer.join_field(self.pd_gml, "PD_id", "gml_id", ["postCode"])
        current_address = ["CJ CALLEJON (FASNIA)12", "CJ CALLEJON (FASNIA)13"]
        self.assertEqual(self.layer.featureCount(), 14)
        self.layer.conflate(current_address)
        self.assertEqual(self.layer.featureCount(), 10)
        self.layer.conflate(current_address)
        self.assertEqual(self.layer.featureCount(), 10)

    def test_get_highway_names(self):
        fn = "test/fixtures/address.geojson"
        layer = AddressLayer(fn, "address", "ogr")
        fn = "test/fixtures/highway.geojson"
        highway = HighwayLayer(fn, "highway", "ogr")
        highway_names = layer.get_highway_names(highway)
        test = {
            "AV PAZ (FASNIA)": ("Avenida la Paz", "OSM"),
            "CL SAN JOAQUIN (FASNIA)": ("Calle San Joaquín", "OSM"),
            "CL HOYO (FASNIA)": ("Calle el Hoyo", "OSM"),
            "CJ CALLEJON (FASNIA)": ("Calleja/Callejón Callejon (Fasnia)", "CAT"),
        }
        for (k, v) in list(highway_names.items()):
            self.assertEqual(v, test[k])
