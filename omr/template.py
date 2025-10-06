"""Template dataclasses for OMR bubble layouts.

Bubble coordinates use a top-left origin expressed in millimetres. ``x`` values
increase to the right and ``y`` values increase downward, matching the raster
space of rendered sheets and scanned images.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from . import config


@dataclass
class Bubble:
    """A single bubble associated with a question option."""

    question_id: str
    option_id: str
    center_x_mm: float
    center_y_mm: float
    radius_mm: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "question_id": self.question_id,
            "option_id": self.option_id,
            "center_x_mm": self.center_x_mm,
            "center_y_mm": self.center_y_mm,
            "radius_mm": self.radius_mm,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "Bubble":
        return cls(
            question_id=str(payload["question_id"]),
            option_id=str(payload["option_id"]),
            center_x_mm=float(payload["center_x_mm"]),
            center_y_mm=float(payload["center_y_mm"]),
            radius_mm=float(payload["radius_mm"]),
        )

    @property
    def key(self) -> Tuple[str, str]:
        return self.question_id, self.option_id


@dataclass
class Template:
    """The layout for a single OMR sheet."""

    name: str
    page_width_mm: float
    page_height_mm: float
    bubbles: List[Bubble] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "page_width_mm": self.page_width_mm,
            "page_height_mm": self.page_height_mm,
            "bubbles": [bubble.to_dict() for bubble in self.bubbles],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "Template":
        bubbles = [Bubble.from_dict(data) for data in payload.get("bubbles", [])]
        return cls(
            name=str(payload.get("name", "Unnamed Template")),
            page_width_mm=float(payload["page_width_mm"]),
            page_height_mm=float(payload["page_height_mm"]),
            bubbles=bubbles,
        )

    def to_json(self) -> str:
        return config.dataclass_to_json(self)

    @classmethod
    def from_json(cls, json_data: str) -> "Template":
        return config.json_to_dataclass(json_data, cls)

    def dump(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "Template":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.from_json(handle.read())

    def add_bubble(self, bubble: Bubble) -> None:
        self.bubbles.append(bubble)

    def bubble_map(self) -> Dict[Tuple[str, str], Bubble]:
        return {bubble.key: bubble for bubble in self.bubbles}

    def ensure_unique_bubbles(self) -> None:
        seen = set()
        for bubble in self.bubbles:
            if bubble.key in seen:
                raise ValueError(f"Duplicate bubble for {bubble.key}")
            seen.add(bubble.key)

    def iter_questions(self) -> Iterable[str]:
        return sorted({bubble.question_id for bubble in self.bubbles})
