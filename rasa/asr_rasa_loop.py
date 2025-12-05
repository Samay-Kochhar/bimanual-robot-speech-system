import sounddevice as sd
import numpy as np
import requests
import subprocess
from typing import Optional
from faster_whisper import WhisperModel

# Rasa NLU HTTP endpoint
RASA_URL = "http://localhost:5005/model/parse"

# Audio settings
SAMPLING_RATE = 16000
DURATION = 5.0  # seconds to listen each time

print("👂 Loading Faster-Whisper (tiny, CPU)...")
asr_model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("✅ ASR model loaded.")


def record_audio(seconds: float = DURATION) -> np.ndarray:
    """Record audio from the default microphone."""
    print(f"\n🎤 Speak for {seconds} seconds...")
    audio = sd.rec(
        int(seconds * SAMPLING_RATE),
        samplerate=SAMPLING_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    print("🎤 Recording stopped.")
    return audio.flatten()


def transcribe(audio: np.ndarray) -> str:
    """Use Faster-Whisper to transcribe the recorded audio."""
    print("🤔 Transcribing with Faster-Whisper...")
    segments, info = asr_model.transcribe(
        audio,
        beam_size=5,
        language="en",
        word_timestamps=False,
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    print(f"🗣️ ASR text: {text}")
    return text


def call_rasa(text: str) -> Optional[dict]:
    """Send the text to Rasa's /model/parse endpoint."""
    if not text:
        print("⚠️ No text to send to Rasa.")
        return None

    print(f"📨 Sending to Rasa: '{text}'")
    try:
        resp = requests.post(RASA_URL, json={"text": text})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ Error calling Rasa: {e}")
        return None


def summarize_nlu(nlu: Optional[dict]) -> str:
    """Create a simple human-readable summary."""
    if not nlu:
        return "I didn't understand anything."

    intent = nlu.get("intent", {}).get("name", "unknown")
    entities = nlu.get("entities", [])

    # Collect useful entities
    colors = [e["value"] for e in entities if e["entity"] == "color"]
    objects = [e["value"] for e in entities if e["entity"] == "object"]
    relations = [e["value"] for e in entities if e["entity"] == "relation"]

    def first(lst, default=""):
        return lst[0] if lst else default

    if intent == "put":
        src_obj = first(objects, "object")
        tgt_obj = first(objects[1:], "target") if len(objects) > 1 else "target"
        color = first(colors, "")
        rel = first(relations, "in")

        if color:
            return f"I understood a PUT command: put the {color} {src_obj} {rel} the {tgt_obj}."
        else:
            return f"I understood a PUT command: put the {src_obj} {rel} the {tgt_obj} (no color detected)."

    if intent == "give":
        obj = first(objects, "object")
        color = first(colors, "")
        if color:
            return f"I understood a GIVE command: give you the {color} {obj}."
        else:
            return f"I understood a GIVE command: give you the {obj} (no color detected)."

    if intent == "stop":
        return "I understood a STOP command."

    if intent == "describe_object":
        return "I understood an OBJECT DESCRIPTION."

    if intent == "greet":
        return "I understood a GREETING."

    if intent == "affirm":
        return "I understood an AFFIRMATION."

    if intent == "deny":
        return "I understood a DENIAL."

    return f"I got intent '{intent}', but no summary is defined yet."


def debug_entities(nlu: Optional[dict]) -> None:
    """Print a compact debug line with intent and entities."""
    if not nlu:
        print("🔎 No NLU data (nlu is None).")
        return

    intent = nlu.get("intent", {}).get("name", "unknown")
    entities = nlu.get("entities", [])

    colors = [e["value"] for e in entities if e["entity"] == "color"]
    objects = [e["value"] for e in entities if e["entity"] == "object"]
    relations = [e["value"] for e in entities if e["entity"] == "relation"]

    print(
        f"🔎 Entities → INTENT: {intent} | "
        f"OBJECTS: {objects} | COLORS: {colors} | RELATIONS: {relations}"
    )


def speak(text: str) -> None:
    """
    Use macOS built-in TTS ('say') to speak the text.

    This uses the system voice, requires no extra Python packages,
    and works well for a local robot prototype.
    """
    if not text:
        return
    print(f"🔊 Robot says: {text}")
    try:
        subprocess.run(["say", text])
    except FileNotFoundError:
        print("⚠️ 'say' command not found. Are you on macOS?")


def main():
    print("\n🤖 ASR + Rasa + TTS test (Python 3.9, macOS 'say').")
    print("Make sure Rasa is running with:  rasa run --enable-api\n")

    while True:
        try:
            input("\nPress Enter to record (Ctrl+C to quit)...")

            # 1) Record audio
            audio = record_audio(DURATION)

            # 2) ASR -> text
            text = transcribe(audio)
            if not text:
                print("⚠️ Nothing recognized, try again.")
                continue

            # 3) Send to Rasa
            nlu = call_rasa(text)

            # 4) Raw JSON for full debug
            print("🔍 Raw Rasa NLU JSON:")
            print(nlu)

            # 5) Human-friendly summary
            summary = summarize_nlu(nlu)
            print("✅ Summary:", summary)

            # 6) Compact entity debug
            debug_entities(nlu)

            # 7) Speak the summary out loud
            speak(summary)

        except KeyboardInterrupt:
            print("\n👋 Shutting down.")
            break


if __name__ == "__main__":
    main()
