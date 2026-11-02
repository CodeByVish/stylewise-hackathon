# Running Stylewise jobs on NSCC / TC2

These jobs generate the MHR preset bodies (and later the larger B-A/B-B experiments). They are **CPU-bound** (mesh slicing), so request many cores, not GPUs. Run every command from the repo root on the cluster.

## 1. Copy the repo to the cluster (from your Mac)
Until the repo is pushed, rsync it. This skips the local envs and the 4.8 GB archive:
```bash
rsync -av --exclude node_modules --exclude .next --exclude '.venv' \
  --exclude 'research/mhr-env' --exclude 'research/dl' --exclude 'research/MHR/assets' \
  "$HOME/NTU & Opportunities/Hackathons/stylewise-hackathon/" <user>@<login-host>:~/stylewise-hackathon/
```
Once you've pushed, `git clone <your repo url>` on the cluster works instead.

Login hosts:
- **NSCC ASPIRE 2A:** NTU users normally use `aspire2antu.nscc.sg`. Use the host given in your NSCC account email if it differs.
- **TC2:** the campus login host you already use.

## 2. One-time setup (login node, ~10 min)
```bash
ssh <user>@<login-host>
cd ~/stylewise-hackathon
bash cluster/setup_env.sh        # uv + Python 3.12 + CPU torch + MHR + fit engine + model download
```
It ends by printing `MHR ok, height 172.7 cm`. On NSCC, set `SCRATCH_DIR=/scratch/users/ntu/$USER` (check with `ls -d /scratch/users/*/$USER`) before running so the 4.8 GB download goes to scratch.

## 3a. NSCC (PBS Pro)
```bash
qsub cluster/nscc_presets.pbs      # project personal-riddhima, normal queue, 32 cores, 1 h
qstat -u $USER                     # Q = queued, R = running
tail -f stylewise-presets.log      # progress, once it starts
qdel <jobid>                       # cancel if needed
```

## 3b. TC2 (Slurm, verify first)
```bash
sinfo                                                  # if this works it's Slurm; pick a CPU partition
sacctmgr show assoc user=$USER format=account,qos      # your QoS
# edit CHANGE_ME (partition, qos) in cluster/tc2_presets.slurm, then:
sbatch cluster/tc2_presets.slurm
squeue -u $USER
tail -f stylewise-presets-<jobid>.log
scancel <jobid>
```
If `sinfo` isn't found but `qstat` is, TC2 runs PBS. Use the NSCC script with TC2's queue name instead.

## 4. Bring results back (from your Mac)
```bash
rsync -av <user>@<login-host>:~/stylewise-hackathon/fixtures/presets/ ~/stylewise-hackathon/fixtures/presets/
```
`fixtures/presets/index.json` lists each preset with its target cm, measured cm, fit error and FFIT class check. The summary line at the end of the log reports the worst girth error and any shape-class mismatches.

## Quick sanity run (no scheduler)
Use this on a short interactive allocation, not on the login node:
```bash
research/mhr-env/bin/python -W ignore fit-engine/scripts/gen_presets.py --quick --workers 5
```
