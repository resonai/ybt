#!/bin/sh

set -e
cd protobuf-2.6.1/
chmod -R 755 .
./configure
make
make check
make install
ldconfig /usr/local/lib
