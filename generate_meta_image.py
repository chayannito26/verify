"""generate_meta_image.py

Generate a default social-preview card at assets/meta_card.png.
Run: python3 generate_meta_image.py --out assets/meta_card.png
"""
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    print("Pillow is required. Install with: pip install Pillow")
    raise


def generate_default(out_path: Path):
    W, H = 1200, 630
    bg = (16, 185, 129)
    fg = (255, 255, 255)
    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 56)
        small = ImageFont.truetype("DejaVuSans.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
        small = ImageFont.load_default()
    padding = 80
    draw.text((padding, padding), "Chayannito 26", fill=fg, font=small)
    draw.text((padding, padding + 48), "Verification Lookup", fill=fg, font=font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    print(f"Wrote {out_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="assets/meta_card.png")
    args = parser.parse_args()
    generate_default(Path(args.out))
