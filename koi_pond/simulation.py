"""Simulation runner for the koi pond growth model."""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union

from .fish import Fish, Cohort
from .pond import Pond
from .model import GrowthModel, GrowthParams
from .water_quality import WaterQualityPenalty, WaterQualityParams


@dataclass
class DailyConditions:
    """Water quality and feeding conditions for a single day."""

    temperature: float  # °C
    ph: float
    total_ammonia: float  # mg/L (TAN)
    nitrite: float  # mg/L
    nitrate: float  # mg/L (tracked but not penalized directly)
    dissolved_oxygen: float  # mg/L
    kh: float = 4.0  # dKH
    daily_ration: float = 20.0  # g total feed per fish
    water_change_fraction: float = 0.0  # fraction of volume changed


@dataclass
class SimulationResult:
    """Results from a simulation run."""

    days: int
    fish_results: Dict[str, Dict] = field(default_factory=dict)
    daily_risk_scores: List[float] = field(default_factory=list)
    daily_penalties: List[Dict] = field(default_factory=list)
    daily_suppression: List[Dict] = field(default_factory=list)


class Simulation:
    """
    Runs the koi pond growth simulation over a time series of conditions.
    """

    def __init__(self, pond: Pond, growth_params: GrowthParams = None,
                 wq_params: WaterQualityParams = None):
        self.pond = pond
        self.wq_penalty = WaterQualityPenalty(wq_params)
        self.model = GrowthModel(growth_params, self.wq_penalty)

    def run(self, conditions: List[DailyConditions]) -> SimulationResult:
        """
        Run simulation for the given daily conditions time series.

        Args:
            conditions: List of DailyConditions, one per day.

        Returns:
            SimulationResult with growth trajectories and diagnostics.
        """
        result = SimulationResult(days=len(conditions))
        ph_previous = None

        for day_idx, cond in enumerate(conditions):
            stocking_density = self.pond.stocking_density

            # Compute detailed penalties for diagnostics
            penalties = self.wq_penalty.detailed_penalties(
                cond.total_ammonia, cond.nitrite, cond.dissolved_oxygen,
                cond.ph, cond.temperature, stocking_density, ph_previous
            )
            result.daily_penalties.append(penalties)
            result.daily_risk_scores.append(1.0 - penalties["combined"])

            # Step each fish/cohort
            day_suppression = {}
            for fish in self.pond.fish:
                fish_id = fish.fish_id if isinstance(fish, Fish) else fish.cohort_id

                # Compute growth suppression index
                suppression = self.model.growth_suppression_index(
                    fish, cond.temperature, cond.daily_ration,
                    cond.total_ammonia, cond.nitrite, cond.dissolved_oxygen,
                    cond.ph, stocking_density, ph_previous
                )
                day_suppression[fish_id] = suppression

                # Advance growth by one day
                self.model.step(
                    fish, cond.temperature, cond.daily_ration,
                    cond.total_ammonia, cond.nitrite, cond.dissolved_oxygen,
                    cond.ph, stocking_density, ph_previous
                )

            result.daily_suppression.append(day_suppression)
            ph_previous = cond.ph

        # Collect final results per fish
        for fish in self.pond.fish:
            fish_id = fish.fish_id if isinstance(fish, Fish) else fish.cohort_id
            result.fish_results[fish_id] = {
                "initial_weight": fish.initial_weight,
                "final_weight": fish.current_weight,
                "initial_length": fish.initial_length,
                "final_length": fish.current_length,
                "weight_history": fish.weight_history.copy(),
                "length_history": fish.length_history.copy(),
                "weight_gain": fish.current_weight - fish.initial_weight,
                "length_gain": fish.current_length - fish.initial_length,
            }

        return result

    def run_scenario(self, base_conditions: List[DailyConditions],
                     modifications: Dict = None) -> SimulationResult:
        """
        Run a what-if scenario by modifying base conditions.

        Args:
            base_conditions: Original daily conditions.
            modifications: Dict with keys like 'fish_count_multiplier',
                          'feed_multiplier', 'filtration_improvement', etc.

        Returns:
            SimulationResult for the modified scenario.
        """
        if modifications is None:
            return self.run(base_conditions)

        # Apply modifications
        modified_conditions = []
        for cond in base_conditions:
            new_cond = DailyConditions(
                temperature=cond.temperature,
                ph=cond.ph,
                total_ammonia=cond.total_ammonia,
                nitrite=cond.nitrite,
                nitrate=cond.nitrate,
                dissolved_oxygen=cond.dissolved_oxygen,
                kh=cond.kh,
                daily_ration=cond.daily_ration,
                water_change_fraction=cond.water_change_fraction,
            )

            # Adjust feed
            if "feed_multiplier" in modifications:
                new_cond.daily_ration *= modifications["feed_multiplier"]

            # Improved filtration reduces ammonia/nitrite
            if "filtration_improvement" in modifications:
                factor = 1.0 - modifications["filtration_improvement"]
                new_cond.total_ammonia *= factor
                new_cond.nitrite *= factor

            # Better aeration increases DO
            if "aeration_improvement" in modifications:
                new_cond.dissolved_oxygen += modifications["aeration_improvement"]

            # More frequent water changes reduce ammonia/nitrite/nitrate
            if "water_change_increase" in modifications:
                dilution = 1.0 - modifications["water_change_increase"] * 0.5
                new_cond.total_ammonia *= dilution
                new_cond.nitrite *= dilution
                new_cond.nitrate *= dilution

            modified_conditions.append(new_cond)

        # Adjust fish count if specified
        original_fish = self.pond.fish.copy()
        if "fish_count_multiplier" in modifications:
            multiplier = modifications["fish_count_multiplier"]
            for fish in self.pond.fish:
                if isinstance(fish, Cohort):
                    fish.count = int(fish.count * multiplier)

        result = self.run(modified_conditions)

        # Restore original fish state (for re-running with different scenarios)
        self.pond.fish = original_fish

        return result

    def sensitivity_analysis(self, conditions: List[DailyConditions]) -> Dict[str, float]:
        """
        Determine which water quality factor is most limiting growth.
        Returns average penalty contribution per factor.
        """
        factors = {"ammonia": [], "nitrite": [], "dissolved_oxygen": [], "ph": [], "density": []}
        ph_previous = None

        for cond in conditions:
            stocking_density = self.pond.stocking_density
            penalties = self.wq_penalty.detailed_penalties(
                cond.total_ammonia, cond.nitrite, cond.dissolved_oxygen,
                cond.ph, cond.temperature, stocking_density, ph_previous
            )
            for key in factors:
                factors[key].append(penalties[key])
            ph_previous = cond.ph

        # Return average penalty per factor (lower = more limiting)
        return {key: float(np.mean(values)) for key, values in factors.items()}
