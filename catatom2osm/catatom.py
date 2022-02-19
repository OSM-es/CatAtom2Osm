"""Reader of Cadastre ATOM GML files."""
import logging
import os
import re
import zipfile

from lxml import etree
from qgis.core import QgsCoordinateReferenceSystem

from catatom2osm import config, download, geo
from catatom2osm.exceptions import CatIOError, CatValueError

log = logging.getLogger(config.app_name)


class Reader(object):
    """Class to download and read Cadastre ATOM GML files."""

    def __init__(self, a_path):
        """
        Construct a cadastre reader.

        Args:
            a_path (str): Directory where the source files are located.
        """
        self.path = a_path
        m = re.match(r"^\d{5}$", os.path.split(a_path)[-1])
        if not m:
            msg = _("Last directory name must be a 5 digits ZIP code")
            raise CatValueError(msg)
        self.zip_code = m.group()
        self.prov_code = self.zip_code[0:2]
        if self.prov_code not in config.prov_codes:
            msg = _("Province code '%s' is not valid") % self.prov_code
            raise CatValueError(msg)
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            raise CatIOError(_("Not a directory: '%s'") % a_path)

    def get_path(self, *paths):
        """Get path from components relative to self.path."""
        return os.path.join(self.path, *paths)

    def get_metadata(self, md_path, zip_path=""):
        """Get the metadata of the source file."""
        if os.path.exists(md_path):
            with open(md_path, "rb") as f:
                text = f.read()
        else:
            try:
                zf = zipfile.ZipFile(zip_path)
                text = zf.read(self.get_path_from_zip(zf, md_path))
            except IOError:
                raise CatIOError(_("Could not read metadata from '%s'") % md_path)
        root = etree.fromstring(text)
        is_empty = len(root) == 0 or len(root[0]) == 0
        namespace = {
            "gco": "http://www.isotc211.org/2005/gco",
            "gmd": "http://www.isotc211.org/2005/gmd",
        }
        if hasattr(root, "nsmap"):
            namespace = root.nsmap
        src_date = root.find("gmd:dateStamp/gco:Date", namespace)
        if is_empty or src_date is None:
            raise CatIOError(_("Could not read metadata from '%s'") % md_path)
        self.src_date = src_date.text
        gml_title = root.find(".//gmd:title/gco:CharacterString", namespace)
        self.cat_mun = gml_title.text.split("-")[-1].split("(")[0].strip()
        gml_code = root.find(".//gmd:code/gco:CharacterString", namespace)
        self.crs_ref = int(gml_code.text.split("/")[-1])

    def get_atom_file(self, url):
        """
        Try to download the ZIP file for self.zip_code.

        Given the url of a Cadastre ATOM service.
        """
        s = re.search(r"INSPIRE/(\w+)/", url)
        log.debug(
            _("Searching the url for the '%s' layer of '%s'..."),
            s.group(1),
            self.zip_code,
        )
        response = download.get_response(url)
        s = re.search(r"http.+/%s.+zip" % self.zip_code, response.text)
        if not s:
            msg = _("Municipality code '%s' don't exists") % self.zip_code
            raise CatValueError(msg)
        url = s.group(0)
        filename = url.split("/")[-1]
        out_path = self.get_path(filename)
        log.info(_("Downloading '%s'"), out_path)
        download.wget(url, out_path)

    def get_layer_paths(self, layername):
        if layername in ["building", "buildingpart", "otherconstruction"]:
            group = "BU"
        elif layername in ["cadastralparcel", "cadastralzoning"]:
            group = "CP"
        elif layername in [
            "address",
            "thoroughfarename",
            "postaldescriptor",
            "adminunitname",
        ]:
            group = "AD"
        else:
            raise CatValueError(_("Unknow layer name '%s'") % layername)
        gml_fn = ".".join((config.fn_prefix, group, self.zip_code, layername, "gml"))
        if group == "AD":
            gml_fn = ".".join((config.fn_prefix, group, self.zip_code, "gml"))
        md_fn = ".".join((config.fn_prefix, group, "MD", self.zip_code, "xml"))
        if group == "CP":
            md_fn = ".".join((config.fn_prefix, group, "MD.", self.zip_code, "xml"))
        zip_fn = ".".join((config.fn_prefix, group, self.zip_code, "zip"))
        md_path = self.get_path(md_fn)
        gml_path = self.get_path(gml_fn)
        zip_path = self.get_path(zip_fn)
        return (md_path, gml_path, zip_path, group)

    def is_empty(self, gml_path, zip_path):
        """
        Detect if the file is empty.

        Cadastre empty files (usually otherconstruction) comes with a null
        feature and results in a non valid layer in QGIS.
        """
        if os.path.exists(zip_path):
            zf = zipfile.ZipFile(zip_path)
            gml_fp = self.get_path_from_zip(zf, gml_path)
            fo = zf.open(gml_fp, "r")
        else:
            fo = open(gml_path, "rb")
        text = fo.read(2000)
        fo.close()
        parser = etree.XMLPullParser(["start", "end"])
        parser.feed(text)
        events = list(parser.read_events())
        return len([event for event, elem in events if event == "start"]) < 3

    def get_path_from_zip(self, zf, a_path):
        """Return full path in zip of this file name."""
        fn = os.path.basename(a_path).split("|")[0]
        for name in zf.namelist():
            if name.endswith(fn):
                return name
        raise KeyError("There is no item named '{}' in the archive".format(fn))

    def get_gml_from_zip(self, gml_path, zip_path, group, layername):
        """Return gml layer from zip if exists and is valid or none."""
        try:
            zf = zipfile.ZipFile(zip_path)
            gml_fp = self.get_path_from_zip(zf, gml_path)
            vsizip_path = "/".join(("/vsizip", zip_path, gml_fp)).replace("\\", "/")
            if group == "AD":
                vsizip_path += "|layername=" + layername
            gml = geo.BaseLayer(vsizip_path, layername + ".gml", "ogr")
            if not gml.isValid():
                gml = None
        except IOError:
            gml = None
        return gml

    def download(self, layername):
        """
        Download the file for a Cadastre layername.

        Args:
            layername (str): Short name of the Cadastre layer. Any of
                'building', 'cadastralzoning', 'address'
        """
        (md_path, gml_path, zip_path, group) = self.get_layer_paths(layername)
        url = config.prov_url[group].format(code=self.prov_code)
        self.get_atom_file(url)

    def read(self, layername, allow_empty=False, force_zip=False):
        """
        Create a QGIS vector layer for a Cadastre layername.

        Derive the GML filename from layername. Downloads the file if not is
        present. First try to read the ZIP file, if fails try with the GML file.

        Args:
            layername (str): Short name of the Cadastre layer. Any of
                'building', 'buildingpart', 'otherconstruction',
                'cadastralparcel', 'cadastralzoning', 'address',
                'thoroughfarename', 'postaldescriptor', 'adminunitname'
            allow_empty (bool): If False (default), raise a exception for empty
                layer, else returns None
            force_zip (bool): Force to use ZIP file.

        Returns:
            QgsVectorLayer: Vector layer.
        """
        (md_path, gml_path, zip_path, group) = self.get_layer_paths(layername)
        url = config.prov_url[group].format(code=self.prov_code)
        if not os.path.exists(zip_path) and (not os.path.exists(gml_path) or force_zip):
            self.get_atom_file(url)
        self.get_metadata(md_path, zip_path)
        if self.is_empty(gml_path, zip_path):
            if not allow_empty:
                raise CatIOError(_("The layer '%s' is empty") % gml_path)
            else:
                log.info(_("The layer '%s' is empty"), gml_path)
                return None
        gml = self.get_gml_from_zip(gml_path, zip_path, group, layername)
        if gml is None:
            gml = geo.BaseLayer(gml_path, layername + ".gml", "ogr")
            if not gml.isValid():
                raise CatIOError(_("Failed to load layer '%s'") % gml_path)
        crs = QgsCoordinateReferenceSystem.fromEpsgId(self.crs_ref)
        if not crs.isValid():
            raise CatIOError(_("Could not determine the CRS of '%s'") % gml_path)
        gml.setCrs(crs)
        log.info(_("Read %d features in '%s'"), gml.featureCount(), gml_path)
        gml.source_date = self.src_date
        return gml
