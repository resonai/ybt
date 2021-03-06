#!/bin/bash

set -e

mv go /usr/local

# Creating GOPATH and allowing access to all users
mkdir "$GOPATH"
# Support for grpc generation.
# TODO(eyal): For some reason when using Apt installer deps for git go get
#             doesn't work due to missing certificate.
#             Figure this out and remove this.
apt update
apt-get install -y git

go get github.com/golang/protobuf/protoc-gen-go
chmod -R 777 "$GOPATH"
