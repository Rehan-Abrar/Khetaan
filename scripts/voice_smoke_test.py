import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure khetaan is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

load_dotenv(ROOT / ".env")

async def test_speech_to_text():
    print("\n=== Testing Speech-To-Text Model Preloading ===")
    try:
        from voice.speech_to_text import initialize_whisper, SpeechToText
        # Initialize whisper model
        initialize_whisper()
        model = SpeechToText.get_model()
        if model:
            print("✓ SpeechToText model initialized successfully.")
        else:
            print("✗ SpeechToText model initialization failed.")
    except Exception as exc:
        print(f"✗ STT Test failed with exception: {exc}")

async def test_text_to_speech():
    print("\n=== Testing Text-To-Speech Generation ===")
    try:
        from voice.text_to_speech import TextToSpeech
        
        output_mp3 = ROOT / "test_reply.mp3"
        if output_mp3.exists():
            os.remove(output_mp3)

        # Test Roman Urdu conversion and TTS
        test_text = "Aap ki fasal ko wheat rust hai. Aabpashi na karein aur spray lagayein."
        print(f"Synthesizing test message (Roman Urdu): {test_text!r}")
        
        success = await TextToSpeech.generate_speech(test_text, "roman_urdu", str(output_mp3))
        
        if success and output_mp3.exists():
            print(f"✓ Speech generated successfully. Output file size: {output_mp3.stat().st_size} bytes")
            # Cleanup
            os.remove(output_mp3)
        else:
            print("✗ Speech generation failed.")
    except Exception as exc:
        print(f"✗ TTS Test failed with exception: {exc}")

def test_audio_converter():
    print("\n=== Testing Audio Converter & FFmpeg ===")
    try:
        from voice.audio_converter import get_ffmpeg_path
        ffmpeg_bin = get_ffmpeg_path()
        print(f"Resolved FFmpeg path: {ffmpeg_bin}")
        
        # Check if FFmpeg executes
        import subprocess
        result = subprocess.run([ffmpeg_bin, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print("✓ FFmpeg is available and executing correctly.")
        else:
            print(f"✗ FFmpeg execution failed with code {result.returncode}.")
    except Exception as exc:
        print(f"ℹ FFmpeg is not available locally. Note: Render native environments include FFmpeg by default. Local error: {exc}")

async def main():
    sys.stdout.reconfigure(encoding="utf-8")
    await test_speech_to_text()
    await test_text_to_speech()
    test_audio_converter()

if __name__ == "__main__":
    asyncio.run(main())
