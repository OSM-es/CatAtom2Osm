#!/bin/bash
python3 -V > /dev/null 2>&1
if [ $? -eq 0 ]; then
    python3 /opt/CatAtom2Osm/catatom2osm $*
else
    python2 /opt/CatAtom2Osm/catatom2osm $*
fi
