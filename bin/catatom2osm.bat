@echo off
docker pull egofer/catatom2osm
IF "%LANG%"=="" set LANG=es_ES.UTF-8
docker run --rm -it -e LANG=%LANG% -v %cd%:/catastro egofer/catatom2osm catatom2osm %*
