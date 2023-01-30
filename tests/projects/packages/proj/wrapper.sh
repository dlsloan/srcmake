#!/bin/bash

SOURCE="${BASH_SOURCE[0]}"
if [[ "${SOURCE:0:1}" != '/' ]]; then
    SOURCE="$(pwd)/${SOURCE}"
fi
SRC_DIR=$(dirname "${SOURCE}")
cp -r "${SRC_DIR}/../deps/wrapper/"* ./
