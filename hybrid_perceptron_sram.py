"""
Hybrid Perceptron SRAM - Best of Both Worlds

Combines:
1. Adaptive Perceptron Gates (logic implementation)
2. MLP Perceptron Noise Model (sophisticated noise prediction)

This creates the most realistic Perceptron-based SRAM simulator.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
import json

from perceptron_calibration import load_and_apply_perceptron_calibration

# ============================================================================
# Part 1: MLP Perceptron for Noise Modeling (from main_advanced.py)
# ============================================================================

class PerceptronNoiseModel:
    """
    2-layer MLP for sophisticated noise weight prediction
    Based on PerceptronGateFunction from main_advanced.py

    Input: Temperature, Voltage
    Output: Noise weight (0~1)
    """

    def __init__(
        self,
        input_dim: int = 2,
        hidden_dim: int = 16,
        use_calibration: bool = True,
        calibration_path: Optional[str] = None,
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        # Xavier initialization
        self.W1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(1.0 / input_dim)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, 1) * np.sqrt(1.0 / hidden_dim)
        self.b2 = np.zeros(1)

        # Normalization parameters
        self.temp_mean = 310  # K
        self.temp_std = 30
        self.volt_mean = 1.0  # V
        self.volt_std = 0.15
        self.calibration_loaded = False

        if use_calibration:
            self.calibration_loaded = load_and_apply_perceptron_calibration(
                self,
                path=calibration_path,
            )

    def relu(self, x: np.ndarray) -> np.ndarray:
        """ReLU activation"""
        return np.maximum(0, x)

    def sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Sigmoid activation"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def normalize_inputs(self, temperature: float, voltage: float) -> np.ndarray:
        """Normalize inputs"""
        norm_temp = (temperature - self.temp_mean) / self.temp_std
        norm_volt = (voltage - self.volt_mean) / self.volt_std
        return np.array([norm_temp, norm_volt])

    def forward(self, temperature: float, voltage: float) -> float:
        """
        Forward pass: Temperature, Voltage -> Noise weight

        Returns:
            Noise weight in [0, 1] range
        """
        x = self.normalize_inputs(temperature, voltage)

        # Hidden layer
        z1 = np.dot(x, self.W1) + self.b1
        a1 = self.relu(z1)

        # Output layer
        z2 = np.dot(a1, self.W2) + self.b2
        output = self.sigmoid(z2)

        return float(output[0])


# ============================================================================
# Part 2: Adaptive Perceptron Gate (logic implementation)
# ============================================================================

class HybridPerceptronGate:
    """
    Perceptron gate with:
    1. Adaptive weights (temperature/voltage dependent)
    2. MLP-based noise modeling

    Best of both worlds!
    """

    def __init__(self, gate_type: str = 'NAND',
                 noise_model: PerceptronNoiseModel = None,
                 learning_rate: float = 0.1,
                 epochs: int = 1000):
        """
        Args:
            gate_type: 'NAND', 'NOR', 'NOT', 'AND', 'OR'
            noise_model: MLP perceptron for noise prediction
            learning_rate: Learning rate for training
            epochs: Training epochs
        """
        self.gate_type = gate_type.upper()
        self.learning_rate = learning_rate
        self.epochs = epochs

        # Noise model (shared across gates)
        self.noise_model = noise_model if noise_model else PerceptronNoiseModel()

        # Base weights (trained at nominal conditions)
        if self.gate_type == 'NOT':
            self.W_base = np.random.randn(1) * 0.1
            self.b_base = np.random.randn() * 0.1
        else:
            self.W_base = np.random.randn(2) * 0.1
            self.b_base = np.random.randn() * 0.1

        # Train at nominal conditions
        self.train()

        # Current environmental conditions
        self.temperature = 300  # K
        self.voltage = 1.0      # V

        # Adaptive weights
        self.W = self.W_base.copy()
        self.b = self.b_base

        # Noise parameters
        self.base_noise_floor = 0.05
        self.k_B = 1.38e-23  # Boltzmann constant

    def get_truth_table(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get truth table for gate type"""
        if self.gate_type == 'NAND':
            X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
            y = np.array([1, 1, 1, 0])
        elif self.gate_type == 'NOR':
            X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
            y = np.array([1, 0, 0, 0])
        elif self.gate_type == 'AND':
            X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
            y = np.array([0, 0, 0, 1])
        elif self.gate_type == 'OR':
            X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
            y = np.array([0, 1, 1, 1])
        elif self.gate_type == 'NOT':
            X = np.array([[0], [1]])
            y = np.array([1, 0])
        else:
            raise ValueError(f"Unknown gate type: {self.gate_type}")

        return X, y

    def train(self):
        """Train perceptron on truth table"""
        X, y = self.get_truth_table()

        for epoch in range(self.epochs):
            errors = 0
            for i in range(len(X)):
                z = np.dot(X[i], self.W_base) + self.b_base
                y_pred = 1 if z >= 0 else 0
                error = y[i] - y_pred

                if error != 0:
                    self.W_base += self.learning_rate * error * X[i]
                    self.b_base += self.learning_rate * error
                    errors += 1

            if errors == 0:
                break  # Converged

    def update_conditions(self, temperature: float, voltage: float):
        """
        Update environmental conditions and adapt weights

        Physical effects:
        1. Temperature: Higher T -> thermal drift, noise
        2. Voltage: Lower V -> weaker drive strength
        """
        self.temperature = temperature
        self.voltage = voltage

        # Temperature factor (normalized around 300K)
        temp_factor = 1.0 + (temperature - 300) / 300 * 0.1

        # Voltage factor (normalized around 1.0V)
        volt_factor = voltage / 1.0

        # Adapt weights
        self.W = self.W_base * temp_factor * volt_factor
        self.b = self.b_base * temp_factor * volt_factor

    def get_mlp_noise_weight(self) -> float:
        """
        Get sophisticated noise weight from MLP model

        Returns:
            Noise weight from 2-layer MLP (0~1)
        """
        return self.noise_model.forward(self.temperature, self.voltage)

    def get_thermal_noise(self) -> float:
        """
        Johnson-Nyquist thermal noise

        Formula: sigma = sqrt(k_B * T)
        """
        thermal_noise = np.sqrt(self.k_B * self.temperature) * 1e10
        return thermal_noise

    def get_total_noise_level(self) -> float:
        """
        Calculate total noise using:
        1. MLP perceptron noise weight
        2. Johnson-Nyquist thermal noise
        3. Voltage-dependent noise margin

        Returns:
            Total noise standard deviation
        """
        # MLP prediction
        mlp_noise_weight = self.get_mlp_noise_weight()

        # Base noise modulated by MLP
        base_noise = self.base_noise_floor * (1 + mlp_noise_weight)

        # Temperature factor
        temp_factor = (self.temperature - 273.15) / 100.0

        # Voltage factor (lower voltage -> more noise susceptibility)
        volt_factor = (1.0 - self.voltage) / 1.0

        # Thermal noise
        thermal_noise = self.get_thermal_noise()

        # Combine all noise sources
        total_noise = base_noise * (1 + 0.5 * temp_factor) * (1 + 0.3 * volt_factor)
        total_noise += thermal_noise * 0.01

        return total_noise

    def forward(self, *inputs) -> int:
        """
        Forward pass with adaptive weights and sophisticated noise

        Returns:
            Gate output (0 or 1)
        """
        # Compute activation with adapted weights
        z = np.dot(inputs, self.W) + self.b

        # Add sophisticated noise
        noise_level = self.get_total_noise_level()
        z += np.random.normal(0, noise_level)

        # Step activation
        return 1 if z >= 0 else 0

    def __call__(self, *inputs) -> int:
        """Allow gate(inputs) syntax"""
        return self.forward(*inputs)


# ============================================================================
# Part 3: Hybrid SR Latch
# ============================================================================

class HybridSRLatch:
    """SR Latch with hybrid perceptron NAND gates"""

    def __init__(self, noise_model: PerceptronNoiseModel = None,
                 temperature: float = 300, voltage: float = 1.0):
        # Shared noise model
        if noise_model is None:
            noise_model = PerceptronNoiseModel()

        # Cross-coupled NAND gates
        self.nand1 = HybridPerceptronGate('NAND', noise_model)
        self.nand2 = HybridPerceptronGate('NAND', noise_model)

        # Internal state
        self.Q = 0
        self.Q_bar = 1

        # Set conditions
        self.update_conditions(temperature, voltage)

    def update_conditions(self, temperature: float, voltage: float):
        """Update environmental conditions for both gates"""
        self.temperature = temperature
        self.voltage = voltage
        self.nand1.update_conditions(temperature, voltage)
        self.nand2.update_conditions(temperature, voltage)

    def update(self, S: int, R: int, iterations: int = 10) -> Tuple[int, int]:
        """
        Update latch state with cross-coupled feedback

        Args:
            S: Set input (active low)
            R: Reset input (active low)
            iterations: Number of feedback iterations

        Returns:
            (Q, Q_bar) tuple
        """
        for _ in range(iterations):
            Q_prev = self.Q
            Q_bar_prev = self.Q_bar

            # Cross-coupled feedback
            self.Q = self.nand1(S, self.Q_bar)
            self.Q_bar = self.nand2(R, self.Q)

            # Check convergence
            if self.Q == Q_prev and self.Q_bar == Q_bar_prev:
                break

        return self.Q, self.Q_bar

    def set(self):
        """Set Q to 1"""
        self.update(S=0, R=1)

    def reset(self):
        """Reset Q to 0"""
        self.update(S=1, R=0)

    def write(self, bit: int):
        """Write a bit"""
        if bit == 1:
            self.set()
        else:
            self.reset()

    def read(self) -> int:
        """Read current state"""
        return self.Q


# ============================================================================
# Part 4: Hybrid 6T SRAM Cell
# ============================================================================

class Hybrid6TSRAM:
    """
    6T SRAM cell with hybrid perceptron gates

    Structure:
    - 2 cross-coupled inverters (Perceptron NOT gates)
    - 2 access transistors (Perceptron AND gates)
    - Sophisticated MLP noise modeling
    """

    def __init__(self, cell_id: int = 0,
                 noise_model: PerceptronNoiseModel = None,
                 temperature: float = 300,
                 voltage: float = 1.0):
        self.cell_id = cell_id

        # Shared noise model
        if noise_model is None:
            noise_model = PerceptronNoiseModel()
        self.noise_model = noise_model

        # Cross-coupled inverters
        self.inv1 = HybridPerceptronGate('NOT', noise_model)
        self.inv2 = HybridPerceptronGate('NOT', noise_model)

        # Access transistors
        self.access1 = HybridPerceptronGate('AND', noise_model)
        self.access2 = HybridPerceptronGate('AND', noise_model)

        # Internal nodes
        self.Q = 0
        self.Q_bar = 1

        # Environmental conditions
        self.temperature = temperature
        self.voltage = voltage
        self.update_conditions(temperature, voltage)

    def update_conditions(self, temperature: float, voltage: float):
        """Update all gates to new environmental conditions"""
        self.temperature = temperature
        self.voltage = voltage

        self.inv1.update_conditions(temperature, voltage)
        self.inv2.update_conditions(temperature, voltage)
        self.access1.update_conditions(temperature, voltage)
        self.access2.update_conditions(temperature, voltage)

    def stabilize(self, iterations: int = 10) -> bool:
        """
        Stabilize through cross-coupled feedback

        Returns:
            True if converged, False if metastable
        """
        for i in range(iterations):
            Q_prev = self.Q
            Q_bar_prev = self.Q_bar

            # Cross-coupled inverters
            Q_new = self.inv1(self.Q_bar)
            Q_bar_new = self.inv2(self.Q)

            self.Q = Q_new
            self.Q_bar = Q_bar_new

            # Check convergence
            if self.Q == Q_prev and self.Q_bar == Q_bar_prev:
                return True  # Converged

        return False  # Possibly metastable

    def write(self, bit_value: int, word_line: int = 1):
        """
        Write operation

        Args:
            bit_value: Bit to write (0 or 1)
            word_line: Word line signal (1 = active)
        """
        if word_line:
            # Force new value
            self.Q = bit_value
            self.Q_bar = 1 - bit_value

            # Let it stabilize through feedback
            self.stabilize()

    def read(self, word_line: int = 1) -> int:
        """
        Read operation

        Args:
            word_line: Word line signal (1 = active)

        Returns:
            Stored bit value
        """
        if word_line:
            # Access transistor allows read
            output = self.access1(word_line, self.Q)
            return output

        return 0

    def get_reliability_metrics(self) -> Dict:
        """
        Calculate reliability metrics with hybrid noise model

        Returns:
            Dictionary with SNM, noise levels, etc.
        """
        # Base SNM (200mV at nominal)
        base_snm = 0.2

        # Temperature degradation
        temp_degradation = (self.temperature - 300) / 300 * 0.25

        # Voltage degradation
        volt_degradation = (1.0 - self.voltage) / 1.0 * 0.5

        # Calculate SNM
        snm = base_snm * (1 - temp_degradation - volt_degradation)
        snm_v = max(float(snm), 0.0)

        # Get MLP noise weight
        mlp_noise_weight = self.noise_model.forward(self.temperature, self.voltage)

        # Total noise level
        total_noise = self.inv1.get_total_noise_level()

        return {
            # Keep SNM in volts for compatibility with standard/native backends.
            'snm': snm_v,
            'snm_mv': snm_v * 1000.0,
            'mlp_noise_weight': mlp_noise_weight,
            'total_noise_level': total_noise,
            'thermal_noise': self.inv1.get_thermal_noise(),
            'temperature': self.temperature,
            'voltage': self.voltage,
            'cell_id': self.cell_id
        }


# ============================================================================
# Part 5: Hybrid SRAM Array
# ============================================================================

class HybridSRAMArray:
    """
    SRAM array with hybrid perceptron cells

    Features:
    - Adaptive perceptron logic gates
    - MLP noise modeling
    - Environmental dependency
    """

    def __init__(self, num_cells: int = 64,
                 temperature: float = 300,
                 voltage: float = 1.0):
        self.num_cells = num_cells
        self.temperature = temperature
        self.voltage = voltage

        # Single shared noise model for all cells (efficient)
        self.noise_model = PerceptronNoiseModel()

        # Create cells
        self.cells = [
            Hybrid6TSRAM(i, self.noise_model, temperature, voltage)
            for i in range(num_cells)
        ]

    def update_conditions(self, temperature: float, voltage: float):
        """Update all cells to new conditions"""
        self.temperature = temperature
        self.voltage = voltage

        for cell in self.cells:
            cell.update_conditions(temperature, voltage)

    def write(self, address: int, bit_value: int):
        """Write to specific address"""
        if 0 <= address < self.num_cells:
            self.cells[address].write(bit_value)

    def read(self, address: int) -> int:
        """Read from specific address"""
        if 0 <= address < self.num_cells:
            return self.cells[address].read()
        return 0

    def write_pattern(self, pattern: str):
        """Write binary pattern to array"""
        for i, bit_char in enumerate(pattern):
            if i >= self.num_cells:
                break
            bit = int(bit_char)
            self.write(i, bit)

    def read_all(self) -> List[int]:
        """Read all cells"""
        return [self.read(i) for i in range(self.num_cells)]

    def get_bit_error_rate(self, expected_pattern: List[int]) -> float:
        """Calculate bit error rate as a ratio in [0, 1]."""
        actual = self.read_all()
        if not expected_pattern:
            return 0.0
        errors = sum(1 for i, bit in enumerate(expected_pattern)
                    if i < len(actual) and actual[i] != bit)
        return errors / len(expected_pattern)

    def simulate(self, temperature: float, voltage: float,
                 input_pattern: List[int]) -> Dict:
        """
        Run complete simulation with hybrid model

        Args:
            temperature: Temperature in K
            voltage: Voltage in V
            input_pattern: Input bit pattern

        Returns:
            Simulation results with metrics
        """
        normalized_input = [1 if int(bit) > 0 else 0 for bit in list(input_pattern)[:self.num_cells]]
        if not normalized_input:
            normalized_input = [i % 2 for i in range(self.num_cells)]

        # Update environmental conditions
        self.update_conditions(temperature, voltage)

        # Write input pattern
        for i, bit in enumerate(normalized_input):
            if i < self.num_cells:
                self.write(i, bit)

        # Read output
        output = self.read_all()[:len(normalized_input)]

        # Calculate metrics
        metrics_list = [cell.get_reliability_metrics() for cell in self.cells]

        snm_values = [m['snm'] for m in metrics_list]
        snm_values = snm_values[:len(normalized_input)]
        mlp_weights = [m['mlp_noise_weight'] for m in metrics_list]
        mlp_weights = mlp_weights[:len(normalized_input)]
        noise_levels = [m['total_noise_level'] for m in metrics_list]
        noise_levels = noise_levels[:len(normalized_input)]
        thermal_levels = [m['thermal_noise'] for m in metrics_list][:len(normalized_input)]

        # Bit error rate as ratio [0, 1] for consistency across backends.
        bit_errors = sum(1 for expected, actual in zip(normalized_input, output) if actual != expected)
        ber_ratio = bit_errors / max(len(normalized_input), 1)

        return {
            # Standard/native-compatible keys
            'input_data': normalized_input,
            'output_data': [float(v) for v in output],
            'noise_values': [float(v) for v in noise_levels],
            'snm_values': snm_values,
            'snm_mean': float(np.mean(snm_values)) if snm_values else 0.0,
            'snm_std': float(np.std(snm_values)) if snm_values else 0.0,
            'bit_errors': int(bit_errors),
            'bit_error_rate': float(ber_ratio),
            'ber_std': 0.0,
            'ber_confidence_95': 0.0,
            'monte_carlo_ber': [float(ber_ratio)],
            'thermal_sigma': float(np.mean(thermal_levels)) if thermal_levels else 0.0,
            'include_thermal_noise': True,
            # Extended hybrid diagnostics
            'input': normalized_input,
            'output': output,
            'mlp_noise_weights': mlp_weights,
            'mlp_noise_mean': float(np.mean(mlp_weights)) if mlp_weights else 0.0,
            'total_noise_levels': noise_levels,
            'noise_mean': float(np.mean(noise_levels)) if noise_levels else 0.0,
            'bit_error_rate_percent': float(ber_ratio * 100.0),
            'temperature': temperature,
            'voltage': voltage,
            'num_cells': self.num_cells
        }


# ============================================================================
# Part 6: Comprehensive Testing
# ============================================================================

def test_hybrid_vs_original():
    """
    Compare hybrid implementation with original main_advanced.py
    """
    print("=" * 70)
    print("Hybrid Perceptron SRAM - Comparison Test")
    print("=" * 70)
    print()

    # Test pattern
    pattern = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1]

    print(f"Test Pattern: {pattern}")
    print()

    # Create hybrid array
    hybrid_array = HybridSRAMArray(num_cells=len(pattern), temperature=300, voltage=1.0)

    # Test conditions
    conditions = [
        ("Nominal", 300, 1.0),
        ("High Temp", 350, 1.0),
        ("Low Voltage", 300, 0.8),
        ("Worst Case", 360, 0.8),
    ]

    print("-" * 70)
    print("SIMULATION RESULTS")
    print("-" * 70)

    for name, temp, volt in conditions:
        result = hybrid_array.simulate(temp, volt, pattern)

        print(f"\n{name} (T={temp}K, V={volt}V):")
        print(f"  Input:          {result['input']}")
        print(f"  Output:         {result['output']}")
        print(f"  BER:            {result['bit_error_rate']*100:.2f}%")
        print(f"  SNM:            {result['snm_mean']*1000:.2f} +/- {result['snm_std']*1000:.2f} mV")
        print(f"  MLP Noise Wt:   {result['mlp_noise_mean']:.4f}")
        print(f"  Total Noise:    {result['noise_mean']:.6f}")

        if name != "Nominal":
            nominal_snm = 0.2  # Volts
            degradation_mv = (nominal_snm - result['snm_mean']) * 1000.0
            print(f"  SNM Degradation: {degradation_mv:.2f} mV")

    print()
    print("-" * 70)
    print("NOISE MODEL COMPARISON")
    print("-" * 70)

    # Compare noise predictions at different conditions
    noise_model = PerceptronNoiseModel()

    test_points = [
        (260, 1.0),
        (300, 1.0),
        (350, 1.0),
        (300, 0.8),
        (300, 1.2),
        (360, 0.8)
    ]

    print("\nMLP Perceptron Noise Weights:")
    print(f"{'Temperature':>12} {'Voltage':>10} {'Noise Weight':>15}")
    print("-" * 40)

    for temp, volt in test_points:
        weight = noise_model.forward(temp, volt)
        print(f"{temp:>12}K {volt:>9}V {weight:>15.4f}")

    print()
    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)


def test_hybrid_details():
    """Detailed test of hybrid model components"""
    print("\n" + "=" * 70)
    print("Hybrid Model - Detailed Component Test")
    print("=" * 70)

    # Create noise model
    noise_model = PerceptronNoiseModel()

    # Test single gate
    print("\n1. Hybrid Perceptron Gate Test")
    print("-" * 70)

    nand = HybridPerceptronGate('NAND', noise_model)

    print("NAND Gate at nominal conditions (T=300K, V=1.0V):")
    for a in [0, 1]:
        for b in [0, 1]:
            output = nand(a, b)
            expected = 1 if not (a and b) else 0
            status = "PASS" if output == expected else "FAIL"
            print(f"  {a} NAND {b} = {output} (expected {expected}) [{status}]")

    # Test under stress
    print("\nNAND Gate under stress (T=360K, V=0.8V):")
    nand.update_conditions(360, 0.8)

    # Run multiple times to see noise effects
    trials = 10
    results = {(a, b): [] for a in [0, 1] for b in [0, 1]}

    for _ in range(trials):
        for a in [0, 1]:
            for b in [0, 1]:
                output = nand(a, b)
                results[(a, b)].append(output)

    for (a, b), outputs in results.items():
        success_rate = sum(outputs) / len(outputs) if (a, b) != (1, 1) else 1 - sum(outputs) / len(outputs)
        expected = 1 if not (a and b) else 0
        print(f"  {a} NAND {b}: outputs={outputs}, success_rate={success_rate*100:.0f}%")

    # Test SRAM cell
    print("\n2. Hybrid 6T SRAM Cell Test")
    print("-" * 70)

    cell = Hybrid6TSRAM(noise_model=noise_model, temperature=300, voltage=1.0)

    print("Write and Read test:")
    for bit in [0, 1, 1, 0]:
        cell.write(bit)
        read_val = cell.read()
        status = "PASS" if read_val == bit else "FAIL"
        print(f"  Write {bit}, Read {read_val} [{status}]")

    # Test reliability metrics
    print("\n3. Reliability Metrics")
    print("-" * 70)

    test_conditions = [(300, 1.0), (350, 1.0), (300, 0.8), (360, 0.8)]

    print(f"{'Temp':>6} {'Volt':>6} {'SNM (mV)':>10} {'MLP Weight':>12} {'Total Noise':>12}")
    print("-" * 60)

    for temp, volt in test_conditions:
        cell.update_conditions(temp, volt)
        metrics = cell.get_reliability_metrics()
        print(f"{temp:>6}K {volt:>5}V {metrics['snm_mv']:>10.2f} "
              f"{metrics['mlp_noise_weight']:>12.4f} {metrics['total_noise_level']:>12.6f}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Run all tests
    test_hybrid_vs_original()
    test_hybrid_details()
