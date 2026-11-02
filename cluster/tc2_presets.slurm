#!/bin/bash
# TC2 campus cluster (Slurm, unconfirmed). Submit from the repo root:  sbatch cluster/tc2_presets.slurm
# Fill in partition/qos from `sinfo` and `sacctmgr show assoc user=$USER format=account,qos`.
#SBATCH --job-name=stylewise-presets
#SBATCH --partition=CHANGE_ME
#SBATCH --qos=CHANGE_ME
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=stylewise-presets-%j.log

cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS=1
research/mhr-env/bin/python -W ignore fit-engine/scripts/gen_presets.py \
  --workers "$SLURM_CPUS_PER_TASK" --max-nfev 25 --out fixtures/presets
