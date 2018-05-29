#!/bin/sh

set -e
bash setup_10.x
apt-get install -y --no-install-recommends nodejs
rm -rf /var/lib/apt/lists/*

