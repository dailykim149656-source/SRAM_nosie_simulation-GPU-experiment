"""Shared types for analytical benchmark backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class BackendCapability:
    """Capability metadata for one benchmark lane."""

    name: str
    device: str
    available: bool
    reason: str
    fallback_allowed: bool
    precision: str


@dataclass
class BackendRunOutput:
    """Concrete execution result for one case/lane."""

    device_name: str
    elapsed_sec: float
    predictions: np.ndarray
    extra: dict[str, Any]
