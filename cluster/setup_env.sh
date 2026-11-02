#!/usr/bin/env bash
# One-time setup on a cluster LOGIN node (NSCC or TC2). Run from the repo root:
#   bash cluster/setup_env.sh
# Creates research/mhr-env (Python 3.12 via uv, CPU torch, MHR, our fit engine) and
# downloads the MHR TorchScript model to research/MHR/assets/mhr_model.pt.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

[ -d research/MHR ] || git clone --depth 1 https://github.com/facebookresearch/MHR research/MHR

# managed Python lives in $HOME (shared with compute nodes); /usr/bin/python3.12 exists only on login nodes
uv venv --clear --python-preference only-managed --python 3.12 research/mhr-env
export VIRTUAL_ENV="$PWD/research/mhr-env"
# CPU wheels: preset generation is bound by mesh slicing, not the model
uv pip install --index-url https://download.pytorch.org/whl/cpu torch
uv pip install trimesh shapely scipy pydantic numpy
uv pip install --no-deps -e ./research/MHR
uv pip install -e ./fit-engine

if [ ! -f research/MHR/assets/mhr_model.pt ]; then
  # 4.8 GB archive; keep it out of the 50 GB home quota if scratch exists
  # ASPIRE 2A scratch is /scratch/users/<inst>/$USER; fall back to the repo if unwritable
  DL="${SCRATCH_DIR:-$PWD/research}/mhr_dl"
  mkdir -p "$DL" 2>/dev/null || { echo "cannot write $DL, using research/mhr_dl"; DL="$PWD/research/mhr_dl"; mkdir -p "$DL"; }
  curl -L -o "$DL/assets.zip" https://github.com/facebookresearch/MHR/releases/latest/download/assets.zip
  unzip -o -q "$DL/assets.zip" assets/mhr_model.pt assets/LICENSE.txt -d research/MHR
  rm -f "$DL/assets.zip"
fi

research/mhr-env/bin/python -W ignore -c "from stylewise_fit.mhr_body import mesh_for; print('MHR ok, height', round(mesh_for([0]*20).bounds[1,1]*100,1), 'cm')"
