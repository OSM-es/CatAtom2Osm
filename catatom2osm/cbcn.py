"""Reader of Carto BCN addresses."""
import logging
import os
import re
from datetime import datetime

from qgis.core import QgsFeature

from catatom2osm import config, download
from catatom2osm.exceptions import CatIOError
from catatom2osm.geo import AddressLayer, BaseLayer, Point
from catatom2osm.geo.tools import is_inside

log = logging.getLogger(config.app_name)

cbcn_thr = 1  # Threshold in meters to search for Cadastre parcel

highway_types_equiv = {
    "Av": "Avinguda",
    "Bda": "Baixada",
    "C": "Carrer",
    "Cro": "Carreró",
    "Csta": "Costa",
    "Ctra": "Carretera",
    "Dav": "Davallada",
    "Drec": "Drecera",
    "Esc": "Escales",
    "Escu": "Escullera",
    "Esp": "Espigó",
    "G.V.": "Gran Via",
    "Jard": "Jardins",
    "Pdis": "Passadís",
    "Pg": "Passeig",
    "Pl": "Plaça",
    "Plta": "Placeta",
    "Ptge": "Passatge",
    "Ptja": "Platja",
    "Rbla": "Rambla",
    "Rda": "Ronda",
    "Rier": "Riera",
    "T": "Torrent",
    "Trav": "Travessera",
    "Trvs": "Travessia",
    "Viad": "Viaducte",
}


def get_cat_address(ad):
    """Convert CBCN addresses to Cadastre attributes."""
    attr = {}
    tip_via = ad["NOM_VIA"].split(" ")[0]
    nom_tip_via = highway_types_equiv.get(tip_via, tip_via)
    nom_via = ad["NOM_VIA"][len(tip_via) :]
    attr["TN_text"] = nom_tip_via + nom_via
    attr["spec"] = "Entrance"
    attr["designator"] = ad["LITERAL"].replace(".", "")
    return attr


def get_address(cbcn, parcel):
    """Get  Cadastre style addresses from CBCN dataset."""
    address = AddressLayer()
    address.rename = {}
    address.resolve = {}
    address.setCrs(cbcn.crs())
    address.startEditing()
    index = parcel.get_index()
    pa_feat = {f.id(): f for f in parcel.getFeatures()}
    for ad in cbcn.getFeatures():
        if ad["NOM_VIA"] == None:  # NOQA
            continue
        attr = get_cat_address(ad)
        pt = Point(ad.geometry().asPoint())
        area_of_candidates = pt.boundingBox(cbcn_thr)
        fids = index.intersects(area_of_candidates)
        parcel = None
        sep = cbcn_thr
        for fid in fids:
            dist = pa_feat[fid].geometry().closestSegmentWithContext(pt)[0]
            if is_inside(ad, pa_feat[fid]):
                parcel = pa_feat[fid]
                break
            elif dist < sep:
                parcel = pa_feat[fid]
                sep = dist
        if parcel:
            ref = f"{ad['CODICARRER']}.{attr['designator']}.{parcel['localId']}"
            attr["localId"] = ref
            feat = QgsFeature(address.fields())
            for key, value in list(attr.items()):
                feat[key] = value
            feat.setGeometry(ad.geometry())
            address.addFeature(feat)
    address.commitChanges()
    msg = _("Read %d features in '%s'")
    log.info(msg, address.featureCount(), address.name())
    return address


class Reader(object):
    """Class to download and read Carto BCN SHP file."""

    def __init__(self, a_path):
        """
        Construct a CBCN reader.

        Args:
            a_path (str): Directory where the source files are located.
        """
        self.path = a_path
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            raise CatIOError(_("Not a directory: '%s'") % a_path)
        self.cbcn_fn = "0501040100_Adreces.zip"
        self.url = (
            "https://opendata-ajuntament.barcelona.cat/"
            "data/dataset/6b5cfa7b-1d8d-45f0-990a-d1844d43ffd1/"
            "resource/6bfe63d8-8c6c-4cde-aaa3-b7c48fa66e34/download"
        )
        self.meta_url = (
            "https://opendata-ajuntament.barcelona.cat/"
            "data/es/dataset/taula-direle/"
            "resource/6bfe63d8-8c6c-4cde-aaa3-b7c48fa66e34"
        )
        self.src_date = None

    def get_metadata(self):
        fn = os.path.join(self.path, self.cbcn_fn + ".txt")
        if os.path.exists(fn):
            with open(fn, "r") as fo:
                self.src_date = fo.read()
        else:
            with download.get_response(self.meta_url) as response:
                s = re.search(
                    r"Fecha publicación</th>[\n\r ]*<td>([\d/]+)",
                    response.text,
                )
            try:
                self.src_date = datetime.strptime(s.group(1), "%d/%m/%Y").strftime(
                    "%Y-%m-%d"
                )
            except Exception:
                raise CatIOError(_("Could not read metadata from '%s'") % "Carto BCN")
            with open(fn, "w") as fo:
                fo.write(self.src_date)

    def read(self):
        fn = os.path.join(self.path, self.cbcn_fn)
        if not os.path.exists(fn):
            log.info(_("Downloading '%s'"), self.cbcn_fn)
            download.wget(self.url, fn)
        cbcn = BaseLayer(fn, "cbcn", "ogr")
        if not cbcn.isValid():
            raise CatIOError(_("Failed to load layer '%s'") % self.cbcn_fn)
        cbcn.setProviderEncoding("ISO-8859-1")
        log.info(_("Read %d features in '%s'"), cbcn.featureCount(), self.cbcn_fn)
        self.get_metadata()
        cbcn.source_date = self.src_date
        return cbcn
