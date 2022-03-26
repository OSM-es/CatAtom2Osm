"""CatAtom2Osm command line entry point."""
import argparse
import logging
import os
import sys
from zipfile import BadZipfile

from requests.exceptions import RequestException

from catatom2osm import boundary, config
from catatom2osm.app import CatAtom2Osm, QgsSingleton
from catatom2osm.catatom import Reader
from catatom2osm.exceptions import CatException

log = config.setup_logger()

usage = _(
    """catatom2osm [OPTION]... [PATHS]
  The argument PATHS states for directories to process municipalities. The last
  directory in each path shall be 5 digits (GGMMM) matching the Cadastral codes
  for Provincial Office (GG) and Municipality (MMM). If the program don't find
  the input files it will download them for you from the INSPIRE Services of
  the Spanish Cadastre."""
)

examples = _(
    """Examples:
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
    of their area within the limit.
  catatom2osm -l 28900
    List OSM administrative boundaries available in Madrid
  catatom2osm -s Atocha 28900
    Downloads administrative boundary of Atocha neighborhood in Madrid and
    process it."""
)


def process(options):
    if options.list:
        boundary.list_code(options.list)
    elif options.download:
        for a_path in options.path:
            cat = Reader(a_path)
            cat.download("address")
            cat.download("cadastralzoning")
            cat.download("building")
    else:
        if not options.config_file and os.path.exists(config.default_config_file):
            options.config_file = config.default_config_file
        if options.config_file:
            config.get_user_config(options.config_file)
        qgs = QgsSingleton()
        for a_path in options.path:
            o = argparse.Namespace(**options.__dict__)
            CatAtom2Osm.create_and_run(a_path, o)
        qgs.exitQgis()


def run():
    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument(
        "path",
        metavar="PATHS",
        nargs="*",
        help=_("Directories for input and output files"),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=config.app_version,
        help=_("Show program's version number and exit"),
    )
    parser.add_argument(
        "-l",
        "--list",
        dest="list",
        metavar="PROV/MUN",
        nargs="?",
        default="",
        const="99",
        help=_(
            "List province codes or municipality codes for PROV (2 digits) "
            "or administrative boundaries for MUN (5 digits)"
        ),
    )
    parser.add_argument(
        "-b",
        "--building",
        dest="building",
        action="store_true",
        help=_("Process only the building dataset"),
    )
    parser.add_argument(
        "-d",
        "--address",
        dest="address",
        action="store_true",
        help=_("Process only the address dataset"),
    )
    parser.add_argument(
        "-z",
        "--zoning",
        dest="zoning",
        action="store_true",
        help=_("Process only the tasks definition file"),
    )
    parser.add_argument(
        "-o",
        "--parcel",
        dest="parcel",
        nargs=1,
        default=[],
        metavar="REFCAT",
        type=str,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-s",
        "--split",
        dest="split",
        help=_(
            "Process data in the parcels delimited by SPLIT "
            "(file / administrative boundary OSM id or name)"
        ),
    )
    parser.add_argument(
        "-m",
        "--manual",
        dest="manual",
        action="store_true",
        help=_("Disable conflation with OSM data"),
    )
    parser.add_argument(
        "-c",
        "--comment",
        dest="comment",
        action="store_true",
        help=_("Recovers the metadata of the tasks"),
    )
    parser.add_argument(
        "-w",
        "--download",
        dest="download",
        action="store_true",
        help=_("Download only"),
    )
    parser.add_argument(
        "--log",
        dest="log_level",
        metavar="LOG_LEVEL",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=config.log_level,
        help=_(
            "Select the log level between " "DEBUG, INFO, WARNING, ERROR or CRITICAL."
        ),
    )
    parser.add_argument(
        "-f",
        "--config-file",
        dest="config_file",
        default=False,
        help=_("Path to the user configuration file. Defaults to %(default)s"),
    )
    parser.add_argument(
        "-g",
        "--generate-config",
        dest="generate_config",
        action="store_true",
        help=_("Output a sample config file with the default user configuration"),
    )
    # Reserved -i --info, -p --push, -u --urban, -r --rustic
    options = parser.parse_args()
    options.args = " ".join(sys.argv[1:])
    log_level = getattr(logging, options.log_level.upper())
    config.set_log_level(log, log_level)
    if not options.building and not options.address:
        options.address = True
        options.building = True
    if options.generate_config:
        config.generate_default_user_config()
    elif options.split and len(options.path) > 1:
        log.error(_("Can't use split file with multiple municipalities"))
    elif len(options.path) == 0 and not options.list and not options.generate_config:
        parser.print_help()
        print()
        print(examples)
    else:
        try:
            process(options)
        except (BadZipfile, CatException, RequestException) as e:
            msg = e.message if getattr(e, "message", "") else str(e)
            log.error(msg)


if __name__ == "__main__":
    run()
