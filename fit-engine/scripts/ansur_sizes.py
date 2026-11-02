"""Build letter-size body tables from ANSUR II, following the ISO 8559-3 approach.

  python -I scripts/ansur_sizes.py            # downloads ANSUR II to research/ansur2 if missing

Method (project's reading of ISO 8559-2/-3; the standard text itself is not reproduced):
- primary dimension for tops is chest girth (ISO 8559-2); secondaries: waist, hip, stature
- the central 90% of the population (P5-P95 of chest) is split into 5 equal intervals, XS-XL;
  2XL and 3XL continue the same interval width above P95 (inclusive range for larger bodies)
- each size reports its chest interval, coverage, and median secondaries of the people in it

ANSUR II (US Army 2012, public domain): chestcircumference, waistcircumference,
buttockcircumference and stature, in mm. Military sample: fitter and younger than the
general population, so these are not a retail chart for any specific market.
"""
import csv
import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "research/ansur2"
OUT = ROOT / "fit-engine/stylewise_fit/data/size_chart_ansur2.json"
URLS = {"female": "https://tools.openlab.psu.edu/publicData/ANSUR_II_FEMALE_Public.csv",
        "male": "https://tools.openlab.psu.edu/publicData/ANSUR_II_MALE_Public.csv"}
SIZES = ("XS", "S", "M", "L", "XL")
EXTENDED = ("2XL", "3XL")
COLS = {"chest": "chestcircumference", "waist": "waistcircumference",
        "hip": "buttockcircumference", "height": "stature"}


def load(sex: str) -> tuple[dict[str, np.ndarray], str]:
    path = RAW / f"{sex}.csv"
    if not path.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URLS[sex], path)
    rows = list(csv.DictReader(path.open(encoding="latin-1")))
    key = {c.lower(): c for c in rows[0]}
    data = {k: np.array([float(r[key[c]]) / 10.0 for r in rows]) for k, c in COLS.items()}  # mm -> cm
    return data, hashlib.sha256(path.read_bytes()).hexdigest()


def table(d: dict[str, np.ndarray]) -> list[dict]:
    lo, hi = np.percentile(d["chest"], [5, 95])
    step = (hi - lo) / len(SIZES)
    # extended sizes continue the same step past P95 so larger bodies are not dropped
    edges = np.round(lo + step * np.arange(len(SIZES) + len(EXTENDED) + 1), 1)
    out = []
    for i, size in enumerate(SIZES + EXTENDED):
        a, b = edges[i], edges[i + 1]
        # half-open [a, b); XL is closed at P95 so XS-XL stay exactly the central 90%
        m = (d["chest"] > a) & (d["chest"] <= b) if size in EXTENDED else \
            (d["chest"] >= a) & ((d["chest"] <= b) if size == SIZES[-1] else (d["chest"] < b))
        out.append({
            "size": size, "chest_min_cm": float(a), "chest_max_cm": float(b),
            "chest_cm": round(float(a + b) / 2, 1),  # interval midpoint: the size's anchor
            "n": int(m.sum()), "coverage": round(float(m.mean()), 3),
            **{f"median_{k}_cm": round(float(np.median(d[k][m])), 1) for k in ("waist", "hip", "height")},
        })
    return out


def main() -> None:
    chart = {"source": "ANSUR II public data (Gordon et al. 2014, US Army NSRDEC), via openlab.psu.edu",
             "method": "ISO 8559-3 approach: chest primary, P5-P95 split into 5 equal intervals",
             "sexes": {}}
    for sex in ("female", "male"):
        d, sha = load(sex)
        chart["sexes"][sex] = {"n": len(d["chest"]), "sha256": sha, "sizes": table(d)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(chart, indent=2) + "\n")
    for sex, s in chart["sexes"].items():
        print(sex, [(r["size"], r["chest_cm"], r["n"]) for r in s["sizes"]])


if __name__ == "__main__":
    main()
