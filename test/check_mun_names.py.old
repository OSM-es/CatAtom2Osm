# -*- coding: utf-8 -*-
"""Check municipality name resolution. Put fails in setup.mun_fails"""
import codecs
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.abspath('.'))
import main
import hgwnames
import download
import overpass
import setup
from osmxml import etree

baseurl = "http://www.catastro.minhap.es/INSPIRE/Buildings/"
fh = codecs.open('check_mun_names.csv', 'w', 'utf-8')
ns = {
    'atom': 'http://www.w3.org/2005/Atom', 
    'georss': 'http://www.georss.org/georss',
    'gco': 'http://www.isotc211.org/2005/gco', 
    'gmd': 'http://www.isotc211.org/2005/gmd'
}
trans = dict(zip([ord(c) for c in u"ÁÉÍÓÚÑÀÈÌÒÙÄËÏÖÜ-/'·.,Ç"], u'AEIOUNAEIOUAEIOU       '))

def run():
    for prov_code in setup.valid_provinces:
        url = setup.prov_url['BU'].format(code=prov_code)
        response = download.get_response(url)
        root = etree.fromstring(response.content)
        for entry in root.findall("atom:entry[atom:title]", namespaces=ns):
            title = entry.find('atom:title', ns).text
            zip_code = title[1:6]
            mun = title.replace('buildings', '').strip()[6:]
            url = u"{0}{1}/{2}-{3}/A.ES.SDGC.BU.{2}.zip".format(baseurl, prov_code, zip_code, mun)
            download.wget(url, 'temp')
            zf = zipfile.ZipFile('temp')
            root = etree.parse(zf.open('A.ES.SDGC.BU.MD.{}.xml'.format(zip_code))).getroot()
            gml_bbox = root.find('.//gmd:EX_GeographicBoundingBox', ns)
            gml_bbox_l = gml_bbox.find('gmd:westBoundLongitude/gco:Decimal', ns)
            gml_bbox_r = gml_bbox.find('gmd:eastBoundLongitude/gco:Decimal', ns)
            gml_bbox_b = gml_bbox.find('gmd:southBoundLatitude/gco:Decimal', ns)
            gml_bbox_t = gml_bbox.find('gmd:northBoundLatitude/gco:Decimal', ns)
            bbox = ','.join([gml_bbox_b.text, gml_bbox_l.text, gml_bbox_t.text,
                    gml_bbox_r.text])
            query = overpass.Query(bbox, 'json', False, False)
            query.add('rel["admin_level"="8"]')
            response = download.get_response(query.get_url())
            sys.stdout.write(' '*70+'\r')
            data = response.json()
            matching = hgwnames.dsmatch(mun, data['elements'], lambda e: e['tags']['name'])
            match =  matching['tags']['name'] if matching else ''
            ok = mun == match.upper().translate(trans)
            color = {False: '\033[0;31m', True: '\033[0m'}[ok]
            print u'{}{}\t{}\t{}\t{}'.format(color, zip_code, mun, match, ok)
            fh.write(u'{}\t{}\t{}\t{}\n'.format(zip_code, mun, match, ok))
    print '\033[0m'
    if os.path.exists('temp'):
        os.remove('temp')

if __name__ == "__main__":
    run()
