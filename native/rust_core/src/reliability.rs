use rand::{rngs::SmallRng, Rng, SeedableRng};
use rand_distr::Normal;
use serde::{Deserialize, Serialize};

const A_NBTI: f64 = 1e-12;
const N_NBTI: f64 = 0.25;
const M_NBTI: f64 = 2.0;
const EA_NBTI: f64 = 0.12;

const A_HCI: f64 = 1e-15;
const Q_HCI: f64 = 0.33;
const R_HCI: f64 = 1.5;
const EB_HCI: f64 = 0.20;

const K_B: f64 = 1.38e-23;
const Q_E: f64 = 1.6e-19;

fn default_temperature() -> f64 {
    330.0
}
fn default_vgs() -> f64 {
    1.0
}
fn default_vds() -> f64 {
    1.0
}
fn default_vth() -> f64 {
    0.4
}
fn default_width() -> f64 {
    1.0
}
fn default_num_cells() -> usize {
    32
}
fn default_failure_threshold() -> f64 {
    0.1
}
fn default_duty_cycle() -> f64 {
    0.5
}
fn default_failure_rate() -> f64 {
    0.01
}

#[derive(Debug, Clone, Deserialize)]
pub struct LifetimeRequest {
    #[serde(default = "default_temperature")]
    pub temperature: f64,
    #[serde(default = "default_vgs")]
    pub vgs: f64,
    #[serde(default = "default_vds")]
    pub vds: f64,
    #[serde(default = "default_vth")]
    pub vth: f64,
    #[serde(default = "default_width")]
    pub width: f64,
    #[serde(default = "default_num_cells")]
    pub num_cells: usize,
    #[serde(default = "default_failure_threshold")]
    pub failure_threshold: f64,
    #[serde(default = "default_duty_cycle")]
    pub duty_cycle: f64,
    #[serde(default = "default_failure_rate")]
    pub failure_rate: f64,
    #[serde(default)]
    pub seed: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct LifetimeResponse {
    pub backend: String,
    pub mean_lifetime: f64,
    pub std_lifetime: f64,
    pub min_lifetime: f64,
    pub max_lifetime: f64,
    pub t_90pct: f64,
    pub t_99pct: f64,
    pub lifetime_at_failure_rate: f64,
    pub failure_rate_fit: f64,
    pub cell_lifetimes: Vec<f64>,
    pub duty_cycle: f64,
    pub accepted_failure_rate: f64,
}

pub fn predict_lifetime(req: &LifetimeRequest) -> Result<LifetimeResponse, String> {
    if !(req.temperature.is_finite() && req.temperature > 0.0) {
        return Err("temperature must be a finite positive value".to_string());
    }
    if !(req.width.is_finite() && req.width > 0.0) {
        return Err("width must be a finite positive value".to_string());
    }
    if !(req.failure_threshold.is_finite() && req.failure_threshold > 0.0) {
        return Err("failure_threshold must be a finite positive value".to_string());
    }
    if !(req.duty_cycle.is_finite() && req.duty_cycle > 0.0 && req.duty_cycle <= 1.0) {
        return Err("duty_cycle must be in the range (0, 1]".to_string());
    }
    if !(req.failure_rate.is_finite() && req.failure_rate > 0.0 && req.failure_rate < 1.0) {
        return Err("failure_rate must be in the range (0, 1)".to_string());
    }

    let num_cells = req.num_cells.max(1);
    let mut lifetimes = Vec::with_capacity(num_cells);
    let seed = req.seed.unwrap_or(0xC0DE_2026_u64);
    let mut rng = SmallRng::seed_from_u64(seed);
    let unit_normal = Normal::new(0.0, 1.0).map_err(|err| err.to_string())?;
    let effective_duty_cycle = req.duty_cycle.max(1e-12);

    for _ in 0..num_cells {
        let jitter: f64 = rng.sample(unit_normal);
        let width_jitter = (1.0_f64 + jitter * 0.03_f64).clamp(0.5_f64, 1.5_f64);
        let effective_width = req.width * width_jitter;
        let stress_lifetime = estimate_lifetime(
            req.temperature,
            req.vgs,
            req.vds,
            req.vth,
            effective_width,
            req.failure_threshold,
        );
        lifetimes.push(stress_lifetime / effective_duty_cycle);
    }

    let mean_lifetime = mean(&lifetimes);
    let std_lifetime = std_dev_population(&lifetimes, mean_lifetime);
    let min_lifetime = lifetimes.iter().copied().fold(f64::INFINITY, f64::min);
    let max_lifetime = lifetimes
        .iter()
        .copied()
        .fold(f64::NEG_INFINITY, f64::max);

    let shape_param = 2.0_f64;
    let scale_param = mean_lifetime.max(1e-12);
    let t_90pct = scale_param * (-0.9_f64.ln()).powf(1.0 / shape_param);
    let t_99pct = scale_param * (-0.99_f64.ln()).powf(1.0 / shape_param);
    let lifetime_at_failure_rate =
        scale_param * (-(1.0_f64 - req.failure_rate).max(1e-12).ln()).powf(1.0 / shape_param);
    let failure_rate_fit = 1e9 / (scale_param * 365.25 * 24.0);

    Ok(LifetimeResponse {
        backend: "lifetime-native".to_string(),
        mean_lifetime,
        std_lifetime,
        min_lifetime,
        max_lifetime,
        t_90pct,
        t_99pct,
        lifetime_at_failure_rate,
        failure_rate_fit,
        cell_lifetimes: lifetimes,
        duty_cycle: req.duty_cycle,
        accepted_failure_rate: req.failure_rate,
    })
}

fn estimate_lifetime(
    temperature: f64,
    vgs: f64,
    vds: f64,
    vth: f64,
    width: f64,
    failure_threshold: f64,
) -> f64 {
    let mut t_min = 1.0_f64;
    let mut t_max = 3.15e9_f64;

    for _ in 0..50 {
        let t_mid = 0.5 * (t_min + t_max);
        let (total_shift, _, _) = calculate_total_vth_shift(temperature, vgs, vds, vth, width, t_mid);
        let snm = 0.2 - 0.05 * total_shift.abs();

        if snm < failure_threshold {
            t_max = t_mid;
        } else {
            t_min = t_mid;
        }
    }

    let lifetime_seconds = 0.5 * (t_min + t_max);
    lifetime_seconds / (365.25 * 24.0 * 3600.0)
}

fn calculate_total_vth_shift(
    temperature: f64,
    vgs: f64,
    vds: f64,
    vth: f64,
    width: f64,
    stress_time: f64,
) -> (f64, f64, f64) {
    let nbti = calculate_nbti_vth_shift(temperature, vgs, vth, stress_time);

    let un = 500.0_f64;
    let cox = 1.7e-3_f64;
    let l_eff = 1.0_f64;
    let vgo = (vgs - vth).max(0.0);
    let wl_ratio = (width * 1e-6) / (l_eff * 1e-6);

    let drain_current = if vds > vgo {
        wl_ratio * un * cox * 0.5 * vgo.powi(2)
    } else {
        wl_ratio * un * cox * (vgo * vds - vds.powi(2) * 0.5)
    };

    let hci = calculate_hci_vth_shift(temperature, drain_current, width, stress_time);
    let total = nbti + hci;
    (total, nbti, hci)
}

fn calculate_nbti_vth_shift(temperature: f64, vgs: f64, vth: f64, stress_time: f64) -> f64 {
    let vgo = vgs - vth;
    let temp_factor = (EA_NBTI / (K_B * temperature / Q_E)).exp();
    let time_factor = if stress_time <= 0.0 {
        0.0
    } else {
        stress_time.powf(N_NBTI)
    };
    let voltage_factor = vgo.max(0.0).powf(M_NBTI);
    A_NBTI * time_factor * temp_factor * voltage_factor
}

fn calculate_hci_vth_shift(
    temperature: f64,
    drain_current: f64,
    width: f64,
    stress_time: f64,
) -> f64 {
    let id_normalized = drain_current / (width * 1e-6).max(1e-18);
    let temp_factor = (-EB_HCI / (K_B * temperature / Q_E)).exp();
    let time_factor = if stress_time <= 0.0 {
        0.0
    } else {
        stress_time.powf(Q_HCI)
    };
    let current_factor = id_normalized.max(0.0).powf(R_HCI);
    -A_HCI * time_factor * temp_factor * current_factor
}

fn mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        0.0
    } else {
        values.iter().sum::<f64>() / values.len() as f64
    }
}

fn std_dev_population(values: &[f64], mean_value: f64) -> f64 {
    if values.len() < 2 {
        return 0.0;
    }
    let variance = values
        .iter()
        .map(|v| {
            let d = *v - mean_value;
            d * d
        })
        .sum::<f64>()
        / values.len() as f64;
    variance.sqrt()
}
