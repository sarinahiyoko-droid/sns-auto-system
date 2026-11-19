import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
SCRIPT = json.loads(Path("content/script.json").read_text(encoding="utf-8"))
ASSETS = Path("assets/illustrations")
OUT = Path("output")
OUT.mkdir(exist_ok=True)


def load_font(size, bold=False):
    names = (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    )
    for path in names:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
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


def draw_centered_lines(draw, text, y, font, fill, max_width=850, line_gap=1.35):
    lines = wrap(draw, text, font, max_width)
    line_height = int(font.size * line_gap)
    for line in lines:
        draw.text((W // 2, y), line, font=font, fill=fill, anchor="mm",
                  stroke_width=2 if fill == "white" else 0,
                  stroke_fill=(0, 0, 0))
        y += line_height


def scene_duration(scene):
    start = float(scene.get("start", 0))
    end = float(scene.get("end", start + 5))
    duration = end - start
    if duration <= 0:
        raise ValueError(f"Invalid scene timing: {scene}")
    return duration


def main():
    scenes = SCRIPT.get("scenes", [])
    if not scenes:
        raise RuntimeError("No scenes found in content/script.json")

    clips = []
    durations = []
    for i, scene in enumerate(scenes, 1):
        duration = scene_duration(scene)
        durations.append(duration)
        canvas = Image.new("RGB", (W, H), (12, 22, 40))
        draw = ImageDraw.Draw(canvas)

        # Main card and header
        draw.rounded_rectangle((42, 58, 1038, 1862), radius=48, fill=(27, 45, 72))
        draw.rounded_rectangle((82, 92, 998, 238), radius=30, fill=(255, 203, 79))
        draw.text((540, 165), SCRIPT.get("title", "今日の雑学"),
                  font=load_font(54), fill=(25, 32, 45), anchor="mm")

        # One or two real illustrations, when available
        candidates = sorted(ASSETS.glob(f"scene{i}-image*"))
        if candidates:
            slots = [(110, 330, 860, 850)] if len(candidates) == 1 else [
                (75, 350, 450, 820), (555, 350, 450, 820)
            ]
            for image_path, (x, y, max_w, max_h) in zip(candidates[:2], slots):
                try:
                    im = Image.open(image_path).convert("RGBA")
                    im.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                    px = x + (max_w - im.width) // 2
                    py = y + (max_h - im.height) // 2
                    canvas.paste(im, (px, py), im)
                except Exception as exc:
                    print(f"Could not render {image_path}: {exc}")

        draw = ImageDraw.Draw(canvas)

        # Speech-bubble style narration card
        draw.rounded_rectangle((95, 1190, 985, 1515), radius=42,
                               fill=(255, 255, 255), outline=(255, 203, 79), width=10)
        draw.polygon([(485, 1510), (595, 1510), (540, 1585)], fill=(255, 255, 255))
        draw_centered_lines(draw, scene.get("text", ""), 1350,
                            load_font(66), (25, 32, 45), max_width=790)

        # Highlight word as a bold bottom caption
        highlight = str(scene.get("highlight", "")).strip()
        if highlight:
            draw.rounded_rectangle((155, 1635, 925, 1760), radius=30,
                                   fill=(255, 222, 120))
            draw.text((540, 1698), highlight, font=load_font(58),
                      fill=(30, 35, 45), anchor="mm")

        # Small visual cue from the script (kept readable, not a paragraph)
        visual_note = str(scene.get("visual_note", "")).strip()
        if visual_note:
            cue = visual_note[:26]
            draw.rounded_rectangle((130, 1010, 950, 1110), radius=24,
                                   fill=(55, 91, 130))
            draw.text((540, 1060), cue, font=load_font(31),
                      fill=(255, 255, 255), anchor="mm")

        path = OUT / f"scene{i}.png"
        canvas.save(path)
        clips.append(path)

    args, filters = [], []
    for i, (path, duration) in enumerate(zip(clips, durations)):
        frames = max(1, round(duration * FPS))
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(path)]
        # Gentle zoom; each scene's duration follows the script's start/end values.
        filters.append(
            f"[{i}:v]zoompan=z='min(zoom+0.00035,1.05)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={W}x{H}:fps={FPS},setsar=1[v{i}]"
        )

    filters.append("".join(f"[v{i}]" for i in range(len(clips))) +
                   f"concat=n={len(clips)}:v=1:a=0[outv]")
    cmd = ["ffmpeg", "-y", *args, "-filter_complex", ";".join(filters),
           "-map", "[outv]", "-c:v", "libx264", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "output/video.mp4"]
    subprocess.run(cmd, check=True)

    total = sum(durations)
    print(f"Created vertical video: output/video.mp4 ({total:.2f}s, {W}x{H}, {FPS}fps)")


if __name__ == "__main__":
    main()
