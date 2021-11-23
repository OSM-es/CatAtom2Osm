"""Reader of Cadastre ATOM GML files"""
from __future__ import print_function, unicode_literals
from builtins import next, object, str
import json
import logging
import os
import re
import zipfile
from requests.exceptions import ConnectionError

import download
import hgwnames
import layer
import overpass
import setup
from compat import etree
from qgiscompat import QgsCoordinateReferenceSystem_fromEpsgId
from report import instance as report
log = setup.log


class Reader(object):
    """Class to download and read Cadastre ATOM GML files"""

    def __init__(self, a_path):
        """
        Args:
            a_path (str): Directory where the source files are located.
        """
        self.path = a_path
        m = re.match(r"^\d{5}$", os.path.split(a_path)[-1])
        if not m:
            raise ValueError(_("Last directory name must be a 5 digits ZIP code"))
        self.zip_code = m.group()
        self.prov_code = self.zip_code[0:2]
        if self.prov_code not in setup.valid_provinces:
            msg = _("Province code '%s' not valid") % self.prov_code
            raise ValueError(msg)
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            raise IOError(_("Not a directory: '%s'") % a_path)

    def get_metadata(self, md_path, zip_path=""):
        """Get the metadata of the source file"""
        if os.path.exists(md_path):
            with open(md_path, 'rb') as f:
                text = f.read()
        else:
            try:
                zf = zipfile.ZipFile(zip_path)
                text = zf.read(self.get_path_from_zip(zf, md_path))
            except IOError:
                raise IOError(_("Could not read metadata from '%s'") % md_path)
        root = etree.fromstring(text)
        is_empty = len(root) == 0 or len(root[0]) == 0
        namespace = {
            'gco': 'http://www.isotc211.org/2005/gco', 
            'gmd': 'http://www.isotc211.org/2005/gmd'
        }
        if hasattr(root, 'nsmap'):
            namespace = root.nsmap
        src_date = root.find('gmd:dateStamp/gco:Date', namespace)
        if is_empty or src_date == None:
            raise IOError(_("Could not read metadata from '%s'") % md_path)
        self.src_date = src_date.text
        gml_title = root.find('.//gmd:title/gco:CharacterString', namespace)
        self.cat_mun = gml_title.text.split('-')[-1].split('(')[0].strip()
        gml_code = root.find('.//gmd:code/gco:CharacterString', namespace)
        self.crs_ref = int(gml_code.text.split('/')[-1])

    def get_atom_file(self, url):
        """
        Given the url of a Cadastre ATOM service, tries to download the ZIP
        file for self.zip_code
        """
        s = re.search(r'INSPIRE/(\w+)/', url)
        log.debug(_("Searching the url for the '%s' layer of '%s'..."), 
            s.group(1), self.zip_code)
        response = download.get_response(url)
        s = re.search(r'http.+/%s.+zip' % self.zip_code, response.text)
        if not s:
            raise ValueError(_("Zip code '%s' don't exists") % self.zip_code)
        url = s.group(0)
        filename = url.split('/')[-1]
        out_path = os.path.join(self.path, filename)
        log.info(_("Downloading '%s'"), out_path)
        download.wget(url, out_path)

    def get_layer_paths(self, layername):
        if layername in ['building', 'buildingpart', 'otherconstruction']:
            group = 'BU'
        elif layername in ['cadastralparcel', 'cadastralzoning']:
            group = 'CP'
        elif layername in ['address', 'thoroughfarename', 'postaldescriptor', 
                'adminunitname']:
            group = 'AD' 
        else:
            raise ValueError(_("Unknow layer name '%s'") % layername)
        gml_fn = ".".join((setup.fn_prefix, group, self.zip_code, layername, "gml"))
        if group == 'AD':
            gml_fn = ".".join((setup.fn_prefix, group, self.zip_code, "gml"))
        md_fn = ".".join((setup.fn_prefix, group, "MD", self.zip_code, "xml"))
        if group == 'CP':
            md_fn = ".".join((setup.fn_prefix, group, "MD.", self.zip_code, "xml"))
        zip_fn = ".".join((setup.fn_prefix, group, self.zip_code, "zip"))
        md_path = os.path.join(self.path, md_fn)
        gml_path = os.path.join(self.path, gml_fn)
        zip_path = os.path.join(self.path, zip_fn)
        return (md_path, gml_path, zip_path, group)

    def is_empty(self, gml_path, zip_path):
        """Detects if the file is empty. Cadastre empty files (usually 
        otherconstruction) comes with a null feature and results in a non valid
        layer in QGIS"""
        if os.path.exists(zip_path):
            zf = zipfile.ZipFile(zip_path)
            gml_fp = self.get_path_from_zip(zf, gml_path)
            f = zf.open(gml_fp, 'r')
        else:
            f = open(gml_path, 'rb')
        context = etree.iterparse(f, events=('end',))
        try:
            event, elem = next(context) # </something>
            event, elem = next(context) # </featureMember>
            event, elem = next(context) # </featureCollection>
            f.close()
            return False
        except StopIteration:
            f.close()
            return True

    def get_path_from_zip(self, zf, a_path):
        """Return full path in zip of this file name"""
        fn = os.path.basename(a_path).split('|')[0]
        for name in zf.namelist():
            if name.endswith(fn):
                return name
        raise(KeyError("There is no item named '{}' in the archive".format(fn)))

    def get_gml_from_zip(self, gml_path, zip_path, group, layername):
        """Return gml layer from zip if exists and is valid or none"""
        try:
            zf = zipfile.ZipFile(zip_path)
            gml_fp = self.get_path_from_zip(zf, gml_path)
            vsizip_path = "/".join(('/vsizip', zip_path, gml_fp)).replace('\\', '/')
            if group == 'AD':
                vsizip_path += "|layername=" + layername
            gml = layer.BaseLayer(vsizip_path, layername+'.gml', 'ogr')
            if not gml.isValid():
                gml = None
        except IOError:
            gml = None
        return gml

    def download(self, layername):
        """
        Downloads the file for a a Cadastre layername.

        Args:
            layername (str): Short name of the Cadastre layer. Any of 
                'building', 'cadastralzoning', 'address'
        """
        (md_path, gml_path, zip_path, group) = self.get_layer_paths(layername)
        url = setup.prov_url[group].format(code=self.prov_code)
        self.get_atom_file(url)

    def read(self, layername, allow_empty=False, force_zip=False):
        """
        Create a QGIS vector layer for a Cadastre layername. Derives the GML 
        filename from layername. Downloads the file if not is present. First try
        to read the ZIP file, if fails try with the GML file.

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
        url = setup.prov_url[group].format(code=self.prov_code)
        if not os.path.exists(zip_path) and (not os.path.exists(gml_path) or force_zip):
            self.get_atom_file(url)
        self.get_metadata(md_path, zip_path)
        if self.is_empty(gml_path, zip_path):
            if not allow_empty:
                raise IOError(_("The layer '%s' is empty") % gml_path)
            else:
                log.info(_("The layer '%s' is empty"), gml_path)
                return None
        gml = self.get_gml_from_zip(gml_path, zip_path, group, layername)
        if gml is None:
            gml = layer.BaseLayer(gml_path, layername+'.gml', 'ogr')
            if not gml.isValid():
                raise IOError(_("Failed to load layer '%s'") % gml_path)
        crs = QgsCoordinateReferenceSystem_fromEpsgId(self.crs_ref)
        if not crs.isValid():
            raise IOError(_("Could not determine the CRS of '%s'") % gml_path)
        gml.setCrs(crs)
        log.info(_("Read %d features in '%s'"), gml.featureCount(), gml_path)
        gml.source_date = self.src_date
        return gml

    def get_boundary(self, zoning):
        """
        Gets the id of the OSM administrative boundary from Overpass.
        If it fails falls back to the bounding box.
        Precondition: called after read any gml (metadata adquired)
        """
        self.boundary_bbox = zoning.bounding_box()
        if self.zip_code in setup.mun_fails:
            self.boundary_name = setup.mun_fails[self.zip_code][0]
            self.boundary_search_area = setup.mun_fails[self.zip_code][1]
            query = overpass.Query(self.boundary_bbox, 'json', False, False)
            query.add('rel({})'.format(self.boundary_search_area))
        else:
            query = overpass.Query(self.boundary_bbox, 'json', False, False)
            query.add('rel["admin_level"="8"]')
        matching = False
        try:
            data = json.loads(query.read())
            matching = hgwnames.dsmatch(self.cat_mun, data['elements'], 
                lambda e: e['tags']['name'])
        except ConnectionError:
            pass
        if matching:
            self.boundary_search_area = str(matching['id'])
            self.boundary_name = matching['tags']['name']
            self.boundary_data = matching['tags']
            log.info(_("Municipality: '%s'"), self.boundary_name)
        else:
            self.boundary_search_area = self.boundary_bbox
            msg = _("Failed to find administrative boundary, falling "
                "back to bounding box")
            log.warning(msg)
            report.warnings.append(msg)

def list_municipalities(prov_code):
    """Get from the ATOM services a list of municipalities for a given province"""
    if prov_code == '99':
        url = setup.serv_url['BU']
        title = _("Territorial office")
    elif prov_code not in setup.valid_provinces:
        raise ValueError(_("Province code '%s' not valid") % prov_code)
    else:
        url = setup.prov_url['BU'].format(code=prov_code)
    response = download.get_response(url)
    root = etree.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    if prov_code != '99':
        office = root.find('atom:title', ns).text.split('Office ')[1]
        title = _("Territorial office %s") % office
    print(title)
    print("=" * len(title))
    for entry in root.findall('atom:entry', namespaces=ns):
        row = entry.find('atom:title', ns).text.replace('buildings', '')
        row = row.replace('Territorial office ', '')
        print(row)

