#!/usr/bin/env bash
# Install Docker Engine from Docker's official Ubuntu package repository.
# Run in Ubuntu: bash scripts/install-docker-wsl.sh
set -euo pipefail

source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 24.04 ]]; then
    echo "This setup script targets Ubuntu 24.04." >&2
    exit 1
fi
if command -v docker >/dev/null 2>&1; then
    echo "Docker already exists. Inspect its configuration before reinstalling."
    exit 0
fi

sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl --fail --show-error --silent --location \
    https://download.docker.com/linux/ubuntu/gpg \
    --output /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

architecture=$(dpkg --print-architecture)
printf '%s\n' \
    'Types: deb' \
    'URIs: https://download.docker.com/linux/ubuntu' \
    'Suites: noble' \
    'Components: stable' \
    "Architectures: $architecture" \
    'Signed-By: /etc/apt/keyrings/docker.asc' \
    | sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
sudo systemctl start docker
sudo docker version
sudo docker info --format 'Docker storage: {{.DockerRootDir}}'
echo 'Docker installed. GPU container access is the next verification step.'
