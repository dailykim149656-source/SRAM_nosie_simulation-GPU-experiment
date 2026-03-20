"""Analytical SRAM ground-truth model utilities.

This module provides lightweight analytical approximations used by the
validation workflow in the UI:
  - Seevinck-style static noise margin (SNM) estimate
  - Pelgrom Vth variability model
  - Closed-form BER from SNM/noise statistics
  - Dataset synthesis for ML benchmarking
"""

from __future__ import annotations

import numpy as np
from scipy import stats


class AnalyticalSRAMModel:
    """Analytical model for SRAM characteristics."""

    def __init__(
        self,
        vth_nom: float = 0.40,
        vdd_nom: float = 1.0,
        cell_ratio_nom: float = 2.0,
        a_vt: float = 0.005,
        temp_ref: float = 300.0,
        cap_farad: float = 5e-15,
        random_state: int | None = None
    ) -> None:
        self.vth_nom = vth_nom
        self.vdd_nom = vdd_nom
        self.cell_ratio_nom = cell_ratio_nom
        self.a_vt = a_vt
        self.temp_ref = temp_ref
        self.cap_farad = cap_farad
        self.random_state = random_state
        self.k_b = 1.38e-23

    def seevinck_snm(self, vdd: np.ndarray | float, vth: np.ndarray | float,
                     cell_ratio: np.ndarray | float) -> np.ndarray | float:
        """Seevinck SNM estimate.

        Formula used:
            SNM = (Vdd - 2*Vth) * CR / (1 + CR + 2*CR*Vth / Vdd)
        """
        vdd = np.asarray(vdd, dtype=float)
        vth = np.asarray(vth, dtype=float)
        cell_ratio = np.asarray(cell_ratio, dtype=float)
        denominator = 1.0 + cell_ratio + 2.0 * cell_ratio * (vth / np.maximum(vdd, 1e-12))
        snm = (vdd - 2.0 * vth) * cell_ratio / np.maximum(denominator, 1e-12)
        return np.maximum(snm, 0.0)

    def pelgrom_sigma_vth(self, width: np.ndarray | float, length: np.ndarray | float,
                          a_vt: float | None = None) -> np.ndarray:
        """Pelgrom σ(Vth) = A_Vt / sqrt(W*L)."""
        a_vt = self.a_vt if a_vt is None else a_vt
        width = np.asarray(width, dtype=float)
        length = np.asarray(length, dtype=float)
        wl = np.maximum(width, 1e-12) * np.maximum(length, 1e-12)
        return np.asarray(a_vt, dtype=float) / np.sqrt(wl)

    def snm_with_variability(
        self,
        vdd: np.ndarray | float,
        vth_nom: np.ndarray | float,
        cell_ratio: np.ndarray | float,
        sigma_vth: np.ndarray | float,
        n_samples: int = 10000,
        random_state: int | None = 42
    ) -> dict[str, np.ndarray]:
        """Monte Carlo SNM with Vth variability.

        For each sample, generate six transistors' Vth perturbations and
        compute one SNM sample from the average perturbed Vth.
        """
        rng = np.random.default_rng(random_state)
        vdd = np.asarray(vdd, dtype=float)
        vth_nom = np.asarray(vth_nom, dtype=float)
        cell_ratio = np.asarray(cell_ratio, dtype=float)
        sigma_vth = np.asarray(sigma_vth, dtype=float)

        if vdd.ndim == 0:
            # Scalar case for compatibility
            sampled = rng.normal(vth_nom, sigma_vth, size=(n_samples, 6))
            snm_samples = self.seevinck_snm(vdd, np.mean(sampled, axis=1), cell_ratio)
            return {
                "snm_samples": snm_samples,
                "snm_mean": float(np.mean(snm_samples)),
                "snm_std": float(np.std(snm_samples, ddof=1) if len(snm_samples) > 1 else 0.0)
            }

        # Vectorized case (N operating points)
        n_points = vdd.size
        sampled_vth = rng.normal(
            loc=vth_nom.reshape(-1, 1, 1),
            scale=np.maximum(sigma_vth.reshape(-1, 1, 1), 0.0),
            size=(n_points, n_samples, 6)
        )
        effective_vth = np.mean(sampled_vth, axis=2)
        snm_samples = self.seevinck_snm(vdd.reshape(-1, 1), effective_vth, cell_ratio.reshape(-1, 1))
        snm_mean = np.mean(snm_samples, axis=1)
        snm_std = np.std(snm_samples, axis=1, ddof=1)

        return {
            "snm_samples": snm_samples,
            "snm_mean": snm_mean,
            "snm_std": snm_std
        }

    def analytical_ber(self, snm_mean: np.ndarray | float, snm_std: np.ndarray | float,
                       noise_amplitude: np.ndarray | float) -> np.ndarray:
        """Approximate BER from Gaussian SNM margin and noise.

        BER = Φ( -μ / √(σ_SNM² + σ_noise²) )
        """
        snm_mean = np.asarray(snm_mean, dtype=float)
        snm_std = np.asarray(snm_std, dtype=float)
        noise_amplitude = np.asarray(noise_amplitude, dtype=float)
        denom = np.sqrt(np.maximum(snm_std ** 2 + noise_amplitude ** 2, 1e-18))
        q = -np.asarray(snm_mean, dtype=float) / denom
        ber = stats.norm.cdf(q)
        ber = np.clip(ber, 0.0, 1.0)
        return ber

    def snm_temperature_model(self, vdd: float, vth_0: float, temp: float,
                             cell_ratio: float) -> float:
        """Temperature-aware SNM using a simple linear Vth shift:
        Vth(T) = Vth_0 - α * (T - T_ref)
        """
        alpha = 0.001
        vth_t = vth_0 - alpha * (temp - self.temp_ref)
        return float(self.seevinck_snm(vdd, vth_t, cell_ratio))

    def thermal_noise_sigma(self, temp: np.ndarray | float, capacitance: float | None = None) -> np.ndarray | float:
        """Thermal noise σV = sqrt(kT/C)"""
        capacitance = self.cap_farad if capacitance is None else capacitance
        temp = np.asarray(temp, dtype=float)
        return np.sqrt(self.k_b * temp / capacitance)

    def generate_dataset(
        self,
        n_samples: int = 5000,
        random_state: int | None = 42,
        temp_range: tuple[float, float] = (250.0, 400.0),
        voltage_range: tuple[float, float] = (0.6, 1.2),
        cell_ratio_range: tuple[float, float] = (1.0, 4.0),
        width_range: tuple[float, float] = (0.1, 2.0),
        length_range: tuple[float, float] = (0.045, 0.18),
        variability_samples: int = 512,
        a_vt: float | None = None
    ) -> dict[str, np.ndarray]:
        """Generate synthetic analytical dataset for ML benchmarking."""
        if random_state is None and self.random_state is not None:
            random_state = self.random_state
        rng = np.random.default_rng(random_state)

        temp = rng.uniform(temp_range[0], temp_range[1], size=n_samples)
        vdd = rng.uniform(voltage_range[0], voltage_range[1], size=n_samples)
        cell_ratio = rng.uniform(cell_ratio_range[0], cell_ratio_range[1], size=n_samples)
        width = rng.uniform(width_range[0], width_range[1], size=n_samples)
        length = rng.uniform(length_range[0], length_range[1], size=n_samples)

        # Nominal model
        snm_nominal = self.seevinck_snm(vdd, self.vth_nom, cell_ratio)
        sigma_vth = self.pelgrom_sigma_vth(width, length, a_vt=a_vt)

        # Monte-Carlo SNM with Vth variability
        vth_nom = np.full_like(vdd, self.vth_nom)
        mc_result = self.snm_with_variability(
            vdd=vdd,
            vth_nom=vth_nom,
            cell_ratio=cell_ratio,
            sigma_vth=sigma_vth,
            n_samples=variability_samples,
            random_state=random_state
        )

        snm_samples_mean = mc_result["snm_mean"]
        snm_samples_std = mc_result["snm_std"]

        # Add thermal noise term for BER
        noise_sigma = self.thermal_noise_sigma(temp)
        ber = self.analytical_ber(snm_samples_mean, snm_samples_std, noise_sigma)

        return {
            "temperature": temp,
            "voltage": vdd,
            "cell_ratio": cell_ratio,
            "width": width,
            "length": length,
            "snm_nominal": snm_nominal,
            "snm_mean": snm_samples_mean,
            "snm_std": snm_samples_std,
            "ber": ber,
            "noise_sigma": noise_sigma,
        }
