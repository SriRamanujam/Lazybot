#!/usr/bin/env bash

NAME=$1

if [[ -n "$NAME" ]]; then
    docker run --rm --name="$NAME" $(docker build .)
else
    exit 1
fi
