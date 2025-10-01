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

# Optional Pillow for meta image generation
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

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
            '<div style="margin-bottom: 1rem; width: 100%; max-width: 24rem; border-radius: 0.75rem; border: 1px solid #fecaca; '
            'background-color: #fef2f2; padding: 1rem; font-size: 0.875rem; font-weight: 500; color: #b91c1c;">'
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
            '<div style="margin-bottom: 1rem; width: 100%; max-width: 24rem; border-radius: 0.75rem; border: 1px solid #fde68a; '
            'background-color: #fffbeb; color: #92400e; padding: 1rem; font-size: 0.875rem; font-weight: 500;">'
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


def generate_meta_card(output_path: Path, name: str, roll: str, registration_id: str, photo_url: str | None, status_text: str, registration_date: str | None = None, site_name: str = "Chayannito 26") -> bool:
    """Generate a social-preview card (1200x630) showing the registrant's name, avatar, roll, registration id and registration date.
    Uses robust text measurement via draw.textbbox. Returns True on success.
    """
    try:
        if not PIL_AVAILABLE:
            console.print("[warning]Pillow not available — skipping meta image generation[/warning]")
            return False

        from io import BytesIO
        import urllib.request

        W, H = 1200, 630
        background = (249, 250, 251)  # light gray canvas
        card_bg = (255, 255, 255)
        accent = (16, 185, 129)  # emerald
        text_dark = (17, 24, 39)
        text_muted = (75, 85, 99)

        img = Image.new("RGB", (W, H), color=background)
        draw = ImageDraw.Draw(img)

        # Card area
        margin = 48
        card_rect = (margin, margin, W - margin, H - margin)
        draw.rounded_rectangle(card_rect, radius=24, fill=card_bg)

        # Fonts: prefer Inter in assets, fall back to DejaVu or default
        def load_font(name, size):
            try:
                p = SCRIPT_DIR / "assets" / name
                return ImageFont.truetype(str(p), size)
            except Exception:
                try:
                    return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
                except Exception:
                    return ImageFont.load_default()

        # Larger, more legible fonts for social preview
        name_font = load_font("Inter-Bold.ttf", 64)
        meta_font = load_font("Inter-Regular.ttf", 32)
        small_font = load_font("Inter-Regular.ttf", 24)
        mono_font = load_font("DejaVuSansMono.ttf", 28)

    # Avatar: larger and vertically centered in the card area so the text can use more space
        avatar_size = 300
        avatar_x = margin + 48
        inner_h = H - margin * 2
        avatar_y = margin + (inner_h - avatar_size) // 2

        avatar = None
        # Build prioritized avatar candidate list
        candidates = []
        if photo_url:
            candidates.append(str(photo_url))
        if roll:
            candidates.append(f"https://chayannito26.com/college-students/images/{roll}.jpg")
            candidates.append(str(SCRIPT_DIR / "assets" / f"{roll}.jpg"))
            candidates.append(str(SCRIPT_DIR / "assets" / f"{roll}.png"))
        if registration_id:
            candidates.append(str(SCRIPT_DIR / "assets" / f"{registration_id}.jpg"))
            candidates.append(str(SCRIPT_DIR / "assets" / f"{registration_id}.png"))

        from io import BytesIO
        import urllib.request
        from urllib.error import HTTPError, URLError

        # Prepare optional SSL context using certifi if available (fix local SSL verification in some envs)
        ssl_context = None
        try:
            import ssl, certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ssl_context = None

        for cand in candidates:
            if not cand:
                continue
            try:
                if cand.lower().startswith("http"):
                    console.print(f"[info]Attempting remote avatar: {cand}[/info]")
                    req = urllib.request.Request(cand, headers={"User-Agent": "chayannito26-meta-generator/1.0"})
                    if ssl_context:
                        with urllib.request.urlopen(req, timeout=6, context=ssl_context) as resp:
                            data = resp.read()
                    else:
                        with urllib.request.urlopen(req, timeout=6) as resp:
                            data = resp.read()
                    avatar = Image.open(BytesIO(data)).convert("RGBA")
                    console.print(f"[success]Loaded remote avatar: {cand}[/success]")
                    break
                else:
                    cpath = Path(cand)
                    console.print(f"[info]Attempting local avatar: {cpath}[/info]")
                    if cpath.is_file():
                        avatar = Image.open(cpath).convert("RGBA")
                        console.print(f"[success]Loaded local avatar: {cpath}[/success]")
                        break
            except (HTTPError, URLError) as e:
                console.print(f"[warning]Remote avatar failed ({cand}): {e}[/warning]")
                avatar = None
            except Exception as e:
                console.print(f"[warning]Avatar candidate error ({cand}): {e}[/warning]")
                avatar = None

        # center-crop to square if needed
        if avatar:
            aw, ah = avatar.size
            if aw != ah:
                side = min(aw, ah)
                left = (aw - side) // 2
                top = (ah - side) // 2
                avatar = avatar.crop((left, top, left + side, top + side))

        if avatar:
            # Resize and crop to square (already center-cropped above), then resize
            avatar = avatar.resize((avatar_size, avatar_size), Image.LANCZOS)
            # Make circular mask and paste with alpha to preserve edges
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            if avatar.mode != "RGBA":
                avatar = avatar.convert("RGBA")
            img.paste(avatar, (avatar_x, avatar_y), mask)
        else:
            # Draw placeholder circle with initials
            circle_bbox = (avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size)
            draw.ellipse(circle_bbox, fill=accent)
            # initials (use a font sized relative to avatar)
            initials = "".join([p[0].upper() for p in (name or "").split()[:2]]) or "?"
            initials_font = load_font("Inter-Bold.ttf", max(48, avatar_size // 4))
            ib = draw.textbbox((0, 0), initials, font=initials_font)
            iw = ib[2] - ib[0]
            ih = ib[3] - ib[1]
            draw.text((avatar_x + (avatar_size - iw) / 2, avatar_y + (avatar_size - ih) / 2), initials, font=initials_font, fill=(255, 255, 255))

        # Site logo: try to include a small logo at the top-left of the card if available
        try:
            logo_path = SCRIPT_DIR / "logo.png"
            if logo_path.is_file():
                logo = Image.open(logo_path).convert("RGBA")
                # small logo size
                lsize = 96
                logo.thumbnail((lsize, lsize), Image.LANCZOS)
                # paste with a small margin inside the card
                logo_x = margin + 20
                logo_y = margin + 20
                img.paste(logo, (logo_x, logo_y), logo)
        except Exception:
            pass

        # Text area start (use more horizontal space)
        text_x = avatar_x + avatar_size + 64
        text_max_w = W - margin - text_x - 48

        # Site label (positioned near top of card area but allow more vertical breathing room)
        site_label = site_name
        draw.text((text_x, margin + 48), site_label, font=small_font, fill=text_muted)

        # Name (wrap if necessary)
        def wrap_lines(text, font, max_width):
            words = text.split()
            lines = []
            cur = []
            for w in words:
                test = " ".join(cur + [w])
                bbox = draw.textbbox((0, 0), test, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    cur.append(w)
                else:
                    if cur:
                        lines.append(" ".join(cur))
                    cur = [w]
            if cur:
                lines.append(" ".join(cur))
            return lines

        name_lines = wrap_lines(name or "Registrant", name_font, text_max_w)
        # Start the name a bit lower so the block occupies the center-left area
        y = margin + inner_h // 4
        for line in name_lines[:4]:
            draw.text((text_x, y), line, font=name_font, fill=text_dark)
            bbox = draw.textbbox((0, 0), line, font=name_font)
            y += (bbox[3] - bbox[1]) + 10

        # Status and roll/id row (give pills more padding for breathing room)
        y += 12
        pill_padding_x = 16
        pill_padding_y = 10
        pill_gap = 16

        # Roll pill
        roll_text = f"Roll: {roll or 'N/A'}"
        rbox = draw.textbbox((0, 0), roll_text, font=meta_font)
        rw = rbox[2] - rbox[0] + pill_padding_x * 2
        rh = rbox[3] - rbox[1] + pill_padding_y * 2
        pill_x = text_x
        pill_y = y
        draw.rounded_rectangle((pill_x, pill_y, pill_x + rw, pill_y + rh), radius=16, fill=(239, 250, 242))
        draw.text((pill_x + pill_padding_x, pill_y + pill_padding_y), roll_text, font=meta_font, fill=accent)

        # Registration ID pill
        id_text = f"ID: {registration_id or '—'}"
        ibox = draw.textbbox((0, 0), id_text, font=mono_font)
        iw = ibox[2] - ibox[0] + pill_padding_x * 2
        id_x = pill_x + rw + pill_gap
        draw.rounded_rectangle((id_x, pill_y, id_x + iw, pill_y + rh), radius=16, fill=(243, 244, 246))
        draw.text((id_x + pill_padding_x, pill_y + pill_padding_y), id_text, font=mono_font, fill=text_dark)

        # Optional status label on right (increase padding and move slightly inward)
        status_text = status_text or ""
        if status_text:
            sbbox = draw.textbbox((0, 0), status_text, font=meta_font)
            sbw = sbbox[2] - sbbox[0] + pill_padding_x * 2
            sbh = sbbox[3] - sbbox[1] + pill_padding_y * 2
            status_x = W - margin - sbw - 56
            status_y = margin + 48
            draw.rounded_rectangle((status_x, status_y, status_x + sbw, status_y + sbh), radius=16, fill=accent)
            draw.text((status_x + pill_padding_x, status_y + pill_padding_y), status_text, font=meta_font, fill=(255, 255, 255))

        # Registration date (if provided) below the pills
        if registration_date:
            date_text = f"Registered: {registration_date}"
            draw.text((text_x, pill_y + rh + 18), date_text, font=small_font, fill=text_muted)

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="PNG")
        console.print(f":white_check_mark: Generated meta image [path]{output_path}[/path]")
        return True
    except Exception as e:
        console.print(f"[warning]Failed to generate meta card:[/warning] {e}")
        return False

def render_master_list(registrants, links, ref_cells) -> str:
    """Create the master_list.html content with Tailwind styling."""
    rows = []
    for (reg, link, ref_cell) in zip(registrants, links, ref_cells):
        rows.append(f"""
        <tr>
            <td>
                <a href="{link}">{reg['name']}</a>
            </td>
            <td>{reg['roll']}</td>
            <td>{reg['registration_id']}</td>
            <td>{reg['registration_date']}</td>
            <td>{ref_cell}</td>
        </tr>
        """)
    rows_html = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Master Verified List</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    /* Chayannito 26 Master List Styles */
    * {{ box-sizing: border-box; }}
    body {{ font-family: 'Inter', sans-serif; margin: 0; padding: 0; background-color: #f3f4f6; min-height: 100vh; padding: 2rem; }}
    .container {{ max-width: 80rem; margin-left: auto; margin-right: auto; background-color: #ffffff; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); border-radius: 1rem; overflow: hidden; }}
    .header {{ padding-left: 1.5rem; padding-right: 1.5rem; padding-top: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; justify-content: space-between; }}
    .header h1 {{ font-size: 1.5rem; line-height: 2rem; font-weight: 700; color: #334155; margin: 0; }}
    .header-right {{ display: flex; align-items: center; gap: 0.75rem; }}
    .header-right span {{ font-size: 0.875rem; line-height: 1.25rem; color: #6b7280; }}
    .shop-btn {{ display: inline-flex; align-items: center; gap: 0.5rem; border-radius: 0.5rem; background-image: linear-gradient(to right, #10b981, #16a34a); padding-left: 0.75rem; padding-right: 0.75rem; padding-top: 0.5rem; padding-bottom: 0.5rem; color: #ffffff; font-size: 0.875rem; line-height: 1.25rem; font-weight: 600; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06); text-decoration: none; transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1); }}
    .shop-btn:hover {{ background-image: linear-gradient(to right, #059669, #15803d); }}
    .shop-btn:focus {{ outline: 2px solid transparent; outline-offset: 2px; box-shadow: 0 0 0 2px rgba(52, 211, 153, 0.5); }}
    .shop-btn svg {{ height: 1rem; width: 1rem; opacity: 0.9; }}
    .table-container {{ overflow-x: auto; }}
    .table {{ min-width: 100%; border-collapse: separate; border-spacing: 0; }}
    .table thead {{ background-color: #dcfce7; }}
    .table th {{ padding-left: 1.5rem; padding-right: 1.5rem; padding-top: 0.75rem; padding-bottom: 0.75rem; text-align: left; font-size: 0.75rem; line-height: 1rem; font-weight: 700; color: #166534; text-transform: uppercase; letter-spacing: 0.05em; }}
    .table tbody {{ background-color: #ffffff; }}
    .table tbody tr {{ border-top: 1px solid #f3f4f6; transition: background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); }}
    .table tbody tr:hover {{ background-color: #f0fdf4; }}
    .table td {{ padding-left: 1.5rem; padding-right: 1.5rem; padding-top: 1rem; padding-bottom: 1rem; }}
    .table td:first-child {{ font-weight: 600; color: #1f2937; }}
    .table td:first-child a {{ color: #16a34a; text-decoration: none; }}
    .table td:first-child a:hover {{ text-decoration: underline; }}
    .table td:nth-child(2) {{ color: #4b5563; }}
    .table td:nth-child(3) {{ font-family: ui-monospace, SFMono-Regular, "SF Mono", Monaco, Inconsolata, "Roboto Mono", monospace; font-size: 0.875rem; line-height: 1.25rem; color: #166534; }}
    .table td:nth-child(4) {{ color: #4b5563; }}
    .table td:nth-child(5) {{ }}
    .table td:nth-child(5) a {{ color: #16a34a; text-decoration: none; }}
    .table td:nth-child(5) a:hover {{ text-decoration: underline; }}
    .table td:nth-child(5) span {{ color: #1f2937; font-weight: 600; }}
    .footer {{ text-align: center; margin-top: 2rem; font-size: 0.75rem; line-height: 1rem; color: #9ca3af; }}
  </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="display:flex; align-items:center; gap:0.75rem;">
                <img src="/assets/logo.png" alt="logo" style="width:48px; height:48px; object-fit:contain; border-radius:6px;" onerror="this.style.display='none'">
                <h1>Chayannito 26  Master Verified List</h1>
            </div>
            <div class="header-right">
                <span>Total: {len(registrants)}</span>
        <a href="https://shop.chayannito26.com" target="_blank" rel="noopener noreferrer" class="shop-btn">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16 11V7a4 4 0 10-8 0v4M5 9h14l-1 10a2 2 0 01-2 2H8a2 2 0 01-2-2L5 9z" />
          </svg>
          Shop
        </a>
      </div>
    </div>
    <div class="table-container">
      <table class="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Roll</th>
            <th>Registration ID</th>
            <th>Date</th>
            <th>Referred By</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>
  <footer class="footer">
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
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #6b7280; font-weight: 500;">Referred By</span>
                    <a href="{href}" style="color: #16a34a; text-decoration: none; font-weight: 600;">{label}</a>
                </div>
        '''
    # fallback: show text as-is
    safe_text = str(ref_val)
    return f'''
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #6b7280; font-weight: 500;">Referred By</span>
                    <span style="color: #1f2937; font-weight: 600;">{safe_text}</span>
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

    # Copy logo into assets if present
    logo_src = ROOT_DIR / "logo.png"
    if logo_src.is_file():
        dst_logo = out_dir / "assets" / "logo.png"
        dst_logo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(logo_src, dst_logo)
        console.print(f":frame_with_picture: Copied [path]{logo_src}[/path] -> [path]{dst_logo}[/path]", style="info")
    else:
        console.print(f"[warning]logo.png not found:[/warning] [path]{logo_src}[/path]")

    # Ensure default meta image is copied into output assets so previews fall back correctly
    meta_src = ROOT_DIR / "assets" / "meta_card.png"
    if meta_src.is_file():
        dst_meta = out_dir / "assets" / "meta_card.png"
        dst_meta.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(meta_src, dst_meta)
        console.print(f":frame_with_picture: Copied default meta image [path]{meta_src}[/path] -> [path]{dst_meta}[/path]", style="info")
    else:
        console.print(f"[warning]Default meta image not found:[/warning] [path]{meta_src}[/path]")

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

            # Meta information for rich previews
            reg_name = entry.get("name", "Registrant")
            reg_id = entry.get("registration_id", "")
            title_status_local = "Verified" if not entry.get("is_placeholder") and not entry.get("revoked") else ("Revoked" if entry.get("revoked") else "Not Registered")
            page_title = f"Registration {title_status_local} - {reg_name}"
            page_description = f"{reg_name} — {entry.get('roll', '')}. Status: {title_status_local}. Registration ID: {reg_id}."

            # Generate or point to a meta image (prefer per-reg image)
            assets_dir = out_dir / "assets"
            meta_image_filename = f"meta_{id_to_filename(reg_id)}.png" if reg_id else "meta_default.png"
            meta_image_path = assets_dir / meta_image_filename
            # Try to generate an image if Pillow is available
            generated_img = False
            if reg_id and PIL_AVAILABLE:
                # treat empty or whitespace-only photo fields as missing
                raw_photo = entry.get("photo") if entry.get("photo") is not None else ""
                photo_clean = raw_photo.strip() if isinstance(raw_photo, str) else ""
                photo_url = photo_clean if photo_clean else f"https://chayannito26.com/college-students/images/{entry.get('roll','placeholder')}.jpg"
                generated_img = generate_meta_card(
                    meta_image_path,
                    name=reg_name,
                    roll=entry.get("roll", ""),
                    registration_id=reg_id,
                    photo_url=photo_url,
                    status_text=title_status_local,
                    registration_date=entry.get("registration_date"),
                )

            # If not generated, use a site-default path (will be copied as-is later if exists)
            if generated_img:
                meta_image_url = f"https://chayannito26.com/verify/assets/{meta_image_filename}"
            else:
                meta_image_url = "https://chayannito26.com/verify/assets/meta_card.png"

            extra_meta = {
                "referred_by_section": ref_section,
                "page_title": page_title,
                "page_description": page_description,
                "canonical_url": f"https://chayannito26.com/verify/{id_to_filename(reg_id)}.html" if reg_id else "https://chayannito26.com/verify/",
                "meta_image": meta_image_url,
            }

            rendered = render_template(template_text, entry, extra_meta)

            changed = write_if_changed(out_path, rendered)
            files_written += int(changed)
            files_unchanged += int(not changed)

            ref_val = entry.get("referred_by")
            referer = _resolve_referer(ref_val, by_id, by_roll, by_name) if ref_val else None
            if referer:
                ref_link = id_to_file.get(referer["registration_id"], "#")
                ref_cells.append(f'<a href="{ref_link}">{referer["name"]}</a>')
            else:
                # If referred_by exists but couldn't be resolved, show the raw text as plain text.
                # If no referred_by provided, show em-dash.
                if ref_val and isinstance(ref_val, str) and ref_val.strip():
                    safe_text = ref_val.strip()
                    ref_cells.append(f'<span style="color: #1f2937; font-weight: 600;">{safe_text}</span>')
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
