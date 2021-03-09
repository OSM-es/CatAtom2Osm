Change log
==========

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
