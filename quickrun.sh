#!/bin/bash
if [ -z $1 ];
then
  NAME="cacophony"
else
  NAME=$1
fi

PYTHONPATH=src:$PYTHONPATH python -m cacophony $NAME
