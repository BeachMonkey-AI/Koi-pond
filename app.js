/**
 * Koi Pond SPA - Application Logic
 */

(function () {
    // --- State ---
    const state = {
        fish: [],
        charts: {},
        baselineResult: null,
    };

    // --- Tab Navigation ---
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
        });
    });

    // --- Fish Type Toggle ---
    document.getElementById('fish-type').addEventListener('change', (e) => {
        document.getElementById('cohort-count-group').style.display =
            e.target.value === 'cohort' ? '' : 'none';
    });

    // --- Add Fish ---
    document.getElementById('add-fish-btn').addEventListener('click', () => {
        const name = document.getElementById('fish-name').value.trim();
        if (!name) { alert('Please enter a fish name/ID.'); return; }

        const fish = {
            id: name,
            type: document.getElementById('fish-type').value,
            count: parseInt(document.getElementById('fish-count').value) || 1,
            length: parseFloat(document.getElementById('fish-length').value),
            weight: parseFloat(document.getElementById('fish-weight').value),
            age: parseFloat(document.getElementById('fish-age').value),
            feedQuality: parseFloat(document.getElementById('feed-quality').value),
        };

        if (fish.type === 'individual') fish.count = 1;

        state.fish.push(fish);
        renderFishList();
        document.getElementById('fish-name').value = '';
    });

    function renderFishList() {
        const container = document.getElementById('fish-list');
        if (state.fish.length === 0) {
            container.innerHTML = '<p class="hint">No fish added yet. Add some fish below.</p>';
            return;
        }
        container.innerHTML = state.fish.map((f, i) => `
            <div class="fish-item">
                <div class="fish-info">
                    <strong>${f.id}</strong>
                    <span>${f.type === 'cohort' ? `Cohort (×${f.count})` : 'Individual'}</span>
                    <span>${f.length}cm</span>
                    <span>${f.weight}g</span>
                    <span>${f.age}mo</span>
                    <span>Q=${f.feedQuality}</span>
                </div>
                <button class="btn btn-danger" onclick="removeFish(${i})">Remove</button>
            </div>
        `).join('');
    }

    window.removeFish = function (index) {
        state.fish.splice(index, 1);
        renderFishList();
    };

    // --- Run Simulation ---
    document.getElementById('run-sim-btn').addEventListener('click', runSimulation);

    function getWQParams() {
        return {
            ammoniaSafe: parseFloat(document.getElementById('nh3-safe').value),
            ammoniaSevere: parseFloat(document.getElementById('nh3-severe').value),
            nitriteSafe: parseFloat(document.getElementById('no2-safe').value),
            nitriteSevere: parseFloat(document.getElementById('no2-severe').value),
            doLethal: parseFloat(document.getElementById('do-lethal').value),
            doSafe: parseFloat(document.getElementById('do-safe').value),
            densityOptimal: parseFloat(document.getElementById('density-opt').value),
            densityDecay: parseFloat(document.getElementById('density-decay').value),
        };
    }

    function getPond() {
        const fishToUse = state.fish.length > 0 ? state.fish : [
            { id: 'Tancho', type: 'individual', count: 1, length: 25, weight: 300, age: 18, feedQuality: 0.8 },
            { id: 'Showa', type: 'individual', count: 1, length: 20, weight: 150, age: 12, feedQuality: 0.8 },
            { id: 'Kohaku', type: 'individual', count: 1, length: 30, weight: 500, age: 24, feedQuality: 0.8 },
            { id: '2025 Fry', type: 'cohort', count: 5, length: 10, weight: 20, age: 3, feedQuality: 0.8 },
        ];

        return {
            volume: parseFloat(document.getElementById('pond-volume').value),
            fish: fishToUse,
        };
    }

    function getConditionsConfig() {
        return {
            days: parseInt(document.getElementById('sim-days').value),
            startMonth: parseInt(document.getElementById('start-month').value),
            baseAmmonia: parseFloat(document.getElementById('base-ammonia').value),
            baseNitrite: parseFloat(document.getElementById('base-nitrite').value),
            basePH: parseFloat(document.getElementById('base-ph').value),
            baseDO: parseFloat(document.getElementById('base-do').value),
            dailyRation: parseFloat(document.getElementById('daily-ration').value),
            waterChangePct: parseFloat(document.getElementById('water-change-pct').value),
            seed: 42,
        };
    }

    function runSimulation() {
        const statusEl = document.getElementById('sim-status');
        statusEl.textContent = 'Running simulation...';

        // Use setTimeout to allow UI update
        setTimeout(() => {
            const pond = getPond();
            const condConfig = getConditionsConfig();
            const wqParams = getWQParams();
            const conditions = KoiSim.generateConditions(condConfig);
            const result = KoiSim.runSimulation(pond, conditions, wqParams);

            state.baselineResult = result;
            state.baselineConditions = conditions;
            state.baselineWQParams = wqParams;
            state.baselinePond = pond;

            displayResults(result, conditions);
            statusEl.textContent = `✓ Simulation complete — ${condConfig.days} days, ${pond.fish.length} fish`;
        }, 10);
    }

    function displayResults(result, conditions) {
        document.getElementById('results').style.display = '';

        // Results table
        const tbody = document.querySelector('#results-table tbody');
        tbody.innerHTML = result.fish.map(f => `
            <tr>
                <td>${f.id}</td>
                <td>${f.weight.toFixed(1)}</td>
                <td>${f.currentWeight.toFixed(1)}</td>
                <td>${(f.currentWeight - f.weight).toFixed(1)}</td>
                <td>${f.length.toFixed(1)}</td>
                <td>${f.currentLength.toFixed(1)}</td>
                <td>${(f.currentLength - f.length).toFixed(1)}</td>
            </tr>
        `).join('');

        // Charts
        const days = Array.from({ length: result.dailyRiskScores.length }, (_, i) => i + 1);
        const dayLabels = Array.from({ length: result.fish[0].weightHistory.length }, (_, i) => i);

        renderChart('chart-weight', 'line', {
            labels: dayLabels,
            datasets: result.fish.map((f, i) => ({
                label: f.id,
                data: f.weightHistory,
                borderColor: getColor(i),
                backgroundColor: getColor(i, 0.1),
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
            })),
        }, { scales: { y: { title: { display: true, text: 'Weight (g)' } }, x: { title: { display: true, text: 'Day' } } } });

        renderChart('chart-length', 'line', {
            labels: dayLabels,
            datasets: result.fish.map((f, i) => ({
                label: f.id,
                data: f.lengthHistory,
                borderColor: getColor(i),
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
            })),
        }, { scales: { y: { title: { display: true, text: 'Length (cm)' } }, x: { title: { display: true, text: 'Day' } } } });

        renderChart('chart-risk', 'line', {
            labels: days,
            datasets: [{
                label: 'Risk Score (1 - P_WQ)',
                data: result.dailyRiskScores,
                borderColor: '#ea4335',
                backgroundColor: 'rgba(234,67,53,0.1)',
                borderWidth: 1.5,
                pointRadius: 0,
                fill: true,
            }],
        }, {
            scales: {
                y: { min: 0, max: 1, title: { display: true, text: 'Risk (0=none, 1=severe)' } },
                x: { title: { display: true, text: 'Day' } }
            },
        });

        const temps = conditions.map(c => c.temperature);
        const dos = conditions.map(c => c.dissolvedOxygen);
        renderChart('chart-conditions', 'line', {
            labels: days,
            datasets: [
                { label: 'Temperature (°C)', data: temps, borderColor: '#fbbc04', borderWidth: 1.5, pointRadius: 0, yAxisID: 'y' },
                { label: 'DO (mg/L)', data: dos, borderColor: '#1a73e8', borderWidth: 1.5, pointRadius: 0, yAxisID: 'y1' },
            ],
        }, {
            scales: {
                y: { position: 'left', title: { display: true, text: '°C' } },
                y1: { position: 'right', title: { display: true, text: 'mg/L' }, grid: { drawOnChartArea: false } },
                x: { title: { display: true, text: 'Day' } },
            },
        });

        // Sensitivity bar chart
        const sensKeys = Object.keys(result.sensitivity);
        const sensValues = sensKeys.map(k => result.sensitivity[k]);
        renderChart('chart-sensitivity', 'bar', {
            labels: sensKeys.map(k => k.replace(/([A-Z])/g, ' $1').trim()),
            datasets: [{
                label: 'Average Penalty (1 = no impact)',
                data: sensValues,
                backgroundColor: sensValues.map(v => v < 0.7 ? '#ea4335' : v < 0.9 ? '#fbbc04' : '#34a853'),
            }],
        }, { scales: { y: { min: 0, max: 1 } }, plugins: { legend: { display: false } } });
    }

    // --- Scenarios ---
    document.getElementById('run-scenario-btn').addEventListener('click', runScenario);

    function runScenario() {
        if (!state.baselineResult) {
            alert('Please run the baseline simulation first (Simulation tab).');
            return;
        }

        const modifications = {
            feedMultiplier: parseFloat(document.getElementById('scenario-feed').value),
            filtrationImprovement: parseFloat(document.getElementById('scenario-filtration').value),
            aerationImprovement: parseFloat(document.getElementById('scenario-aeration').value),
            fishCountMultiplier: parseFloat(document.getElementById('scenario-fish').value),
            waterChangeIncrease: parseFloat(document.getElementById('scenario-waterchange').value),
        };

        const scenarioResult = KoiSim.runScenario(
            state.baselinePond, state.baselineConditions, state.baselineWQParams, modifications
        );

        displayScenarioResults(state.baselineResult, scenarioResult);
    }

    function displayScenarioResults(baseline, scenario) {
        document.getElementById('scenario-results').style.display = '';

        const dayLabels = Array.from({ length: baseline.fish[0].weightHistory.length }, (_, i) => i);

        // Weight comparison - first fish only for clarity, or all
        const datasets = [];
        baseline.fish.forEach((f, i) => {
            datasets.push({
                label: `${f.id} (baseline)`,
                data: f.weightHistory,
                borderColor: getColor(i),
                borderWidth: 2,
                pointRadius: 0,
                borderDash: [5, 5],
            });
            datasets.push({
                label: `${f.id} (scenario)`,
                data: scenario.fish[i].weightHistory,
                borderColor: getColor(i),
                borderWidth: 2,
                pointRadius: 0,
            });
        });

        renderChart('chart-scenario-weight', 'line', {
            labels: dayLabels,
            datasets,
        }, { scales: { y: { title: { display: true, text: 'Weight (g)' } }, x: { title: { display: true, text: 'Day' } } } });

        // Risk comparison
        const days = Array.from({ length: baseline.dailyRiskScores.length }, (_, i) => i + 1);
        renderChart('chart-scenario-risk', 'line', {
            labels: days,
            datasets: [
                { label: 'Baseline Risk', data: baseline.dailyRiskScores, borderColor: '#ea4335', borderWidth: 1.5, pointRadius: 0, borderDash: [5, 5] },
                { label: 'Scenario Risk', data: scenario.dailyRiskScores, borderColor: '#34a853', borderWidth: 1.5, pointRadius: 0 },
            ],
        }, { scales: { y: { min: 0, max: 1 }, x: { title: { display: true, text: 'Day' } } } });

        // Summary table
        const tbody = document.querySelector('#scenario-table tbody');
        tbody.innerHTML = baseline.fish.map((f, i) => {
            const baseW = f.currentWeight;
            const scenW = scenario.fish[i].currentWeight;
            const diff = scenW - baseW;
            const pct = ((diff / baseW) * 100).toFixed(1);
            return `<tr>
                <td>${f.id}</td>
                <td>${baseW.toFixed(1)}</td>
                <td>${scenW.toFixed(1)}</td>
                <td>${diff > 0 ? '+' : ''}${diff.toFixed(1)}</td>
                <td>${diff > 0 ? '+' : ''}${pct}%</td>
            </tr>`;
        }).join('');
    }

    // --- Chart Helpers ---
    function renderChart(canvasId, type, data, options = {}) {
        if (state.charts[canvasId]) {
            state.charts[canvasId].destroy();
        }
        const ctx = document.getElementById(canvasId).getContext('2d');
        state.charts[canvasId] = new Chart(ctx, {
            type,
            data,
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: { intersect: false, mode: 'index' },
                plugins: { legend: { position: 'top' } },
                ...options,
            },
        });
    }

    const COLORS = ['#1a73e8', '#ea4335', '#34a853', '#fbbc04', '#9c27b0', '#ff6d00', '#00bcd4', '#795548'];
    function getColor(index, alpha) {
        const c = COLORS[index % COLORS.length];
        if (alpha !== undefined) {
            const r = parseInt(c.slice(1, 3), 16);
            const g = parseInt(c.slice(3, 5), 16);
            const b = parseInt(c.slice(5, 7), 16);
            return `rgba(${r},${g},${b},${alpha})`;
        }
        return c;
    }

    // --- Init ---
    renderFishList();

    // Add default fish if none
    if (state.fish.length === 0) {
        state.fish = [
            { id: 'Tancho', type: 'individual', count: 1, length: 25, weight: 300, age: 18, feedQuality: 0.8 },
            { id: 'Showa', type: 'individual', count: 1, length: 20, weight: 150, age: 12, feedQuality: 0.8 },
            { id: 'Kohaku', type: 'individual', count: 1, length: 30, weight: 500, age: 24, feedQuality: 0.8 },
            { id: '2025 Fry', type: 'cohort', count: 5, length: 10, weight: 20, age: 3, feedQuality: 0.8 },
        ];
        renderFishList();
    }
})();
