#!/usr/bin/env python3
"""
generate_verifications.py

Reads 'registrants.json' and 'template.html', then writes one HTML file per registrant
into a 'verify' folder. Filenames are produced as:
    base64(registration_id) -> rot13(base64) -> reversed string + ".html"

Notes:
 - We use URL-safe base64 and strip '=' padding so filenames won't include '/' or '+'.
 - Rot13 is applied to letters only (Python codecs.encode(..., 'rot_13')).
"""

import os
import json
import base64
import codecs
from pathlib import Path

# Config / filenames
REG_JSON = "registrants.json"
TEMPLATE_FILE = "template.html"
OUTPUT_DIR = "../."

def id_to_filename(reg_id: str) -> str:
    """
    Produce filename from registration id:
      1) urlsafe base64 (no padding)
      2) rot13 on the base64 string
      3) reverse the resulting string
    Returns the filename WITHOUT the .html extension.
    """
    # 1) urlsafe base64 (bytes -> b64 -> decode)
    b64 = base64.urlsafe_b64encode(reg_id.encode('utf-8')).decode('utf-8')
    # 2) strip padding to keep filenames shorter and avoid '=' at end if present
    b64 = b64.rstrip('=')
    # 3) apply rot13
    rot = codecs.encode(b64, 'rot_13')
    # 4) reverse
    rev = rot[::-1]
    return rev

def render_template(template_text: str, data: dict) -> str:
    """
    Simple placeholder replacement. Template placeholders are {{name}}, {{roll}}, etc.
    """
    out = template_text
    # safe defaults for placeholders
    placeholders = {
        "name": data.get("name", ""),
        "roll": data.get("roll", ""),
        "gender": data.get("gender", ""),
        "registration_date": data.get("registration_date", ""),
        "registration_id": data.get("registration_id", ""),
        "photo": data.get("photo", "")
    }
    for key, val in placeholders.items():
        out = out.replace("{{" + key + "}}", str(val))
    return out

def main():
    # ensure files exist
    if not Path(REG_JSON).is_file():
        print(f"Error: {REG_JSON} not found.")
        return
    if not Path(TEMPLATE_FILE).is_file():
        print(f"Error: {TEMPLATE_FILE} not found.")
        return

    # load template
    template_text = Path(TEMPLATE_FILE).read_text(encoding='utf-8')

    # load registrants
    with open(REG_JSON, 'r', encoding='utf-8') as f:
        registrants = json.load(f)

    # create output directory
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # generate files
    for entry in registrants:
        reg_id = entry.get("registration_id", "")
        if not reg_id:
            print("Skipping entry without registration_id:", entry)
            continue

        base_name = id_to_filename(reg_id)
        filename = f"{base_name}.html"
        out_path = Path(OUTPUT_DIR) / filename

        rendered = render_template(template_text, entry)
        out_path.write_text(rendered, encoding='utf-8')
        print(f"Wrote: {out_path}  (from registration_id: {reg_id})")

if __name__ == "__main__":
    main()
