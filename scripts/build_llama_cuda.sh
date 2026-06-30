#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LLAMA_DIR="${ROOT_DIR}/runtimes/llama.cpp"
BUILD_DIR="${LLAMA_DIR}/build-cuda"

if [[ ! -d "${LLAMA_DIR}" ]]; then
  echo "Missing ${LLAMA_DIR}. Clone llama.cpp into runtimes/llama.cpp first." >&2
  exit 1
fi

export MAX_JOBS="${MAX_JOBS:-2}"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-2}"
export MAKEFLAGS="${MAKEFLAGS:--j2}"

cmake \
  -B "${BUILD_DIR}" \
  -S "${LLAMA_DIR}" \
  -DGGML_CUDA=ON \
  -DGGML_NATIVE=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=89

cmake --build "${BUILD_DIR}" --config Release --target llama-completion -j "${CMAKE_BUILD_PARALLEL_LEVEL}"
cmake --build "${BUILD_DIR}" --config Release --target llama-diffusion-cli -j "${CMAKE_BUILD_PARALLEL_LEVEL}"
