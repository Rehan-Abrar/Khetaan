from __future__ import annotations

import os
import shutil
import subprocess
import sys


def get_ffmpeg_path() -> str:
    # Check system PATH
    path = shutil.which("ffmpeg")
    if path:
        return path
    
    # Check local bin directory in workspace (for local Windows dev environments)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_paths = [
        os.path.join(root_dir, "bin", "ffmpeg.exe"),
        os.path.join(root_dir, "bin", "ffmpeg"),
    ]
    for p in local_paths:
        if os.path.exists(p):
            return p
            
    return "ffmpeg"


class AudioConverter:
    @classmethod
    def convert_to_wav(cls, input_path: str, wav_path: str) -> bool:
        ffmpeg_bin = get_ffmpeg_path()
        print(f"[AudioConverter] Converting {input_path} to WAV: {wav_path}", file=sys.stderr)
        
        # Whisper performs best with 16000Hz, mono, 16-bit PCM WAV files
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            wav_path
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(f"[AudioConverter] ffmpeg failed with code {result.returncode}. Stderr: {result.stderr}", file=sys.stderr)
                return False
            return True
        except Exception as exc:
            print(f"[AudioConverter] Exception during wav conversion: {exc}", file=sys.stderr)
            return False

    @classmethod
    def mp3_to_ogg(cls, mp3_path: str, ogg_path: str) -> bool:
        ffmpeg_bin = get_ffmpeg_path()
        print(f"[AudioConverter] Converting {mp3_path} to WhatsApp-compatible OGG: {ogg_path}", file=sys.stderr)
        
        # WhatsApp prefers OGG containers using the Opus codec
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", mp3_path,
            "-c:a", "libopus",
            "-b:a", "64k",
            "-application", "voip",
            ogg_path
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(f"[AudioConverter] ffmpeg failed with code {result.returncode}. Stderr: {result.stderr}", file=sys.stderr)
                return False
            return True
        except Exception as exc:
            print(f"[AudioConverter] Exception during ogg conversion: {exc}", file=sys.stderr)
            return False
