#!/bin/bash
docker pull egofer/catatom2osm
docker run --rm -it -e LANG="$LANG" -v $(pwd):/catastro egofer/catatom2osm catatom2osm "$@"
