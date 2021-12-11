@echo off
docker pull egofer/catatom2osm
docker run --rm -it -e LANG="$LANG" -v %cd%:/catastro catatom2osm:dev catatom2osm %*
