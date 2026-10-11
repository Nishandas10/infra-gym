"""Generate scenarios/<id>/ (instances) and scenarios/CATALOG.md from templates/.

usage:
  python scripts/generate.py            # write every instance and the catalog
  python scripts/generate.py --check    # exit 1 if any instance is out of date (CI)
  python scripts/generate.py --index    # only rebuild scenarios/CATALOG.md

Never edit scenarios/<id>/ by hand: edit templates/<family>/<id>/ and regenerate.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gym.core import generate  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="fail if scenarios/ differs from the templates")
    p.add_argument("--index", action="store_true", help="only rebuild scenarios/CATALOG.md")
    args = p.parse_args()
    built = generate.build_all()
    if args.check:
        problems = generate.stale(built)
        if problems:
            print("scenarios/ is out of date with templates/ (run: python scripts/generate.py):")
            for pr in problems:
                print("  -", pr)
            sys.exit(1)
        print(f"{len(built)} instances up to date")
        return
    if not args.index:
        generate.write(built)
        print(f"generated {len(built)} instances")
    (generate.SCENARIOS / "CATALOG.md").write_text(generate.catalog_markdown(built))
    print("wrote scenarios/CATALOG.md")


if __name__ == "__main__":
    main()
