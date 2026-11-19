import json
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
SCRIPT = json.loads(Path("content/script.json").read_text(encoding="utf-8"))
ASSETS = Path("assets/illustrations")
OUT = Path("output")
OUT.mkdir(exist_ok=True)

PALETTE = [
    ((255, 235, 112), (255, 111, 145), (76, 190, 255)),
    ((166, 235, 205), (255, 143, 112), (117, 115, 255)),
    ((190, 177, 255), (255, 210, 89), (255, 116, 158)),
    ((255, 190, 216), (110, 205, 255), (255, 184, 77)),
]


def load_font(size):
    for path in (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
    return ImageFont.load_default()


def wrap(draw, text, font, max_width):
    lines, current = [], ""
    for char in str(text):
        candidate = current + char
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def centered_text(draw, text, y, font, fill, max_width=850, line_gap=1.2):
    lines = wrap(draw, text, font, max_width)
    line_height = int(font.size * line_gap)
    y -= line_height * len(lines) // 2
    for line in lines:
        draw.text((W // 2, y), line, font=font, fill=fill, anchor="mm",
                  stroke_width=1, stroke_fill=(255, 255, 255))
        y += line_height


def burst_points(cx, cy, outer, inner, count=16):
    points = []
    for i in range(count * 2):
        angle = -math.pi / 2 + i * math.pi / count
        radius = outer if i % 2 == 0 else inner
        points.append((cx + math.cos(angle) * radius,
                       cy + math.sin(angle) * radius))
    return points


def main():
    scenes = SCRIPT.get("scenes", [])
    if not scenes:
        raise RuntimeError("No scenes found in content/script.json")

    clips, durations = [], []
    for i, scene in enumerate(scenes, 1):
        duration = float(scene.get("end", 5)) - float(scene.get("start", 0))
        if duration <= 0:
            raise ValueError(f"Invalid scene timing: {scene}")
        durations.append(duration)
        accent, second, pale = PALETTE[(i - 1) % len(PALETTE)]
        canvas = Image.new("RGB", (W, H), pale)
        draw = ImageDraw.Draw(canvas)

        # Colorful pop-art background and confetti.
        draw.ellipse((-190, 250, 210, 650), fill=accent)
        draw.ellipse((880, 600, 1240, 960), fill=accent)
        draw.ellipse((-130, 1510, 240, 1880), fill=accent)
        for x, y, r in [(90, 290, 14), (960, 300, 18), (940, 1080, 12),
                        (120, 1080, 10), (880, 1690, 16), (210, 1780, 12)]:
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 255, 255))

        # White poster with a bold outline.
        draw.rounded_rectangle((38, 48, 1042, 1872), radius=58,
                               fill=(255, 255, 255), outline=(35, 43, 68), width=8)
        draw.rounded_rectangle((78, 82, 410, 158), radius=34, fill=second)
        draw.text((244, 120), "1分でわかる！雑学", font=load_font(34),
                  fill=(30, 36, 55), anchor="mm")

        title = SCRIPT.get("title", "今日の雑学")
        title_lines = wrap(draw, title, load_font(48), 850)
        title_y = 210
        for line in title_lines[:2]:
            draw.text((540, title_y), line, font=load_font(48),
                      fill=(30, 36, 55), anchor="mm")
            title_y += 58

        # Make the real illustration the main focus, like a sticker.
        image_box = (112, 340, 968, 1080)
        draw.rounded_rectangle((122, 354, 978, 1094), radius=48, fill=(218, 222, 232))
        draw.rounded_rectangle(image_box, radius=48, fill=(250, 250, 255),
                               outline=accent, width=16)
        candidates = sorted(ASSETS.glob(f"scene{i}-image*"))
        if candidates:
            try:
                im = Image.open(candidates[0]).convert("RGBA")
                im.thumbnail((760, 650), Image.Resampling.LANCZOS)
                canvas.paste(im, (540 - im.width // 2, 710 - im.height // 2), im)
            except Exception as exc:
                print(f"Could not render {candidates[0]}: {exc}")
                draw.text((540, 710), "！", font=load_font(220),
                          fill=second, anchor="mm")
        else:
            draw.polygon(burst_points(540, 710, 190, 145), fill=second)
            draw.text((540, 710), "？", font=load_font(190),
                      fill=(35, 43, 68), anchor="mm")

        # Comic reaction badge.
        draw.polygon(burst_points(875, 410, 105, 78, 12), fill=second,
                     outline=(35, 43, 68))
        reactions = ["!? ", "!!", "へえ", "！"]
        draw.text((875, 410), reactions[(i - 1) % len(reactions)],
                  font=load_font(48), fill=(35, 43, 68), anchor="mm")

        # Large, readable subtitle.
        draw.rounded_rectangle((88, 1135, 992, 1465), radius=46,
                               fill=(255, 255, 255), outline=(35, 43, 68), width=7)
        centered_text(draw, scene.get("text", ""), 1300, load_font(66),
                      (30, 36, 55), max_width=800, line_gap=1.18)

        # Big comic burst for the key word.
        highlight = str(scene.get("highlight", "")).strip()
        if highlight:
            draw.polygon(burst_points(540, 1590, 360, 325, 18), fill=accent,
                         outline=(35, 43, 68))
            draw.text((540, 1590), highlight, font=load_font(78),
                      fill=(30, 36, 55), anchor="mm",
                      stroke_width=2, stroke_fill=(255, 255, 255))

        # Progress bar keeps the short moving toward its payoff.
        draw.rounded_rectangle((110, 1785, 970, 1815), radius=15, fill=(225, 228, 235))
        draw.rounded_rectangle((110, 1785, 110 + int(860 * i / len(scenes)), 1815),
                               radius=15, fill=second)
        draw.text((540, 1840), f"{i} / {len(scenes)}", font=load_font(30),
                  fill=(90, 96, 112), anchor="mm")

        path = OUT / f"scene{i}.png"
        canvas.save(path)
        clips.append(path)

    args, filters = [], []
    for i, (path, duration) in enumerate(zip(clips, durations)):
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(path)]
        filters.append(
            f"[{i}:v]zoompan=z='min(zoom+0.00055,1.075)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={W}x{H}:fps={FPS},setsar=1[v{i}]"
        )

    filters.append("".join(f"[v{i}]" for i in range(len(clips))) +
                   f"concat=n={len(clips)}:v=1:a=0[outv]")
    cmd = ["ffmpeg", "-y", *args, "-filter_complex", ";".join(filters),
           "-map", "[outv]", "-c:v", "libx264", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "output/video.mp4"]
    subprocess.run(cmd, check=True)
    print(f"Created pop-style vertical video: output/video.mp4 ({sum(durations):.2f}s, {W}x{H}, {FPS}fps)")


if __name__ == "__main__":
    main()
