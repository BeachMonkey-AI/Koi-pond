### Overview

Here’s a concise spec you can hand to a data/modeling person (or use yourself) to model how water quality affects koi growth and size in your pond.

---

### 1. Modeling goal

- **Primary objective:**  
  Predict koi growth (length and/or weight over time) as a function of water quality, stocking, and feeding.
- **Secondary objectives:**  
  - Flag conditions that suppress growth or increase stress risk.  
  - Explore “what‑if” scenarios (e.g., more fish, more feeding, better filtration).

---

### 2. Core entities and variables

#### 2.1 Fish-level variables (per fish or per cohort)

- **ID / Cohort:** Unique fish ID or group label (e.g., “2024 fry batch”).
- **Initial size:**  
  - **Length:** \(L_0\) (cm)  
  - **Weight:** \(W_0\) (g)
- **Age:** \(A\) (months or years).
- **Growth outputs:**  
  - **Length over time:** \(L(t)\)  
  - **Weight over time:** \(W(t)\)
- **Feeding exposure:**  
  - **Daily ration per fish:** \(F(t)\) (g/day)  
  - **Feed quality index:** \(Q_f\) (0–1, based on protein, fat, etc.)

#### 2.2 Pond-level water quality variables (time‑series)

All as functions of time \(t\):

- **Temperature:** \(T(t)\) (°C)
- **pH:** \(\text{pH}(t)\)
- **Ammonia (total):** \(\text{NH}_3^{\text{tot}}(t)\) (mg/L)
- **Nitrite:** \(\text{NO}_2(t)\) (mg/L)
- **Nitrate:** \(\text{NO}_3(t)\) (mg/L)
- **Dissolved oxygen:** \(\text{DO}(t)\) (mg/L)
- **KH / alkalinity:** \(\text{KH}(t)\) (dKH or mg/L CaCO\(_3\))
- **TDS / conductivity (optional):** \(\text{TDS}(t)\)
- **Water change events:** volume and timing.

#### 2.3 Stocking and system variables

- **Pond volume:** \(V\) (L or gallons).
- **Fish count:** \(N(t)\).
- **Biomass:** \(B(t) = \sum W_i(t)\) (g or kg).
- **Stocking density:** \(D(t) = B(t)/V\) (g/L).
- **Filtration capacity index:** \(C_f\) (0–1, relative to recommended).
- **Aeration capacity index:** \(C_a\) (0–1, relative to recommended).

---

### 3. Model structure

#### 3.1 High-level approach

- **Type:** Semi‑mechanistic growth model with water‑quality modifiers.  
- **Base growth:** Use a standard fish growth curve (e.g., von Bertalanffy or logistic) driven by temperature and feeding.  
- **Modifiers:** Apply penalty factors for suboptimal water quality (ammonia, nitrite, DO, pH swings, high density).

#### 3.2 Base growth equation

For each fish or cohort:

- **Potential growth rate (no stress):**

\[
\frac{dW}{dt} = G_{\text{max}} \cdot f_T(T) \cdot f_F(F, Q_f)
\]

Where:

- \(G_{\text{max}}\): maximum specific growth rate parameter.
- \(f_T(T)\): temperature response (0–1), e.g. bell‑shaped around optimal temp.
- \(f_F(F, Q_f)\): feeding response (0–1), saturating with ration and quality.

Example forms:

- **Temperature function:**

\[
f_T(T) =
\begin{cases}
0 & T < T_{\text{min}} \text{ or } T > T_{\text{max}} \\
\text{scaled curve} & \text{otherwise}
\end{cases}
\]

- **Feeding function (Michaelis–Menten style):**

\[
f_F(F, Q_f) = Q_f \cdot \frac{F}{F + K_F}
\]

#### 3.3 Water quality penalty functions

Define a combined penalty \(P_{\text{WQ}}(t)\) (0–1) as the product of individual penalties:

\[
P_{\text{WQ}}(t) = p_{\text{NH}_3}(t) \cdot p_{\text{NO}_2}(t) \cdot p_{\text{DO}}(t) \cdot p_{\text{pH}}(t) \cdot p_D(t)
\]

Each \(p_x(t)\) is 1 in ideal range and declines toward 0 as conditions worsen.

- **Ammonia penalty \(p_{\text{NH}_3}(t)\):**

  - Compute toxic un‑ionized ammonia \(\text{NH}_3^{\text{tox}}(t)\) from total ammonia, pH, and temperature.
  - Define thresholds:  
    - **Safe:** \(\text{NH}_3^{\text{tox}} < a_1\) → penalty = 1  
    - **Stress:** \(a_1 \le \text{NH}_3^{\text{tox}} < a_2\) → linear drop  
    - **Severe:** \(\text{NH}_3^{\text{tox}} \ge a_2\) → near 0

- **Nitrite penalty \(p_{\text{NO}_2}(t)\):** similar piecewise function with thresholds \(n_1, n_2\).

- **Dissolved oxygen penalty \(p_{\text{DO}}(t)\):**

\[
p_{\text{DO}}(t) =
\begin{cases}
0 & \text{DO} \le d_0 \\
\frac{\text{DO} - d_0}{d_1 - d_0} & d_0 < \text{DO} < d_1 \\
1 & \text{DO} \ge d_1
\end{cases}
\]

- **pH stability penalty \(p_{\text{pH}}(t)\):**  
  - Penalize both deviation from optimal pH and large daily swings \(|\Delta \text{pH}_{24h}|\).

- **Density penalty \(p_D(t)\):**

\[
p_D(t) =
\begin{cases}
1 & D \le D_{\text{opt}} \\
\exp\left(-k_D (D - D_{\text{opt}})\right) & D > D_{\text{opt}}
\end{cases}
\]

#### 3.4 Final growth equation

\[
\frac{dW}{dt} = G_{\text{max}} \cdot f_T(T) \cdot f_F(F, Q_f) \cdot P_{\text{WQ}}(t)
\]

Length can be derived from weight via a length–weight relationship:

\[
W = a \cdot L^b \quad \Rightarrow \quad L(t) = \left(\frac{W(t)}{a}\right)^{1/b}
\]

---

### 4. Data requirements

#### 4.1 Time resolution

- **Recommended:** Daily or at least 2–3× per week for water quality and feeding.
- **Time step for model:** Daily.

#### 4.2 Inputs to collect

- **Per day:**
  - **Water quality:** \(T, \text{pH}, \text{NH}_3^{\text{tot}}, \text{NO}_2, \text{NO}_3, \text{DO}, \text{KH}\).
  - **Feeding:** total feed added, type/brand (to infer \(Q_f\)).
  - **Fish:** occasional sample weights/lengths (e.g., monthly) for calibration.
  - **Events:** water changes, filter cleaning, new fish added, mortalities.

- **Static:**
  - Pond volume, filtration type, aeration setup, approximate filter rating.

---

### 5. Calibration and validation

- **Step 1: Initialize parameters**  
  Use literature or default values for \(G_{\text{max}}, K_F, a, b, D_{\text{opt}}, k_D\), and penalty thresholds.
- **Step 2: Fit to your pond**  
  - Use historical data (water quality + measured growth) to adjust parameters so simulated \(W(t)\) matches observed.
- **Step 3: Validate**  
  - Hold out a period of data and check prediction error on growth and any observed stress events.

---

### 6. Outputs and use cases

- **Per fish/cohort:**
  - Predicted weight and length over time.
  - Growth suppression index: ratio of actual growth to “ideal” growth with perfect water.
- **Per day/period:**
  - Water quality risk score (0–1).
  - Sensitivity analysis: which parameter (ammonia, DO, density, etc.) is most limiting.
- **Scenario mode:**
  - Change stocking, feeding, or filtration and simulate 3–12 months ahead.
