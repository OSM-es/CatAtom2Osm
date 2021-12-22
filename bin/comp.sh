#!/bin/bash
echo "      OLD NEW"
old="results/$1/tasks/*.gz"
new="results/$2/tasks/*.gz"
exp="<node"
echo $exp $(zegrep -c $exp $old | cut -d":" -f2 | paste -sd+ | bc) $(zegrep -c $exp $new | cut -d":" -f2 | paste -sd+ | bc)
exp="<way"
echo $exp $(zegrep -c $exp $old | cut -d":" -f2 | paste -sd+ | bc) $(zegrep -c $exp $new | cut -d":" -f2 | paste -sd+ | bc)
exp="<relation"
echo $exp $(zegrep -c $exp $old | cut -d":" -f2 | paste -sd+ | bc) $(zegrep -c $exp $new | cut -d":" -f2 | paste -sd+ | bc)
exp='k=".*building"'
echo $exp $(zegrep -c $exp $old | cut -d":" -f2 | paste -sd+ | bc) $(zegrep -c $exp $new | cut -d":" -f2 | paste -sd+ | bc)
exp='building:part'
echo $exp $(zegrep -c $exp $old | cut -d":" -f2 | paste -sd+ | bc) $(zegrep -c $exp $new | cut -d":" -f2 | paste -sd+ | bc)
exp='swimming_pool'
echo $exp $(zegrep -c $exp $old | cut -d":" -f2 | paste -sd+ | bc) $(zegrep -c $exp $new | cut -d":" -f2 | paste -sd+ | bc)
exp="addr:postcode"
echo $exp $(zegrep -c $exp $old | cut -d":" -f2 | paste -sd+ | bc) $(zegrep -c $exp $new | cut -d":" -f2 | paste -sd+ | bc)
