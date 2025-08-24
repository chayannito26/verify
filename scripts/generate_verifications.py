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

def render_template(template_text: str, data: dict, extra: dict | None = None) -> str:
    out = template_text
    revoked = True if data.get("revoked") is True else False

    # Accent mapping
    if revoked:
        title_status = "Revoked"
        avatar_border_class = "border-red-500"
        avatar_filter_class = "grayscale"
        status_badge_bg = "bg-red-500"
        status_icon_path = "M6 18L18 6M6 6l12 12"
        status_text_class = "text-red-600"
        status_text = "Registration Revoked"
        footer_bar_bg_class = "bg-red-50"
        footer_bar_border_class = "border-red-100"
        id_text_class = "text-red-800"
        id_badge_bg_class = "bg-red-200"
        revoked_banner = (
            '<div class="mb-4 w-full max-w-sm rounded-xl border border-red-200 '
            'bg-red-50 text-red-700 px-4 py-3 text-sm font-medium">'
            'This registration has been revoked. If you believe this is an error, please contact the organizers.'
            "</div>"
        )
    else:
        title_status = "Verified"
        avatar_border_class = "border-green-500"
        avatar_filter_class = ""
        status_badge_bg = "bg-green-500"
        status_icon_path = "M5 13l4 4L19 7"
        status_text_class = "text-green-600"
        status_text = "Registration Verified"
        footer_bar_bg_class = "bg-green-50"
        footer_bar_border_class = "border-green-100"
        id_text_class = "text-green-800"
        id_badge_bg_class = "bg-green-200"
        revoked_banner = ""

    placeholders = {
        "name": data.get("name", ""),
        "roll": data.get("roll", ""),
        "gender": data.get("gender", ""),
        "registration_date": data.get("registration_date", ""),
        "registration_id": data.get("registration_id", ""),
        "photo": data.get("photo", "") or f"https://chayannito26.com/college-students/images/bulbul/{data.get('roll', 'placeholder')}.jpg",
        # New dynamic placeholders
        "title_status": title_status,
        "avatar_border_class": avatar_border_class,
        "avatar_filter_class": avatar_filter_class,
        "status_badge_bg": status_badge_bg,
        "status_icon_path": status_icon_path,
        "status_text_class": status_text_class,
        "status_text": status_text,
        "footer_bar_bg_class": footer_bar_bg_class,
        "footer_bar_border_class": footer_bar_border_class,
        "id_text_class": id_text_class,
        "id_badge_bg_class": id_badge_bg_class,
        "revoked_banner": revoked_banner,
        # new default placeholder so template never shows raw braces
        "referred_by_section": "",
    }
    if extra:
        placeholders.update(extra)
    for key, val in placeholders.items():
        out = out.replace("{{" + key + "}}", str(val))
    return out

def render_master_list(registrants, links, ref_cells) -> str:
    """Create the master_list.html content with Tailwind styling."""
    rows = []
    for (reg, link, ref_cell) in zip(registrants, links, ref_cells):
        rows.append(f"""
        <tr class="hover:bg-green-50 transition-colors">
            <td class="px-6 py-4 font-semibold text-gray-800">
                <a href="{link}" class="text-green-600 hover:underline">{reg['name']}</a>
            </td>
            <td class="px-6 py-4 text-gray-600">{reg['roll']}</td>
            <td class="px-6 py-4 font-mono text-sm text-green-800">{reg['registration_id']}</td>
            <td class="px-6 py-4 text-gray-600">{reg['registration_date']}</td>
            <td class="px-6 py-4">{ref_cell}</td>
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
            <th class="px-6 py-3 text-left text-xs font-bold text-green-800 uppercase tracking-wider">Referred By</th>
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

def write_if_changed(path: Path, content: str) -> bool:
    """Write only if content differs. Returns True if written."""
    if path.exists():
        try:
            old = path.read_text(encoding="utf-8")
            if old == content:
                print(f"Unchanged: {path}")
                return False
        except Exception:
            pass
    path.write_text(content, encoding="utf-8")
    print(f"Wrote: {path}")
    return True

# ---- Referral helpers ----
def _build_indexes(registrants):
    by_id = {}
    by_roll = {}
    by_name = {}
    for r in registrants:
        rid = r.get("registration_id")
        if rid:
            by_id[rid] = r
        roll = r.get("roll")
        if roll:
            by_roll[roll] = r
        name = r.get("name")
        if name:
            by_name[name.strip().lower()] = r
    return by_id, by_roll, by_name

def _resolve_referer(ref_value, by_id, by_roll, by_name):
    if not ref_value or not isinstance(ref_value, str):
        return None
    ref_value = ref_value.strip()
    # Prefer registration_id
    if ref_value in by_id:
        return by_id[ref_value]
    # Try roll
    if ref_value in by_roll:
        return by_roll[ref_value]
    # Try case-insensitive name
    key = ref_value.lower()
    if key in by_name:
        return by_name[key]
    return None

def _build_ref_section(entry, by_id, by_roll, by_name, id_to_file):
    ref_val = entry.get("referred_by")
    if not ref_val:
        return ""
    referer = _resolve_referer(ref_val, by_id, by_roll, by_name)
    if referer:
        href = id_to_file.get(referer.get("registration_id"), "#")
        label = referer.get("name", ref_val)
        return f'''
                <div class="flex justify-between items-center">
                    <span class="text-gray-500 font-medium">Referred By</span>
                    <a href="{href}" class="text-green-600 hover:underline font-semibold">{label}</a>
                </div>
        '''
    # fallback: show text as-is
    safe_text = str(ref_val)
    return f'''
                <div class="flex justify-between items-center">
                    <span class="text-gray-500 font-medium">Referred By</span>
                    <span class="text-gray-800 font-semibold">{safe_text}</span>
                </div>
    '''

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

    # Build filename mapping first (stable, based on registration_id only)
    id_to_file = {}
    for r in registrants:
        reg_id = r.get("registration_id", "")
        if reg_id:
            id_to_file[reg_id] = f"{id_to_filename(reg_id)}.html"

    # Build lookup indexes for referral resolution
    by_id, by_roll, by_name = _build_indexes(registrants)

    links = []
    ref_cells = []
    for entry in registrants:
        reg_id = entry.get("registration_id", "")
        if not reg_id:
            print("Skipping entry without registration_id:", entry)
            links.append("#")
            ref_cells.append("—")
            continue

        filename = id_to_file[reg_id]
        out_path = Path(OUTPUT_DIR) / filename

        # Build referral UI snippet for detail page
        ref_section = _build_ref_section(entry, by_id, by_roll, by_name, id_to_file)

        rendered = render_template(template_text, entry, {"referred_by_section": ref_section})
        write_if_changed(out_path, rendered)
        print(f"(from registration_id: {reg_id})")

        # For master list: pre-render a compact cell (link if resolvable)
        ref_val = entry.get("referred_by")
        referer = _resolve_referer(ref_val, by_id, by_roll, by_name) if ref_val else None
        if referer:
            ref_link = id_to_file.get(referer["registration_id"], "#")
            ref_cells.append(f'<a href="{ref_link}" class="text-green-600 hover:underline">{referer["name"]}</a>')
        else:
            ref_cells.append("—")

        links.append(filename)

    # Generate master list
    master_html = render_master_list(registrants, links, ref_cells)
    write_if_changed(Path(OUTPUT_DIR, "master_list.html"), master_html)

if __name__ == "__main__":
    main()
