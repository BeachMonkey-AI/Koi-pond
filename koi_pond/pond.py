"""Pond system variables for the koi pond growth model."""

from dataclasses import dataclass, field
from typing import List, Union

from .fish import Fish, Cohort


@dataclass
class Pond:
    """Represents the pond system with its physical parameters and fish stock."""

    volume_liters: float
    filtration_capacity: float = 0.8  # C_f: 0-1
    aeration_capacity: float = 0.8  # C_a: 0-1
    fish: List[Union[Fish, Cohort]] = field(default_factory=list)

    def add_fish(self, fish: Union[Fish, Cohort]):
        self.fish.append(fish)

    def remove_fish(self, fish_id: str):
        self.fish = [f for f in self.fish if f.fish_id != fish_id
                     and (not hasattr(f, 'cohort_id') or f.cohort_id != fish_id)]

    @property
    def fish_count(self) -> int:
        """Total number of fish in the pond."""
        total = 0
        for f in self.fish:
            if isinstance(f, Cohort):
                total += f.count
            else:
                total += 1
        return total

    @property
    def total_biomass(self) -> float:
        """Total biomass in grams."""
        total = 0.0
        for f in self.fish:
            if isinstance(f, Cohort):
                total += f.total_biomass
            else:
                total += f.current_weight
        return total

    @property
    def stocking_density(self) -> float:
        """Stocking density in g/L."""
        if self.volume_liters == 0:
            return 0.0
        return self.total_biomass / self.volume_liters
