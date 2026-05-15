import asyncio
from pathlib import Path
import sys

from dotenv import load_dotenv

from orchestrator import Orchestrator


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    orch = Orchestrator()

    tests = [
        ("Weather", "pani 31.5204,74.3587", None),
        ("Market", "gandum price", None),
        ("Help", "help", None),
        ("Disease-no-image", "meri fasal", None),
    ]

    image_path = Path("reference_images/wheat_leaf_rust_1.jpg")
    if image_path.exists():
        tests.append(("Disease-with-image", "meri fasal", image_path.read_bytes()))

    for label, message, image_bytes in tests:
        reply = await orch.route(message=message, image_bytes=image_bytes, sender="whatsapp:+1000000000")
        print(f"== {label} ==\n{reply}\n")


asyncio.run(main())