"""Fish and Cohort entities for the koi pond growth model."""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Fish:
    """Represents an individual koi fish."""

    fish_id: str
    initial_length: float  # cm
    initial_weight: float  # g
    age_months: float = 0.0
    feed_quality: float = 0.8  # Q_f: 0-1

    # Length-weight relationship: W = a * L^b
    lw_a: float = 0.02  # typical for koi
    lw_b: float = 3.0

    # Tracking
    current_weight: float = field(init=False)
    current_length: float = field(init=False)
    weight_history: list = field(default_factory=list)
    length_history: list = field(default_factory=list)

    def __post_init__(self):
        self.current_weight = self.initial_weight
        self.current_length = self.initial_length
        self.weight_history = [self.initial_weight]
        self.length_history = [self.initial_length]

    def length_from_weight(self, weight: float) -> float:
        """Derive length from weight using L-W relationship: W = a * L^b."""
        return (weight / self.lw_a) ** (1.0 / self.lw_b)

    def weight_from_length(self, length: float) -> float:
        """Derive weight from length using L-W relationship."""
        return self.lw_a * (length ** self.lw_b)

    def update(self, new_weight: float):
        """Update fish state with new weight after a time step."""
        self.current_weight = new_weight
        self.current_length = self.length_from_weight(new_weight)
        self.weight_history.append(new_weight)
        self.length_history.append(self.current_length)


@dataclass
class Cohort:
    """Represents a group of similar-sized koi (e.g., a fry batch)."""

    cohort_id: str
    count: int
    initial_length: float  # cm, average
    initial_weight: float  # g, average
    age_months: float = 0.0
    feed_quality: float = 0.8

    lw_a: float = 0.02
    lw_b: float = 3.0

    current_weight: float = field(init=False)
    current_length: float = field(init=False)
    weight_history: list = field(default_factory=list)
    length_history: list = field(default_factory=list)

    def __post_init__(self):
        self.current_weight = self.initial_weight
        self.current_length = self.initial_length
        self.weight_history = [self.initial_weight]
        self.length_history = [self.initial_length]

    def length_from_weight(self, weight: float) -> float:
        return (weight / self.lw_a) ** (1.0 / self.lw_b)

    def update(self, new_weight: float):
        self.current_weight = new_weight
        self.current_length = self.length_from_weight(new_weight)
        self.weight_history.append(new_weight)
        self.length_history.append(self.current_length)

    @property
    def total_biomass(self) -> float:
        """Total biomass of the cohort in grams."""
        return self.count * self.current_weight
