import argparse
import json
import sys

from .fit import evaluate
from .schemas import FitRequest


def main() -> None:
    p = argparse.ArgumentParser(prog="stylewise-fit")
    sub = p.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("evaluate", help="FitRequest JSON -> FitReport JSON")
    ev.add_argument("request", help="path to FitRequest JSON, or - for stdin")
    args = p.parse_args()

    raw = sys.stdin.read() if args.request == "-" else open(args.request).read()
    report = evaluate(FitRequest.model_validate_json(raw))
    json.dump(report.model_dump(), sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
