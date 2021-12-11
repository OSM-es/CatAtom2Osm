#!/bin/bash
docker pull egofer/catatom2osm
docker run --rm -it -e LANG="$LANG" -v $(pwd):/catastro catatom2osm:dev catatom2osm "$@"
