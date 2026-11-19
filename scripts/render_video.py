import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
SCRIPT = json.loads(Path("content/script.json").read_text(encoding="utf-8"))
ASSETS = Path("assets/illustrations")
OUT = Path("output")
OUT.mkdir(exist_ok=True)


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
        canvas = Image.new("RGB", (W, H), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        # One large Irasutoya illustration in the center.
        candidates = sorted(ASSETS.glob(f"scene{i}-image1*"))
        if candidates:
            try:
                im = Image.open(candidates[0]).convert("RGBA")
                im.thumbnail((850, 1050), Image.Resampling.LANCZOS)
                canvas.paste(im, (W // 2 - im.width // 2, 780 - im.height // 2), im)
            except Exception as exc:
                print(f"Could not render {candidates[0]}: {exc}")
                draw.text((540, 760), "？", font=load_font(220), fill=(20, 20, 20), anchor="mm")
        else:
            draw.text((540, 760), "？", font=load_font(220), fill=(20, 20, 20), anchor="mm")

        # Big black caption near the bottom, with no card or decoration.
        caption = str(scene.get("text", "")).strip()
        font = load_font(78 if len(caption) <= 13 else 66)
        lines = wrap(draw, caption, font, 900)
        if len(lines) > 3:
            font = load_font(58)
            lines = wrap(draw, caption, font, 900)
        line_height = int(font.size * 1.22)
        y = 1510 - (line_height * len(lines)) // 2
        for line in lines:
            draw.text((540, y), line, font=font, fill=(15, 15, 15), anchor="mm")
            y += line_height

        # Minimal progress indicator.
        bar_width = 720
        x0 = (W - bar_width) // 2
        draw.rounded_rectangle((x0, 1810, x0 + bar_width, 1824), radius=7, fill=(225, 225, 225))
        draw.rounded_rectangle((x0, 1810, x0 + int(bar_width * i / len(scenes)), 1824),
                               radius=7, fill=(20, 20, 20))

        path = OUT / f"scene{i}.png"
        canvas.save(path)
        clips.append(path)

    args, filters = [], []
    for i, (path, duration) in enumerate(zip(clips, durations)):
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(path)]
        filters.append(
            f"[{i}:v]zoompan=z='min(zoom+0.0008,1.10)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={W}x{H}:fps={FPS},setsar=1[v{i}]"
        )
    filters.append("".join(f"[v{i}]" for i in range(len(clips))) +
                   f"concat=n={len(clips)}:v=1:a=0[outv]")
    cmd = ["ffmpeg", "-y", *args, "-filter_complex", ";".join(filters),
           "-map", "[outv]", "-c:v", "libx264", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "output/video.mp4"]
    subprocess.run(cmd, check=True)
    print(f"Created clean white-background vertical video: output/video.mp4 ({sum(durations):.2f}s, {W}x{H}, {FPS}fps)")


if __name__ == "__main__":
    main()
