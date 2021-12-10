# -*- coding: utf-8 -*-
"""CatAtom2Osm command line entry point"""
from __future__ import unicode_literals
from builtins import str
from argparse import ArgumentParser
import logging
import os
import sys
from zipfile import BadZipfile

import compat
import setup
from report import instance as report
log = setup.log
terminal = compat.Terminal(setup.encoding)


usage = terminal.encode(_("""catatom2osm [OPTION]... [PATH]
The argument path states the directory for input and output files. 
The directory name shall start with 5 digits (GGMMM) matching the Cadastral 
Provincial Office and Municipality Code. If the program don't find the input 
files it will download them for you from the INSPIRE Services of the Spanish 
Cadastre."""))

def process(options):
    a_path = '' if len(options.path) == 0 else options.path[0]
    if options.list:
        from catatom import list_municipalities
        list_municipalities('{:>02}'.format(options.list))
    elif options.download:
        from catatom import Reader
        cat = Reader(a_path)
        cat.download('address')
        cat.download('cadastralzoning')
        cat.download('building')
    else:
        from catatom2osm import CatAtom2Osm
        app = CatAtom2Osm(a_path, options)
        app.run()
        app.exit()

def run():
    parser = ArgumentParser(usage=usage)
    parser.add_argument("path", nargs="*",
        help=terminal.encode(_("Directory for input and output files")))
    parser.add_argument("-v", "--version", action="version",
        help=terminal.encode(_("Show program's version number and exit")),
        version=setup.app_version)
    parser.add_argument("-l", "--list", dest="list", metavar="prov", nargs='?',
        default=False, const=99, help=terminal.encode(_("List available municipalities "
        "given the two digits province code")))
    parser.add_argument("--list-zones", dest="list_zones", action="store_true",
        help=terminal.encode(_("List zone labels in the municipality")))
    parser.add_argument("-t", "--tasks", dest="tasks", action="store_true",
        help=terminal.encode(_("Splits constructions into tasks files "
        "(default, implies -z)")))
    parser.add_argument("-c", "--comment", dest="comment", action="store_true",
        help=terminal.encode(_("Recovers the comments of the tasks")))
    parser.add_argument("-b", "--building", dest="building",
        action="store_true", help=terminal.encode(_("Process buildings to a "
        "single file instead of tasks")))
    parser.add_argument("-z", "--zoning", dest="zoning", action="store_true",
        help=terminal.encode(_("Process the cadastral zoning dataset")))
    parser.add_argument("-o", "--zone", dest="zone", metavar="label", nargs=1,
        default=False, type=str, help=terminal.encode(_("Process a zone given "
        "its label")))
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
        default=setup.log_level, help=terminal.encode(_("Select the log level "
        "between DEBUG, INFO, WARNING, ERROR or CRITICAL.")))
    options = parser.parse_args()
    report.options = ' '.join(sys.argv[1:])
    options.zone = options.zone[0] if options.zone else None
    if options.zone:
        if not options.building and not options.address:
            options.address = True
        options.building = True
        options.zoning = False
        options.tasks = False
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
    if len(options.path) > 1:
        log.error(_("Too many arguments, supply only a directory path."))
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
