"""Core growth model for the koi pond simulation."""

import numpy as np
from dataclasses import dataclass
from typing import Union

from .fish import Fish, Cohort
from .water_quality import WaterQualityPenalty


@dataclass
class GrowthParams:
    """Parameters for the growth model."""

    # Maximum specific growth rate (g/day per g body weight)
    g_max: float = 0.015

    # Temperature response parameters (bell-shaped)
    temp_min: float = 8.0  # °C - below this, no growth
    temp_opt: float = 24.0  # °C - optimal temperature
    temp_max: float = 34.0  # °C - above this, no growth
    temp_sigma: float = 6.0  # width of the bell curve

    # Feeding response (Michaelis-Menten)
    k_f: float = 15.0  # half-saturation constant for daily ration (g/day)


class GrowthModel:
    """
    Semi-mechanistic growth model for koi.

    dW/dt = G_max * f_T(T) * f_F(F, Q_f) * P_WQ(t)

    - f_T: temperature response (bell-shaped, 0-1)
    - f_F: feeding response (Michaelis-Menten, 0-1)
    - P_WQ: water quality penalty (0-1)
    """

    def __init__(self, params: GrowthParams = None, wq_penalty: WaterQualityPenalty = None):
        self.params = params or GrowthParams()
        self.wq_penalty = wq_penalty or WaterQualityPenalty()

    def temperature_response(self, temperature: float) -> float:
        """
        Bell-shaped temperature response function f_T(T).
        Returns 0-1, with 1 at optimal temperature.
        """
        p = self.params
        if temperature <= p.temp_min or temperature >= p.temp_max:
            return 0.0

        # Gaussian-like bell curve centered on optimal temp
        return np.exp(-((temperature - p.temp_opt) ** 2) / (2 * p.temp_sigma ** 2))

    def feeding_response(self, daily_ration: float, feed_quality: float) -> float:
        """
        Michaelis-Menten feeding response: f_F(F, Q_f) = Q_f * F / (F + K_F)
        """
        if daily_ration <= 0:
            return 0.0
        return feed_quality * daily_ration / (daily_ration + self.params.k_f)

    def growth_rate(self, fish: Union[Fish, Cohort], temperature: float,
                    daily_ration: float, total_ammonia: float, nitrite: float,
                    dissolved_oxygen: float, ph: float, stocking_density: float,
                    ph_previous: float = None) -> float:
        """
        Compute the daily weight gain (g/day) for a fish or cohort.

        dW/dt = G_max * W * f_T(T) * f_F(F, Q_f) * P_WQ(t)

        Returns the absolute weight gain in grams per day.
        """
        f_t = self.temperature_response(temperature)
        f_f = self.feeding_response(daily_ration, fish.feed_quality)
        p_wq = self.wq_penalty.combined_penalty(
            total_ammonia, nitrite, dissolved_oxygen,
            ph, temperature, stocking_density, ph_previous
        )

        # Specific growth rate * current weight = absolute growth
        dw_dt = self.params.g_max * fish.current_weight * f_t * f_f * p_wq
        return dw_dt

    def step(self, fish: Union[Fish, Cohort], temperature: float,
             daily_ration: float, total_ammonia: float, nitrite: float,
             dissolved_oxygen: float, ph: float, stocking_density: float,
             ph_previous: float = None, dt: float = 1.0):
        """
        Advance the fish by one time step (default 1 day).
        Updates the fish's weight and length in place.
        """
        dw = self.growth_rate(
            fish, temperature, daily_ration, total_ammonia, nitrite,
            dissolved_oxygen, ph, stocking_density, ph_previous
        )
        new_weight = fish.current_weight + dw * dt
        # Weight cannot decrease below a minimum (fish don't shrink significantly)
        new_weight = max(new_weight, fish.current_weight * 0.99)
        fish.update(new_weight)

    def ideal_growth_rate(self, fish: Union[Fish, Cohort], temperature: float,
                          daily_ration: float) -> float:
        """
        Growth rate under ideal water quality conditions (all penalties = 1).
        Useful for computing growth suppression index.
        """
        f_t = self.temperature_response(temperature)
        f_f = self.feeding_response(daily_ration, fish.feed_quality)
        return self.params.g_max * fish.current_weight * f_t * f_f

    def growth_suppression_index(self, fish: Union[Fish, Cohort], temperature: float,
                                 daily_ration: float, total_ammonia: float, nitrite: float,
                                 dissolved_oxygen: float, ph: float, stocking_density: float,
                                 ph_previous: float = None) -> float:
        """
        Ratio of actual growth to ideal growth. 1.0 = no suppression, <1.0 = suppressed.
        """
        ideal = self.ideal_growth_rate(fish, temperature, daily_ration)
        if ideal <= 0:
            return 1.0
        actual = self.growth_rate(
            fish, temperature, daily_ration, total_ammonia, nitrite,
            dissolved_oxygen, ph, stocking_density, ph_previous
        )
        return actual / ideal
