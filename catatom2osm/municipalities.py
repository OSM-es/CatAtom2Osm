"""Create a municipalities.csv from Catastre Addresses (AD) and IGN Admin Units (AU) data."""
import csv
import logging
import os
import re
import requests
import zipfile
from lxml import etree
from fuzzywuzzy import fuzz, process
from catatom2osm import config

config.setup_logger('municipalities')
log = logging.getLogger('municipalities')
config.set_log_level(log, logging.DEBUG)

HOME_DIR = os.path.dirname(__file__)

# AD Atom URL: https://www.catastro.hacienda.gob.es/INSPIRE/Addresses/ES.SDGC.AD.atom.xml'
CAT_AD_ATOM_URL = config.serv_url['AD']
IGN_AU_ATOM_URL = 'https://www.ign.es/atom/dataset_feeds/lin_lim_mun.es.xml'

# For later...
SPECIAL_URLS = [
    'https://apli.bizkaia.eus/apps/Danok/INSPIRE/addresses.xml',
    'https://b5m.gipuzkoa.eus/inspire/download/addresses.xml',
    'https://filescartografia.navarra.es/2_CARTOGRAFIA_TEMATICA/2_7_CATASTRO/2_7_3_INSPIRE_ATOM/2_7_3_3_AD/Addresses_ServiceATOM_Navarra.xml']
CAT_AD_CSV = f'{HOME_DIR}/municipalities-cat-ad.csv'
IGN_AU_CSV = f'{HOME_DIR}/municipalities-ign-au.csv'
MUN_CSV = f'{HOME_DIR}/municipalities.csv'
MUN_OLD_CSV = f'{HOME_DIR}/municipalities-old.csv'
IGN_AU_GML_ZIP = f'{HOME_DIR}/lineas_limite_gml.zip'
IGN_AU4_GML_FILE = 'au_AdministrativeUnit_4thOrder0.gml'
MISSING_AU = [['55', '55101', 'Ceuta'], ['56', '56101', 'Melilla']]

# For fuzzywuzzy fuzzy matching
MATCH_THR = 60

def normalize(text):
    return re.sub(r" *\(.*\)", "", (text or "").lower().strip())


def clean(text):
    """
    Clean excess spaces and begin+end whitespace.
    :param text:
    :return:
    """
    return re.sub(' +', ' ', text).lstrip().rstrip()


def match(name, choices):
    """
    Fuzzy search best match for string name in iterable choices like (IGN AU) municipality names.

    If the result is not good enough returns the original name.

    Args:
        name (str): String to look for
        choices (list): Iterable with choices
    """
    if fuzz and name:
        normalized = [normalize(c) for c in choices]
        try:
            matching = process.extractOne(
                normalize(name), normalized, scorer=fuzz.token_sort_ratio
            )
            if matching and matching[1] > MATCH_THR:
                return choices[normalized.index(matching[0])]
        except RuntimeError:
            pass
    # No match: return original
    return name


def create_ign_au_dict():
    """
    Create a dict of provinces (keys) with municipalities.

    Each value is a list/array of municipality names to prepare for matching
    as only matching for a municipality within a province is needed.
    """
    ign_au_dict = {}
    with open(IGN_AU_CSV) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=config.delimiter)
        for row in csv_reader:
            if len(row) < 1:
                raise Exception(f'Incomplete IGN_AU_CSV row {row}')
            prov = row[0]
            if prov not in ign_au_dict:
                # Start new Province
                ign_au_dict[prov] = []
            # Append the municipality name
            ign_au_dict[prov].append(row[2])
    return ign_au_dict


def generate_mun_csv(path):
    """
    Generate the final CSV of municipalities.
    """

    log.info(f'generate_mun_csv: START create_ign_au_dict...')
    ign_au_dict = create_ign_au_dict()

    # Create a dict of dict with lists for the Catastre municipalities.
    # Each main entry is a Province code. Values are municipality codes.
    # Each municipality code entry has as value its list of municipality names.
    # This is to facilitate iterating and matching with IGN AU municipality names.
    cat_ad_dict = {}
    with open(CAT_AD_CSV) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=config.delimiter)
        for row in csv_reader:
            if len(row) < 1:
                raise Exception(f'Incomplete CAT_AD_CSV row {row}')
            prov_num = row[0]
            if prov_num not in cat_ad_dict:
                cat_ad_dict[prov_num] = {}
            cat_mun_num = row[1]
            if cat_mun_num not in cat_ad_dict[prov_num]:
                # Start list for municipality names for Province
                cat_ad_dict[prov_num][cat_mun_num] = []

            # Append the municipality CAT-name
            cat_ad_dict[prov_num][cat_mun_num].append(row[2])

    # Collect the old version for the second column to preserve...
    mun_old_dict = {}
    with open(MUN_OLD_CSV) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=config.delimiter)
        for row in csv_reader:
            mun_old_dict[row[0]] = row[1]

    # Go through each of the Provinces and match all CAT with IGN AU municipalities.
    dest_csv = MUN_CSV
    if path is not None:
        dest_csv = path
        if type(path) == list:
            dest_csv = path[0]

    log.info(f'generate_mun_csv: write to {dest_csv}...')
    with open(dest_csv, 'wb') as f:
        for prov_num in cat_ad_dict:
            cat_muns = cat_ad_dict[prov_num]
            for cat_mun_code in cat_muns:
                for cat_mun_name in cat_muns[cat_mun_code]:
                    cat_mun_name = clean(cat_mun_name)
                    cat_mun_code = clean(cat_mun_code)
                    mun_name = clean(match(cat_mun_name, ign_au_dict[prov_num]))

                    # Try to get the original col2 number to keep new CSV largely same
                    mun_old_col2 = mun_old_dict.get(cat_mun_code, '123456')
                    f.write(f'{cat_mun_code}{config.delimiter}{mun_old_col2}{config.delimiter}{mun_name}\n'.encode('utf-8'))

    log.info(f'generate_mun_csv: DONE')


def create_ign_au_csv():
    """
    Generate a CSV of IGN Administrative Units (AU) municipalities.

    Each row contains: province code, municipality code, municipality name.
    """

    log.info(f'create_ign_au_csv: START get {IGN_AU_ATOM_URL}...')
    xml = requests.get(IGN_AU_ATOM_URL)
    root = etree.fromstring(xml.text.encode('utf-8'))

    au_gml_url = root.xpath('/atom:feed/atom:entry/atom:link', namespaces={'atom': 'http://www.w3.org/2005/Atom'})[0].attrib['href']
    log.info(f'create_ign_au_csv: get {au_gml_url}...')
    headers = {'user-agent': 'Wget/1.25.0'}
    au_gml_zip = requests.get(au_gml_url, headers=headers)

    log.info(f'create_ign_au_csv: process zip from {IGN_AU_GML_ZIP}...')
    with open(IGN_AU_GML_ZIP, 'wb') as f:
        f.write(au_gml_zip.content)
    zip_file = zipfile.ZipFile(IGN_AU_GML_ZIP, "r")
    gml = zip_file.read(IGN_AU4_GML_FILE)

    if os.path.exists(IGN_AU_GML_ZIP):
        os.remove(IGN_AU_GML_ZIP)

    root = etree.fromstring(gml)
    mun_id_elms = root.xpath('//au:nationalCode', namespaces={'au': 'http://inspire.ec.europa.eu/schemas/au/4.0'})
    mun_name_elms = root.xpath('//gn:text', namespaces={'gn': 'http://inspire.ec.europa.eu/schemas/gn/4.0'})
    elms = [list(x) for x in zip(mun_id_elms, mun_name_elms)]
    elms.sort(key=lambda x: x[0].text[-5:])
    log.info(f'create_ign_au_csv: got through municipalities in {IGN_AU4_GML_FILE}...')
    with open(IGN_AU_CSV, 'wb') as f:
        for elm in elms:
            mun_num = elm[0].text[-5:]
            prov_num = mun_num[:2]
            mun_name = elm[1].text
            f.write(f'{prov_num}{config.delimiter}{mun_num}{config.delimiter}{mun_name}\n'.encode('utf-8'))

        # Append missing Provs in AU (Ceuta+Melilla)
        for missing in MISSING_AU:
            f.write(f'{missing[0]}{config.delimiter}{missing[1]}{config.delimiter}{missing[2]}\n'.encode('utf-8'))

    log.info(f'create_ign_au_csv: created {IGN_AU_CSV} - DONE')


def create_cat_ad_csv():
    """
    Generate a CSV of Catastre municipalities from INSPIRE AD Atom.

    Each row contains: province code, municipality code, municipality name.
    """

    log.info(f'create_cat_ad_csv: START get {CAT_AD_ATOM_URL}...')
    xml = requests.get(CAT_AD_ATOM_URL)
    root = etree.fromstring(xml.text.encode('utf-8'))

    # Get the embedded download links per province
    prov_url_elms = root.xpath('/atom:feed//atom:entry/atom:link', namespaces={'atom': 'http://www.w3.org/2005/Atom'})
    log.info(f'create_cat_ad_csv: go through provinces...')
    with open(CAT_AD_CSV, 'wb') as f:
        for prov_url_elm in prov_url_elms:
            prov_url = prov_url_elm.attrib['href']

            # Skip irregular URLs for now...
            if prov_url not in SPECIAL_URLS:
                xml = requests.get(prov_url)
                root = etree.fromstring(xml.text.encode('utf8'))
                mun_url_elms = sorted(root.xpath('/atom:feed//atom:entry/atom:title', namespaces={'atom': 'http://www.w3.org/2005/Atom'}), key=lambda mun: mun.text)
                # sorted(student_tuples, key=lambda student: student[2])
                for mun_url_elm in mun_url_elms:
                    mun_entry = mun_url_elm.text
                    mun_entry = mun_entry[:-len(' addresses')] + '\n'
                    mun_entry = mun_entry.split('-')
                    prov_num = mun_entry[0].strip(' ')[:2]
                    f.write(f'{prov_num}{config.delimiter}{mun_entry[0]}{config.delimiter}{mun_entry[1]}'.encode('ISO-8859-1'))

    log.info(f'create_cat_ad_csv: DONE')


def generate_municipalities(path=None):
    create_cat_ad_csv()
    create_ign_au_csv()
    generate_mun_csv(path)


if __name__ == "__main__":
    generate_municipalities()
