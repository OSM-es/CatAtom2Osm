Change log
==========

**2023-06-14 (2.14.0)**
* Includes cadastre street names along ref.
* Output OSM XML in utf-8.

**2023-06-13 (2.13.1)**
* Option to exclude addresses by street name.

**2023-06-12 (2.13.0)**
* Option to include cadastral references in tasks files.

**2023-05-10 (2.12.1)**
* Fix error log files were not made independent.

**2023-04-25 (2.12.0)**
* Removes fixme 'Building parts don't fill the building outline'.

**2023-04-22 (2.11.2)**
* Capacity to format loggers externally.

**2023-04-20 (2.11.1)**
* Adds cartobase overpass instance.

**2023-04-19 (2.11.0)**
* Search on line for municipalities not previously registered (#114)
* Update municipalities list.

**2022-12-03 (2.10.4)**
* Fix error don't copy zoning.zip to tasks

**2022-11-08 (2.10.3)**
* Fix error #112
* Fix error #111

**2022-11-07 (2.10.2)**
* Fix error when name is missing in place

**2022-10-13 (2.10.1)**
* Put place=square names in addr:place

**2022-09-02 (2.10.0)**
* Merge osm place names to addresses

**2022-08-29 (2.9.20)**
* Add conversion source to highway_names.csv
* Update feature term translation

**2022-08-23 (2.9.19)**
* Show administrative boundary on processing start
* Rearrange tasks folder

**2022-08-18 (2.9.18)**
* Compress task zoning file

**2022-08-17 (2.9.17)**
* Harden task zoning node simplification to avoid problems when importing in Task Manager.

**2022-08-14 (2.9.16)**
* Fix language output in the report
* Add tasks config in the report

**2022-08-12 (2.9.15)**
* Fix error displaying municipality divisions when someone is defined with a closed way.

**2022-08-09 (2.9.14)**
* Option to get dataset information.

**2022-07-01 (2.9.13)**
* Include fixme count in review file

**2022-06-29 (2.9.12)**
* Fix count of cdau addresses
* Improve final review message
* Fix error 'module' object is not callable

**2022-05-16 (2.9.11)**
* Dynamic setup of overpass api servers

**2022-05-12 (2.9.10)**
* Allow existing user in dockerfile

**2022-05-11 (2.9.9)**
* Fix debug prints left out

**2022-04-23 (2.9.8)**
* Restrict CDAU address to split limits

**2022-04-22 (2.9.7)**
* Dynamic setup of progressbars

**2022-04-20 (2.9.6)**
* Dynamic setup of language

**2022-04-19 (2.9.5)**
* Optionally hides progress bars
* Put split data in report

**2022-04-13 (2.9.4)**
* Update locale, CONTRIBUTING (#109)
* Update readme help
* Warning for invalid config settings (#108)

**2022-04-09 (2.9.3)**
* Log separated by process

**2022-04-07 (2.9.2)**
* Take system locale in Windows scripts

**2022-03-28 (2.9.1)**
* Rename geo.aux, not a valid Windows name

**2022-03-27 (2.9.0)**
* Add user configuration file

**2022-03-14 (2.8.2)**
* Remove debug tag left by mistake

**2022-03-11 (2.8.1)**
* Error loading project due to acute symbols

**2022-03-07 (2.8.0)**
* Download administrative boundaries to split municipalities

**2022-02-24 (2.7.0)**
* Add Carto BCN addresses #35
* Preserve existing task files in zone processing

**2022-02-22 (2.6.8)**
* Fix errors #99, #100, #101, #102.

**2022-02-21 (2.6.7)**
* Fix error applying topology to bad parts.

**2022-02-21 (2.6.6)**
* Fix error assigning abandoned buildings tag.

**2022-02-20 (2.6.5)**
* Detect bad municipality codes #98.

**2022-02-19 (2.6.4)**
* Integrate code style checking in each commit #77.

**2022-02-19 (2.6.3)**
* Integrate code style checking into publishing #77.

**2022-02-18 (2.6.2)**
* Fix errors #92, #93, #95, #96.

**2022-02-17 (2.6.1)**
* Adds municipality code to tasks project file.

**2022-02-16 (2.6.0)**
* Distribute task files using parcels instead of zones.
* Generate projects containing only addresses.
* Adds parts count to project as a task complexity indicator.
* The option -o split using zone codes is abandoned.

**2022-1-05 (2.5.3)**
* Fixs CDAU coordinates

**2022-02-03 (2.5.2)**
* Includes Jerez de la Frontera in CDAU

**2022-02-03 (2.5.1)**
* Fix reference to layer

**2022-01-30 (2.5.0)**
* Process much faster unsing in memory layers.
* Avoids to move entrances to shared wall between buildings.
* Don't generate output to view building conflation.

**2022-01-23 (2.4.0)**
* Remove parts without associated building #86

**2022-01-22 (2.3.0)**
* Fix bug assigning multiple entrances to building
* Creates backup subdirectory for split municipalities
* Fix addresses stats for split municipalities
* Fix incorrect detection of void zones
* Set log file level to DEBUG
* Avoids incorrect message for -z option
* Process of buildings without zone #88
* Split zoning with -o is used

**2022-01-21 (2.2.2)**
* Improves definition of bounding box to search in Overpass

**2022-01-20 (2.2.1)**
* Raises error for non-existing -o zones
* Flux control for no data to process
* Fix subdirectory name for -o option

**2022-01-20 (2.2.0)**
* Store municipality names and search areas #82 #87

**2022-01-16 (2.1.0)**
* Add entrance addresses associated with multiple buildings
* Fix bug moving the project
* Fix bug for keeping shapefiles in debug mode

**2022-01-14 (2.0.0)**
* Update to Ubuntu 20.04 / QGIS3 / python3 #67.
* Simplify CLI.
* Allow to process tasks for addresses only (-d).

**2022-01-11 (1.9.3)**
* Fix error deleting osm elements.

**2022-01-10 (1.9.2)**
* Fix overpass search area for -s option.

**2022-01-8 (1.9.1)**
* Clip polygon includes zones if overlapped area is greater than 50%.
* Fix error renaming the project.

**2022-01-8 (1.9.0)**
* Option to split big municipallities using a file (#78)
* Fix and perfomance improvement of -o option (#73)

**2021-12-21 (1.8.7)**
* Fixes ResourceWarning unclosed file in Python3 (#67).
* Fixes join entrance to building:part ways with QGIS3 (#67).
* Change install method (in docker) due to QGIS3 error (#67).
* Fixs error accesing __main__.py.
* Unify simplify results in python2/3 (#67).
* New utility scripts (for development).

**2021-12-20 (1.8.6)**
* Consider bilingualism and case to assign places (#71).

**2021-12-19 (1.8.5)**
* Integrate testing with publishing.

**2021-12-19 (1.8.4)**
* Fix task for buildings without zone (#70).

**2021-12-19 (1.8.3)**
* Update changes downloading CDAU data.

**2021-12-17 (1.8.2)**
* Update install documentation.

**2021-12-16 (1.8.1)**
* Adds warning for possible zones with bad geometry.

**2021-12-16 (1.8.0)**
* Supports multiple municipalities or zones.

**2021-12-15 (1.7.2)**
* Fix error processing zoning of Madrid (#69)

**2021-12-12 (1.7.1)**
* Windows Installer (#59).

**2021-12-11 (1.7.0)**
* Simplify install and use of docker image (#59, #66)

**2021-12-10 (1.6.1)**
* Don't create outline for parts without associated building

**2021-12-10 (1.6.0)**
* Option to review changesets tags (#64)

**2021-12-09 (1.5.1)**
* Fix zone label in tasks definition files (#65)

**2021-12-08 (1.5.0)**
* Reorganization of task files (#65)

**2021-12-03 (1.4.0dev)**
* Option to divide large municipalities by zones (#58).
* Option to list zones in a municipality (#58).

**2021-11-15 (1.3.10)**
* Simplify language setup (#60).
* Add the language setup to the report (#60).

**2021-06-12 (1.3.9)**
* Recomendation to use Docker.

**2021-06-07 (1.3.8)**
* Fixes Docker versioning error.

**2021-06-07 (1.3.7)**
* Adds Docker authentication to Travis.

**2021-06-07 (1.3.6)**
* Fixes syntax error in Python3.

**2021-04-14 (1.3.5)**
* Adds a 'generator' tag to identify the version in the changesets

**2021-04-07 (1.3.4)**
* Avoids to fail for broken zonification files with missing zones in Cadastre (issue #57)
* Option '-l' list territorial offices if used without argument value

**2021-03-09 (1.3.3)**
* Fix tests broken in d851c4b (issue #56)

**2021-03-09 (1.3.2)**
* Update recommend python3 packages for the initial setup (issue #52)
* Update URL in cdau.py (issue #54)


**2021-03-09 (1.3.1)**
* Add a 'fixme' when the building parts area is not equal to the building area (issue #56)

**2021-03-08 (1.3)**
* Keep all building parts to fulfill the Simple 3D Buildings scheme (issue #56)

**2020-01-08 (1.2.2)**
* Fix TypeError: expected string or bytes-like object #49
* Infinite loop deleting invalid geometries #50

**2020-01-07 (1.2.1)**
* Fix circular reference translating compat.py
* Add missing dev requisites

**2020-01-07 (1.2)**
* Qgis 3.x compatible version

**2019-12-18 (1.1.14)**
* Set docker app path owner

**2019-12-17 (1.1.13)**
* Fix docker repository name

**2019-12-17 (1.1.12)**
* Fix docker push script name

**2019-12-17 (1.1.11)**
* Deploy only to tagged releases
* Fix docker repository name

**2019-12-17 (1.1.10)**

* Add docker container and Travis CI

**2019-12-09 (1.1.9)**

* Fix error tras actualización de archivos GML de Catastro #47

**2018-11-09 (1.1.8)**

* Resolves error opening the most current Cadastre files (issue #29)
* Reduces the processing time to generate the zoning.geojson file for certain provinces (issue #26)
* Fix errors in the English translation and memory units in the report (by @javirg)

**2018-05-29 (1.1.7)**

* Add translation of street names in Galician and Catalan.

**2018-03-20 (1.1.6)**

* Fix minor errors.

**2018-03-19 (1.1.5)**

* Fix minor errors.

**2018-03-14 (1.1.4)**

* Merge Cadastre address with CDAU (issue #11).

**2018-03-13 (1.1.3)**

* Remove some prefixes from address name (issue #13).
* Put image links in the address.osm file (issue #14).
* Option to download only the Cadastre files (issue #16).

**2018-03-02 (1.1.2)**

* Remove upload=yes parameter from OSM josm files (issue #12)

**2018-02-18 (1.1.1)**

* Change CSV separator to tab (issue #10)

**2018-01-23 (1.1.0)**

* Move repository to OSM-es organization.
* Put all addresses in address.geojson enhancement #71
* Compress task files enhancement #69
* List of tasks to review. enhancement #66
* Remove selected streets from addresses enhancement #65
* Translate througfare types to Catalan enhancement #64
* Improve changeset comments enhancement help wanted #63

**2018-01-16 (1.0.5)**

* Compress the task files (issue #69).
* Fix error (issue #62).

**2018-01-01 (1.0.2)**

* Enhacements in the project definition file for the tasking manager (issues #58, #59 and #60).
* Fix some bugs (issues #57 y #61).

**2017-12-30 (1.0.1)**

* Fix minor error in Macos script.

**2017-12-11 (1.0.0)**

* Passed tests in macOS Sierra 10.2, Debian 8.1.0 and Debian 9.3.0.
* Fixed errors (issues #53, #56).

**2017-11-25**

* Detect swimming pools over buildings (issue #51).

**2017-11-22**

* Run code tests in Windows.
* Export image links in address.geojson.

**2017-11-13**

* Alternative method to get OSM files for data conflation in big municipalities.
* -m option also dissables highway names conflation.

**2017-11-09**

* Delete zig-zag and spike vertices.
* Test for parts bigger than it building.

**2017-11-06**

* Generate statistics report (issues #50).

**2017-10-31**

* Rebuild code for better performance (issues #46, #48).
* Conflation of existing OSM buildings/pools and addresses (issues #43, #44, #49).

**2017-07-11**

* Fix some errors.
* Check floors and area of buildings (issue #40).
* Adds changeset tags to the OSM XML files (issue #38).

**2017-07-05**

* Reduces JOSM Validation errors (issue #29)
* Improve code to reduce execution time (issue #31)
* Improve simplify method (issue #35)
* Move entrances to footprint and merge addresses with buildings (issues #34, #33)
* Some bugs (issues #25, #30, #32, #36, #37)
* Some enhancements (issues #2, #7, #22, #23, #24, #26, #28)

**2017-06-15**

* Minor version (issue #21)

**2017-06-14**

* Some improvements and a bug fix (issues #16, #17, #18, #19, #20)

**2017-06-13**

* Fix some bugs (issues #9, #10, #11, #12, #13, #14, #15).

**2017-06-07**

* Adds creation of tasks files (issue #5).

**2017-06-05**

* Adds creation of task boundaries (issue #4).

**2017-05-28**

* Adds support to translations and translation to Spanish (issue #3).

**2017-03-28**

* Adds support to download source Cadastre ATOM files (issue #1).

**2017-03-22**

* Rewrites simplify and topology in ConsLayer.

**2017-03-18**

* Initial development.
