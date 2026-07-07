from __future__ import annotations

import os

# ── Run-mode ───────────────────────────────────────────────────────────────
# Set PROTOTYPE=true in your environment / Render dashboard to enable
# hardcoded demo responses (no live API calls for image diagnosis).
# Leave unset or PROTOTYPE=false for normal MVP behaviour.
PROTOTYPE_MODE: bool = os.getenv("PROTOTYPE", "false").strip().lower() in ("1", "true", "yes")

# ── Prototype hardcoded responses ──────────────────────────────────────────
# These are shown in prototype mode instead of calling the Groq/Gemini API.

PROTO_DISEASE_IMAGE_RESPONSE = {
    "agent": "disease_agent",
    "disease": "Leaf Rust (Kungi)",
    "confidence": 85,
    "urgency": "high",
    "urdu_message": (
        "Aapki kanak ki fasal par 'Leaf Rust' (kungi) ka hamla hua hai. "
        "Patton par narangi aur bhoore rang ke dhabbe saaf nazar aa rahe hain. "
        "Is bimari ko foran rokne ke liye Propiconazole ya Tebuconazole ka spray karein "
        "taake fasal mazeed kharab na ho."
    ),
    "suggestions": [
        "Propiconazole ya Tebuconazole fungicide spray karein",
        "Beemar patton ko tod kar jala dein",
        "Aas paas ki faslon ki bhi nigrani karein",
    ],
}

PROTO_DISEASE_TEXT_RESPONSE = {
    "agent": "disease_agent",
    "disease": "",
    "confidence": 0,
    "urgency": "low",
    "urdu_message": (
        "Bhai, aapne masla ya alamat nahi batayin. "
        "Kya patte murrh rahe hain, un par rangat badal rahi hai ya keeray hain? "
        "Behtar ilaj ke liye aik photo bhejen."
    ),
    "suggestions": [],
}
