# Koi Pond Growth Simulator

A single-page web app that models how water quality affects koi growth and size in a pond.

## Features

- **Pond Setup** — Configure pond volume, filtration, aeration, and add individual fish or cohorts
- **Water Quality** — Set baseline parameters (ammonia, nitrite, pH, DO) and penalty thresholds
- **Growth Simulation** — Run a daily time-step simulation with interactive charts (weight, length, risk scores, environmental conditions)
- **What-If Scenarios** — Compare modified conditions (feed, filtration, aeration, stocking density, water changes) against a baseline
- **Sensitivity Analysis** — Identify which water quality factor is most limiting growth

## How It Works

The model uses a semi-mechanistic growth equation:

```
dW/dt = G_max × f_T(T) × f_F(F, Q_f) × P_WQ(t)
```

- **f_T** — Bell-shaped temperature response (optimal ~24°C)
- **f_F** — Michaelis–Menten feeding response based on ration and feed quality
- **P_WQ** — Combined water quality penalty (ammonia, nitrite, DO, pH, stocking density)

## Usage

Open `index.html` in any modern browser. No server or build step required.

Charts are rendered using [Chart.js](https://www.chartjs.org/) loaded via CDN.

## Project Structure

```
index.html      — Main SPA page with tabbed interface
style.css       — Responsive styles
simulation.js   — Growth model engine (penalties, growth equations, condition generation)
app.js          — UI logic, charts, and interaction handling
spec.md         — Original modeling specification
```
