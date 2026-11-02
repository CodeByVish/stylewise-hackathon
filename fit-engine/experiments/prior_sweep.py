"""Which prior weight lets extreme shapes (hourglass, oval) reach their targets?

  research/mhr-env/bin/python -W ignore fit-engine/experiments/prior_sweep.py
"""
from concurrent.futures import ProcessPoolExecutor


def run(args):
    shape, prior_weight = args
    from stylewise_fit.mhr_body import fit
    from stylewise_fit.presets import classify, estimate

    e = estimate(shape, "M")
    target = {"height": 165.0, "chest": e.chest_cm, "waist": e.waist_cm, "hip": e.hip_cm}
    r = fit(target, max_nfev=25, prior_weight=prior_weight)
    m = r["measured"]
    return (shape, prior_weight, {k: round(v, 2) for k, v in r["error"].items()},
            classify(m["chest"], m["waist"], m["hip"]), round(r["seconds"]))


if __name__ == "__main__":
    grid = [(s, pw) for s in ("hourglass", "oval") for pw in (0.5, 0.2, 0.05)]
    with ProcessPoolExecutor(6) as ex:
        for row in ex.map(run, grid):
            print(row, flush=True)
