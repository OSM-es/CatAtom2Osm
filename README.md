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

The argument PATHS states for directories to process municipalities. The last
directory in each path shall be 5 digits (GGMMM) matching the Cadastral codes
for Provincial Office (GG) and Municipality (MMM). If the program don't find
the input files it will download them for you from the INSPIRE Services of
the Spanish Cadastre.

**Options**:

* \-h, --help                Show this help message and exit
* \-v, --version             Show program's version number and exit
* \-l, --list                List province codes
* \-l [PROV], --list [PROV]  List available municipality codes for PROV (2 digits)
* \-l [MUN], --list [MUN]    List administrative boundaries for MUN (5 digits)
* \-b, --building            Process only the building dataset
* \-d, --address             Process only the address dataset
* \-z, --zoning              Process only the tasks definition file
* \-s SPLIT, --split SPLIT   Process data in the parcels delimited by SPLIT (file / administrative boundary OSM id or name)
* \-m, --manual              Dissable conflation with OSM data
* \-c, --comment             Recovers the metadata of the tasks
* \-w, --download            Download only
* \--log=log_level           Select the log level between DEBUG, INFO, WARNING, ERROR or CRITICAL

More info about the split option in the [wiki](Más información sobre dividir municipio en la [wiki](https://wiki.openstreetmap.org/wiki/ES:Catastro_espa%C3%B1ol/Importaci%C3%B3n_de_edificios/Gesti%C3%B3n_de_proyectos#Anexo:_Modificar_proyectos) (es)

Settings
--------

The software use the system locales to select the language to use translating the throughfare types. To use another language, set the LANG environment variable. For example, in Linux:

	LANG=es_ES.UTF-8; catatom2osm

Forces to use Spanish.

	LANG=ca_ES.UTF-8; catatom2osm

Forces to use Catalan.

	LANG=gl_ES.UTF-8; catatom2osm

Forces to use Galician

In the Windows terminal (CMD):

   set LANG=ca_ES.UTF-8 && catatom2osm

In PowerShell:

   ${LANG}="ca_ES.UTF-8"; catatom2osm

For more options and permanent settings use the config file.

To create a template:

   catatom2osm -g

These are the available options:

* language: Language to translate thoroughfare names: es_ES ca_ES gl_ES
* highway_types: Dictionary to translate thoroughfare types
* place_types: List of highway types to translate as place addresses (addr:place)
* remove_place_from_name: List of highway types to remove from the name
* excluded_types List of highway types not to be parsed
* warning_min_area: Area in m² for small area warning
* warning_max_area: Area in m² for big area warning
* parcel_parts: Number of building parts to agregate parcels
* parcel_dist: Distance in meters to agregate parcels

Documentation
-------------

Browse the software documentation.

https://OSM-es.github.io/CatAtom2Osm/en

