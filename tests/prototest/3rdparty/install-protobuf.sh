#!/bin/sh

cd protobuf-2.6.1/
# cd protobuf-2.5.0/
./configure
make
make check
sudo make install
sudo ldconfig /usr/local/lib

