import base64
import json
import os
import re
import wave
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SCRIPT_PATH = Path("content/script.json")
OUTPUT_PATH = Path("output/audio.wav")
MODEL = "gemini-3.8-flash-lite-tts"
VOICE = "Puck"  # Upbeat male voice


def save_audio(audio_bytes, mime_type):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Gemini 3.8 TTS normally returns a complete WAV file.
    if audio_bytes[:4] == b"RIFF":
        OUTPUT_PATH.write_bytes(audio_bytes)
        return

    # Defensive fallback for raw 16-bit PCM responses.
    if "L16" in mime_type.upper():
        rate_match = re.search(r"rate=(\d+)", mime_type, re.IGNORECASE)
        sample_rate = int(rate_match.group(1)) if rate_match else 24000
        with wave.open(str(OUTPUT_PATH), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_bytes)
        return

    raise RuntimeError(f"Unexpected audio format: {mime_type}")


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    narration = str(script.get("narration", "")).strip()
    if not narration:
        raise ValueError("Narration is empty.")

    request_body = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": narration,
                "speech_metadata": {
                    "style": (
                        "Natural Japanese. A friendly young adult male narrator "
                        "for a modern short-form trivia video. Bright, upbeat, "
                        "clear articulation, conversational and confident. "
                        "Moderately energetic pace; not rushed. Keep the delivery "
                        "warm and engaging, with natural pauses."
                    )
                }
            }]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": VOICE
                    }
                }
            }
        }
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent"
    )
    request = Request(
        url,
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        },
        method="POST"
    )

    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini TTS API error {error.code}: {details}") from error

    candidates = result.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {result}")

    parts = candidates[0].get("content", {}).get("parts", [])
    audio_part = next((part.get("inlineData") for part in parts if part.get("inlineData")), None)
    if not audio_part or not audio_part.get("data"):
        raise RuntimeError(f"Gemini returned no audio data: {result}")

    audio_bytes = base64.b64decode(audio_part["data"])
    mime_type = audio_part.get("mimeType", "audio/wav")
    save_audio(audio_bytes, mime_type)

    if not OUTPUT_PATH.exists() or OUTPUT_PATH.stat().st_size < 1000:
        raise RuntimeError("Generated audio file is missing or unexpectedly small.")

    print(f"Generated Japanese narration with Gemini TTS ({VOICE}, {mime_type}).")
    print(f"Audio size: {OUTPUT_PATH.stat().st_size} bytes.")


if __name__ == "__main__":
    main()
