#!/bin/bash
if [ -z $1 ];
then
  NAME="cacophony"
else
  NAME=$1
fi

PYTHONPATH=.:$PYTHONPATH scripts/app.py $NAME
