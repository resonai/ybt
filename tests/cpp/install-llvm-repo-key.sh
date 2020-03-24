#!/bin/bash
set -e
curl https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
apt-get update
apt-get --yes install software-properties-common
apt-add-repository "deb http://apt.llvm.org/bionic/ llvm-toolchain-bionic-8 main"
apt-get update
