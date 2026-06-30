#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo:" >&2
  echo "  sudo bash scripts/setup_gpu_runtime_deps.sh" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  build-essential \
  cmake \
  ninja-build \
  pkg-config \
  nvidia-cuda-toolkit

echo
echo "Installed toolchain versions:"
cmake --version | head -n 1 || true
g++ --version | head -n 1 || true
nvcc --version | tail -n 1 || true

echo
echo "GPU visibility:"
nvidia-smi || true
