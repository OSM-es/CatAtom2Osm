#!/usr/bin/env bash
set -ex

VERSION=$(grep "app_version =" setup.py | cut -d"=" -f2 | tr -d " \"'")

# https://github.com/docker/docker-credential-helpers/issues/102
# This code avoids unencrypted password warning, but user validation don't works
# curl -fsSL "https://github.com/docker/docker-credential-helpers/releases/download/v0.6.3/docker-credential-pass-v0.6.3-amd64.tar.gz" | tar zxv
# DCP_PATH=$(pwd)/docker-credential-pass
# chmod +x $DCP_PATH
# sudo mv $DCP_PATH /usr/local/bin/
# init key for pass
# gpg --batch --gen-key <<-EOF
# %echo Generating a standard key
# Key-Type: DSA
# Key-Length: 1024
# Subkey-Type: ELG-E
# Subkey-Length: 1024
# Name-Real: Javier Sanchez
# Name-Email: javiersanp@gmail.com
# Expire-Date: 0
# %commit
# %echo done
# EOF
# pass init $(gpg --no-auto-check-trustdb --list-secret-keys | grep ^sec | cut -d/ -f2 | cut -d" " -f1)

echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

docker push "$DOCKER_USERNAME"/catatom2osm:latest
docker tag "$DOCKER_USERNAME"/catatom2osm:latest "$DOCKER_USERNAME"/catatom2osm:"$VERSION"
docker push "$DOCKER_USERNAME"/catatom2osm:"$VERSION"
