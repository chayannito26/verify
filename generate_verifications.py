#!/usr/bin/env python3
"""
generate_verifications.py

- Generates per-registrant verification HTML files.
- Generates 'master_list.html'.
- Copies static pages (index.html, 404.html) into the output dir.

Usage examples:
  - CI full build to dist/:       python3 generate_verifications.py --out ../dist --clean
  - Local quick sample build:     python3 generate_verifications.py --out ../dist --clean --limit 10
  - Build specific IDs only:      python3 generate_verifications.py --out ../dist --ids SC-B-0001,AR-G-0001
"""

import json
import base64
import codecs
import shutil
import argparse
from pathlib import Path
from typing import Iterable, Optional

# Rich: pretty console, spinners, progress bars, traceback
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TaskProgressColumn
from rich.traceback import install as rich_traceback_install
from rich.panel import Panel
from rich.theme import Theme

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent

# --- Constants ---
# These IDs will always be generated, even if not in registrants.json
PLACEHOLDER_IDS = ["AR-B-0001", "SC-G-0001", "CO-B-0001"]
# Path definitions
ROOT_DIR = SCRIPT_DIR
REG_JSON = SCRIPT_DIR / "registrants.json"
TEMPLATE_FILE = SCRIPT_DIR / "template.html"

# Rich setup
CUSTOM_THEME = Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "bold red",
    "path": "magenta",
})
console = Console(theme=CUSTOM_THEME)
rich_traceback_install(show_locals=False)

def id_to_filename(reg_id: str) -> str:
    b64 = base64.urlsafe_b64encode(reg_id.encode('utf-8')).decode('utf-8')
    b64 = b64.rstrip("=")
    rot = codecs.encode(b64, "rot_13")
    return rot[::-1]

def render_template(template_text: str, data: dict, extra: dict | None = None) -> str:
    out = template_text
    revoked = True if data.get("revoked") is True else False
    is_placeholder = data.get("is_placeholder", False)

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
    elif is_placeholder:
        title_status = "Not Registered"
        avatar_border_class = "border-gray-300"
        avatar_filter_class = "grayscale"
        status_badge_bg = "bg-gray-400"
        status_icon_path = "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        status_text_class = "text-gray-600"
        status_text = "Not Yet Registered"
        footer_bar_bg_class = "bg-gray-50"
        footer_bar_border_class = "border-gray-100"
        id_text_class = "text-gray-800"
        id_badge_bg_class = "bg-gray-200"
        revoked_banner = (
            '<div class="mb-4 w-full max-w-sm rounded-xl border border-amber-200 '
            'bg-amber-50 text-amber-800 px-4 py-3 text-sm font-medium">'
            'No one has registered for this slot yet. Please retry later.'
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
        "photo": data.get("photo", "") or f"https://chayannito26.com/college-students/images/{data.get('roll', 'placeholder')}.jpg",
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
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">Total: {len(registrants)}</span>
        <a href="https://shop.chayannito26.com" target="_blank" rel="noopener noreferrer"
           class="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-emerald-500 to-green-600 px-3 py-2 text-white text-sm font-semibold shadow hover:from-emerald-600 hover:to-green-700 focus:outline-none focus:ring-2 focus:ring-emerald-400">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-90" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16 11V7a4 4 0 10-8 0v4M5 9h14l-1 10a2 2 0 01-2 2H8a2 2 0 01-2-2L5 9z" />
          </svg>
          Shop
        </a>
      </div>
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
                console.print(f"Unchanged: [path]{path}[/path]", style="warning")
                return False
        except Exception as e:
            console.print(f"[warning]Could not read existing file[/warning] [path]{path}[/path]: {e}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    console.print(f":white_check_mark: [success]Wrote[/success] [path]{path}[/path]")
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

def _copy_static_pages(out_dir: Path):
    """Copy index.html, 404.html and registrants.json from repo root (verify/) into out_dir."""
    for name in ("index.html", "404.html"):
        src = ROOT_DIR / name
        if src.is_file():
            dst = out_dir / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            console.print(f":page_facing_up: Copied [path]{src}[/path] -> [path]{dst}[/path]", style="info")
        else:
            console.print(f"[warning]Static page not found:[/warning] [path]{src}[/path]")

    # Copy the registrants.json file so the output bundle includes the source data
    if REG_JSON.is_file():
        dst = out_dir / REG_JSON.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REG_JSON, dst)
        console.print(f":page_facing_up: Copied [path]{REG_JSON}[/path] -> [path]{dst}[/path]", style="info")
    else:
        console.print(f"[warning]registrants.json not found:[/warning] [path]{REG_JSON}[/path]")

def _filter_registrants(registrants: list[dict], ids: Optional[Iterable[str]], limit: Optional[int]) -> list[dict]:
    if ids:
        wanted = {i.strip() for i in ids if i and i.strip()}
        return [r for r in registrants if r.get("registration_id") in wanted]
    if isinstance(limit, int) and limit > 0:
        return registrants[:limit]
    return registrants

def main(argv: Optional[list[str]] = None):
    parser = argparse.ArgumentParser(description="Generate verification pages")
    parser.add_argument("--out", default=str(ROOT_DIR / "dist"), help="Output directory for generated site")
    parser.add_argument("--clean", action="store_true", help="Clean output directory before generating")
    parser.add_argument("--limit", type=int, default=None, help="Generate only first N registrants")
    parser.add_argument("--ids", type=str, default=None, help="Comma-separated registration_id list to generate")
    parser.add_argument("--no-static", action="store_true", help="Do not copy index.html and 404.html into output")
    args = parser.parse_args(argv)

    console.rule("[bold cyan]Chayannito 26 – Verification Generator")

    # Prepare output directory
    with console.status("[cyan]Preparing output directory..."):
        out_dir = Path(args.out).resolve()
        if args.clean and out_dir.exists():
            console.print(f":broom: [warning]Cleaning[/warning] [path]{out_dir}[/path]")
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    # Validate and load inputs
    with console.status("[cyan]Loading template and data..."):
        if not REG_JSON.is_file():
            console.print(f"[error]Error:[/error] [path]{REG_JSON}[/path] not found.")
            return
        if not TEMPLATE_FILE.is_file():
            console.print(f"[error]Error:[/error] [path]{TEMPLATE_FILE}[/path] not found.")
            return
        template_text = TEMPLATE_FILE.read_text(encoding="utf-8")
        with open(REG_JSON, "r", encoding="utf-8") as f:
            all_registrants = json.load(f)

    # --- Add placeholder entries for special IDs if they don't exist ---
    existing_ids = {r["registration_id"] for r in all_registrants if "registration_id" in r}
    for reg_id in PLACEHOLDER_IDS:
        if reg_id not in existing_ids:
            all_registrants.append({
                "registration_id": reg_id,
                "name": "Not Yet Registered",
                "roll": "N/A",
                "gender": "N/A",
                "registration_date": "N/A",
                "photo": "https://chayannito26.com/college-students/images/placeholder.jpg",
                "revoked": False,
                "referred_by": "",
                "is_placeholder": True,
            })

    # Apply filters for local testing
    ids_list = [s for s in (args.ids.split(",") if args.ids else []) if s]
    registrants = _filter_registrants(all_registrants, ids_list or None, args.limit)
    console.print(f":mag: [info]Filtered registrants:[/info] {len(registrants)}")

    # Mapping and indexes based on filtered set
    id_to_file = {}
    for r in registrants:
        reg_id = r.get("registration_id", "")
        if reg_id:
            id_to_file[reg_id] = f"{id_to_filename(reg_id)}.html"

    by_id, by_roll, by_name = _build_indexes(registrants)

    # Render pages with a progress bar
    links = []
    ref_cells = []
    files_written = 0
    files_unchanged = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Rendering registrant pages", total=len(registrants))
        for entry in registrants:
            reg_id = entry.get("registration_id", "")
            if not reg_id:
                console.print("[warning]Skipping entry without registration_id:[/warning] " + str(entry))
                links.append("#")
                ref_cells.append("—")
                progress.advance(task)
                continue

            filename = id_to_file[reg_id]
            out_path = out_dir / filename

            ref_section = _build_ref_section(entry, by_id, by_roll, by_name, id_to_file)
            rendered = render_template(template_text, entry, {"referred_by_section": ref_section})

            changed = write_if_changed(out_path, rendered)
            files_written += int(changed)
            files_unchanged += int(not changed)

            ref_val = entry.get("referred_by")
            referer = _resolve_referer(ref_val, by_id, by_roll, by_name) if ref_val else None
            if referer:
                ref_link = id_to_file.get(referer["registration_id"], "#")
                ref_cells.append(f'<a href="{ref_link}" class="text-green-600 hover:underline">{referer["name"]}</a>')
            else:
                ref_cells.append("—")

            links.append(filename)
            progress.advance(task)

    # Filter out placeholder registrants from the master list
    final_registrants_for_master_list = [r for r in registrants if not r.get("is_placeholder")]
    final_links = [links[i] for i, r in enumerate(registrants) if not r.get("is_placeholder")]
    final_ref_cells = [ref_cells[i] for i, r in enumerate(registrants) if not r.get("is_placeholder")]

    master_html = render_master_list(final_registrants_for_master_list, final_links, final_ref_cells)
    changed_master = write_if_changed(out_dir / "master_list.html", master_html)

    # Copy static files unless explicitly disabled
    if not args.no_static:
        _copy_static_pages(out_dir)

    console.print(Panel.fit(
        f"Total registrants processed: {len(registrants)}\n"
        f"Registrants in master list: {len(final_registrants_for_master_list)}\n"
        f"Generated pages: {files_written}\n"
        f"Unchanged pages: {files_unchanged}\n"
        f"master_list.html: {'updated' if changed_master else 'unchanged'}\n"
        f"Output: [path]{out_dir}[/path]",
        title="Summary",
        border_style="green"
    ))

if __name__ == "__main__":
    main()
