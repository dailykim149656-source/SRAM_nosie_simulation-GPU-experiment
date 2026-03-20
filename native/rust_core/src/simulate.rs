use rand::{rngs::SmallRng, Rng, SeedableRng};
use rand_distr::Normal;
use serde::{Deserialize, Serialize};

fn default_backend() -> String {
    "standard".to_string()
}
fn default_temperature() -> f64 {
    310.0
}
fn default_voltage() -> f64 {
    1.0
}
fn default_num_cells() -> usize {
    32
}
fn default_noise_enable() -> bool {
    true
}
fn default_variability_enable() -> bool {
    true
}
fn default_monte_carlo_runs() -> usize {
    10
}
fn default_width() -> f64 {
    1.0
}
fn default_length() -> f64 {
    1.0
}
fn default_include_thermal_noise() -> bool {
    true
}

#[derive(Debug, Clone, Deserialize)]
pub struct SimulateRequest {
    #[serde(default = "default_backend")]
    pub backend: String,
    #[serde(default = "default_temperature")]
    pub temperature: f64,
    #[serde(default = "default_voltage")]
    pub voltage: f64,
    #[serde(default = "default_num_cells")]
    pub num_cells: usize,
    #[serde(default)]
    pub input_data: Vec<i32>,
    #[serde(default = "default_noise_enable")]
    pub noise_enable: bool,
    #[serde(default = "default_variability_enable")]
    pub variability_enable: bool,
    #[serde(default = "default_monte_carlo_runs")]
    pub monte_carlo_runs: usize,
    #[serde(default = "default_width")]
    pub width: f64,
    #[serde(default = "default_length")]
    pub length: f64,
    #[serde(default = "default_include_thermal_noise")]
    pub include_thermal_noise: bool,
    #[serde(default)]
    pub seed: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct SimulateResponse {
    pub backend: String,
    pub temperature: f64,
    pub voltage: f64,
    pub input_data: Vec<i32>,
    pub output_data: Vec<f64>,
    pub noise_values: Vec<f64>,
    pub snm_values: Vec<f64>,
    pub bit_errors: usize,
    pub bit_error_rate: f64,
    pub ber_std: f64,
    pub ber_confidence_95: f64,
    pub monte_carlo_ber: Vec<f64>,
    pub thermal_sigma: f64,
    pub include_thermal_noise: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum BackendKind {
    Standard,
    Hybrid,
}

pub fn simulate_array(req: &SimulateRequest) -> Result<SimulateResponse, String> {
    if !(req.temperature.is_finite() && req.temperature > 0.0) {
        return Err("temperature must be a finite positive value".to_string());
    }
    if !(req.voltage.is_finite() && req.voltage > 0.0) {
        return Err("voltage must be a finite positive value".to_string());
    }
    if !(req.width.is_finite() && req.width > 0.0) {
        return Err("width must be a finite positive value".to_string());
    }
    if !(req.length.is_finite() && req.length > 0.0) {
        return Err("length must be a finite positive value".to_string());
    }

    let backend_kind = parse_backend(&req.backend);
    let num_cells = req.num_cells.max(1);
    let runs = req.monte_carlo_runs.max(1);
    let input_data = normalized_input_data(&req.input_data, num_cells);
    let thermal_sigma = if req.include_thermal_noise {
        thermal_noise_sigma(req.temperature, req.voltage)
    } else {
        0.0
    };

    let wl = (req.width * req.length).max(1e-12);
    let sigma_vth = 5.0 / wl.sqrt() / 1000.0;

    let seed = req.seed.unwrap_or(0x5A17_2026_u64);
    let mut rng = SmallRng::seed_from_u64(seed);
    let normal_unit = Normal::new(0.0, 1.0).map_err(|err| err.to_string())?;

    let (output_data, noise_values, snm_values, monte_carlo_ber) = match backend_kind {
        BackendKind::Standard => run_standard_backend(
            req,
            &input_data,
            thermal_sigma,
            sigma_vth,
            &mut rng,
            &normal_unit,
            runs,
        ),
        BackendKind::Hybrid => run_hybrid_backend(
            req,
            &input_data,
            thermal_sigma,
            sigma_vth,
            &mut rng,
            &normal_unit,
            runs,
        ),
    };

    let bit_error_rate = mean(&monte_carlo_ber);
    let ber_std = std_dev_population(&monte_carlo_ber, bit_error_rate);
    let ber_confidence_95 = 1.96 * ber_std / (runs as f64).sqrt();
    let bit_errors = (bit_error_rate * num_cells as f64).round() as usize;

    Ok(SimulateResponse {
        backend: match backend_kind {
            BackendKind::Standard => "standard-native".to_string(),
            BackendKind::Hybrid => "hybrid-native".to_string(),
        },
        temperature: req.temperature,
        voltage: req.voltage,
        input_data,
        output_data,
        noise_values,
        snm_values,
        bit_errors,
        bit_error_rate,
        ber_std,
        ber_confidence_95,
        monte_carlo_ber,
        thermal_sigma,
        include_thermal_noise: req.include_thermal_noise,
    })
}

fn parse_backend(backend: &str) -> BackendKind {
    let normalized = backend.trim().to_ascii_lowercase();
    if normalized == "hybrid" || normalized.starts_with("hybrid-") || normalized.starts_with("hybrid_") {
        BackendKind::Hybrid
    } else {
        BackendKind::Standard
    }
}

fn run_standard_backend(
    req: &SimulateRequest,
    input_data: &[i32],
    thermal_sigma: f64,
    sigma_vth: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
    runs: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let num_cells = input_data.len().max(1);
    let mut output_data = Vec::with_capacity(num_cells);
    let mut noise_values = Vec::with_capacity(num_cells);
    let mut snm_values = Vec::with_capacity(num_cells);
    let mut monte_carlo_ber = Vec::with_capacity(runs);

    for run_idx in 0..runs {
        let mut run_errors: usize = 0;

        for bit_ref in input_data.iter() {
            let stored_bit = if *bit_ref > 0 { 1.0 } else { 0.0 };

            let noise = if req.noise_enable {
                let mut n = compute_standard_noise(
                    req.temperature,
                    req.voltage,
                    req.variability_enable,
                    req.include_thermal_noise,
                    thermal_sigma,
                    sigma_vth,
                    rng,
                    normal_unit,
                );
                if !n.is_finite() {
                    n = 0.0;
                }
                n.max(0.0)
            } else {
                0.0
            };

            let mut output = stored_bit;
            if req.noise_enable {
                output += gaussian(rng, normal_unit, noise);
                output = output.clamp(0.0, 1.0);
            }

            if run_idx == 0 {
                output_data.push(output);
                noise_values.push(noise);
                if req.variability_enable {
                    let delta_vth = gaussian(rng, normal_unit, sigma_vth);
                    snm_values.push(calculate_snm(req.voltage, delta_vth));
                }
            }

            let expected_high = stored_bit > 0.5;
            let actual_high = output > 0.5;
            if expected_high != actual_high {
                run_errors += 1;
            }
        }

        monte_carlo_ber.push(run_errors as f64 / num_cells as f64);
    }

    (output_data, noise_values, snm_values, monte_carlo_ber)
}

#[derive(Debug, Clone, Copy)]
struct NotGateParams {
    w: f64,
    b: f64,
}

#[derive(Debug, Clone, Copy)]
struct AndGateParams {
    w1: f64,
    w2: f64,
    b: f64,
}

#[derive(Debug, Clone, Copy)]
struct HybridCellGateParams {
    inv1: NotGateParams,
    inv2: NotGateParams,
    access1: AndGateParams,
}

fn run_hybrid_backend(
    req: &SimulateRequest,
    input_data: &[i32],
    thermal_sigma: f64,
    sigma_vth: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
    runs: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let num_cells = input_data.len().max(1);
    let mut output_data = Vec::with_capacity(num_cells);
    let mut noise_values = Vec::with_capacity(num_cells);
    let mut snm_values = Vec::with_capacity(num_cells);
    let mut monte_carlo_ber = Vec::with_capacity(runs);

    for run_idx in 0..runs {
        let mut run_errors: usize = 0;

        for bit_ref in input_data.iter() {
            let gate_params = sample_hybrid_cell_gate_params(
                req.variability_enable,
                sigma_vth,
                rng,
                normal_unit,
            );
            let target_bit = if *bit_ref > 0 { 1 } else { 0 };
            let (q, _q_bar) = hybrid_write_and_stabilize(
                target_bit,
                gate_params.inv1,
                gate_params.inv2,
                req.temperature,
                req.voltage,
                req.noise_enable,
                req.include_thermal_noise,
                thermal_sigma,
                rng,
                normal_unit,
            );

            let read_value = hybrid_read(
                q,
                gate_params.access1,
                req.temperature,
                req.voltage,
                req.noise_enable,
                req.include_thermal_noise,
                thermal_sigma,
                rng,
                normal_unit,
            );
            let output_bit = if read_value >= 0.5 { 1 } else { 0 };

            if run_idx == 0 {
                output_data.push(output_bit as f64);
                let noise = if req.noise_enable {
                    hybrid_total_noise_level(
                        req.temperature,
                        req.voltage,
                        req.include_thermal_noise,
                        thermal_sigma,
                    )
                } else {
                    0.0
                };
                noise_values.push(noise);

                if req.variability_enable {
                    let snm = hybrid_snm_with_variability(
                        req.temperature,
                        req.voltage,
                        sigma_vth,
                        rng,
                        normal_unit,
                    );
                    snm_values.push(snm);
                }
            }

            if output_bit != target_bit {
                run_errors += 1;
            }
        }

        monte_carlo_ber.push(run_errors as f64 / num_cells as f64);
    }

    (output_data, noise_values, snm_values, monte_carlo_ber)
}

fn sample_hybrid_cell_gate_params(
    variability_enable: bool,
    sigma_vth: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
) -> HybridCellGateParams {
    HybridCellGateParams {
        inv1: sample_not_gate_params(variability_enable, sigma_vth, rng, normal_unit),
        inv2: sample_not_gate_params(variability_enable, sigma_vth, rng, normal_unit),
        access1: sample_and_gate_params(variability_enable, sigma_vth, rng, normal_unit),
    }
}

fn sample_not_gate_params(
    variability_enable: bool,
    sigma_vth: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
) -> NotGateParams {
    // Calibrated to the Python hybrid gate training distribution.
    let mut w = -0.114_9 + gaussian(rng, normal_unit, 0.049_0);
    let mut b = 0.051_4 + gaussian(rng, normal_unit, 0.031_2);

    if variability_enable {
        let mismatch_sigma = (sigma_vth * 6.0).max(0.0);
        w += gaussian(rng, normal_unit, mismatch_sigma);
        b += gaussian(rng, normal_unit, mismatch_sigma * 0.8);
    }

    NotGateParams { w, b }
}

fn sample_and_gate_params(
    variability_enable: bool,
    sigma_vth: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
) -> AndGateParams {
    // Calibrated to the Python hybrid gate training distribution.
    let mut w1 = 0.190_9 + gaussian(rng, normal_unit, 0.053_9);
    let mut w2 = 0.103_8 + gaussian(rng, normal_unit, 0.040_1);
    let mut b = -0.243_4 + gaussian(rng, normal_unit, 0.061_2);

    if variability_enable {
        let mismatch_sigma = (sigma_vth * 6.0).max(0.0);
        w1 += gaussian(rng, normal_unit, mismatch_sigma);
        w2 += gaussian(rng, normal_unit, mismatch_sigma);
        b += gaussian(rng, normal_unit, mismatch_sigma * 1.2);
    }

    AndGateParams { w1, w2, b }
}

fn normalized_input_data(input_data: &[i32], num_cells: usize) -> Vec<i32> {
    if input_data.is_empty() {
        return (0..num_cells).map(|i| (i % 2) as i32).collect();
    }
    input_data
        .iter()
        .take(num_cells)
        .map(|v| if *v > 0 { 1 } else { 0 })
        .chain((input_data.len()..num_cells).map(|i| (i % 2) as i32))
        .collect()
}

fn compute_standard_noise(
    temperature: f64,
    voltage: f64,
    variability_enable: bool,
    include_thermal_noise: bool,
    thermal_sigma: f64,
    sigma_vth: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
) -> f64 {
    let perceptron_weight = perceptron_noise_weight(temperature, voltage);
    let temp_factor = (temperature - 273.15) / 100.0;
    let volt_factor = ((1.0 - voltage) / 1.0).max(-0.8);

    let mut total_noise = 0.05 * (1.0 + perceptron_weight);
    total_noise *= 1.0 + 0.5 * temp_factor;
    total_noise *= 1.0 + 0.3 * volt_factor;

    if variability_enable {
        total_noise += gaussian(rng, normal_unit, sigma_vth).abs();
    }

    if include_thermal_noise {
        total_noise += thermal_sigma * 0.1;
    }

    total_noise
}

fn hybrid_write_and_stabilize(
    target_bit: i32,
    inv1: NotGateParams,
    inv2: NotGateParams,
    temperature: f64,
    voltage: f64,
    noise_enable: bool,
    include_thermal_noise: bool,
    thermal_sigma: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
) -> (i32, i32) {
    let mut q = if target_bit > 0 { 1 } else { 0 };
    let mut q_bar = 1 - q;
    let gate_noise = if noise_enable {
        hybrid_total_noise_level(temperature, voltage, include_thermal_noise, thermal_sigma)
    } else {
        0.0
    };

    for _ in 0..10 {
        let q_new = hybrid_gate_not(
            q_bar as f64,
            inv1,
            temperature,
            voltage,
            gate_noise,
            rng,
            normal_unit,
        );
        let q_bar_new = hybrid_gate_not(
            q as f64,
            inv2,
            temperature,
            voltage,
            gate_noise,
            rng,
            normal_unit,
        );
        if q_new == q && q_bar_new == q_bar {
            break;
        }
        q = q_new;
        q_bar = q_bar_new;
    }

    (q, q_bar)
}

fn hybrid_read(
    q: i32,
    access1: AndGateParams,
    temperature: f64,
    voltage: f64,
    noise_enable: bool,
    include_thermal_noise: bool,
    thermal_sigma: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
) -> f64 {
    let gate_noise = if noise_enable {
        hybrid_total_noise_level(temperature, voltage, include_thermal_noise, thermal_sigma)
    } else {
        0.0
    };
    let read_bit = hybrid_gate_and(
        1.0,
        q as f64,
        access1,
        temperature,
        voltage,
        gate_noise,
        rng,
        normal_unit,
    );
    read_bit as f64
}

fn hybrid_gate_not(
    input: f64,
    gate: NotGateParams,
    temperature: f64,
    voltage: f64,
    gate_noise: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
) -> i32 {
    // Perceptron NOT gate: z = w*x + b, scaled by PVT and perturbed by noise.
    let mut z = gate.w * input + gate.b;
    z *= hybrid_drive_factor(temperature, voltage);
    z += gaussian(rng, normal_unit, gate_noise);
    if z >= 0.0 { 1 } else { 0 }
}

fn hybrid_gate_and(
    a: f64,
    b: f64,
    gate: AndGateParams,
    temperature: f64,
    voltage: f64,
    gate_noise: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
) -> i32 {
    // Perceptron AND gate: z = w1*a + w2*b + b0, scaled by PVT and perturbed by noise.
    let mut z = gate.w1 * a + gate.w2 * b + gate.b;
    z *= hybrid_drive_factor(temperature, voltage);
    z += gaussian(rng, normal_unit, gate_noise);
    if z >= 0.0 { 1 } else { 0 }
}

fn hybrid_drive_factor(temperature: f64, voltage: f64) -> f64 {
    let temp_factor = 1.0 + (temperature - 300.0) / 300.0 * 0.1;
    let volt_factor = voltage / 1.0;
    (temp_factor * volt_factor).max(0.05)
}

fn hybrid_total_noise_level(
    temperature: f64,
    voltage: f64,
    include_thermal_noise: bool,
    thermal_sigma: f64,
) -> f64 {
    let mlp_noise_weight = perceptron_noise_weight(temperature, voltage);
    let base_noise = 0.05 * (1.0 + mlp_noise_weight);
    let temp_factor = (temperature - 273.15) / 100.0;
    let volt_factor = (1.0 - voltage) / 1.0;

    let mut total_noise = base_noise * (1.0 + 0.5 * temp_factor) * (1.0 + 0.3 * volt_factor);
    if include_thermal_noise {
        let thermal_noise = (1.38e-23_f64 * temperature).sqrt() * 1e10_f64;
        total_noise += thermal_noise * 0.01;
        total_noise += thermal_sigma * 0.1;
    }
    total_noise.max(0.0)
}

fn hybrid_snm_with_variability(
    temperature: f64,
    voltage: f64,
    sigma_vth: f64,
    rng: &mut SmallRng,
    normal_unit: &Normal<f64>,
) -> f64 {
    let base_snm = 0.2_f64;
    let temp_degradation = (temperature - 300.0) / 300.0 * 0.25;
    let volt_degradation = (1.0 - voltage) / 1.0 * 0.5;
    let nominal_snm = (base_snm * (1.0 - temp_degradation - volt_degradation)).max(0.0);
    let mismatch = gaussian(rng, normal_unit, sigma_vth * 0.1);
    (nominal_snm + mismatch).max(0.0)
}

fn perceptron_noise_weight(temperature: f64, voltage: f64) -> f64 {
    let norm_temp = (temperature - 310.0) / 30.0;
    let norm_volt = (voltage - 1.0) / 0.15;
    let z = 0.7 * norm_temp - 0.9 * norm_volt;
    1.0 / (1.0 + (-z).exp())
}

fn thermal_noise_sigma(temperature: f64, voltage: f64) -> f64 {
    let k_b = 1.38e-23_f64;
    let cap = 5e-15_f64;
    let sigma = (k_b * temperature / cap).sqrt();
    let voltage_factor = (1.0 / voltage).max(0.5);
    sigma * voltage_factor
}

fn calculate_snm(voltage: f64, delta_vth: f64) -> f64 {
    let vth_eff = 0.4 + delta_vth;
    ((voltage - 2.0 * vth_eff) * 0.5).abs().max(0.0)
}

fn gaussian(rng: &mut SmallRng, normal_unit: &Normal<f64>, sigma: f64) -> f64 {
    if sigma <= 0.0 {
        0.0
    } else {
        rng.sample(*normal_unit) * sigma
    }
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
    let var = values
        .iter()
        .map(|v| {
            let d = *v - mean_value;
            d * d
        })
        .sum::<f64>()
        / values.len() as f64;
    var.sqrt()
}
