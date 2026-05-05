/**
 * Koi Pond Growth Simulation Engine
 * Implements the semi-mechanistic growth model from the spec.
 */

const KoiSim = (() => {

    // --- Pseudo-random number generator (seeded) ---
    class SeededRandom {
        constructor(seed = 42) {
            this.seed = seed;
        }
        next() {
            this.seed = (this.seed * 16807) % 2147483647;
            return (this.seed - 1) / 2147483646;
        }
        normal(mean = 0, std = 1) {
            // Box-Muller transform
            const u1 = this.next();
            const u2 = this.next();
            const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
            return mean + z * std;
        }
    }

    // --- Water Quality Penalties ---
    class WaterQualityPenalty {
        constructor(params = {}) {
            this.ammoniaSafe = params.ammoniaSafe ?? 0.02;
            this.ammoniaSevere = params.ammoniaSevere ?? 0.10;
            this.nitriteSafe = params.nitriteSafe ?? 0.1;
            this.nitriteSevere = params.nitriteSevere ?? 0.5;
            this.doLethal = params.doLethal ?? 2.0;
            this.doSafe = params.doSafe ?? 6.0;
            this.phOptimal = params.phOptimal ?? 7.2;
            this.phTolerance = params.phTolerance ?? 1.0;
            this.phSwingThreshold = params.phSwingThreshold ?? 0.5;
            this.densityOptimal = params.densityOptimal ?? 5.0;
            this.densityDecay = params.densityDecay ?? 0.3;
        }

        computeUnionizedAmmonia(totalAmmonia, ph, temperature) {
            const pka = 0.09018 + 2729.92 / (temperature + 273.15);
            const fractionNH3 = 1.0 / (1.0 + Math.pow(10, pka - ph));
            return totalAmmonia * fractionNH3;
        }

        penaltyAmmonia(totalAmmonia, ph, temperature) {
            const nh3 = this.computeUnionizedAmmonia(totalAmmonia, ph, temperature);
            if (nh3 <= this.ammoniaSafe) return 1.0;
            if (nh3 >= this.ammoniaSevere) return 0.05;
            return 1.0 - 0.95 * (nh3 - this.ammoniaSafe) / (this.ammoniaSevere - this.ammoniaSafe);
        }

        penaltyNitrite(nitrite) {
            if (nitrite <= this.nitriteSafe) return 1.0;
            if (nitrite >= this.nitriteSevere) return 0.05;
            return 1.0 - 0.95 * (nitrite - this.nitriteSafe) / (this.nitriteSevere - this.nitriteSafe);
        }

        penaltyDO(dissolvedOxygen) {
            if (dissolvedOxygen <= this.doLethal) return 0.0;
            if (dissolvedOxygen >= this.doSafe) return 1.0;
            return (dissolvedOxygen - this.doLethal) / (this.doSafe - this.doLethal);
        }

        penaltyPH(ph, phPrevious = null) {
            const deviation = Math.abs(ph - this.phOptimal);
            let penaltyDev;
            if (deviation <= this.phTolerance * 0.5) {
                penaltyDev = 1.0;
            } else if (deviation >= this.phTolerance * 2.0) {
                penaltyDev = 0.2;
            } else {
                penaltyDev = 1.0 - 0.8 * (deviation - this.phTolerance * 0.5) / (this.phTolerance * 1.5);
            }

            let penaltySwing = 1.0;
            if (phPrevious !== null) {
                const swing = Math.abs(ph - phPrevious);
                if (swing > this.phSwingThreshold * 3) {
                    penaltySwing = 0.3;
                } else if (swing > this.phSwingThreshold) {
                    penaltySwing = 1.0 - 0.7 * (swing - this.phSwingThreshold) / (this.phSwingThreshold * 2);
                }
            }

            return penaltyDev * penaltySwing;
        }

        penaltyDensity(stockingDensity) {
            if (stockingDensity <= this.densityOptimal) return 1.0;
            return Math.exp(-this.densityDecay * (stockingDensity - this.densityOptimal));
        }

        combined(totalAmmonia, nitrite, dissolvedOxygen, ph, temperature, stockingDensity, phPrevious = null) {
            return (
                this.penaltyAmmonia(totalAmmonia, ph, temperature) *
                this.penaltyNitrite(nitrite) *
                this.penaltyDO(dissolvedOxygen) *
                this.penaltyPH(ph, phPrevious) *
                this.penaltyDensity(stockingDensity)
            );
        }

        detailed(totalAmmonia, nitrite, dissolvedOxygen, ph, temperature, stockingDensity, phPrevious = null) {
            return {
                ammonia: this.penaltyAmmonia(totalAmmonia, ph, temperature),
                nitrite: this.penaltyNitrite(nitrite),
                dissolvedOxygen: this.penaltyDO(dissolvedOxygen),
                ph: this.penaltyPH(ph, phPrevious),
                density: this.penaltyDensity(stockingDensity),
            };
        }
    }

    // --- Growth Model ---
    class GrowthModel {
        constructor(params = {}) {
            this.gMax = params.gMax ?? 0.015;
            this.tempMin = params.tempMin ?? 8.0;
            this.tempOpt = params.tempOpt ?? 24.0;
            this.tempMax = params.tempMax ?? 34.0;
            this.tempSigma = params.tempSigma ?? 6.0;
            this.kF = params.kF ?? 15.0;
        }

        temperatureResponse(temperature) {
            if (temperature <= this.tempMin || temperature >= this.tempMax) return 0.0;
            return Math.exp(-Math.pow(temperature - this.tempOpt, 2) / (2 * Math.pow(this.tempSigma, 2)));
        }

        feedingResponse(dailyRation, feedQuality) {
            if (dailyRation <= 0) return 0.0;
            return feedQuality * dailyRation / (dailyRation + this.kF);
        }
    }

    // --- Simulation ---
    function generateConditions(config) {
        const rng = new SeededRandom(config.seed ?? 42);
        const days = config.days ?? 90;
        const startMonth = config.startMonth ?? 5;
        const baseAmmonia = config.baseAmmonia ?? 0.1;
        const baseNitrite = config.baseNitrite ?? 0.05;
        const basePH = config.basePH ?? 7.2;
        const baseDO = config.baseDO ?? 8.0;
        const dailyRation = config.dailyRation ?? 20;
        const waterChangePct = (config.waterChangePct ?? 10) / 100;

        const conditions = [];
        for (let day = 0; day < days; day++) {
            const dayOfYear = (startMonth - 1) * 30 + day;
            let temp = 18 + 8 * Math.sin(2 * Math.PI * (dayOfYear - 80) / 365) + rng.normal(0, 1.5);
            temp = Math.max(5, Math.min(35, temp));

            let ph = basePH + rng.normal(0, 0.15);
            ph = Math.max(6.5, Math.min(8.5, ph));

            let ammonia = baseAmmonia + Math.abs(rng.normal(0, 0.05));
            if (rng.next() < 0.05) ammonia += rng.next() * 0.3 + 0.2;

            let nitrite = baseNitrite + ammonia * 0.3 + Math.abs(rng.normal(0, 0.02));

            let nitrate = 20 + day * 0.1 + rng.normal(0, 2);

            let dissolvedOxygen = baseDO - 0.1 * (temp - 20) + rng.normal(0, 0.5);
            dissolvedOxygen = Math.max(3, Math.min(12, dissolvedOxygen));

            let ration = dailyRation;
            if (temp < 10) ration = 2;
            else if (temp < 15) ration = 8;
            else ration = dailyRation + rng.normal(0, 2);

            const waterChange = (day % 7 === 0) ? waterChangePct : 0;
            if (waterChange > 0) {
                nitrate *= (1 - waterChange);
                ammonia *= (1 - waterChange * 0.3);
            }

            conditions.push({
                temperature: temp,
                ph,
                totalAmmonia: ammonia,
                nitrite,
                nitrate,
                dissolvedOxygen,
                dailyRation: Math.max(0, ration),
                waterChange,
            });
        }
        return conditions;
    }

    function runSimulation(pond, conditions, wqParams = {}) {
        const wq = new WaterQualityPenalty(wqParams);
        const model = new GrowthModel();

        // Deep clone fish for simulation
        const fish = pond.fish.map(f => ({
            ...f,
            currentWeight: f.weight,
            currentLength: f.length,
            weightHistory: [f.weight],
            lengthHistory: [f.length],
        }));

        const totalFishCount = fish.reduce((sum, f) => sum + (f.count || 1), 0);
        const dailyRiskScores = [];
        const dailyPenalties = [];
        let phPrevious = null;

        for (const cond of conditions) {
            const totalBiomass = fish.reduce((sum, f) => sum + f.currentWeight * (f.count || 1), 0);
            const stockingDensity = totalBiomass / pond.volume;

            const penalties = wq.detailed(
                cond.totalAmmonia, cond.nitrite, cond.dissolvedOxygen,
                cond.ph, cond.temperature, stockingDensity, phPrevious
            );
            const combinedPenalty = wq.combined(
                cond.totalAmmonia, cond.nitrite, cond.dissolvedOxygen,
                cond.ph, cond.temperature, stockingDensity, phPrevious
            );
            dailyRiskScores.push(1.0 - combinedPenalty);
            dailyPenalties.push(penalties);

            for (const f of fish) {
                const fT = model.temperatureResponse(cond.temperature);
                const fF = model.feedingResponse(cond.dailyRation, f.feedQuality);
                const dw = model.gMax * f.currentWeight * fT * fF * combinedPenalty;
                f.currentWeight = Math.max(f.currentWeight + dw, f.currentWeight * 0.99);
                f.currentLength = Math.pow(f.currentWeight / 0.02, 1.0 / 3.0);
                f.weightHistory.push(f.currentWeight);
                f.lengthHistory.push(f.currentLength);
            }

            phPrevious = cond.ph;
        }

        // Sensitivity analysis
        const sensitivity = { ammonia: 0, nitrite: 0, dissolvedOxygen: 0, ph: 0, density: 0 };
        for (const p of dailyPenalties) {
            for (const key of Object.keys(sensitivity)) {
                sensitivity[key] += p[key];
            }
        }
        for (const key of Object.keys(sensitivity)) {
            sensitivity[key] /= dailyPenalties.length;
        }

        return {
            fish,
            dailyRiskScores,
            dailyPenalties,
            sensitivity,
            conditions,
        };
    }

    function runScenario(pond, conditions, wqParams, modifications) {
        const modifiedConditions = conditions.map(cond => {
            const c = { ...cond };
            if (modifications.feedMultiplier) {
                c.dailyRation *= modifications.feedMultiplier;
            }
            if (modifications.filtrationImprovement) {
                const factor = 1.0 - modifications.filtrationImprovement;
                c.totalAmmonia *= factor;
                c.nitrite *= factor;
            }
            if (modifications.aerationImprovement) {
                c.dissolvedOxygen += modifications.aerationImprovement;
            }
            if (modifications.waterChangeIncrease) {
                const dilution = 1.0 - modifications.waterChangeIncrease * 0.5;
                c.totalAmmonia *= dilution;
                c.nitrite *= dilution;
                c.nitrate *= dilution;
            }
            return c;
        });

        const modifiedPond = {
            ...pond,
            fish: pond.fish.map(f => {
                const clone = { ...f };
                if (modifications.fishCountMultiplier && clone.count) {
                    clone.count = Math.round(clone.count * modifications.fishCountMultiplier);
                }
                return clone;
            }),
        };

        return runSimulation(modifiedPond, modifiedConditions, wqParams);
    }

    return {
        generateConditions,
        runSimulation,
        runScenario,
        WaterQualityPenalty,
        GrowthModel,
    };
})();
