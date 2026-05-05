"""Water quality penalty functions for the koi pond growth model."""

import numpy as np
from dataclasses import dataclass


@dataclass
class WaterQualityParams:
    """Thresholds and parameters for water quality penalty functions."""

    # Ammonia thresholds (mg/L un-ionized NH3)
    ammonia_safe: float = 0.02  # a1: below this, penalty = 1
    ammonia_severe: float = 0.10  # a2: above this, penalty ~ 0

    # Nitrite thresholds (mg/L)
    nitrite_safe: float = 0.1  # n1
    nitrite_severe: float = 0.5  # n2

    # Dissolved oxygen thresholds (mg/L)
    do_lethal: float = 2.0  # d0: below this, penalty = 0
    do_safe: float = 6.0  # d1: above this, penalty = 1

    # pH optimal range
    ph_optimal: float = 7.2
    ph_tolerance: float = 1.0  # deviation from optimal before penalty
    ph_swing_threshold: float = 0.5  # max acceptable 24h swing

    # Stocking density
    density_optimal: float = 5.0  # g/L (D_opt)
    density_decay: float = 0.3  # k_D exponential decay rate


class WaterQualityPenalty:
    """Computes water quality penalty factors for koi growth."""

    def __init__(self, params: WaterQualityParams = None):
        self.params = params or WaterQualityParams()

    def compute_unionized_ammonia(self, total_ammonia: float, ph: float, temperature: float) -> float:
        """
        Compute toxic un-ionized NH3 from total ammonia nitrogen (TAN), pH, and temperature.
        Uses the equilibrium: fraction_NH3 = 1 / (1 + 10^(pKa - pH))
        where pKa ≈ 0.09018 + 2729.92 / (T + 273.15)
        """
        pka = 0.09018 + 2729.92 / (temperature + 273.15)
        fraction_nh3 = 1.0 / (1.0 + 10.0 ** (pka - ph))
        return total_ammonia * fraction_nh3

    def penalty_ammonia(self, total_ammonia: float, ph: float, temperature: float) -> float:
        """Ammonia penalty: 1 if safe, linear decline to ~0 at severe threshold."""
        nh3_toxic = self.compute_unionized_ammonia(total_ammonia, ph, temperature)
        a1 = self.params.ammonia_safe
        a2 = self.params.ammonia_severe

        if nh3_toxic <= a1:
            return 1.0
        elif nh3_toxic >= a2:
            return 0.05  # near-zero but not completely zero
        else:
            return 1.0 - 0.95 * (nh3_toxic - a1) / (a2 - a1)

    def penalty_nitrite(self, nitrite: float) -> float:
        """Nitrite penalty: piecewise linear."""
        n1 = self.params.nitrite_safe
        n2 = self.params.nitrite_severe

        if nitrite <= n1:
            return 1.0
        elif nitrite >= n2:
            return 0.05
        else:
            return 1.0 - 0.95 * (nitrite - n1) / (n2 - n1)

    def penalty_dissolved_oxygen(self, do: float) -> float:
        """Dissolved oxygen penalty: 0 below lethal, linear ramp to 1 at safe level."""
        d0 = self.params.do_lethal
        d1 = self.params.do_safe

        if do <= d0:
            return 0.0
        elif do >= d1:
            return 1.0
        else:
            return (do - d0) / (d1 - d0)

    def penalty_ph(self, ph: float, ph_previous: float = None) -> float:
        """
        pH penalty: penalizes deviation from optimal and large daily swings.
        """
        p = self.params
        # Deviation penalty
        deviation = abs(ph - p.ph_optimal)
        if deviation <= p.ph_tolerance * 0.5:
            penalty_dev = 1.0
        elif deviation >= p.ph_tolerance * 2.0:
            penalty_dev = 0.2
        else:
            penalty_dev = 1.0 - 0.8 * (deviation - p.ph_tolerance * 0.5) / (p.ph_tolerance * 1.5)

        # Swing penalty (if previous pH available)
        if ph_previous is not None:
            swing = abs(ph - ph_previous)
            if swing <= p.ph_swing_threshold:
                penalty_swing = 1.0
            elif swing >= p.ph_swing_threshold * 3:
                penalty_swing = 0.3
            else:
                penalty_swing = 1.0 - 0.7 * (swing - p.ph_swing_threshold) / (p.ph_swing_threshold * 2)
        else:
            penalty_swing = 1.0

        return penalty_dev * penalty_swing

    def penalty_density(self, stocking_density: float) -> float:
        """Density penalty: 1 at/below optimal, exponential decay above."""
        d_opt = self.params.density_optimal
        k_d = self.params.density_decay

        if stocking_density <= d_opt:
            return 1.0
        else:
            return np.exp(-k_d * (stocking_density - d_opt))

    def combined_penalty(self, total_ammonia: float, nitrite: float, do: float,
                         ph: float, temperature: float, stocking_density: float,
                         ph_previous: float = None) -> float:
        """
        Compute the combined water quality penalty P_WQ(t).
        Product of all individual penalties.
        """
        p_nh3 = self.penalty_ammonia(total_ammonia, ph, temperature)
        p_no2 = self.penalty_nitrite(nitrite)
        p_do = self.penalty_dissolved_oxygen(do)
        p_ph = self.penalty_ph(ph, ph_previous)
        p_d = self.penalty_density(stocking_density)

        return p_nh3 * p_no2 * p_do * p_ph * p_d

    def detailed_penalties(self, total_ammonia: float, nitrite: float, do: float,
                           ph: float, temperature: float, stocking_density: float,
                           ph_previous: float = None) -> dict:
        """Return individual penalty breakdown for diagnostics."""
        return {
            "ammonia": self.penalty_ammonia(total_ammonia, ph, temperature),
            "nitrite": self.penalty_nitrite(nitrite),
            "dissolved_oxygen": self.penalty_dissolved_oxygen(do),
            "ph": self.penalty_ph(ph, ph_previous),
            "density": self.penalty_density(stocking_density),
            "combined": self.combined_penalty(
                total_ammonia, nitrite, do, ph, temperature, stocking_density, ph_previous
            ),
        }
