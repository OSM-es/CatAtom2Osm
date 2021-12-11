#!/bin/bash
# Extract OSM data for conflation using Osmosis
# Usage: extract PATH
# PATH should contain a '.pbf' file with the input data and a 'boundary.poly' 
# file whit the boundary polygon limits.
# Sugested source for pbf's https://mapzen.com/data/metro-extracts/
if [ $# -ne 1 ]; then
  echo "Uso: `basename $0` PATH"
  exit 1
fi
OUTPATH=$1
shopt -s nullglob
FILES=($OUTPATH/*.pbf)
if [ ${#FILES[@]} == 0 ]; then
    echo "PATH debe contener un fichero .pbf"
    exit
fi
PBFFILE=${FILES[0]}
POLYGON="$OUTPATH/boundary.poly"
if [ ! -f $POLYGON ]; then
    echo "PATH debe contener un fichero boundary.poly"
    exit
fi

CURADDR="$OUTPATH/current_address.osm"
if [ ! -f $CURADDR ]; then
    osmosis \
    --read-pbf $PBFFILE \
    --node-key keyList="addr:street,addr:place" \
    --tag-filter accept-nodes "addr:housenumber=*" outPipe.0=nodedata \
    \
    --read-pbf $PBFFILE \
    --way-key keyList="addr:street,addr:place" \
    --tag-filter accept-ways "addr:housenumber=*" \
    --tf reject-relations --used-node outPipe.0=waydata \
    \
    --merge inPipe.0=nodedata inPipe.1=waydata outPipe.0=waynodedata \
    \
    --read-pbf $PBFFILE \
    --tag-filter accept-relations "addr:street=*" "addr:place=*" \
    --tag-filter accept-relations "addr:housenumber=*" \
    --used-way --used-node outPipe.0=reldata \
    \
    --merge inPipe.0=waynodedata inPipe.1=reldata \
    --bounding-polygon file="$POLYGON" \
    --write-xml $CURADDR
fi
ls -lh $CURADDR

CURHGW="$OUTPATH/current_highway.osm"
if [ ! -f $CURHGW ]; then
    osmosis \
    --read-pbf $PBFFILE \
    --node-key-value keyValueList="place.square" outPipe.0=nodedata \
    \
    --read-pbf $PBFFILE \
    --tag-filter accept-ways "highway=*" "place=square" \
    --tag-filter accept-ways "name=*" \
    --tf reject-relations --used-node outPipe.0=waydata \
    \
    --merge inPipe.0=nodedata inPipe.1=waydata outPipe.0=waynodedata \
    \
    --read-pbf $PBFFILE \
    --tag-filter accept-relations "place=square" \
    --tag-filter accept-relations "name=*" \
    --used-way --used-node outPipe.0=reldata \
    \
    --merge inPipe.0=waynodedata inPipe.1=reldata \
    --bounding-polygon file="$POLYGON" \
    --write-xml $CURHGW
fi
ls -lh $CURHGW

CURBU="$OUTPATH/current_building.osm"
if [ ! -f $CURBU ]; then
    osmosis \
    --read-pbf $PBFFILE \
    --tag-filter accept-ways "building=*" "leisure=swimming_pool" \
    --tf reject-relations --used-node outPipe.0=waydata \
    \
    --read-pbf $PBFFILE \
    --tag-filter accept-relations "building=*" "leisure=swimming_pool" \
    --used-way --used-node outPipe.0=reldata \
    \
    --merge inPipe.0=waydata inPipe.1=reldata \
    --bounding-polygon file="$POLYGON" \
    --write-xml $CURBU
fi
ls -lh $CURBU

