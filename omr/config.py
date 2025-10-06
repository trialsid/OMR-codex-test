"""Configuration helpers shared across the OMR package.

The coordinate system for bubble positions assumes the origin at the top-left
corner of the sheet. Horizontal (``x``) coordinates increase to the right and
vertical (``y``) coordinates increase downward. Distances are expressed in
millimetres (mm) when stored in templates; helper functions convert between mm
and device pixels using dots-per-inch (DPI) metadata.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from typing import Any, Type, TypeVar

MM_PER_INCH = 25.4


def mm_to_pixels(value_mm: float, dpi: int) -> int:
    """Convert millimetres to integer pixels using the supplied DPI."""
    if dpi <= 0:
        raise ValueError("DPI must be positive")
    return int(round(value_mm / MM_PER_INCH * dpi))


def pixels_to_mm(value_px: float, dpi: int) -> float:
    """Convert pixels to millimetres using the supplied DPI."""
    if dpi <= 0:
        raise ValueError("DPI must be positive")
    return value_px / dpi * MM_PER_INCH


T = TypeVar("T")


def dataclass_to_json(data: Any) -> str:
    """Serialize a dataclass or nested dataclasses to a JSON string."""
    if not is_dataclass(data):
        raise TypeError("dataclass_to_json expects a dataclass instance")
    return json.dumps(asdict(data), indent=2, sort_keys=True)


def json_to_dataclass(json_data: str, factory: Type[T]) -> T:
    """Deserialize JSON into a dataclass using the provided factory."""
    payload = json.loads(json_data)
    if not hasattr(factory, "from_dict"):
        raise TypeError("factory must define a from_dict classmethod")
    return factory.from_dict(payload)
