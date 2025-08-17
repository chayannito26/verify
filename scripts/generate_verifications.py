#!/usr/bin/env python3
"""
generate_verifications.py

- Generates per-registrant verification HTML files in 'verify/'.
- Also generates a 'master_list.html' that lists all registrants with links.
"""

import os
import json
import base64
import codecs
from pathlib import Path

REG_JSON = "registrants.json"
TEMPLATE_FILE = "template.html"
OUTPUT_DIR = "../."

def id_to_filename(reg_id: str) -> str:
    b64 = base64.urlsafe_b64encode(reg_id.encode('utf-8')).decode('utf-8')
    b64 = b64.rstrip("=")
    rot = codecs.encode(b64, "rot_13")
    return rot[::-1]

def render_template(template_text: str, data: dict) -> str:
    out = template_text
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

def render_master_list(registrants, links) -> str:
    """Create the master_list.html content with Tailwind styling."""
    rows = []
    for reg, link in zip(registrants, links):
        rows.append(f"""
        <tr class="hover:bg-green-50 transition-colors">
            <td class="px-6 py-4 font-semibold text-gray-800">
                <a href="{link}" class="text-green-600 hover:underline">{reg['name']}</a>
            </td>
            <td class="px-6 py-4 text-gray-600">{reg['roll']}</td>
            <td class="px-6 py-4 font-mono text-sm text-green-800">{reg['registration_id']}</td>
            <td class="px-6 py-4 text-gray-600">{reg['registration_date']}</td>
        </tr>
        """)
    rows_html = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Master Verified List</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Inter', sans-serif; }}
  </style>
</head>
<body class="bg-gray-100 min-h-screen p-8">
  <div class="max-w-5xl mx-auto bg-white shadow-lg rounded-2xl overflow-hidden">
    <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-slate-700">Chayannito 26 – Master Verified List</h1>
      <span class="text-sm text-gray-500">Total: {len(registrants)}</span>
    </div>
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-green-100">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-bold text-green-800 uppercase tracking-wider">Name</th>
            <th class="px-6 py-3 text-left text-xs font-bold text-green-800 uppercase tracking-wider">Roll</th>
            <th class="px-6 py-3 text-left text-xs font-bold text-green-800 uppercase tracking-wider">Registration ID</th>
            <th class="px-6 py-3 text-left text-xs font-bold text-green-800 uppercase tracking-wider">Date</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-100">
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>
  <footer class="text-center mt-8 text-xs text-gray-400">
    Generated automatically
  </footer>
</body>
</html>"""

def main():
    if not Path(REG_JSON).is_file():
        print(f"Error: {REG_JSON} not found.")
        return
    if not Path(TEMPLATE_FILE).is_file():
        print(f"Error: {TEMPLATE_FILE} not found.")
        return

    template_text = Path(TEMPLATE_FILE).read_text(encoding="utf-8")

    with open(REG_JSON, "r", encoding="utf-8") as f:
        registrants = json.load(f)

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    links = []
    for entry in registrants:
        reg_id = entry.get("registration_id", "")
        if not reg_id:
            print("Skipping entry without registration_id:", entry)
            continue

        base_name = id_to_filename(reg_id)
        filename = f"{base_name}.html"
        out_path = Path(OUTPUT_DIR) / filename

        rendered = render_template(template_text, entry)
        out_path.write_text(rendered, encoding="utf-8")
        print(f"Wrote: {out_path}  (from registration_id: {reg_id})")

        links.append(filename)

    # Generate master list
    master_html = render_master_list(registrants, links)
    Path(OUTPUT_DIR, "master_list.html").write_text(master_html, encoding="utf-8")
    print(f"Master list written to {OUTPUT_DIR}/master_list.html")

if __name__ == "__main__":
    main()
