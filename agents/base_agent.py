from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AgentResponse:
    urdu_message: str
    payload: dict[str, Any] | None = None
