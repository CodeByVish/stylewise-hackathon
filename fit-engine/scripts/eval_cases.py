"""Controlled fit cases: known body x garment -> the verdict we expect and why. Prints a markdown
table for the write-up and exits non-zero if any case disagrees.

  python scripts/eval_cases.py
"""
import sys

from stylewise_fit.catalogue import garment_input
from stylewise_fit.fit import evaluate
from stylewise_fit.schemas import BodyInput, FitRequest

B = {"height_cm": 165}
CASES = [  # (label, body, garment_id, size, pref, region, expected verdict, why)
    ("Kurta, roomy chest", B | {"chest_cm": 90}, "green-kurta", "M", None, "chest", "ok",
     "+9 cm is inside the regular band (2-12)"),
    ("Kurta one size down", B | {"chest_cm": 92}, "green-kurta", "XS", None, "chest", "tight",
     "-3 cm, and silk cannot stretch"),
    ("Same kurta, snug preference", B | {"chest_cm": 90}, "green-kurta", "M", "snug", "chest", "loose",
     "+9 cm is above the snug band (0-6)"),
    ("Trousers on elastic waist", B | {"waist_cm": 87, "hip_cm": 100}, "gold-trousers", "M", None, "waist",
     "borderline", "-1 cm relaxed, fits only by using the 6 cm elastic"),
    ("Trousers waist beyond elastic", B | {"waist_cm": 96, "hip_cm": 100}, "gold-trousers", "M", None, "waist",
     "tight", "-10 cm, more than the elastic can give"),
    ("Stretch dress at the bust", B | {"chest_cm": 88}, "uniqlo-dress-E487286", "M", None, "chest",
     "borderline", "-2 cm relaxed; cotton stretch gives ~4 cm"),
    ("Missing hip measurement", B | {"chest_cm": 90}, "green-kurta", "M", None, "hip", "unknown",
     "never estimated when not given"),
    ("Preset body near band edge", {"height_cm": 165, "source": "preset",
     "preset": {"shape": "rectangle", "usual_size": "M", "sex": "female"}}, "green-kurta", "M", None, "chest",
     "borderline", "+3.1 cm ±2.7 crosses the 2 cm minimum"),
]


def main() -> int:
    rows, failed = [], 0
    for label, body, gid, size, pref, region, want, why in CASES:
        report = evaluate(FitRequest(body=BodyInput.model_validate(body), garment=garment_input(gid, size),
                                     preferences={"fit_pref": pref}))
        got = report.regions[region]
        ok = got.verdict == want
        failed += not ok
        ease = "-" if got.ease_cm is None else f"{got.ease_cm:+.1f}"
        rows.append(f"| {label} | {gid} {size} | {region} | {ease} | {want} | {got.verdict} | "
                    f"{'pass' if ok else '**FAIL**'} | {why} |")
    print("| case | garment | region | ease cm | expected | got | | why |\n|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
    print(f"\n{len(CASES) - failed}/{len(CASES)} cases pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
