Read me
=======

![](https://user-images.githubusercontent.com/1605829/141660065-1ad64b8f-dde9-4946-a4af-b556c270545f.png)

Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services (http://www.catastro.minhap.gob.es/webinspire/index.html) to OSM files. This is part of an ongoing import:

https://openstreetmap.es/catastro

Requeriments
------------

Docker https://www.docker.com/get-started

Install
-------

See INSTALL.md (https://OSM-es.github.io/CatAtom2Osm/en/install.html).


Usage
-----

To run the application:

    catatom2osm <paths>

The argument path states the directory for input and output files. 
The directory name shall start with 5 digits (GGMMM) matching the Cadastral 
Provincial Office and Municipality Code. If the program don't find the input 
files it will download them for you from the INSPIRE Services of the Spanish 
Cadastre.

**Options**:

* \-h, --help                Show this help message and exit
* \-v, --version             Print CatAtom2Osm version and exit
* \-l [prov], --list [prov]  List available municipalities given the two digits province code
* \--list-zones              List zone labels in the municipality.
* \-t, --tasks               Splits constructions into tasks files (default, implies -z)
* \-c, --comment             Recovers the metadata of the tasks
* \-b, --building            Process buildings to a single file instead of tasks
* \-d, --address             Process the address dataset
* \-z, --zoning              Process the cadastral zoning dataset.
* \-p, --parcel              Process the cadastral parcel dataset
* \-a, --all                 Process all datasets (equivalent to -bdptz)
* \-o labels, --zone labels  Process zones given its labels
* \-m, --manual              Dissable conflation with OSM data
* \-w, --download            Download only
* \--log=log_level           Select the log level between DEBUG, INFO, WARNING, ERROR or CRITICAL

Settings
--------

The software use the system locales to select the language to use translating the throughfare types. To use another language, set the LANG environment variable.

	LANG=es_ES.UTF-8; catatom2osm

Forces to use Spanish.

	LANG=ca_ES.UTF-8; catatom2osm

Forces to use Catalan.

	LANG=gl_ES.UTF-8; catatom2osm

Forces to use Galician

Documentation
-------------

Browse the software documentation.

https://OSM-es.github.io/CatAtom2Osm/en

