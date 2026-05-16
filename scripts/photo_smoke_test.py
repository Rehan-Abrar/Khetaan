from __future__ import annotations

import asyncio
import tempfile
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.crop_agent import CropAgent


def _save_temp_image(image: Image.Image) -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    handle.close()
    path = Path(handle.name)
    image.save(path, quality=95)
    return path


async def main() -> None:
    agent = CropAgent()

    samples: list[tuple[str, Path]] = [
        ("wheat rust", Path("reference_images/wheat_leaf_rust_1.jpg")),
        ("cotton leaf curl", Path("reference_images/cotton_leaf_curl_1.jpg")),
        ("aphids", Path("reference_images/aphids_1.jpg")),
    ]

    healthy = Image.new("RGB", (900, 900), "#67b65a")
    draw = ImageDraw.Draw(healthy)
    draw.ellipse((160, 80, 760, 840), fill="#57a84f")
    draw.line((450, 100, 470, 840), fill="#3e7d3b", width=10)
    for y in [220, 320, 420, 520, 620, 720]:
        draw.line((460, y, 330, y - 60), fill="#4d9547", width=5)
        draw.line((470, y, 620, y - 60), fill="#4d9547", width=5)
    healthy_path = _save_temp_image(healthy)
    samples.append(("healthy", healthy_path))

    blurred_source = Image.open("reference_images/wheat_leaf_rust_1.jpg").convert("RGB")
    blurred = blurred_source.filter(ImageFilter.GaussianBlur(radius=18))
    blur_path = _save_temp_image(blurred)
    samples.append(("blurred", blur_path))

    try:
        for label, path in samples:
            result = await agent.diagnose("test", path.read_bytes(), "image/jpeg", "roman_urdu")
            print(f"{label}: {result['disease']} | {result['confidence']} | {result['urgency']}")
            print(result["urdu_message"].splitlines()[0])
            print("---")
    finally:
        healthy_path.unlink(missing_ok=True)
        blur_path.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())