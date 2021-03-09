# -*- coding: utf-8 -*-
"""Reader of CDAU CSV files"""
from __future__ import unicode_literals
from builtins import object, range, str

import logging
import locale
import os
import re
from collections import defaultdict
from datetime import datetime

from qgis.core import *

import compat
import download
import layer
import setup
from report import instance as report
log = setup.log
compat.set_es_time()


andalucia = {'04': 'Almeria', '11': 'Cadiz', '14': 'Cordova', '18': 'Granada',
    '21': 'Huelva', '23': 'Jaen', '29': 'Malaga', '41': 'Sevilla'}

cdau_url = 'http://www.juntadeandalucia.es/institutodeestadisticaycartografia/cdau/portales/{}'
csv_name = 'portal_{}.csv'
meta_url = 'https://www.callejerodeandalucia.es/portal/informaci%C3%B3n-alfanum%C3%A9rica'
cdau_crs = 25830
cdau_thr = 5 # Threhold in meters to conflate Cadastre addresses
cod_mun_trans = {
    '04': {40: 901, 104: 902, 105: 903, 900: 13},
    '11': {43: 901, 44: 902, 900: 12},
    '14': {900: 21},
    '18': {20: 911, 53: 908, 59: 907, 63: 119, 83: 905, 92: 906, 105: 910, 106: 103, 120: 903, 130: 904, 132: 902, 141: 909, 163: 901, 199: 912, 200: 913, 900: 87},
    '21': {79: 60, 900: 41},
    '23': {13: 902, 23: 901, 78: 904, 100: 903, 102: 905, 900: 50},
    '29': {102: 902, 103: 901, 900: 67},
    '41': {103: 901, 104: 902, 105: 903, 900: 91}
}

highway_types_equiv = {
    'ACCESO': 'AC', 'ALAMEDA': 'AL', 'ARROYO': 'AY', 'AUTOPISTA': 'AU',
    'AUTOVIA': 'AU', 'AVENIDA': 'AV', 'BARRIO': 'BO', 'BAJADA': 'BJ',
    'BARRANCO': 'BR', 'BULEVAR': 'BV', 'CALLE': 'CL', 'CAÑADA': 'CA',
    'CASERIO': 'CS', 'CALZADA': 'CZ', 'CINTURON': 'CI', 'CONCEJO, COLEGIO': 'CO',
    'DISEMINADO': 'DS', 'EXPLANADA': 'EX', 'EXTRAMUROS': 'EM', 'EXTRARRADIO': 'ER',
    'GRAN VIA': 'GV', 'GRUPO': 'GR',  'GLORIETA': 'GL', 'HUERTA, HUERTO': 'HT',
    'JARDINES': 'JR', 'LUGAR': 'LG', 'MONTE': 'MT', 'MUELLE': 'ML', 'PASEO': 'PS',
    'POBLADO': 'PB', 'PLAZA': 'PZ', 'PUENTE': 'PT', 'POLIGONO': 'PL',
    'RAMAL': 'RM', 'RAMBLA': 'RB', 'RONDA': 'RD', 'SUBIDA': 'SU', 'SECTOR': 'SC',
    'URBANIZACION': 'UR',
}


def cod_mun_cat2ine(cod_mun_cat):
    """Return the INE municipality code from the Cadastre code"""
    cod_prov = cod_mun_cat[0:2]
    cod_mun = int(cod_mun_cat[2:])
    if cod_prov == '18':
        if cod_mun in list(cod_mun_trans[cod_prov].keys()):
            cod_mun = cod_mun_trans[cod_prov][cod_mun]
        else:
            if cod_mun in range(64, 120) or cod_mun in range(137, 143):
                cod_mun -= 2
            elif cod_mun in range(144, 184):
                cod_mun -= 3
            elif cod_mun in range(185, 199):
                cod_mun -= 4
            else:
                cod_mun -= 1
    elif cod_prov == '21':
        cod_mun = cod_mun_trans[cod_prov].get(cod_mun, cod_mun + 1 if cod_mun > 59 else cod_mun)
    else: 
        cod_mun = cod_mun_trans[cod_prov].get(cod_mun, cod_mun)
    cod_mun_ine = '{}{:03d}'.format(cod_prov, cod_mun)
    return cod_mun_ine

def get_cat_address(ad, cod_mun_cat):
    """Convert CDAU address to Cadastre attributes"""
    attr = {}
    attr['localId'] = '{}.{}.{}.{}'.format(cod_mun_cat[:2], cod_mun_cat[2:], 
        ad['dgc_via'], ad['refcatparc'])
    nom_tip_via = highway_types_equiv.get(ad['nom_tip_via'], ad['nom_tip_via'])
    attr['TN_text'] = "{} {}".format(str(nom_tip_via), str(ad['nom_via']))
    attr['postCode'] = ad['cod_postal']
    attr['spec'] = 'Entrance'
    to = '{}{}'.format(ad['num_por_hasta'] or '', ad['ext_hasta'] or '')
    attr['designator'] = '{}{}'.format(ad['num_por_desde'] or '', ad['ext_desde'] or '')
    if to:
        attr['designator'] += '-' + to
    return attr


class Reader(object):
    """Class to download and read CDAU CSV files"""

    def __init__(self, a_path):
        """
        Args:
            a_path (str): Directory where the source files are located.
        """
        self.path = a_path
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            raise IOError(_("Not a directory: '%s'") % a_path)
        self.crs_ref = cdau_crs
        self.src_date = None

    def get_metadata(self, md_path):
        if os.path.exists(md_path):
            with open(md_path, 'r') as fo:
                self.src_date = fo.read()
        else:
            response = download.get_response(meta_url)
            s = re.search(r'fecha de referencia.*([0-9]{1,2} de .+ de [0-9]{4})', response.text)
            try:
                self.src_date = datetime.strptime(s.group(1), '%d de %B de %Y').strftime('%Y-%m-%d')
            except:
                raise IOError(_("Could not read metadata from '%s'") % 'CDAU')
            with open(md_path, 'w') as fo:
                fo.write(self.src_date)

    def read(self, prov_code):
        if prov_code not in list(andalucia.keys()):
            raise ValueError(_("Province code '%s' not valid") % prov_code)
        csv_fn = csv_name.format(andalucia[prov_code])
        csv_path = os.path.join(self.path, csv_fn)
        url = cdau_url.format(csv_fn)
        if not os.path.exists(csv_path):
            log.info(_("Downloading '%s'"), csv_path)
            download.wget(url, csv_path)
        csv = layer.BaseLayer(csv_path, csv_fn, 'ogr')
        if not csv.isValid():
            raise IOError(_("Failed to load layer '%s'") % csv_path)
        csv.setCrs(QgsCoordinateReferenceSystem(cdau_crs))
        log.info(_("Read %d features in '%s'"), csv.featureCount(), csv_path)
        self.get_metadata(csv_path.replace('.csv', '.txt'))
        csv.source_date = self.src_date
        return csv


def conflate(cdau_address, cat_address, cod_mun_cat):
    """Conflate CDAU over Cadastre addresses datasets"""
    cod_mun = cod_mun_cat2ine(cod_mun_cat)
    q = "ine_mun='{}' and (tipo_portal_pk='{}' or tipo_portal_pk='{}')"
    exp = q.format(cod_mun, 'PORTAL', 'ACCESORIO')
    c = 0
    addresses = defaultdict(list)
    index = cat_address.get_index()
    to_add = []
    to_change = {}
    to_change_g = {}
    for feat in cat_address.getFeatures():
        g = feat['localId'].split('.')
        ref = '.'.join(g[:3] + g[4:])
        addresses[ref].append(feat)
    for ad in cdau_address.search(exp):
        c += 1
        attr = get_cat_address(ad, cod_mun_cat)
        ref = attr['localId']
        pt = layer.Point(float(ad['x']), float(ad['y']))
        if len(addresses[ref]) == 0: # can't resolve cadastral reference
            area_of_candidates = layer.Point(pt).boundingBox(cdau_thr)
            fids = index.intersects(area_of_candidates)
            if len(fids) == 0: # no close cadastre address
                feat = QgsFeature(cat_address.fields())
                for key, value in list(attr.items()):
                    feat[key] = value
                feat.setGeometry(layer.Geometry.fromPointXY(pt))
                to_add.append(feat) # add new
        else: # get nearest
            min_dist = 100
            candidate = None
            for feat in addresses[ref]:
                dist = feat.geometry().asPoint().sqrDist(pt)
                if dist < min_dist:
                   min_dist = dist
                   candidate = feat
            if candidate is not None: # update existing
                to_change_g[candidate.id()] = layer.Geometry.fromPointXY(pt)
                for key, value in list(attr.items()):
                    candidate[key] = value
                to_change[candidate.id()] = layer.get_attributes(candidate)
    log.info(_("Parsed %d addresses from '%s'"), c, 'CDAU')
    report.inp_address_cdau = c
    if to_change:
        cat_address.writer.changeAttributeValues(to_change)
        cat_address.writer.changeGeometryValues(to_change_g)
        log.info(_("Replaced %d addresses from '%s'"), len(to_change), 'CDAU')
        report.rep_address_cdau = len(to_change)
        cat_address.source_date = cdau_address.source_date
        report.address_date = cdau_address.source_date
    if to_add:
        cat_address.writer.addFeatures(to_add)
        log.info(_("Added %d addresses from '%s'"), len(to_add), 'CDAU')
        report.add_address_cdau = len(to_add)
        report.inp_address += len(to_add)
        report.inp_address_entrance += len(to_add)
        cat_address.source_date = cdau_address.source_date
        report.address_date = cdau_address.source_date

