#!/usr/bin/env bash
# Follow NVIDIA's apt installation guide for GPU access from Docker in WSL.
set -euo pipefail

source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 24.04 ]]; then
    echo 'This script targets Ubuntu 24.04.' >&2
    exit 1
fi
command -v docker >/dev/null
if [[ -n "$(sudo docker ps -q)" ]]; then
    echo 'Running containers detected. Stop them deliberately before configuring Docker.' >&2
    exit 1
fi

sudo apt-get update
sudo apt-get install -y --no-install-recommends ca-certificates curl gnupg2
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | sudo gpg --batch --yes --dearmor \
        -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
sudo apt-get update
sudo apt-get install -y \
    nvidia-container-toolkit=1.20.0-1 \
    nvidia-container-toolkit-base=1.20.0-1 \
    libnvidia-container-tools=1.20.0-1 \
    libnvidia-container1=1.20.0-1

# Preserve an existing Docker configuration before NVIDIA adds its runtime.
if sudo test -f /etc/docker/daemon.json; then
    backup_path=$(sudo mktemp /etc/docker/daemon.json.turboserve-backup.XXXXXX)
    sudo cp -p /etc/docker/daemon.json "$backup_path"
    echo "Saved Docker configuration: $backup_path"
fi
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
nvidia-ctk --version

# This disposable container tests GPU visibility; it does not load an LLM.
sudo docker run --rm --runtime=nvidia --gpus all ubuntu:24.04 nvidia-smi
echo 'GPU container test passed.'
