"""Machine-learning benchmark utilities for SRAM datasets.

Supports two dataset sources:
1) Analytical synthetic data (`analytical_ground_truth.py`)
2) External CSV data (for SPICE/native correlation studies)
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import numpy as np

try:
    from sklearn.base import BaseEstimator, RegressorMixin, clone
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import GroupKFold, KFold
    from sklearn.neural_network import MLPRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import PolynomialFeatures, StandardScaler
    from sklearn.svm import SVR
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "scikit-learn is required for SRAM model benchmarking. "
        "Install via `pip install scikit-learn>=1.3.0`."
    ) from exc

try:
    from analytical_ground_truth import AnalyticalSRAMModel
except Exception as exc:  # pragma: no cover
    raise ImportError("analytical_ground_truth module is required for dataset generation.") from exc

PROBABILITY_LIKE_TARGETS = frozenset({"ber", "read_fail", "write_fail"})
FAIL_AUX_TARGETS = frozenset({"read_fail", "write_fail"})
R2_CLIP_MIN = -10.0
R2_CLIP_MAX = 1.0
R2_VAR_EPS = 1e-12
DEFAULT_TARGET_IMPORTANCE = {
    "snm": 1.0,
    "hold_snm": 1.0,
    "read_snm": 1.2,
    "write_margin": 1.2,
    "noise_sigma": 1.3,
    "ber": 1.5,
    "read_fail": 2.0,
    "write_fail": 2.0,
}


class TwoLayerPerceptronRegressor(BaseEstimator, RegressorMixin):
    """Two-layer perceptron regressor with explicit weighted training support."""

    def __init__(
        self,
        hidden_dim: int = 16,
        alpha: float = 1e-3,
        learning_rate: float = 0.01,
        max_iter: int = 3000,
        tol: float = 1e-7,
        random_state: int | None = 42,
        grad_clip: float = 5.0,
    ):
        self.hidden_dim = hidden_dim
        self.alpha = alpha
        self.learning_rate = learning_rate
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state
        self.grad_clip = grad_clip

    @staticmethod
    def _weighted_stats(values: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        w_sum = float(np.sum(weights))
        if w_sum <= 1e-12:
            mean = np.mean(values, axis=0)
            std = np.std(values, axis=0)
        else:
            mean = np.sum(values * weights[:, None], axis=0) / w_sum
            var = np.sum(weights[:, None] * (values - mean) ** 2, axis=0) / w_sum
            std = np.sqrt(np.maximum(var, 1e-12))
        std = np.where(std > 1e-12, std, 1.0)
        return mean, std

    @staticmethod
    def _weighted_stats_1d(values: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
        w_sum = float(np.sum(weights))
        if w_sum <= 1e-12:
            mean = float(np.mean(values))
            std = float(np.std(values))
        else:
            mean = float(np.sum(values * weights) / w_sum)
            var = float(np.sum(weights * (values - mean) ** 2) / w_sum)
            std = float(np.sqrt(max(var, 1e-12)))
        if std <= 1e-12:
            std = 1.0
        return mean, std

    def fit(self, X: np.ndarray, y: np.ndarray, sample_weight: np.ndarray | None = None):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n_samples, n_features = X.shape
        if sample_weight is None:
            weights = np.ones(n_samples, dtype=float)
        else:
            weights = np.asarray(sample_weight, dtype=float).reshape(-1)
            if len(weights) != n_samples:
                raise ValueError("sample_weight length mismatch")
            weights = np.clip(weights, 1e-12, None)
        weights = weights / max(float(np.mean(weights)), 1e-12)

        self.x_mean_, self.x_std_ = self._weighted_stats(X, weights)
        x_norm = (X - self.x_mean_) / self.x_std_

        self.y_mean_, self.y_std_ = self._weighted_stats_1d(y, weights)
        y_norm = (y - self.y_mean_) / self.y_std_

        rng = np.random.default_rng(self.random_state)
        hidden_dim = max(int(self.hidden_dim), 1)
        self.W1_ = rng.normal(0.0, 0.1, size=(n_features, hidden_dim))
        self.b1_ = np.zeros(hidden_dim, dtype=float)
        self.W2_ = rng.normal(0.0, 0.1, size=(hidden_dim,))
        self.b2_ = 0.0

        lr = float(self.learning_rate)
        best_loss = float("inf")
        no_improve = 0

        for _ in range(max(int(self.max_iter), 1)):
            z1 = x_norm @ self.W1_ + self.b1_
            a1 = np.tanh(z1)
            y_pred = a1 @ self.W2_ + self.b2_
            err = y_pred - y_norm

            weighted_err = weights * err
            mse = float(np.mean(weighted_err * err))
            reg = float(self.alpha) * (float(np.sum(self.W1_ ** 2)) + float(np.sum(self.W2_ ** 2)))
            loss = mse + reg

            if loss + float(self.tol) < best_loss:
                best_loss = loss
                no_improve = 0
            else:
                no_improve += 1
                if no_improve > 150:
                    break

            d_out = (2.0 / max(n_samples, 1)) * weighted_err
            grad_W2 = a1.T @ d_out + 2.0 * float(self.alpha) * self.W2_
            grad_b2 = float(np.sum(d_out))

            da1 = np.outer(d_out, self.W2_)
            dz1 = da1 * (1.0 - a1 * a1)
            grad_W1 = x_norm.T @ dz1 + 2.0 * float(self.alpha) * self.W1_
            grad_b1 = np.sum(dz1, axis=0)

            clip = float(self.grad_clip)
            if clip > 0.0:
                np.clip(grad_W2, -clip, clip, out=grad_W2)
                grad_b2 = float(np.clip(grad_b2, -clip, clip))
                np.clip(grad_W1, -clip, clip, out=grad_W1)
                np.clip(grad_b1, -clip, clip, out=grad_b1)

            self.W2_ -= lr * grad_W2
            self.b2_ -= lr * grad_b2
            self.W1_ -= lr * grad_W1
            self.b1_ -= lr * grad_b1

        self.coefs_ = [np.asarray(self.W1_), np.asarray(self.W2_).reshape(-1, 1)]
        self.intercepts_ = [np.asarray(self.b1_), np.asarray([self.b2_])]
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if not hasattr(self, "W1_"):
            raise RuntimeError("Model has not been fitted.")
        x_norm = (X - self.x_mean_) / self.x_std_
        hidden = np.tanh(x_norm @ self.W1_ + self.b1_)
        y_norm_pred = hidden @ self.W2_ + self.b2_
        y_norm_pred = np.asarray(y_norm_pred, dtype=float).reshape(-1)
        return y_norm_pred * self.y_std_ + self.y_mean_


class SRAMModelBenchmark:
    """Run multi-model benchmark on SRAM targets."""

    def __init__(self, n_samples: int = 5000, n_folds: int = 5, random_state: int = 42) -> None:
        self.n_samples = n_samples
        self.n_folds = n_folds
        self.random_state = random_state

    @staticmethod
    def _build_analytical_dataset(n_samples: int, random_state: int) -> dict[str, object]:
        model = AnalyticalSRAMModel(random_state=random_state)
        data = model.generate_dataset(n_samples=n_samples, random_state=random_state)
        feature_names = ["temperature", "voltage", "cell_ratio", "width", "length"]
        X = np.column_stack(
            [
                data["temperature"],
                data["voltage"],
                data["cell_ratio"],
                data["width"],
                data["length"],
            ]
        ).astype(float)
        targets = {
            "snm": np.asarray(data["snm_mean"], dtype=float),
            "ber": np.asarray(data["ber"], dtype=float),
            "noise_sigma": np.asarray(data["noise_sigma"], dtype=float),
        }
        return {
            "X": X,
            "targets": targets,
            "data": data,
            "meta": {
                "dataset_type": "analytical",
                "feature_names": feature_names,
                "target_source": "analytical",
                "n_samples": int(len(X)),
            },
        }

    @staticmethod
    def _safe_fill_non_finite(values: np.ndarray) -> np.ndarray:
        arr = np.asarray(values, dtype=float).reshape(-1)
        finite_mask = np.isfinite(arr)
        if np.all(finite_mask):
            return arr
        finite_vals = arr[finite_mask]
        fill_value = float(np.median(finite_vals)) if finite_vals.size else 0.0
        out = arr.copy()
        out[~finite_mask] = fill_value
        return out

    @staticmethod
    def _condition_target_array(
        values: np.ndarray,
        target_name: str,
        clip_quantile: float,
        normalize: bool,
        prob_logit: bool,
    ) -> tuple[np.ndarray, dict[str, float | str | bool]]:
        arr = SRAMModelBenchmark._safe_fill_non_finite(values)
        n_samples = int(len(arr))

        q = max(0.0, min(float(clip_quantile), 0.49))
        clip_low = float(np.min(arr))
        clip_high = float(np.max(arr))
        if q > 0.0 and n_samples >= 8:
            q_low, q_high = np.quantile(arr, [q, 1.0 - q])
            if np.isfinite(q_low) and np.isfinite(q_high) and q_low < q_high:
                clip_low = float(q_low)
                clip_high = float(q_high)
                arr = np.clip(arr, clip_low, clip_high)

        transform = "identity"
        logit_eps = 1e-6
        if (
            bool(prob_logit)
            and str(target_name) in PROBABILITY_LIKE_TARGETS
            and np.min(arr) >= 0.0
            and np.max(arr) <= 1.0
        ):
            transform = "logit"
            clipped_prob = np.clip(arr, logit_eps, 1.0 - logit_eps)
            arr = np.log(clipped_prob / (1.0 - clipped_prob))

        loc = 0.0
        scale = 1.0
        if bool(normalize):
            med = float(np.median(arr))
            q1, q3 = np.quantile(arr, [0.25, 0.75])
            iqr = float(q3 - q1)
            robust_scale = iqr / 1.349 if iqr > 1e-12 else 0.0
            std_scale = float(np.std(arr))
            scale = robust_scale if robust_scale > 1e-9 else std_scale
            if not np.isfinite(scale) or scale <= 1e-9:
                scale = 1.0
            loc = med
            arr = (arr - loc) / scale

        params: dict[str, float | str | bool] = {
            "clip_quantile": q,
            "clip_low": clip_low,
            "clip_high": clip_high,
            "transform": transform,
            "logit_eps": logit_eps,
            "normalize": bool(normalize),
            "loc": float(loc),
            "scale": float(scale),
        }
        return arr, params

    @staticmethod
    def _inverse_target_conditioning(
        values: np.ndarray,
        params: dict[str, float | str | bool] | None,
    ) -> np.ndarray:
        arr = np.asarray(values, dtype=float).reshape(-1)
        if not params:
            return arr

        normalize = bool(params.get("normalize", False))
        loc = float(params.get("loc", 0.0))
        scale = float(params.get("scale", 1.0))
        if normalize:
            safe_scale = scale if np.isfinite(scale) and abs(scale) > 1e-12 else 1.0
            arr = arr * safe_scale + loc

        transform = str(params.get("transform", "identity"))
        if transform == "logit":
            arr = 1.0 / (1.0 + np.exp(-arr))

        clip_low = float(params.get("clip_low", np.min(arr)))
        clip_high = float(params.get("clip_high", np.max(arr)))
        if np.isfinite(clip_low) and np.isfinite(clip_high) and clip_low < clip_high:
            arr = np.clip(arr, clip_low, clip_high)
        return arr

    @staticmethod
    def _resolve_target_importance(
        target_names: tuple[str, ...] | list[str],
        overrides: dict[str, float] | None = None,
    ) -> dict[str, float]:
        out: dict[str, float] = {}
        override_map = overrides if isinstance(overrides, dict) else {}
        for target_name in target_names:
            if target_name in override_map:
                value = float(override_map[target_name])
            else:
                value = float(DEFAULT_TARGET_IMPORTANCE.get(target_name, 1.0))
            if not np.isfinite(value) or value <= 0.0:
                value = 1.0
            out[str(target_name)] = value
        return out

    @staticmethod
    def load_spice_csv_dataset(
        csv_path: str | Path,
        target_source: str = "spice",
        risk_weighting: bool = True,
        split_mode: str = "group_pvt",
        target_clip_quantile: float = 0.01,
        target_normalize: bool = True,
        target_prob_logit: bool = True,
        target_importance: dict[str, float] | None = None,
        fail_aux_split: bool = False,
        fail_aux_profile: str = "auto",
    ) -> dict[str, object]:
        """Load external SPICE/native correlation CSV as benchmark dataset.

        Supported target_source:
        - spice|native|delta: legacy 3-target set (snm, ber, noise_sigma)
        - spice_v2|native_v2|delta_v2: extended set from measure-contract v2

        Target conditioning:
        - quantile clipping (clip_quantile)
        - optional probability logit transform (ber/read_fail/write_fail)
        - optional robust normalization
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV dataset not found: {path}")

        with path.open("r", encoding="utf-8", newline="") as fp:
            rows = list(csv.DictReader(fp))
        if not rows:
            raise ValueError(f"empty CSV dataset: {path}")

        source = str(target_source).strip().lower()
        supported_sources = {
            "spice",
            "native",
            "delta",
            "spice_v2",
            "native_v2",
            "delta_v2",
        }
        if source not in supported_sources:
            supported = ", ".join(sorted(supported_sources))
            raise ValueError(f"unsupported target_source '{target_source}' (supported: {supported})")

        required_feature_cols = ("temp_k", "vdd", "corner")
        for col in required_feature_cols:
            if col not in rows[0]:
                raise ValueError(f"required column missing from CSV: {col}")

        prefix = "spice"
        if source.startswith("native"):
            prefix = "native"
        elif source.startswith("delta"):
            prefix = "delta"

        base_target_cols = {
            "snm": f"{prefix}_snm_mv",
            "ber": f"{prefix}_ber",
            "noise_sigma": f"{prefix}_noise" if f"{prefix}_noise" in rows[0] else f"{prefix}_noise_sigma",
        }
        v2_optional_cols = {
            "hold_snm": f"{prefix}_hold_snm_mv",
            "read_snm": f"{prefix}_read_snm_mv",
            "write_margin": f"{prefix}_write_margin_mv",
            "read_fail": f"{prefix}_read_fail",
            "write_fail": f"{prefix}_write_fail",
        }

        selected_targets: dict[str, str] = dict(base_target_cols)
        if source.endswith("_v2"):
            for key, col in v2_optional_cols.items():
                if col in rows[0]:
                    selected_targets[key] = col

        for key, col in selected_targets.items():
            if col not in rows[0]:
                raise ValueError(f"required target column missing from CSV ({key}): {col}")

        corners = sorted({str(row["corner"]).strip().lower() for row in rows})
        if not corners:
            raise ValueError("corner column has no values")
        corner_index = {name: idx for idx, name in enumerate(corners)}

        vdd_values = np.asarray([float(row["vdd"]) for row in rows], dtype=float)
        temp_values = np.asarray([float(row["temp_k"]) for row in rows], dtype=float)
        low_vdd_threshold = float(np.quantile(vdd_values, 0.34))
        high_temp_threshold = float(np.quantile(temp_values, 0.66))

        X_list: list[list[float]] = []
        targets_buffer: dict[str, list[float]] = {name: [] for name in selected_targets}
        sample_weight: list[float] = []
        group_labels: list[str] = []
        pdk_ids_seen: set[str] = set()

        for row in rows:
            corner = str(row["corner"]).strip().lower()
            if corner not in corner_index:
                raise ValueError(f"unknown corner value: {corner}")

            temp_k = float(row["temp_k"])
            vdd = float(row["vdd"])
            feature_vec = [temp_k, vdd]
            one_hot = [0.0] * len(corners)
            one_hot[corner_index[corner]] = 1.0
            feature_vec.extend(one_hot)
            X_list.append(feature_vec)

            for key, col in selected_targets.items():
                targets_buffer[key].append(float(row[col]))

            pdk_id = str(row.get("pdk_id", "")).strip().lower()
            if pdk_id:
                pdk_ids_seen.add(pdk_id)
            group_labels.append(f"{corner}|{temp_k:.2f}|{pdk_id}")

            if risk_weighting:
                weight = 1.0
                if corner == "ss":
                    weight *= 1.8
                if temp_k >= high_temp_threshold:
                    weight *= 1.4
                if vdd <= low_vdd_threshold:
                    weight *= 1.6
                sample_weight.append(weight)
            else:
                sample_weight.append(1.0)

        feature_names = ["temp_k", "vdd"] + [f"corner_{name}" for name in corners]
        X = np.asarray(X_list, dtype=float)
        raw_targets = {
            name: SRAMModelBenchmark._safe_fill_non_finite(np.asarray(values, dtype=float))
            for name, values in targets_buffer.items()
        }
        targets: dict[str, np.ndarray] = {}
        target_conditioning: dict[str, dict[str, float | str | bool]] = {}
        for name, raw_values in raw_targets.items():
            conditioned, params = SRAMModelBenchmark._condition_target_array(
                values=raw_values,
                target_name=name,
                clip_quantile=target_clip_quantile,
                normalize=target_normalize,
                prob_logit=target_prob_logit,
            )
            targets[name] = conditioned
            target_conditioning[name] = params

        sample_weight_arr = np.asarray(sample_weight, dtype=float)
        groups_arr = np.asarray(group_labels, dtype=object)

        target_importance_resolved = SRAMModelBenchmark._resolve_target_importance(
            target_names=list(targets.keys()),
            overrides=target_importance,
        )
        if len(pdk_ids_seen) == 1:
            dataset_pdk_id = next(iter(pdk_ids_seen))
        elif len(pdk_ids_seen) > 1:
            dataset_pdk_id = "mixed"
        else:
            dataset_pdk_id = "unknown"
        requested_fail_aux_profile = str(fail_aux_profile).strip().lower() if fail_aux_profile is not None else "auto"
        if requested_fail_aux_profile in {"", "auto"}:
            if dataset_pdk_id in {"sky130", "gf180mcu", "freepdk45_openram"}:
                resolved_fail_aux_profile = dataset_pdk_id
            else:
                resolved_fail_aux_profile = "default"
        else:
            resolved_fail_aux_profile = requested_fail_aux_profile

        return {
            "X": X,
            "targets": targets,
            "raw_targets": raw_targets,
            "target_conditioning": target_conditioning,
            "target_importance": target_importance_resolved,
            "fail_aux_split": bool(fail_aux_split),
            "fail_aux_profile": str(resolved_fail_aux_profile),
            "sample_weight": sample_weight_arr,
            "groups": groups_arr,
            "data": rows,
            "meta": {
                "dataset_type": "external_csv",
                "csv_path": str(path.as_posix()),
                "feature_names": feature_names,
                "target_source": source,
                "n_samples": int(len(rows)),
                "corners": corners,
                "target_names": list(targets.keys()),
                "risk_weighting": bool(risk_weighting),
                "split_mode": str(split_mode),
                "target_clip_quantile": float(target_clip_quantile),
                "target_normalize": bool(target_normalize),
                "target_prob_logit": bool(target_prob_logit),
                "target_importance": target_importance_resolved,
                "fail_aux_split": bool(fail_aux_split),
                "fail_aux_profile": str(resolved_fail_aux_profile),
                "fail_aux_profile_requested": str(requested_fail_aux_profile),
                "pdk_id": str(dataset_pdk_id),
                "low_vdd_threshold": low_vdd_threshold,
                "high_temp_threshold": high_temp_threshold,
                "group_count": int(len(np.unique(groups_arr))),
            },
        }

    @staticmethod
    def _build_models() -> list[tuple[str, object]]:
        return [
            ("Linear Regression", LinearRegression()),
            (
                "Polynomial (deg=2)",
                Pipeline(
                    [
                        ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                        ("ridge", Ridge(alpha=3.0)),
                    ]
                ),
            ),
            (
                "Polynomial (deg=3)",
                Pipeline(
                    [
                        ("poly", PolynomialFeatures(degree=3, include_bias=False)),
                        ("ridge", Ridge(alpha=8.0)),
                    ]
                ),
            ),
            (
                "Random Forest",
                RandomForestRegressor(
                    n_estimators=240,
                    max_depth=12,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=1,
                ),
            ),
            (
                "Gradient Boosting",
                GradientBoostingRegressor(
                    random_state=42,
                    n_estimators=220,
                    learning_rate=0.05,
                    max_depth=2,
                    subsample=0.8,
                ),
            ),
            (
                "SVR (RBF)",
                Pipeline(
                    [
                        ("scale", StandardScaler()),
                        ("svr", SVR(kernel="rbf", C=20, gamma="scale", epsilon=0.01)),
                    ]
                ),
            ),
            (
                "MLP 2-layer (Perceptron Gate)",
                TwoLayerPerceptronRegressor(
                    hidden_dim=20,
                    alpha=3e-2,
                    learning_rate=0.006,
                    max_iter=3500,
                    random_state=42,
                ),
            ),
            (
                "MLP 3-layer (sklearn)",
                Pipeline(
                    [
                        ("scale", StandardScaler()),
                        (
                            "mlp",
                            MLPRegressor(
                                hidden_layer_sizes=(24, 12),
                                activation="tanh",
                                solver="adam",
                                alpha=1e-3,
                                learning_rate_init=1e-3,
                                max_iter=2000,
                                early_stopping=True,
                                n_iter_no_change=30,
                                random_state=42,
                            ),
                        ),
                    ]
                ),
            ),
        ]

    @staticmethod
    def _param_count(model: object) -> int:
        if hasattr(model, "named_steps"):
            named_steps = getattr(model, "named_steps", {})
            if isinstance(named_steps, dict):
                for _, step_model in reversed(list(named_steps.items())):
                    nested = SRAMModelBenchmark._param_count(step_model)
                    if nested > 0:
                        return nested
        if hasattr(model, "coef_"):
            coef = np.asarray(model.coef_)
            n_params = int(coef.size)
            if hasattr(model, "intercept_"):
                n_params += int(np.asarray(model.intercept_).size)
            return n_params
        if hasattr(model, "coefs_") and hasattr(model, "intercepts_"):
            coefs = getattr(model, "coefs_", [])
            intercepts = getattr(model, "intercepts_", [])
            return int(
                sum(np.asarray(w).size for w in coefs) +
                sum(np.asarray(b).size for b in intercepts)
            )
        if hasattr(model, "estimators_"):
            estimators = getattr(model, "estimators_", [])
            if isinstance(estimators, np.ndarray):
                estimator_items = list(estimators.ravel())
            else:
                estimator_items = list(estimators)
            node_count = 0
            for estimator in estimator_items:
                tree = getattr(estimator, "tree_", None)
                if tree is not None:
                    node_count += int(getattr(tree, "node_count", 0))
            if node_count > 0:
                return node_count
        if hasattr(model, "W1_") and hasattr(model, "W2_"):
            return int(np.size(model.W1_) + np.size(model.W2_))
        return 0

    @staticmethod
    def _adapt_estimator_for_target(model_name: str, estimator: object, target_name: str) -> object:
        name = str(model_name)
        target = str(target_name)
        if target not in PROBABILITY_LIKE_TARGETS:
            return estimator

        if name == "Linear Regression":
            return Ridge(alpha=2.0)
        if name == "Polynomial (deg=2)":
            return Pipeline(
                [
                    ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                    ("ridge", Ridge(alpha=6.0)),
                ]
            )
        if name == "Polynomial (deg=3)":
            return Pipeline(
                [
                    ("poly", PolynomialFeatures(degree=3, include_bias=False)),
                    ("ridge", Ridge(alpha=12.0)),
                ]
            )
        if name == "SVR (RBF)":
            return Pipeline(
                [
                    ("scale", StandardScaler()),
                    ("svr", SVR(kernel="rbf", C=25, gamma="scale", epsilon=0.005)),
                ]
            )
        if name == "Gradient Boosting":
            return GradientBoostingRegressor(
                random_state=42,
                n_estimators=260,
                learning_rate=0.04,
                max_depth=2,
                subsample=0.8,
            )
        if name == "Random Forest":
            return RandomForestRegressor(
                n_estimators=260,
                max_depth=12,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=1,
            )
        if name == "MLP 2-layer (Perceptron Gate)":
            return TwoLayerPerceptronRegressor(
                hidden_dim=24,
                alpha=5e-2,
                learning_rate=0.005,
                max_iter=4000,
                random_state=42,
            )
        if name == "MLP 3-layer (sklearn)":
            return Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "mlp",
                        MLPRegressor(
                            hidden_layer_sizes=(20, 10),
                            activation="tanh",
                            solver="adam",
                            alpha=2e-3,
                            learning_rate_init=8e-4,
                            max_iter=2400,
                            early_stopping=True,
                            n_iter_no_change=40,
                            random_state=42,
                        ),
                    ),
                ]
            )
        return Ridge(alpha=10.0)

    @staticmethod
    def _build_fail_aux_estimator(model_name: str, target_name: str, fail_aux_profile: str = "default") -> object:
        """Dedicated auxiliary regressors for fail-rate heads."""
        name = str(model_name)
        target = str(target_name)
        is_write_fail = target == "write_fail"
        profile_key = str(fail_aux_profile).strip().lower()
        if profile_key in {"", "auto", "unknown", "mixed"}:
            profile_key = "default"
        if profile_key.startswith("sky130"):
            profile_key = "sky130"
        elif profile_key.startswith("gf180"):
            profile_key = "gf180mcu"
        elif profile_key in {"freepdk45_openram", "freepdk45", "free45"}:
            profile_key = "freepdk45_openram"
        elif profile_key not in {"default"}:
            profile_key = "default"

        if profile_key == "sky130":
            if name == "MLP 2-layer (Perceptron Gate)":
                return TwoLayerPerceptronRegressor(
                    hidden_dim=22 if is_write_fail else 26,
                    alpha=6e-2 if is_write_fail else 5e-2,
                    learning_rate=0.0045,
                    max_iter=4500,
                    random_state=42,
                )
            if name == "Linear Regression":
                return Ridge(alpha=9.0 if is_write_fail else 8.0)

        if profile_key == "gf180mcu":
            if name == "Linear Regression":
                return Ridge(alpha=2.5 if is_write_fail else 2.0)
            if name == "MLP 3-layer (sklearn)":
                return Pipeline(
                    [
                        ("scale", StandardScaler()),
                        (
                            "mlp",
                            MLPRegressor(
                                hidden_layer_sizes=(20, 10),
                                activation="tanh",
                                solver="adam",
                                alpha=2e-3,
                                learning_rate_init=8e-4,
                                max_iter=2400,
                                early_stopping=True,
                                n_iter_no_change=40,
                                random_state=42,
                            ),
                        ),
                    ]
                )

        if profile_key == "freepdk45_openram":
            if name == "Linear Regression":
                return Ridge(alpha=4.0 if is_write_fail else 3.0)

        if name == "Linear Regression":
            return Ridge(alpha=12.0 if is_write_fail else 10.0)
        if name == "Polynomial (deg=2)":
            return Pipeline(
                [
                    ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                    ("ridge", Ridge(alpha=20.0 if is_write_fail else 16.0)),
                ]
            )
        if name == "Polynomial (deg=3)":
            return Pipeline(
                [
                    ("poly", PolynomialFeatures(degree=3, include_bias=False)),
                    ("ridge", Ridge(alpha=40.0 if is_write_fail else 32.0)),
                ]
            )
        if name == "SVR (RBF)":
            return Pipeline(
                [
                    ("scale", StandardScaler()),
                    ("svr", SVR(kernel="rbf", C=16 if is_write_fail else 20, gamma="scale", epsilon=0.004)),
                ]
            )
        if name == "Gradient Boosting":
            return GradientBoostingRegressor(
                random_state=42,
                n_estimators=320 if is_write_fail else 300,
                learning_rate=0.03,
                max_depth=2,
                subsample=0.75,
                min_samples_leaf=2,
            )
        if name == "Random Forest":
            return RandomForestRegressor(
                n_estimators=320 if is_write_fail else 300,
                max_depth=10,
                min_samples_leaf=3,
                random_state=42,
                n_jobs=1,
            )
        if name == "MLP 2-layer (Perceptron Gate)":
            return TwoLayerPerceptronRegressor(
                hidden_dim=24 if is_write_fail else 28,
                alpha=8e-2 if is_write_fail else 6e-2,
                learning_rate=0.004,
                max_iter=4500,
                random_state=42,
            )
        if name == "MLP 3-layer (sklearn)":
            return Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "mlp",
                        MLPRegressor(
                            hidden_layer_sizes=(20, 10) if is_write_fail else (24, 12),
                            activation="tanh",
                            solver="adam",
                            alpha=5e-3 if is_write_fail else 4e-3,
                            learning_rate_init=7e-4,
                            max_iter=2600,
                            early_stopping=True,
                            n_iter_no_change=50,
                            random_state=42,
                        ),
                    ),
                ]
            )
        return Ridge(alpha=10.0)

    def _effective_n_folds(self, n_samples: int) -> int:
        if n_samples < 2:
            raise ValueError("at least 2 samples are required for cross-validation")
        return max(2, min(self.n_folds, n_samples))

    @staticmethod
    def _stable_r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
        y_true = np.asarray(y_true, dtype=float).reshape(-1)
        y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
        var = float(np.var(y_true))
        if not np.isfinite(var) or var < R2_VAR_EPS:
            mae = float(mean_absolute_error(y_true, y_pred))
            denom = max(float(np.mean(np.abs(y_true))), 1e-6)
            raw_r2 = 1.0 - (mae / denom)
        else:
            raw_r2 = float(r2_score(y_true, y_pred))
        if not np.isfinite(raw_r2):
            raw_r2 = R2_CLIP_MIN
        clipped_r2 = float(np.clip(raw_r2, R2_CLIP_MIN, R2_CLIP_MAX))
        return clipped_r2, raw_r2

    def _build_splitter(
        self,
        n_samples: int,
        groups: np.ndarray | None = None,
        split_mode: str = "random",
    ) -> tuple[list[tuple[np.ndarray, np.ndarray]], int]:
        mode = str(split_mode).strip().lower()
        if mode == "group_pvt" and groups is not None:
            unique_groups = np.unique(groups)
            if len(unique_groups) >= 2:
                n_splits = max(2, min(self.n_folds, len(unique_groups)))
                splitter = GroupKFold(n_splits=n_splits)
                return list(splitter.split(np.arange(n_samples), groups=groups)), n_splits
        n_splits = self._effective_n_folds(n_samples)
        splitter = KFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)
        return list(splitter.split(np.arange(n_samples))), n_splits

    @staticmethod
    def _fit_with_optional_sample_weight(estimator, X, y, sample_weight=None):
        fit_kwargs = {}
        if sample_weight is not None:
            if hasattr(estimator, "named_steps") and isinstance(getattr(estimator, "named_steps", None), dict):
                step_names = list(getattr(estimator, "named_steps", {}).keys())
                if step_names:
                    fit_kwargs[f"{step_names[-1]}__sample_weight"] = sample_weight
            else:
                fit_kwargs["sample_weight"] = sample_weight

        try:
            estimator.fit(X, y, **fit_kwargs)
            return estimator
        except ValueError as exc:
            if "validation set is too small" not in str(exc).lower():
                if fit_kwargs:
                    estimator.fit(X, y)
                    return estimator
                raise

            fallback_params = {}
            for key in estimator.get_params(deep=True):
                if key == "early_stopping" or key.endswith("__early_stopping"):
                    fallback_params[key] = False
            if fallback_params:
                estimator.set_params(**fallback_params)
            if fit_kwargs:
                estimator.fit(X, y, **fit_kwargs)
            else:
                estimator.fit(X, y)
            return estimator
        except TypeError:
            estimator.fit(X, y)
            return estimator

    def _run_single_target(
        self,
        estimator,
        X: np.ndarray,
        y: np.ndarray,
        y_eval: np.ndarray | None = None,
        target_conditioning: dict[str, float | str | bool] | None = None,
        sample_weight: np.ndarray | None = None,
        groups: np.ndarray | None = None,
        split_mode: str = "random",
    ) -> dict[str, object]:
        fold_indices, n_splits = self._build_splitter(
            n_samples=len(y),
            groups=groups,
            split_mode=split_mode,
        )

        y_true_list: list[np.ndarray] = []
        y_pred_list: list[np.ndarray] = []
        r2_scores: list[float] = []
        r2_raw_scores: list[float] = []
        rmse_scores: list[float] = []
        mae_scores: list[float] = []
        train_times: list[float] = []
        infer_times: list[float] = []
        fitted_model = None

        for train_idx, test_idx in fold_indices:
            x_train = X[train_idx]
            y_train = y[train_idx]
            x_test = X[test_idx]
            y_test_eval = y[test_idx] if y_eval is None else y_eval[test_idx]
            w_train = None if sample_weight is None else np.asarray(sample_weight[train_idx], dtype=float)

            est = clone(estimator)
            train_start = time.perf_counter()
            est = self._fit_with_optional_sample_weight(
                est,
                x_train,
                y_train,
                sample_weight=w_train,
            )
            train_time = time.perf_counter() - train_start

            infer_start = time.perf_counter()
            y_pred = est.predict(x_test)
            infer_time = time.perf_counter() - infer_start

            if target_conditioning is not None:
                y_pred = self._inverse_target_conditioning(y_pred, target_conditioning)

            y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
            y_test_eval = np.asarray(y_test_eval, dtype=float).reshape(-1)

            y_true_list.append(y_test_eval)
            y_pred_list.append(y_pred)
            train_times.append(train_time)
            infer_times.append(max(infer_time, 1e-12))
            stable_r2, raw_r2 = self._stable_r2_score(y_test_eval, y_pred)
            r2_scores.append(stable_r2)
            r2_raw_scores.append(raw_r2)
            rmse_scores.append(float(np.sqrt(mean_squared_error(y_test_eval, y_pred))))
            mae_scores.append(mean_absolute_error(y_test_eval, y_pred))

            if fitted_model is None:
                fitted_model = est

        y_true = np.concatenate(y_true_list)
        y_pred = np.concatenate(y_pred_list)
        residual = y_pred - y_true

        return {
            "r2": float(np.nanmean(r2_scores)),
            "rmse": float(np.nanmean(rmse_scores)),
            "mae": float(np.nanmean(mae_scores)),
            "train_ms": float(np.mean(train_times) * 1000.0),
            "infer_ms": float(np.mean(infer_times) * 1000.0 / max(len(y), 1)),
            "param_count": int(self._param_count(fitted_model)),
            "y_true": y_true,
            "y_pred": y_pred,
            "residual": residual,
            "cv_r2": [float(v) for v in r2_scores],
            "cv_r2_raw": [float(v) for v in r2_raw_scores],
            "n_folds_used": int(n_splits),
        }

    def run_benchmark(self, dataset: dict[str, object] | None = None) -> dict[str, object]:
        """Run benchmark over all targets.

        If `dataset` is None, analytical synthetic dataset is generated.
        """
        if dataset is None:
            dataset = self._build_analytical_dataset(self.n_samples, self.random_state)

        X = np.asarray(dataset["X"], dtype=float)
        targets = dataset["targets"]
        if not isinstance(targets, dict):
            raise ValueError("dataset['targets'] must be a dict")
        raw_targets = dataset.get("raw_targets", targets)
        if not isinstance(raw_targets, dict):
            raise ValueError("dataset['raw_targets'] must be a dict when provided")
        target_conditioning = dataset.get("target_conditioning", {})
        if not isinstance(target_conditioning, dict):
            raise ValueError("dataset['target_conditioning'] must be a dict when provided")
        target_names = tuple(str(name) for name in targets.keys())
        if not target_names:
            raise ValueError("dataset has no targets")
        for target in target_names:
            if len(np.asarray(targets[target])) != len(X):
                raise ValueError(f"target length mismatch for '{target}'")
            if target not in raw_targets:
                raise ValueError(f"raw target missing for '{target}'")
            if len(np.asarray(raw_targets[target])) != len(X):
                raise ValueError(f"raw target length mismatch for '{target}'")

        sample_weight = dataset.get("sample_weight")
        if sample_weight is not None:
            sample_weight = np.asarray(sample_weight, dtype=float).reshape(-1)
            if len(sample_weight) != len(X):
                raise ValueError("sample_weight length mismatch")
        groups = dataset.get("groups")
        if groups is not None:
            groups = np.asarray(groups).reshape(-1)
            if len(groups) != len(X):
                raise ValueError("groups length mismatch")
        split_mode = str(dataset.get("meta", {}).get("split_mode", "random"))
        fail_aux_split = bool(dataset.get("fail_aux_split", dataset.get("meta", {}).get("fail_aux_split", False)))
        fail_aux_profile = str(dataset.get("fail_aux_profile", dataset.get("meta", {}).get("fail_aux_profile", "default")))
        if not fail_aux_profile:
            fail_aux_profile = "default"
        target_importance_raw = dataset.get("target_importance", dataset.get("meta", {}).get("target_importance", {}))
        target_importance = self._resolve_target_importance(
            target_names=target_names,
            overrides=target_importance_raw if isinstance(target_importance_raw, dict) else None,
        )
        importance_vec = np.asarray([float(target_importance[t]) for t in target_names], dtype=float)
        importance_sum = float(np.sum(importance_vec))
        if not np.isfinite(importance_sum) or importance_sum <= 1e-12:
            importance_vec = np.ones_like(importance_vec)
            importance_sum = float(np.sum(importance_vec))

        model_records: list[dict[str, object]] = []
        per_model_predictions: dict[str, dict[str, dict[str, np.ndarray]]] = {}

        for model_name, estimator in self._build_models():
            model_target_records: dict[str, dict[str, object]] = {}
            model_pred_records: dict[str, dict[str, np.ndarray]] = {}
            for target_name in target_names:
                if fail_aux_split and target_name in FAIL_AUX_TARGETS:
                    target_estimator = self._build_fail_aux_estimator(
                        model_name=model_name,
                        target_name=target_name,
                        fail_aux_profile=fail_aux_profile,
                    )
                else:
                    target_estimator = self._adapt_estimator_for_target(model_name, estimator, target_name)
                conditioning = target_conditioning.get(target_name)
                target_result = self._run_single_target(
                    target_estimator,
                    X,
                    np.asarray(targets[target_name], dtype=float),
                    y_eval=np.asarray(raw_targets[target_name], dtype=float),
                    target_conditioning=conditioning if isinstance(conditioning, dict) else None,
                    sample_weight=sample_weight,
                    groups=groups,
                    split_mode=split_mode,
                )
                model_target_records[target_name] = {
                    "r2": target_result["r2"],
                    "rmse": target_result["rmse"],
                    "mae": target_result["mae"],
                    "train_ms": target_result["train_ms"],
                    "infer_ms": target_result["infer_ms"],
                    "param_count": target_result["param_count"],
                    "cv_r2": target_result["cv_r2"],
                    "cv_r2_raw": target_result["cv_r2_raw"],
                    "n_folds_used": target_result["n_folds_used"],
                }
                model_pred_records[target_name] = {
                    "y_true": target_result["y_true"],
                    "y_pred": target_result["y_pred"],
                }

            r2_vec = np.asarray([float(model_target_records[t]["r2"]) for t in target_names], dtype=float)
            rmse_vec = np.asarray([float(model_target_records[t]["rmse"]) for t in target_names], dtype=float)
            mae_vec = np.asarray([float(model_target_records[t]["mae"]) for t in target_names], dtype=float)
            train_vec = np.asarray([float(model_target_records[t]["train_ms"]) for t in target_names], dtype=float)
            infer_vec = np.asarray([float(model_target_records[t]["infer_ms"]) for t in target_names], dtype=float)

            mean_r2_unweighted = float(np.nanmean(r2_vec))
            mean_rmse_unweighted = float(np.nanmean(rmse_vec))
            mean_mae_unweighted = float(np.nanmean(mae_vec))
            mean_train_unweighted = float(np.nanmean(train_vec))
            mean_infer_unweighted = float(np.nanmean(infer_vec))

            mean_r2 = float(np.sum(importance_vec * r2_vec) / importance_sum)
            mean_rmse = float(np.sum(importance_vec * rmse_vec) / importance_sum)
            mean_mae = float(np.sum(importance_vec * mae_vec) / importance_sum)
            mean_train_ms = float(np.sum(importance_vec * train_vec) / importance_sum)
            mean_infer_ms = float(np.sum(importance_vec * infer_vec) / importance_sum)

            per_model_predictions[model_name] = {}
            for target_name in target_names:
                per_model_predictions[model_name][target_name] = {
                    "y_true": model_pred_records[target_name]["y_true"],
                    "y_pred": model_pred_records[target_name]["y_pred"],
                }

            model_records.append(
                {
                    "model": model_name,
                    "mean_r2": mean_r2,
                    "mean_rmse": mean_rmse,
                    "mean_mae": mean_mae,
                    "mean_train_ms": mean_train_ms,
                    "mean_infer_ms": mean_infer_ms,
                    "mean_r2_unweighted": mean_r2_unweighted,
                    "mean_rmse_unweighted": mean_rmse_unweighted,
                    "mean_mae_unweighted": mean_mae_unweighted,
                    "mean_train_ms_unweighted": mean_train_unweighted,
                    "mean_infer_ms_unweighted": mean_infer_unweighted,
                    "param_count": model_target_records[target_names[0]]["param_count"],
                    "target_count": len(target_names),
                    "target_importance": dict(target_importance),
                    "targets": model_target_records,
                }
            )

        model_records = sorted(
            model_records,
            key=lambda item: float(item["mean_r2"]) if np.isfinite(item["mean_r2"]) else -np.inf,
            reverse=True,
        )
        best_model = model_records[0]["model"] if model_records else None

        meta = {
            "n_samples": int(len(X)),
            "n_folds_requested": int(self.n_folds),
            "random_state": int(self.random_state),
            "target_names": list(target_names),
            "risk_weighting": bool(dataset.get("meta", {}).get("risk_weighting", False)),
            "split_mode": split_mode,
            "fail_aux_split": bool(fail_aux_split),
            "fail_aux_profile": str(fail_aux_profile),
            "target_importance": dict(target_importance),
            "r2_clip_min": float(R2_CLIP_MIN),
            "r2_clip_max": float(R2_CLIP_MAX),
            "r2_var_eps": float(R2_VAR_EPS),
        }
        meta.update(dict(dataset.get("meta", {})))

        return {
            "data": dataset.get("data"),
            "model_records": model_records,
            "predictions": per_model_predictions,
            "meta": meta,
            "best_model": best_model,
        }

    def get_results_table(self, benchmark_result: dict[str, object] | None = None) -> list[dict[str, object]]:
        """Return ranking table with core metrics."""
        result = benchmark_result if benchmark_result is not None else self.run_benchmark()
        rows: list[dict[str, object]] = []
        for rec in result["model_records"]:
            rows.append(
                {
                    "Model": rec["model"],
                    "R2": rec["mean_r2"],
                    "RMSE": rec["mean_rmse"],
                    "MAE": rec["mean_mae"],
                    "Train Time (ms)": rec["mean_train_ms"],
                    "Inference Time (ms)": rec["mean_infer_ms"],
                    "Params": rec["param_count"],
                }
            )
        return rows

    def create_r2_comparison_figure(self, result: dict[str, object]):
        import matplotlib.pyplot as plt

        records = result["model_records"]
        model_names = [r["model"] for r in records]
        r2_values = [r["mean_r2"] for r in records]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(model_names, r2_values, color="#1f77b4", alpha=0.8)
        ax.set_title("R2 Comparison (avg over SNM/BER/noise_sigma)")
        ax.set_xlabel("Model")
        ax.set_ylabel("R2")
        ax.set_xticklabels(model_names, rotation=30, ha="right")
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        return fig

    def create_speed_accuracy_scatter(self, result: dict[str, object]):
        import matplotlib.pyplot as plt

        records = result["model_records"]
        infer_us = [r["mean_infer_ms"] * 1000.0 for r in records]
        r2_values = [r["mean_r2"] for r in records]
        model_names = [r["model"] for r in records]
        rmse_values = [r["mean_rmse"] for r in records]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(infer_us, r2_values, s=80, c="#2ca02c", alpha=0.8)
        for x_val, y_val, name, rmse in zip(infer_us, r2_values, model_names, rmse_values):
            ax.annotate(
                f"{name} (RMSE={rmse:.3g})",
                (x_val, y_val),
                textcoords="offset points",
                xytext=(4, 4),
                fontsize=8,
            )
        ax.set_xscale("log")
        ax.set_xlabel("Inference time (microseconds per sample)")
        ax.set_ylabel("R2")
        ax.set_title("Speed vs Accuracy")
        ax.grid(alpha=0.3)
        plt.tight_layout()
        return fig

    def create_predicted_vs_actual_figure(self, result: dict[str, object], target: str = "snm"):
        import matplotlib.pyplot as plt

        if result["best_model"] is None:
            return None

        model_name = result["best_model"]
        pred_data = result["predictions"][model_name][target]
        y_true = pred_data["y_true"]
        y_pred = pred_data["y_pred"]

        fig, ax = plt.subplots(figsize=(7, 7))
        ax.scatter(y_true, y_pred, alpha=0.5, s=16)
        mn = float(min(np.min(y_true), np.min(y_pred)))
        mx = float(max(np.max(y_true), np.max(y_pred)))
        ax.plot([mn, mx], [mn, mx], "k--", lw=1.2)
        ax.set_title(f"Predicted vs Actual ({model_name}, target={target})")
        ax.set_xlabel("Actual")
        ax.set_ylabel("Predicted")
        ax.grid(alpha=0.3)
        plt.tight_layout()
        return fig

    def create_residual_distribution_figure(self, result: dict[str, object], target: str = "snm"):
        import matplotlib.pyplot as plt

        if result["best_model"] is None:
            return None
        model_name = result["best_model"]
        pred_data = result["predictions"][model_name][target]
        residual = np.asarray(pred_data["y_pred"]) - np.asarray(pred_data["y_true"])

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.hist(residual, bins=40, alpha=0.8)
        ax.set_title(f"Residual Distribution ({model_name}, target={target})")
        ax.set_xlabel("Predicted - Actual")
        ax.set_ylabel("Count")
        ax.grid(alpha=0.3)
        plt.tight_layout()
        return fig
