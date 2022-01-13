"""CatAtom2Osm command line entry point"""
import argparse
import logging
import sys
from zipfile import BadZipfile

from catatom2osm import config
log = config.log


usage = _("""catatom2osm [OPTION]... [PATHS]
  The argument PATHS states for folders to process municipalities.
  The last folder in each path shall be 5 digits (GGMMM) matching the Cadastral
  codes for Provincial Office (GG) and Municipality (MMM). If the program don't
  find the input files it will download them for you from the INSPIRE Services
  of the Spanish Cadastre.""")

examples = _("""Examples:
  catatom2osm 05015
    Process a municipality. 05015/highway_names.csv is generated.
    You need to correct it following the wiki and process a second time.
    https://openstreetmap.es/catastro [Projects management].
  catatom2osm -l
    List province codes.
  catatom2osm -l 05
    List municipality codes in province 05 Ávila.
  catatom2osm -b 05015
    Process only buildings (without addresses).
  catatom2osm -s Atocha.geojson 28900
    It processes the Atocha neighborhood delimited by a geojson file with
    its administrative limit. Pass only the zones that have more than 50%
    of their area within the limit.""")

def process(options):
    if options.list:
        from catatom2osm.catatom import list_municipalities
        list_municipalities('{:>02}'.format(options.list))
    elif options.download:
        from catatom2osm.catatom import Reader
        for a_path in options.path:
            cat = Reader(a_path)
            cat.download('address')
            cat.download('cadastralzoning')
            cat.download('building')
    else:
        from catatom2osm.app import CatAtom2Osm, QgsSingleton
        qgs = QgsSingleton()
        for a_path in options.path:
            CatAtom2Osm.create_and_run(a_path, options)
        qgs.exitQgis()

def run():
    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument("path", metavar="PATHS", nargs="*",
        help=_("Directories for input and output files"))
    parser.add_argument("-v", "--version", action="version",
        help=_("Show program's version number and exit"),
        version=config.app_version)
    parser.add_argument("-l", "--list", dest="list", metavar="PROV/MUN", nargs='?',
        default='', const='99', help=_("List province codes or municipality "
        "codes for PROV (2 digits) or zone labels for MUN (5 digits) and exit"))
    parser.add_argument("--list-zones", dest="list_zones", action="store_true",
        help=argparse.SUPPRESS)
    parser.add_argument("-c", "--comment", dest="comment", action="store_true",
        help=_("Recovers the metadata of the tasks"))
    parser.add_argument("-b", "--building", dest="building",
        action="store_true", help=_("Process only the building dataset"))
    parser.add_argument("-d", "--address", dest="address", action="store_true",
        help=_("Process only the address dataset"))
    parser.add_argument("-z", "--zoning", dest="zoning", action="store_true",
        help=_("Process only the cadastral zoning dataset"))
    parser.add_argument("-o", "--zone", dest="zone", nargs='+',
        default=[], type=str, help=_("Process data in these zones"))
    parser.add_argument("-s", "--split", dest="split",
        help=_("Process data in the zones delimited by SPLIT file"))
    parser.add_argument("-m", "--manual", dest="manual", action="store_true",
        help=_("Dissable conflation with OSM data"))
    parser.add_argument("-w", "--download", dest="download",
        action="store_true", help=_("Download only"))
    parser.add_argument("--log", dest="log_level", metavar="LOG_LEVEL",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=config.log_level, help=_("Select the log level "
        "between DEBUG, INFO, WARNING, ERROR or CRITICAL."))
    # Reserved -i --info, -p --push, -u --urban, -r --rustic
    options = parser.parse_args()
    options.args = ' '.join(sys.argv[1:])
    if not options.building and not options.address:
        options.address = True
        options.building = True
    if len(options.zone) > 0:
        if len(options.path) == 0:
            options.path = [options.zone[-1]]
            options.zone = options.zone[:-1]
    if len(options.list) > 2:
        options.list_zones = True
        options.path = [options.list]
        options.list = ''
    log_level = getattr(logging, options.log_level.upper())
    log.setLevel(log_level)
    log.debug(_("Using Python %s.%s.%s"), *sys.version_info[:3])
    if len(options.zone) > 1 and len(options.path) > 1:
        log.error(_("Can't use multiple zones with multiple municipalities"))
    elif len(options.path) == 0 and not options.list:
        parser.print_help()
        print()
        print(examples)
    elif log.getEffectiveLevel() == logging.DEBUG:
        process(options)
    else:
        try:
            process(options)
        except (ImportError, IOError, OSError, ValueError, BadZipfile) as e:
            msg = e.message if getattr(e, 'message', '') else str(e)
            log.error(msg)
            if 'qgis' in msg or 'core' in msg or 'osgeo' in msg:
                log.error(_("Please, install QGIS"))

if __name__ == "__main__":
    run()
