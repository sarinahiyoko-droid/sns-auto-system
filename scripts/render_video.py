import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
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
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap(draw, text, font, max_width):
    lines, current = [], ""
    for char in text:
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
    clips = []
    images = sorted(ASSETS.glob("scene*"))
    for i, scene in enumerate(SCRIPT.get("scenes", []), 1):
        canvas = Image.new("RGB", (W, H), (12, 22, 40))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((48, 70, 1032, 1850), radius=44, fill=(27, 45, 72))
        draw.rounded_rectangle((90, 110, 990, 245), radius=28, fill=(255, 203, 79))
        draw.text((540, 177), SCRIPT.get("title", "今日の雑学"),
                  font=load_font(56), fill=(25, 32, 45), anchor="mm")

        candidates = sorted(ASSETS.glob(f"scene{i}-image*"))
        if candidates:
            try:
                im = Image.open(candidates[0]).convert("RGBA")
                im.thumbnail((850, 900), Image.Resampling.LANCZOS)
                x, y = (W-im.width)//2, 330+(900-im.height)//2
                canvas.paste(im, (x, y), im)
            except Exception as exc:
                print(f"Could not render {candidates[0]}: {exc}")

        draw = ImageDraw.Draw(canvas)
        highlight = scene.get("highlight", "")
        if highlight:
            draw.rounded_rectangle((120, 1260, 960, 1370), radius=28, fill=(255, 222, 120))
            draw.text((540, 1315), highlight, font=load_font(46),
                      fill=(30, 35, 45), anchor="mm")

        lines = wrap(draw, scene.get("text", ""), load_font(68), 850)
        y = 1490
        for line in lines[:3]:
            draw.text((540, y), line, font=load_font(68), fill="white",
                      anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0))
            y += 100

        path = OUT / f"scene{i}.png"
        canvas.save(path)
        clips.append(path)

    if not clips:
        raise RuntimeError("No scenes found in content/script.json")

    args, filters = [], []
    for i, path in enumerate(clips):
        args += ["-loop", "1", "-t", "5", "-i", str(path)]
        filters.append(
            f"[{i}:v]zoompan=z='min(zoom+0.0005,1.06)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=150:s={W}x{H}:fps=30,setsar=1[v{i}]"
        )
    filters.append("".join(f"[v{i}]" for i in range(len(clips))) +
                   f"concat=n={len(clips)}:v=1:a=0[outv]")
    cmd = ["ffmpeg", "-y", *args, "-filter_complex", ";".join(filters),
           "-map", "[outv]", "-c:v", "libx264", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "output/video.mp4"]
    subprocess.run(cmd, check=True)
    print("Created illustrated vertical video: output/video.mp4")


if __name__ == "__main__":
    main()
