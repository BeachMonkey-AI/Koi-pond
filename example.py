"""
Example: Simulate 90 days of koi growth in a backyard pond.

Demonstrates:
- Setting up a pond with fish
- Generating synthetic water quality data
- Running the simulation
- Analyzing results and plotting growth curves
"""

import numpy as np
import matplotlib.pyplot as plt

from koi_pond import Fish, Cohort, Pond, GrowthModel, Simulation
from koi_pond.simulation import DailyConditions
from koi_pond.model import GrowthParams
from koi_pond.water_quality import WaterQualityParams


def generate_synthetic_conditions(days: int, season_start_month: int = 4) -> list:
    """
    Generate realistic synthetic daily water quality data.
    Simulates spring/summer conditions with some variability.
    """
    conditions = []
    for day in range(days):
        # Temperature: seasonal curve with daily noise
        day_of_year = (season_start_month - 1) * 30 + day
        base_temp = 18 + 8 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
        temp = base_temp + np.random.normal(0, 1.5)
        temp = np.clip(temp, 5, 35)

        # pH: relatively stable with small fluctuations
        ph = 7.2 + np.random.normal(0, 0.15)
        ph = np.clip(ph, 6.5, 8.5)

        # Ammonia: low baseline with occasional spikes (e.g., after heavy feeding)
        ammonia = 0.1 + abs(np.random.normal(0, 0.05))
        if np.random.random() < 0.05:  # 5% chance of spike
            ammonia += np.random.uniform(0.2, 0.5)

        # Nitrite: correlated with ammonia (biological filter lag)
        nitrite = 0.05 + ammonia * 0.3 + abs(np.random.normal(0, 0.02))

        # Nitrate: accumulates slowly, reduced by water changes
        nitrate = 20 + day * 0.1 + np.random.normal(0, 2)

        # Dissolved oxygen: inversely related to temperature
        do = 9.0 - 0.1 * (temp - 20) + np.random.normal(0, 0.5)
        do = np.clip(do, 3, 12)

        # KH: stable
        kh = 5.0 + np.random.normal(0, 0.2)

        # Daily ration: temperature dependent (feed less in cold)
        if temp < 10:
            ration = 2.0
        elif temp < 15:
            ration = 8.0
        else:
            ration = 20.0 + np.random.normal(0, 2)

        # Weekly water change of ~10%
        water_change = 0.10 if day % 7 == 0 else 0.0
        if water_change > 0:
            nitrate *= 0.9  # dilution

        conditions.append(DailyConditions(
            temperature=temp,
            ph=ph,
            total_ammonia=ammonia,
            nitrite=nitrite,
            nitrate=nitrate,
            dissolved_oxygen=do,
            kh=kh,
            daily_ration=ration,
            water_change_fraction=water_change,
        ))

    return conditions


def main():
    # --- Setup pond ---
    pond = Pond(volume_liters=5000)  # ~1300 gallons

    # Add individual fish
    pond.add_fish(Fish(fish_id="Tancho", initial_length=25, initial_weight=300, age_months=18))
    pond.add_fish(Fish(fish_id="Showa", initial_length=20, initial_weight=150, age_months=12))
    pond.add_fish(Fish(fish_id="Kohaku", initial_length=30, initial_weight=500, age_months=24))

    # Add a cohort of young fish
    pond.add_fish(Cohort(cohort_id="2025_fry", count=5, initial_length=10, initial_weight=20, age_months=3))

    print(f"Pond: {pond.volume_liters}L, {pond.fish_count} fish, "
          f"biomass={pond.total_biomass:.0f}g, density={pond.stocking_density:.2f} g/L")

    # --- Generate 90 days of conditions (spring/summer) ---
    np.random.seed(42)
    days = 90
    conditions = generate_synthetic_conditions(days, season_start_month=5)

    # --- Run simulation ---
    sim = Simulation(pond)
    result = sim.run(conditions)

    # --- Print results ---
    print(f"\n{'='*60}")
    print(f"Simulation complete: {days} days")
    print(f"{'='*60}\n")

    for fish_id, data in result.fish_results.items():
        print(f"  {fish_id}:")
        print(f"    Weight: {data['initial_weight']:.1f}g → {data['final_weight']:.1f}g "
              f"(+{data['weight_gain']:.1f}g)")
        print(f"    Length: {data['initial_length']:.1f}cm → {data['final_length']:.1f}cm "
              f"(+{data['length_gain']:.1f}cm)")
        print()

    # --- Risk analysis ---
    avg_risk = np.mean(result.daily_risk_scores)
    max_risk = np.max(result.daily_risk_scores)
    print(f"  Water quality risk: avg={avg_risk:.3f}, max={max_risk:.3f}")

    # --- Sensitivity analysis ---
    sensitivity = sim.sensitivity_analysis(conditions)
    print(f"\n  Limiting factors (lower = more limiting):")
    for factor, score in sorted(sensitivity.items(), key=lambda x: x[1]):
        print(f"    {factor}: {score:.3f}")

    # --- Plot results ---
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    # Weight over time
    ax = axes[0, 0]
    for fish_id, data in result.fish_results.items():
        ax.plot(data["weight_history"], label=fish_id)
    ax.set_xlabel("Day")
    ax.set_ylabel("Weight (g)")
    ax.set_title("Koi Weight Over Time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Length over time
    ax = axes[0, 1]
    for fish_id, data in result.fish_results.items():
        ax.plot(data["length_history"], label=fish_id)
    ax.set_xlabel("Day")
    ax.set_ylabel("Length (cm)")
    ax.set_title("Koi Length Over Time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Water quality risk score
    ax = axes[1, 0]
    ax.plot(result.daily_risk_scores, color="red", alpha=0.7)
    ax.axhline(y=0.3, color="orange", linestyle="--", label="Moderate risk")
    ax.axhline(y=0.5, color="red", linestyle="--", label="High risk")
    ax.set_xlabel("Day")
    ax.set_ylabel("Risk Score (1 - P_WQ)")
    ax.set_title("Daily Water Quality Risk")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Temperature and conditions
    ax = axes[1, 1]
    temps = [c.temperature for c in conditions]
    ax.plot(temps, label="Temperature", color="orange")
    ax2 = ax.twinx()
    dos = [c.dissolved_oxygen for c in conditions]
    ax2.plot(dos, label="DO", color="blue", alpha=0.6)
    ax.set_xlabel("Day")
    ax.set_ylabel("Temperature (°C)", color="orange")
    ax2.set_ylabel("DO (mg/L)", color="blue")
    ax.set_title("Environmental Conditions")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("koi_growth_simulation.png", dpi=150)
    print(f"\n  Plot saved to koi_growth_simulation.png")
    plt.show()


if __name__ == "__main__":
    main()
