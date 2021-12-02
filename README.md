Read me
=======

Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services (http://www.catastro.minhap.gob.es/webinspire/index.html) to OSM files. This is part of an import proposal under construction:

https://wiki.openstreetmap.org/wiki/Spanish_Cadastre/Buildings_Import

Requeriments
------------

* fuzzywuzzy[speedup]
* psutil
* pyqgis
* requests
* GDAL

Fuzzywuzzy is needed for street names conflation. 
The main requisites (pyqgis, GDAL) should be provided by QGIS using the 
installers available on http://qgis.org/

QGIS >= 2.10.1, GDAL >= 2 are required.

Install
-------

We recomend to use this Docker image 
(https://hub.docker.com/r/egofer/catatom2osm).

If you want to install without Docker see INSTALL.md (https://OSM-es.github.io/CatAtom2Osm/en/install.html). 

Usage
-----

To run the application:

    catatom2osm <path>

The argument path states the directory for input and output files. 
The directory name shall start with 5 digits (GGMMM) matching the Cadastral 
Provincial Office and Municipality Code. If the program don't find the input 
files it will download them for you from the INSPIRE Services of the Spanish 
Cadastre.

**Options**:

* \-h, --help                Show this help message and exit
* \-v, --version             Print CatAtom2Osm version and exit
* \-l [prov], --list [prov]  List available municipalities given the two digits province code
* \-t, --tasks               Splits constructions into tasks files (default, implies -z)
* \-b, --building            Process buildings to a single file instead of tasks
* \-d, --address             Process the address dataset
* \-z, --zoning              Process the cadastral zoning dataset.
* \-p, --parcel              Process the cadastral parcel dataset
* \-a, --all                 Process all datasets (equivalent to -bdptz)
* \-o label, --zone label    Process a zone given its label
* \-m, --manual              Dissable conflation with OSM data
* \-w, --download            Download only
* \--log=log_level           Select the log level between DEBUG, INFO, WARNING, ERROR or CRITICAL

Settings
--------

The software use the system locales to select the language to use translating the throughfare types. To use another language, set the LANG environment variable.

	LANG=es_ES.UTF-8; catatom2osm

Forces to use Spanish.

	LANG=cat_ES.UTF-8; catatom2osm

Forces to use Catalan.

	LANG=cat_ES.UTF-8; catatom2osm

Forces to use Galician

Documentation
-------------

Browse the software documentation.

https://OSM-es.github.io/CatAtom2Osm/en

