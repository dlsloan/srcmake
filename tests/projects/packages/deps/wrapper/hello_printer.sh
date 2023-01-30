#!/bin/bash

SOURCE="${BASH_SOURCE[0]}"
if [[ "${SOURCE:0:1}" != '/' ]]; then
    SOURCE="$(pwd)/${SOURCE}"
fi
SRC_DIR=$(dirname "${SOURCE}")
# Remember the cp hack will be called from inside _pkg/wrapper
cp -r "${SRC_DIR}/../../../deps/hello_printer/"* ./
