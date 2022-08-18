#!/bin/bash
t1=$1/$3
t2=$2/$3
left="$1/$3/tasks/*.gz"
right="$2/$3/tasks/*.gz"

function countexp {
    echo $(zegrep -c "$1" $2 | cut -d":" -f2 | paste -sd+ | bc)
}

function outrow {
    t="$1"
    exp="$2"
    leftcount=$(countexp "$exp" "$left")
    rightcount=$(countexp "$exp" "$right")
    diff=$(($rightcount - $leftcount))
    echo $t $leftcount $rightcount $diff
}

function tasks {
    leftcount=$(grep -c localId $t1/zoning.geojson)
    rightcount=$(grep -c localId $t2/zoning.geojson)
    diff=$(($rightcount - $leftcount))
    echo tareas $leftcount $rightcount $diff
}

function table {
    echo "exp $t1 $t2 diff"
    outrow nodos "<node"
    outrow vías "<way"
    outrow relaciones "<relation"
    outrow edificios 'k="[^=]*building"'
    outrow partes 'building:part'
    outrow piscinas 'swimming_pool'
    outrow direcciones "addr:postcode"
    tasks
}

table | column -t -s' '
