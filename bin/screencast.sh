#!/bin/bash

function pausa {
    xdotool windowactivate $WINDOW1
    echo "press key"
    read -rsn1 key < /dev/tty
    xdotool windowactivate $WINDOW2
    sleep 1
}

WINDOW1=$(xdotool getactivewindow)
INPUT=$1
OUTPUT=${INPUT%.*}.cast
xdotool key "ctrl+shift+n"
sleep 1
WINDOW2=$(xdotool getactivewindow)
xdotool windowactivate $WINDOW2

sleep 1
xdotool type "asciinema  rec -i 1 --overwrite $OUTPUT"
xdotool key Return
sleep 1

IFS=''
while read -r line
do
    echo $line
    xdotool type --delay 140 "$line"
    pausa
    xdotool key Return
    pausa
done < $INPUT

xdotool key ctrl+d
xdotool key ctrl+d

#sleep 1
#asciinema play -i 1 $OUTPUT

