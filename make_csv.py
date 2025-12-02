#!/usr/bin/env python3
"""Convert `registrants.json` into `registrants.csv`.

Columns: registration_id, name, roll_last5, paid, tshirt_size
Sorted by `registration_id`.
"""
import argparse
import csv
import json
import sys


def get_tshirt_size(item):
    # common keys observed in data
    for k in ("tshirt_size", "tshirt", "t_shirt", "t_shirt_size", "size"):
        v = item.get(k)
        if v:
            return v
    return ""


def main(argv=None):
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser(description="Make CSV from registrants.json")
    p.add_argument("-i", "--input", default="registrants.json", help="input JSON file")
    p.add_argument("-o", "--output", default="registrants.csv", help="output CSV file")
    args = p.parse_args(argv)

    try:
        with open(args.input, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {args.input}: {e}", file=sys.stderr)
        return 2

    rows = []
    for item in data:
        reg_id = item.get("registration_id", "")
        name = item.get("name", "")
        roll_full = item.get("roll", "")
        roll_last5 = roll_full[-5:] if roll_full else ""
        paid = item.get("paid", "")
        tshirt = get_tshirt_size(item)
        rows.append({
            "registration_id": reg_id,
            "name": name,
            "roll_last5": roll_last5,
            "paid": paid,
            "tshirt_size": tshirt,
        })

    # sort by registration_id (empty ids go last)
    rows.sort(key=lambda r: (r["registration_id"] is None, r["registration_id"]))

    with open(args.output, "w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["registration_id", "name", "roll_last5", "paid", "tshirt_size"])
        for r in rows:
            writer.writerow([r["registration_id"], r["name"], r["roll_last5"], r["paid"], r["tshirt_size"]])

    print(f"Wrote {len(rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
