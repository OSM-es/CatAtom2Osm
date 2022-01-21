"""Application preferences"""
import gettext
import locale
import logging
import os
import sys

from catatom2osm import __version__

app_name = 'CatAtom2Osm'
app_version = __version__
app_author = 'Javier Sanchez Portero'
app_copyright = '2017, Javier Sanchez Portero'
app_desc = 'Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files'
app_tags = ''

MIN_QGIS_VERSION_INT = 21001
MIN_QGIS_VERSION = '2.10.1'
MIN_GDAL_VERSION_INT = 11103
MIN_GDAL_VERSION = '1.11.3'

def install_gettext(app_name, localedir):
    try:
        gettext.install(app_name.lower(), localedir=localedir, unicode=1)
    except TypeError:
        gettext.install(app_name.lower(), localedir=localedir)
    gettext.bindtextdomain('argparse', localedir)
    gettext.textdomain('argparse')

language, encoding = locale.getdefaultlocale()
language = language or 'es_ES'
encoding = encoding or 'UTF-8'
app_path = os.path.dirname(__file__)
localedir = os.path.join(os.path.dirname(app_path), 'locale', 'po')
platform = sys.platform
eol = '\n'

install_gettext(app_name, localedir)

log_level = 'INFO' # Default log level
log_file = 'catatom2osm.log'
log_format = '%(asctime)s - %(levelname)s - %(message)s'
log = logging.getLogger(app_name)
fh = logging.FileHandler(log_file)
ch = logging.StreamHandler(sys.stderr)
fh.setLevel(logging.DEBUG)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(log_format)
ch.setFormatter(formatter)
fh.setFormatter(formatter)
log.addHandler(ch)
log.addHandler(fh)

fn_prefix = 'A.ES.SDGC' # Inspire Atom file name prefix

silence_gdal = False

delimiter = '\t'
dup_thr = 0.012 # Distance in meters to merge nearest vertexs.
                # 0.011 is about 1E-7 degrees in latitude
dist_thr = 0.02 # Threshold in meters for vertex simplification and topological points.
straight_thr = 2 # Threshold in degrees from straight angle to delete a vertex
acute_thr = 10 # Remove vertices with an angle smaller than this value
min_area = 0.05 # Delete geometries with an area smaller than this value
addr_thr = 10 # Distance in meters to merge address node with building outline
acute_inv = 5 # Remove geometries/rings that result invalid after removing any vertex with an angle smaller than this value
dist_inv = 0.1 # Threshold in meters to filter angles for zig-zag and spikes
entrance_thr = 0.4 # Minimum distance in meters from a entrance to the nearest corner
warning_min_area = 1 # Area in m2 for small area warning
warning_max_area = 30000 # Area in m2 for big area warning
bbox_buffer = 0.002 # Buffer in degrees around overpass bounding boxes

changeset_tags = {
    'comment': "#Spanish_Cadastre_Buildings_Import",
    'source': u"Dirección General del Catastro",
    'type': 'import',
    'url': "https://wiki.openstreetmap.org/wiki/Spanish_Cadastre/Buildings_Import",
    'generator':  app_name + ' ' + app_version
}

base_url = {
    "BU": "http://www.catastro.minhap.es/INSPIRE/buildings/",
    "AD": "http://www.catastro.minhap.es/INSPIRE/addresses/",
    "CP": "http://www.catastro.minhap.es/INSPIRE/CadastralParcels/"
}

serv_url = {
    "BU": base_url['BU'] + "ES.SDGC.BU.atom.xml",
    "AD": base_url['AD'] + "ES.SDGC.AD.atom.xml",
    "CP": base_url['CP'] + "ES.SDGC.CP.atom.xml"
}

prov_url = {
    "BU": base_url['BU'] + "{code}/ES.SDGC.bu.atom_{code}.xml",
    "AD": base_url['AD'] + "{code}/ES.SDGC.ad.atom_{code}.xml",
    "CP": base_url['CP'] + "{code}/ES.SDGC.CP.atom_{code}.xml"
}

cadastre_doc_url = 'http://ovc.catastro.meh.es/OVCServWeb/OVCWcfLibres/OVCFotoFachada.svc/RecuperarFotoFachadaGet?ReferenciaCatastral={}'

fixme_doc_url = 'https://wiki.openstreetmap.org/wiki/ES:Catastro_espa%C3%B1ol/Importaci%C3%B3n_de_edificios/Gesti%C3%B3n_de_proyectos#Generar_y_corregir_los_archivos_a_importar'

no_number = 'S-N' # Regular expression to match addresses without number

lowcase_words = [ # Words to exclude from the general Title Case rule for highway names
    'DE', 'DEL', 'EL', 'LA', 'LOS', 'LAS', 'Y', 'AL', 'EN',
    'A LA', 'A EL', 'A LOS', 'DE LA', 'DE EL', 'DE LOS', 'DE LAS',
    'ELS', 'LES', "L'", "D'", "N'", "S'", "NA", "DE NA", "SES", "DE SES",
    "D'EN", "D'EL", "D'ES", "DE'N", "DE'L", "DE'S"
]

highway_types_d = {
    'es_ES': { 
        'AG': 'Agregado',
        'AL': 'Aldea/Alameda',
        'AR': 'Área/Arrabal',
        'AU': 'Autopista',
        'AV': 'Avenida',
        'AY': 'Arroyo',
        'BJ': 'Bajada',
        'BO': 'Barrio',
        'BR': 'Barranco',
        'CA': 'Cañada',
        'CG': 'Colegio/Cigarral',
        'CH': 'Chalet',
        'CI': 'Cinturón',
        'CJ': 'Calleja/Callejón',
        'CL': 'Calle',
        'CM': 'Camino/Carmen',
        'CN': 'Colonia',
        'CO': 'Concejo/Colegio',
        'CP': 'Campa/Campo',
        'CR': 'Carretera/Carrera',
        'CS': 'Caserío',
        'CT': 'Cuesta/Costanilla',
        'CU': 'Conjunto',
        'CY': 'Caleya',
        'DE': 'Detrás',
        'DP': 'Diputación',
        'DS': 'Diseminados',
        'ED': 'Edificios',
        'EM': 'Extramuros',
        'EN': 'Entrada/Ensanche',
        'ER': 'Extrarradio',
        'ES': 'Escalinata',
        'EX': 'Explanada',
        'FC': 'Ferrocarril/Finca',
        'FN': 'Finca',
        'GL': 'Glorieta',
        'GR': 'Grupo',
        'GV': 'Gran Vía',
        'HT': 'Huerta/Huerto',
        'JR': 'Jardines',
        'LD': 'Lado/Ladera',
        'LG': 'Lugar',
        'MC': 'Mercado',
        'ML': 'Muelle',
        'MN': 'Município',
        'MS': 'Masías',
        'MT': 'Monte',
        'MZ': 'Manzana',
        'PB': 'Poblado',
        'PD': 'Partida',
        'PJ': 'Pasaje/Pasadizo',
        'PL': 'Polígono',
        'PM': 'Páramo',
        'PQ': 'Parroquia/Parque',
        'PR': 'Prolongación/Continuación',
        'PS': 'Paseo',
        'PT': 'Puente',
        'PZ': 'Plaza',
        'QT': 'Quinta',
        'RB': 'Rambla',
        'RC': 'Rincón/Rincona',
        'RD': 'Ronda',
        'RM': 'Ramal',
        'RP': 'Rampa',
        'RR': 'Riera',
        'RU': 'Rúa',
        'SA': 'Salida',
        'SD': 'Senda',
        'SL': 'Solar',
        'SN': 'Salón',
        'SU': 'Subida',
        'TN': 'Terrenos',
        'TO': 'Torrente',
        'TR': 'Travesía/Transversal',
        'UR': 'Urbanización',
        'VR': 'Vereda',
        'AC': 'Acceso',
        'AD': 'Aldea',
        'BV': 'Bulevar',
        'CZ': 'Calzada',
        'PA': 'Paralela',
        'PC': 'Placeta/Plaça',
        'PG': 'Polígono',
        'PO': 'Polígono',
        'SB': 'Subida',
        'SC': 'Sector',
        'CALLEJON': 'Callejón', 'CANTON': 'Cantón',
        'CIRCUNVALACION': 'Circunvalación', 'GENERICA': 'Genérica',
        'JARDIN': 'Jardín', 'MALECON': 'Malecón', 'RINCON': 'Rincón',
        'PROLONGACION': 'Prolongación', 'TRANSITO': 'Tránsito',
        'TRAVESIA': 'Travesía', 'VIA': 'Vía'
    },
    'ca_ES': {
        'AG': 'Agregat',
        'AL': 'Llogaret',
        'AR': 'Àrea/Raval',
        'AU': 'Autopista',
        'AV': 'Avinguda',
        'AY': 'Rierol',
        'BJ': 'Baixada',
        'BO': 'Barri',
        'BR': 'Barranc',
        'CA': 'Camí ramader',
        'CG': 'Col·legi/Cigarral',
        'CH': 'Xalet',
        'CI': 'Cinturó/Ronda',
        'CJ': 'Carreró',
        'CL': 'Carrer',
        'CM': 'Camí',
        'CN': 'Colònia',
        'CO': 'Ajuntament/Col·legi',
        'CP': 'Camp',
        'CR': 'Carretera',
        'CS': 'Mas',
        'CT': 'Costa/Rost',
        'CU': 'Conjunt',
        'CY': 'Carreró',
        'DE': 'Darrere',
        'DP': 'Diputació',
        'DS': 'Disseminats',
        'ED': 'Edificis',
        'EM': 'Extramurs/Raval',
        'EN': 'Entrada/Eixample',
        'ER': 'Extraradi/Raval',
        'ES': 'Escalinata',
        'EX': 'Pla',
        'FC': 'Ferrocarril',
        'FN': 'Finca',
        'GL': 'Rotonda/Plaça',
        'GR': 'Grup',
        'GV': 'Gran Via',
        'HT': 'Hort',
        'JR': 'Jardins',
        'LD': 'Marge/Vessant',
        'LG': 'Lloc',
        'MC': 'Mercat',
        'ML': 'Moll',
        'MN': 'Municipi',
        'MS': 'Masies',
        'MT': 'Muntanya',
        'MZ': 'Illa',
        'PB': 'Poblat',
        'PD': 'Partida',
        'PJ': 'Passatge',
        'PL': 'Polígon',
        'PM': 'Erm',
        'PQ': 'Parròquia/Parc',
        'PR': 'Prolongació/Continuació',
        'PS': 'Passeig',
        'PT': 'Pont',
        'PZ': 'Plaça',
        'QT': 'Quinta',
        'RB': 'Rambla',
        'RC': 'Racó',
        'RD': 'Ronda',
        'RM': 'Branc',
        'RP': 'Rampa',
        'RR': 'Riera',
        'RU': 'Rua',
        'SA': 'Sortida',
        'SD': 'Sender',
        'SL': 'Solar',
        'SN': 'Saló',
        'SU': 'Pujada',
        'TN': 'Terrenys',
        'TO': 'Torrent',
        'TR': 'Travessera',
        'UR': 'Urbanització',
        'VR': 'Sendera',
        'AC': 'Accès',
        'AD': 'Llogaret',
        'BV': 'Bulevard',
        'CZ': 'Calçada',
        'PA': 'Paral·lel',
        'PC': 'Placeta/plaça',
        'PG': 'Polígon',
        'PO': 'Polígon',
        'SB': 'Pujada',
        'SC': 'Sector',
    },
    'gl_ES': {
        'AG': 'Engadido',
        'AL': 'Aldea/Alameda',
        'AR': 'Área/Arrabalde',
        'AU': 'Autoestrada',
        'AV': 'Avenida',
        'AY': 'Regato',
        'BJ': 'Baixada',
        'BO': 'Barrio',
        'BR': 'Cavorco',
        'CA': 'Canella',
        'CG': 'Colexio/Cigarreiro',
        'CH': 'Chalet',
        'CI': 'Cinto',
        'CJ': 'Calexa/Quella/Ruela',
        'CL': 'Rúa',
        'CM': 'Camiño/Carme',
        'CN': 'Colonia',
        'CO': 'Concello/Colexio',
        'CP': 'Campeira/Campo',
        'CR': 'Estrada/Carreiro',
        'CS': 'Caserío',
        'CT': 'Costa/Pendente',
        'CU': 'Conxunto',
        'CY': 'Caleya',
        'DE': 'Detrás',
        'DP': 'Deputación',
        'DS': 'Espallado',
        'ED': 'Edificios',
        'EM': 'Extramuros',
        'EN': 'Entrada/Ensanche',
        'ER': 'Arrabalde',
        'ES': 'Escalinata',
        'EX': 'Chaira',
        'FC': 'Ferrocarril/Finca',
        'FN': 'Finca',
        'GL': 'Glorieta',
        'GR': 'Grupo',
        'GV': 'Gran Vía',
        'HT': 'Horta/Horto',
        'JR': 'Xardíns',
        'LD': 'Costado/Ladeira',
        'LG': 'Lugar',
        'MC': 'Mercado',
        'ML': 'Peirao',
        'MN': 'Concello',
        'MS': 'Masías',
        'MT': 'Monte',
        'MZ': 'Mazá',
        'PB': 'Poboado',
        'PD': 'Partida',
        'PJ': 'Pasaxe/Pasadizo',
        'PL': 'Polígono',
        'PM': 'Páramo',
        'PQ': 'Parroquia/Parque',
        'PR': 'Prolonga/Continuación',
        'PS': 'Paseo',
        'PT': 'Ponte',
        'PZ': 'Praza',
        'QT': 'Quinta',
        'RB': 'Rambla',
        'RC': 'Recuncho/Cornecho',
        'RD': 'Rolda',
        'RM': 'Ramal',
        'RP': 'Rampla',
        'RR': 'Riera',
        'RU': 'Rúa',
        'SA': 'Saída',
        'SD': 'Sendeiro',
        'SL': 'Soar',
        'SN': 'Salón',
        'SU': 'Costa',
        'TN': 'Terreos',
        'TO': 'Torrente',
        'TR': 'Travesía/Transversal',
        'UR': 'Urbanización',
        'VR': 'Carreiro/Verea',
        'AC': 'Acceso',
        'AD': 'Aldea',
        'BV': 'Bulevar',
        'CZ': 'Calzada',
        'PA': 'Paralela',
        'PC': 'Prazola',
        'PG': 'Polígono',
        'PO': 'Polígono',
        'SB': 'Costa',
        'SC': 'Sector',
        'CALLEJON': 'Quella/Ruela', 'CANTON': 'Cantón',
        'CIRCUNVALACION': 'Circunvalación', 'GENERICA': 'Xenérica',
        'JARDIN': 'Xardín', 'MALECON': 'Dique', 'RINCON': 'Recuncho',
        'PROLONGACION': 'Prolonga', 'TRANSITO': 'Tránsito',
        'TRAVESIA': 'Travesía', 'VIA': 'Vía'
    },
}

# Use lower case
place_types_d = {
    'es_ES': [
        'agregado', 'aldea', 'área', 'barrio', 'barranco', 'cañada', 'colegio',
        'cigarral', 'chalet', 'concejo', 'campa', 'campo', 'caserío',
        'conjunto', 'diputación', 'diseminados', 'edificios', 'extramuros',
        'entrada', 'ensanche', 'extrarradio', 'finca', 'grupo', 'huerta',
        'huerto', 'jardines', 'lugar', 'mercado', 'muelle', 'municipio',
        'masías', 'monte', 'manzana', 'poblado', 'partida', 'polígono',
        'páramo', 'parroquia', 'solar', 'terrenos', 'urbanización', 'bulevar',
        'sector',
    ],
    'ca_ES': [
        'agregat', 'llogaret', 'àrea', 'barri', 'barranc', 'camí ramader',
        'col·legi/cigarral', 'xalet', 'ajuntament/col·legi', 'camp', 'mas',
        'conjunt', 'diputació', 'disseminats', 'edificis', 'extramurs',
        'entrada', 'extraradi', 'finca', 'grup', 'hort', 'jardins', 'lloc',
        'mercat', 'moll', 'municipi', 'masies', 'muntanya', 'illa', 'poblat',
        'partida', 'polígon', 'erm', 'parròquia', 'solar', 'terrenys',
        'urbanització', 'bulevard', 'sector',
    ],
    'gl_ES': [
        'engadido', 'aldea', 'área', 'barrio', 'cavorco', 'canella', 'colexio',
        'cigarreiro', 'chalet', 'concello', 'campeira', 'campo', 'caserío',
        'conxunto', u'deputación', 'espallados', 'edificios', 'extramuros',
        'entrada', 'ensanche', 'arrabaldes', 'finca', 'grupo', 'horta', 'horto',
        'xardíns', 'lugar', 'mercado', 'peirao', 'concello', 'masías', 'monte',
        'mazá', 'poboado', 'partida', 'polígono', 'páramo', 'parroquia', 'soar',
        'terreos', 'urbanización', 'bulevar', 'sector'
    ],
}

# language is defined in system locales
available_langs = highway_types_d.keys()
language = language if language in available_langs else 'es_ES'

# Dictionary for default 'highway_types.csv'
highway_types = highway_types_d[language]

# List of highway types to translate as place addresses
place_types = place_types_d['es_ES']
if language != 'es_ES':
    place_types += place_types_d[language]

# List of place types to remove from the name
remove_place_from_name = [place_types[26]]

# List of highway types not to be parsed
excluded_types = ['DS', 'ER']

aux_address = {'cdau': ['04', '11', '14', '18', '21', '23', '29', '41']}
aux_path = 'auxsrcs'

prov_codes = {
    '02': 'Albacete',
    '03': 'Alicante',
    '04': 'Almería',
    '05': 'Ávila',
    '06': 'Badajoz',
    '07': 'Baleares',
    '08': 'Barcelona',
    '09': 'Burgos',
    '10': 'Cáceres',
    '11': 'Cádiz',
    '12': 'Castellón',
    '13': 'Ciudad Real',
    '14': 'Córdoba',
    '15': 'Coruña',
    '16': 'Cuenca',
    '17': 'Girona',
    '18': 'Granada',
    '19': 'Guadalajara',
    '21': 'Huelva',
    '22': 'Huesca',
    '23': 'Jaén',
    '24': 'León',
    '25': 'Lleida',
    '26': 'La Rioja',
    '27': 'Lugo',
    '28': 'Madrid',
    '29': 'Málaga',
    '30': 'Murcia',
    '32': 'Ourense',
    '33': 'Oviedo',
    '34': 'Palencia',
    '35': 'Las Palmas',
    '36': 'Pontevedra',
    '37': 'Salamanca',
    '38': 'Santa Cruz de Tenerife',
    '39': 'Cantabria',
    '40': 'Segovia',
    '41': 'Sevilla',
    '42': 'Soria',
    '43': 'Tarragona',
    '44': 'Teruel',
    '45': 'Toledo',
    '46': 'Valencia',
    '47': 'Valladolid',
    '49': 'Zamora',
    '50': 'Zaragoza',
    '51': 'Cartagena',
    '52': 'Gijón',
    '53': 'Jerez de la Frontera',
    '54': 'Vigo',
    '55': 'Ceuta',
    '56': 'Melilla',
}
