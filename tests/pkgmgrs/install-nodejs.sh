#!/bin/sh

sudo -E bash setup_4.x \
  && sudo apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

