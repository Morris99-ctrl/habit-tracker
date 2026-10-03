from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
import argparse
import random


def load_font(size, bold=False):
    candidates = [
        "arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return Image.load_default() if False else __import__("PIL.ImageFont", fromlist=["truetype"]).truetype(path, size)
        except Exception:
            continue
    return __import__("PIL.ImageFont", fromlist=["load_default"]).load_default()


def create_card(name="Friend", photo_path=None, output_path="birthday_card.png"):
    width, height = 900, 1200
    card = Image.new("RGB", (width, height), "#fff4f8")
    draw = ImageDraw.Draw(card)

    # Background gradient-like effect
    for y in range(height):
        ratio = y / height
        r = int(255 * (1 - ratio * 0.35) + 240 * ratio * 0.15)
        g = int(120 * (1 - ratio * 0.15) + 80 * ratio * 0.25)
        b = int(220 * (1 - ratio * 0.2) + 180 * ratio * 0.1)
        draw.line((0, y, width, y), fill=(r, g, b))

    # Decorative balloons
    for i in range(8):
        x = 120 + i * 95
        y = 120 + (i % 3) * 35
        r = 35 + (i % 4) * 10
        draw.ellipse((x, y, x + r * 2, y + r * 2), fill=random.choice(["#ff5d8f", "#ffb703", "#7b2cbf", "#06d6a0"]))
        draw.line((x + r, y + r * 2, x + r, y + r * 2 + 80), fill="#6c757d", width=4)

    # Top text
    title_font = load_font(54, True)
    name_font = load_font(40, True)
    body_font = load_font(26)

    draw.text((width // 2, 260), "Happy Birthday", fill="white", anchor="mm", font=title_font)
    draw.text((width // 2, 330), name.upper(), fill="#ffe66d", anchor="mm", font=name_font)
    draw.text((width // 2, 390), "Wishing you a day full of smiles, laughter, and joy!", fill="white", anchor="mm", font=body_font)

    # Photo frame
    frame_x, frame_y, frame_w, frame_h = 300, 470, 300, 300
    draw.rounded_rectangle((frame_x, frame_y, frame_x + frame_w, frame_y + frame_h), radius=28, fill="#ffffff", outline="#ff5d8f", width=6)

    if photo_path and Path(photo_path).exists():
        try:
            photo = Image.open(photo_path).convert("RGBA")
            photo = ImageOps.fit(photo, (260, 260))
            mask = Image.new("L", (260, 260), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle((0, 0, 260, 260), radius=24, fill=255)
            photo = Image.composite(photo, Image.new("RGBA", photo.size, (255, 255, 255, 255)), mask)
            card.paste(photo, (320, 510), photo)
        except Exception:
            draw.text((width // 2, 620), "Photo could not be loaded", fill="#ff5d8f", anchor="mm", font=body_font)
    else:
        draw.text((width // 2, 620), "Add your photo with --photo", fill="#ff5d8f", anchor="mm", font=body_font)

    # Cake
    cake_y = 820
    draw.rounded_rectangle((240, cake_y, 660, cake_y + 120), radius=20, fill="#ff7f50")
    draw.rounded_rectangle((280, cake_y - 90, 620, cake_y + 30), radius=18, fill="#9b5de5")
    draw.rounded_rectangle((320, cake_y - 180, 580, cake_y - 60), radius=16, fill="#00b4d8")
    for x in range(300, 600, 50):
        draw.ellipse((x, cake_y + 10, x + 20, cake_y + 30), fill="#ffd166")
    for x in [330, 380, 430, 480, 530]:
        draw.rectangle((x, cake_y - 120, x + 10, cake_y - 20), fill="#ff006e")
        draw.ellipse((x - 6, cake_y - 150, x + 16, cake_y - 120), fill="#ff9f1c")

    # Confetti dots
    for _ in range(60):
        x = random.randint(60, width - 60)
        y = random.randint(720, height - 60)
        size = random.randint(6, 12)
        draw.ellipse((x, y, x + size, y + size), fill=random.choice(["#ff006e", "#4cc9f0", "#80ed99", "#ffd166", "#8338ec"]))

    card.save(output_path)
    print(f"Birthday card saved as {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Create a colorful birthday card")
    parser.add_argument("--name", default="Friend", help="Name to put on the birthday card")
    parser.add_argument("--photo", default=None, help="Optional path to a photo to place in the card")
    parser.add_argument("--output", default="birthday_card.png", help="Output image file name")
    args = parser.parse_args()

    create_card(name=args.name, photo_path=args.photo, output_path=args.output)


if __name__ == "__main__":
    main()
