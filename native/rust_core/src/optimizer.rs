use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize)]
pub struct WorkloadConfig {
    #[serde(default = "default_hidden_dim")]
    pub hidden_dim: usize,
    #[serde(default = "default_num_layers")]
    pub num_layers: usize,
    #[serde(default = "default_num_heads")]
    pub num_heads: usize,
    #[serde(default = "default_seq_length")]
    pub seq_length: usize,
    #[serde(default = "default_batch_size")]
    pub batch_size: usize,
    #[serde(default = "default_precision")]
    pub precision: String,
    #[serde(default = "default_attention_type")]
    pub attention_type: String,
    #[serde(default)]
    pub num_kv_heads: Option<usize>,
    #[serde(default)]
    pub intermediate_size: Option<usize>,
}

impl Default for WorkloadConfig {
    fn default() -> Self {
        Self {
            hidden_dim: default_hidden_dim(),
            num_layers: default_num_layers(),
            num_heads: default_num_heads(),
            seq_length: default_seq_length(),
            batch_size: default_batch_size(),
            precision: default_precision(),
            attention_type: default_attention_type(),
            num_kv_heads: None,
            intermediate_size: None,
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct DesignConstraints {
    #[serde(default = "default_max_area_mm2")]
    pub max_area_mm2: f64,
    #[serde(default = "default_max_power_mw")]
    pub max_power_mw: f64,
    #[serde(default = "default_min_tapout_success_prob")]
    pub min_tapout_success_prob: f64,
}

impl Default for DesignConstraints {
    fn default() -> Self {
        Self {
            max_area_mm2: default_max_area_mm2(),
            max_power_mw: default_max_power_mw(),
            min_tapout_success_prob: default_min_tapout_success_prob(),
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct OptimizeRequest {
    #[serde(default)]
    pub workload: Option<WorkloadConfig>,
    #[serde(default)]
    pub sram_sizes_mb: Vec<f64>,
    #[serde(default)]
    pub snm_values_mv: Vec<f64>,
    #[serde(default)]
    pub vmin_values_v: Vec<f64>,
    #[serde(default)]
    pub constraints: Option<DesignConstraints>,
}

#[derive(Debug, Clone, Serialize)]
pub struct DesignPoint {
    pub sram_mb: f64,
    pub snm_mv: f64,
    pub vmin_v: f64,
    pub area_mm2: f64,
    pub power_mw: f64,
    pub tapout_success_prob: f64,
    pub tokens_per_sec: f64,
    pub accuracy_degradation: f64,
    pub ber: f64,
}

#[derive(Debug, Clone)]
struct KpiResult {
    ber: f64,
    accuracy_degradation_percent: f64,
    tokens_per_second: f64,
}

pub fn optimize_design(req: &OptimizeRequest) -> Result<Vec<DesignPoint>, String> {
    let workload = req.workload.clone().unwrap_or_default();
    let constraints = req.constraints.clone().unwrap_or_default();

    let sram_sizes = if req.sram_sizes_mb.is_empty() {
        vec![64.0, 96.0, 128.0, 192.0, 256.0, 384.0, 512.0]
    } else {
        req.sram_sizes_mb.clone()
    };
    let snm_values = if req.snm_values_mv.is_empty() {
        vec![150.0, 155.0, 160.0, 165.0, 170.0, 175.0, 180.0, 190.0]
    } else {
        req.snm_values_mv.clone()
    };
    let vmin_values = if req.vmin_values_v.is_empty() {
        vec![0.50, 0.55, 0.60, 0.65, 0.70]
    } else {
        req.vmin_values_v.clone()
    };

    if sram_sizes.is_empty() || snm_values.is_empty() || vmin_values.is_empty() {
        return Err("search space vectors must not be empty".to_string());
    }

    let mut candidates: Vec<DesignPoint> = Vec::new();
    for sram_mb in sram_sizes {
        for snm_mv in &snm_values {
            for vmin_v in &vmin_values {
                let perf = translate_to_system_kpis(&workload, *snm_mv, *vmin_v, 2.0, 25.0);
                let area_mm2 = estimate_area(sram_mb, *snm_mv);
                let power_mw = estimate_power(*vmin_v, 2.0);
                let tapout_success_prob = 100.0 - quantify_tapout_risk(*snm_mv, *vmin_v, &perf);

                if area_mm2 > constraints.max_area_mm2 {
                    continue;
                }
                if power_mw > constraints.max_power_mw {
                    continue;
                }
                if tapout_success_prob < constraints.min_tapout_success_prob {
                    continue;
                }

                candidates.push(DesignPoint {
                    sram_mb,
                    snm_mv: *snm_mv,
                    vmin_v: *vmin_v,
                    area_mm2,
                    power_mw,
                    tapout_success_prob,
                    tokens_per_sec: perf.tokens_per_second,
                    accuracy_degradation: perf.accuracy_degradation_percent,
                    ber: perf.ber,
                });
            }
        }
    }

    let mut pareto = extract_pareto_frontier(&candidates);
    pareto.sort_by(|a, b| a.area_mm2.total_cmp(&b.area_mm2));
    Ok(pareto)
}

fn default_hidden_dim() -> usize {
    4096
}
fn default_num_layers() -> usize {
    32
}
fn default_num_heads() -> usize {
    32
}
fn default_seq_length() -> usize {
    2048
}
fn default_batch_size() -> usize {
    1
}
fn default_precision() -> String {
    "fp16".to_string()
}
fn default_attention_type() -> String {
    "standard".to_string()
}
fn default_max_area_mm2() -> f64 {
    100.0
}
fn default_max_power_mw() -> f64 {
    50.0
}
fn default_min_tapout_success_prob() -> f64 {
    85.0
}

fn translate_to_system_kpis(
    workload: &WorkloadConfig,
    snm_mv: f64,
    vmin_v: f64,
    leakage_mw: f64,
    temp_c: f64,
) -> KpiResult {
    let ber = estimate_ber(snm_mv, temp_c, vmin_v);
    let active_bits = total_memory_bytes(workload) * 8.0;
    let token_error_prob = ber_to_token_error(ber, active_bits);
    let accuracy_degradation = (token_error_prob * 100.0).min(100.0);

    let nominal_latency_ms = estimate_nominal_latency(workload);
    let voltage_penalty_ms = voltage_to_latency_penalty(workload, vmin_v);
    let tail_latency_ms = nominal_latency_ms + voltage_penalty_ms;
    let tokens_per_second = if tail_latency_ms > 0.0 {
        1000.0 / tail_latency_ms
    } else {
        0.0
    };

    let _energy_per_token_uj = (leakage_mw / 1000.0) * tail_latency_ms * 1000.0;

    KpiResult {
        ber,
        accuracy_degradation_percent: accuracy_degradation,
        tokens_per_second,
    }
}

fn estimate_ber(snm_mv: f64, temp_c: f64, vmin_v: f64) -> f64 {
    let base_ber = 1e-12;
    let snm_delta = (175.0 - snm_mv).max(0.0);
    let snm_factor = 10_f64.powf(snm_delta / 15.0);

    let temp_delta = temp_c - 25.0;
    let temp_factor = 10_f64.powf(temp_delta / 40.0);

    let voltage_delta = (0.70 - vmin_v).max(0.0);
    let voltage_factor = 10_f64.powf(voltage_delta / 0.10);

    (base_ber * snm_factor * temp_factor * voltage_factor).min(1.0)
}

fn ber_to_token_error(ber: f64, active_bits: f64) -> f64 {
    if ber >= 1.0 {
        return 1.0;
    }
    if ber < 1e-6 {
        (active_bits * ber).min(1.0)
    } else {
        (1.0 - (1.0 - ber).powf(active_bits)).min(1.0)
    }
}

fn estimate_nominal_latency(workload: &WorkloadConfig) -> f64 {
    let base_latency_ms = 1.0;
    let size_factor = (workload.num_layers as f64 / 32.0) * (workload.hidden_dim as f64 / 4096.0);
    let seq_factor = (workload.seq_length as f64 / 2048.0).sqrt();
    let batch_factor = 1.0 / (workload.batch_size.max(1) as f64).sqrt();
    base_latency_ms * size_factor * seq_factor * batch_factor
}

fn voltage_to_latency_penalty(workload: &WorkloadConfig, vmin_v: f64) -> f64 {
    let nominal_voltage = 0.70;
    if vmin_v >= nominal_voltage {
        return 0.0;
    }
    let voltage_ratio = nominal_voltage / vmin_v.max(0.4);
    let latency_multiplier = voltage_ratio * voltage_ratio;
    estimate_nominal_latency(workload) * (latency_multiplier - 1.0)
}

fn estimate_area(sram_mb: f64, snm_mv: f64) -> f64 {
    let base_area_per_mb = 0.05;
    let mut snm_reduction = 1.0 - (180.0 - snm_mv) / 100.0;
    snm_reduction = snm_reduction.clamp(0.8, 1.2);
    sram_mb * base_area_per_mb * snm_reduction
}

fn estimate_power(vmin_v: f64, leakage_mw: f64) -> f64 {
    let nominal_vmin = 0.70;
    let voltage_ratio = vmin_v / nominal_vmin;
    let dynamic_factor = voltage_ratio * voltage_ratio;
    let leakage_factor = 10_f64.powf((vmin_v - nominal_vmin) / 0.1);
    leakage_mw * (0.5 * dynamic_factor + 0.5 * leakage_factor)
}

fn quantify_tapout_risk(snm_mv: f64, vmin_v: f64, perf: &KpiResult) -> f64 {
    let mut risk = 0.0;

    let pelgrom_sigma = 5.0;
    let snm_margin_sigma = (snm_mv - 160.0) / (3.0 * pelgrom_sigma);
    if snm_margin_sigma < 1.0 {
        risk += 25.0 * (1.0 - snm_margin_sigma);
    }

    if vmin_v < 0.55 {
        let vmin_risk = (0.55 - vmin_v) / 0.05;
        risk += 20.0 * vmin_risk;
    }

    if perf.accuracy_degradation_percent > 0.3 {
        let margin_risk = (perf.accuracy_degradation_percent - 0.3) / (0.5 - 0.3);
        risk += 10.0 * margin_risk;
    }

    risk += 5.0;
    risk.min(95.0)
}

fn extract_pareto_frontier(candidates: &[DesignPoint]) -> Vec<DesignPoint> {
    if candidates.is_empty() {
        return Vec::new();
    }

    let mut pareto = Vec::new();
    for (i, cand) in candidates.iter().enumerate() {
        let mut dominated = false;
        for (j, other) in candidates.iter().enumerate() {
            if i == j {
                continue;
            }

            let area_better = other.area_mm2 <= cand.area_mm2;
            let power_better = other.power_mw <= cand.power_mw;
            let success_better = other.tapout_success_prob >= cand.tapout_success_prob;
            let strict = other.area_mm2 < cand.area_mm2
                || other.power_mw < cand.power_mw
                || other.tapout_success_prob > cand.tapout_success_prob;

            if area_better && power_better && success_better && strict {
                dominated = true;
                break;
            }
        }

        if !dominated {
            pareto.push(cand.clone());
        }
    }
    pareto
}

fn total_memory_bytes(workload: &WorkloadConfig) -> f64 {
    let bytes_per_elem = precision_bytes(&workload.precision);
    let num_heads = workload.num_heads.max(1) as f64;
    let head_dim = workload.hidden_dim as f64 / num_heads;
    let batch = workload.batch_size.max(1) as f64;
    let seq = workload.seq_length.max(1) as f64;
    let layers = workload.num_layers.max(1) as f64;
    let num_kv_heads = workload
        .num_kv_heads
        .unwrap_or_else(|| {
            if workload.attention_type == "mqa" {
                1
            } else {
                workload.num_heads
            }
        })
        .max(1) as f64;
    let intermediate = workload
        .intermediate_size
        .unwrap_or(4 * workload.hidden_dim) as f64;

    let kv_cache_per_layer = 2.0 * batch * seq * num_kv_heads * head_dim * bytes_per_elem;
    let kv_cache = kv_cache_per_layer * layers;

    let hidden_states = batch * seq * workload.hidden_dim as f64 * bytes_per_elem;
    let attention_scores = batch
        * num_heads
        * seq
        * seq
        * bytes_per_elem
        * attention_sparsity_factor(&workload.attention_type);
    let ffn_intermediate = batch * seq * intermediate * bytes_per_elem;
    let activation = 2.0 * (hidden_states + attention_scores + ffn_intermediate);

    kv_cache + activation
}

fn precision_bytes(precision: &str) -> f64 {
    match precision {
        "fp32" => 4.0,
        "fp16" => 2.0,
        "bf16" => 2.0,
        "fp8" => 1.0,
        "int8" => 1.0,
        "int4" => 0.5,
        _ => 2.0,
    }
}

fn attention_sparsity_factor(attention_type: &str) -> f64 {
    match attention_type {
        "sparse" => 0.5,
        "local" => 0.3,
        _ => 1.0,
    }
}

