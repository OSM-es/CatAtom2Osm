# -*- coding: utf-8 -*-
"""CatAtom2Osm command line entry point"""
from __future__ import unicode_literals
from builtins import str
from argparse import ArgumentParser
import logging
import sys
from zipfile import BadZipfile

from catatom2osm import config, compat
log = config.log
terminal = compat.Terminal(config.encoding)


usage = terminal.encode(_("""catatom2osm [OPTION]... [PATH]
The argument path states the directory for input and output files. 
The directory name shall start with 5 digits (GGMMM) matching the Cadastral 
Provincial Office and Municipality Code. If the program don't find the input 
files it will download them for you from the INSPIRE Services of the Spanish 
Cadastre."""))

def process(options):
    a_path = '' if len(options.path) == 0 else options.path[0]
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
    parser = ArgumentParser(usage=usage)
    parser.add_argument("path", nargs="*",
        help=terminal.encode(_("Directory for input and output files")))
    parser.add_argument("-v", "--version", action="version",
        help=terminal.encode(_("Show program's version number and exit")),
        version=config.app_version)
    parser.add_argument("-l", "--list", dest="list", metavar="prov", nargs='?',
        default=False, const=99, help=terminal.encode(_("List available municipalities "
        "given the two digits province code")))
    parser.add_argument("--list-zones", dest="list_zones", action="store_true",
        help=terminal.encode(_("List zone labels in the municipality")))
    parser.add_argument("-t", "--tasks", dest="tasks", action="store_true",
        help=terminal.encode(_("Splits constructions into tasks files "
        "(default, implies -z)")))
    parser.add_argument("-c", "--comment", dest="comment", action="store_true",
        help=terminal.encode(_("Recovers the metadata of the tasks")))
    parser.add_argument("-b", "--building", dest="building",
        action="store_true", help=terminal.encode(_("Process buildings to a "
        "single file instead of tasks")))
    parser.add_argument("-z", "--zoning", dest="zoning", action="store_true",
        help=terminal.encode(_("Process the cadastral zoning dataset")))
    parser.add_argument("-o", "--zone", dest="zone", metavar="label", nargs='+',
        default=[], type=str, help=terminal.encode(_("Process zones given "
        "its labels")))

    parser.add_argument("-s", "--split", dest="split",
        help=terminal.encode(_("Process zones within a boundary polygon")))

    parser.add_argument("-d", "--address", dest="address", action="store_true",
        help=terminal.encode(_("Process the address dataset (default)")))
    parser.add_argument("-p", "--parcel", dest="parcel", action="store_true",
        help=terminal.encode(_("Process the cadastral parcel dataset")))
    parser.add_argument("-a", "--all", dest="all", action="store_true",
        help=terminal.encode(_("Process all datasets (equivalent to -bdptz)")))
    parser.add_argument("-m", "--manual", dest="manual", action="store_true",
        help=terminal.encode(_("Dissable conflation with OSM data")))
    parser.add_argument("-w", "--download", dest="download",
        action="store_true", help=terminal.encode(_("Download only")))
    parser.add_argument("--log", dest="log_level", metavar="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=config.log_level, help=terminal.encode(_("Select the log level "
        "between DEBUG, INFO, WARNING, ERROR or CRITICAL.")))
    options = parser.parse_args()
    options.args = ' '.join(sys.argv[1:])
    if len(options.zone) > 0:
        if len(options.path) == 0:
            options.path = [options.zone[-1]]
            options.zone = options.zone[:-1]
        if not options.building and not options.address:
            options.address = True
        options.building = False
        options.tasks = True
        options.parcel = False
        options.all = False
        options.download = False
    if options.all:
        options.building = True
        options.tasks = True
        options.address = True
        options.parcel = True
    if not (options.tasks or options.zoning or options.building or 
            options.address or options.parcel): # default options
        options.tasks = True
        options.address = True
    if options.tasks:
        options.zoning = True
    log_level = getattr(logging, options.log_level.upper())
    log.setLevel(log_level)
    log.debug(_("Using Python %s.%s.%s"), *sys.version_info[:3])
    log.debug(compat.etreemsg)
    #if len(options.path) > 1:
    #    log.error(_("Too many arguments, supply only a directory path."))
    if len(options.zone) > 1 and len(options.path) > 1:
        log.error(_("Can't use multiple zones with multiple municipalities"))
    elif len(options.path) == 0 and not options.list:
        parser.print_help()
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
