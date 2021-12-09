# -*- coding: utf-8 -*-
"""Count number of features in all building dataset"""
import codecs
import os
import sys

sys.path.insert(0, os.path.abspath('.'))
import catatom2osm
import download
import layer
import setup
from osmxml import etree

baseurl = "http://www.catastro.minhap.es/INSPIRE/Buildings/"
fh = codecs.open('count_buildings.csv', 'w', 'utf-8') 
ns = {
    'atom': 'http://www.w3.org/2005/Atom', 
    'georss': 'http://www.georss.org/georss',
    'gco': 'http://www.isotc211.org/2005/gco', 
    'gmd': 'http://www.isotc211.org/2005/gmd'
}

def run():
    qgs = catatom2osm.QgsSingleton()
    for prov_code in setup.valid_provinces:
        url = setup.prov_url['BU'].format(code=prov_code)
        response = download.get_response(url)
        root = etree.fromstring(response.content)
        for entry in root.findall("atom:entry[atom:title]", namespaces=ns):
            title = entry.find('atom:title', ns).text
            zip_code = title[1:6]
            mun = title.replace('buildings', '').strip()[6:]
            url = u"{0}{1}/{2}-{3}/A.ES.SDGC.BU.{2}.zip".format(baseurl, prov_code, zip_code, mun)
            gml_fn = ".".join((setup.fn_prefix, 'BU', zip_code, 'building.gml'))
            download.wget(url, 'temp.zip')
            gml = layer.BaseLayer('/vsizip/temp.zip/'+gml_fn, 'temp', 'ogr')
            sys.stdout.write(' '*70+'\r')
            c = gml.featureCount()
            print zip_code, mun, c
            fh.write(u'{}\t{}\t{}\n'.format(zip_code, mun, c))
    if os.path.exists('temp'):
        os.remove('temp')

if __name__ == "__main__":
    run()
