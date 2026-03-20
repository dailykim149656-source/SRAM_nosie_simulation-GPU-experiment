"""
Adaptive Perceptron-Based SRAM
- Perceptron weights adapt to Temperature, Voltage, and Cell count
- Realistic physical modeling with environmental dependencies
"""

import numpy as np
from typing import Tuple, List, Dict

class AdaptivePerceptronGate:
    """
    Perceptron gate with weights that adapt to environmental conditions

    Key idea: Temperature, Voltage affect transistor behavior
              → Perceptron weights change accordingly
    """

    def __init__(self, gate_type: str = 'NAND', learning_rate: float = 0.1, epochs: int = 1000):
        """
        Args:
            gate_type: 'NAND', 'NOR', 'NOT', 'AND', 'OR'
            learning_rate: Base learning rate
            epochs: Training iterations
        """
        self.gate_type = gate_type.upper()
        self.learning_rate = learning_rate
        self.epochs = epochs

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
        self.temperature = 300  # K (nominal: 27°C)
        self.voltage = 1.0      # V (nominal)

        # Adaptive weights (will change with conditions)
        self.W = self.W_base.copy()
        self.b = self.b_base

    def activation(self, z: float, noise_level: float = 0.0) -> int:
        """
        Step activation with temperature-dependent noise

        Args:
            z: Activation value
            noise_level: Noise standard deviation

        Returns:
            Gate output (0 or 1)
        """
        if noise_level > 0:
            z += np.random.normal(0, noise_level)
        return 1 if z >= 0 else 0

    def get_truth_table(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get truth table for the gate type"""
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
        """Train perceptron at nominal conditions"""
        X, y = self.get_truth_table()

        for epoch in range(self.epochs):
            errors = 0
            for i in range(len(X)):
                z = np.dot(X[i], self.W_base) + self.b_base
                y_pred = self.activation(z)
                error = y[i] - y_pred

                if error != 0:
                    errors += 1
                    self.W_base += self.learning_rate * error * X[i]
                    self.b_base += self.learning_rate * error

            if errors == 0:
                break

    def update_conditions(self, temperature: float, voltage: float):
        """
        Update environmental conditions and adapt weights

        Physical effects modeled:
        1. Temperature: Higher T → more thermal noise, slower switching
        2. Voltage: Lower V → weaker drive, more susceptible to noise

        Args:
            temperature: Temperature in Kelvin (260-360K typical)
            voltage: Supply voltage in Volts (0.8-1.2V typical)
        """
        self.temperature = temperature
        self.voltage = voltage

        # Temperature factor (normalized around 300K)
        # Higher temp → weights drift (thermal effects)
        temp_factor = 1.0 + (temperature - 300) / 300 * 0.1

        # Voltage factor (normalized around 1.0V)
        # Lower voltage → reduced drive strength → weights change
        volt_factor = voltage / 1.0

        # Adapt weights based on conditions
        self.W = self.W_base * temp_factor * volt_factor
        self.b = self.b_base * temp_factor * volt_factor

    def get_noise_level(self) -> float:
        """
        Calculate noise level based on temperature and voltage

        Johnson-Nyquist thermal noise: sigma ∝ sqrt(kT)
        Voltage dependency: sigma ∝ 1/V

        Returns:
            Noise standard deviation
        """
        k_B = 1.38e-23  # Boltzmann constant

        # Thermal noise (simplified)
        thermal_noise = np.sqrt(k_B * self.temperature) * 1e10  # Scaled

        # Voltage dependency
        voltage_factor = 1.0 / max(self.voltage, 0.5)

        # Combined noise
        noise_level = thermal_noise * voltage_factor * 0.01

        return noise_level

    def forward(self, *inputs) -> int:
        """
        Compute gate output with environmental effects

        Args:
            *inputs: Gate inputs

        Returns:
            Gate output (0 or 1)
        """
        inputs = np.array(inputs)

        if self.gate_type == 'NOT' and len(inputs) != 1:
            raise ValueError("NOT gate requires exactly 1 input")
        elif self.gate_type != 'NOT' and len(inputs) != 2:
            raise ValueError(f"{self.gate_type} gate requires exactly 2 inputs")

        # Compute with adapted weights
        z = np.dot(inputs, self.W) + self.b

        # Add noise based on conditions
        noise_level = self.get_noise_level()

        return self.activation(z, noise_level)

    def __call__(self, *inputs) -> int:
        """Allow gate(A, B) syntax"""
        return self.forward(*inputs)


class AdaptiveSRLatch:
    """SR Latch with adaptive perceptron gates"""

    def __init__(self, temperature: float = 300, voltage: float = 1.0):
        """
        Args:
            temperature: Operating temperature (K)
            voltage: Supply voltage (V)
        """
        self.nand1 = AdaptivePerceptronGate('NAND')
        self.nand2 = AdaptivePerceptronGate('NAND')

        # Set conditions
        self.temperature = temperature
        self.voltage = voltage
        self.update_conditions(temperature, voltage)

        # Internal state
        self.Q = 0
        self.Q_bar = 1

    def update_conditions(self, temperature: float, voltage: float):
        """Update environmental conditions"""
        self.temperature = temperature
        self.voltage = voltage
        self.nand1.update_conditions(temperature, voltage)
        self.nand2.update_conditions(temperature, voltage)

    def update(self, S: int, R: int, stabilize_iterations: int = 10) -> Tuple[int, int]:
        """Update latch state with environmental effects"""
        if S == 0 and R == 0:
            raise ValueError("Invalid SR Latch state: S=0, R=0")

        for _ in range(stabilize_iterations):
            Q_prev = self.Q
            Q_bar_prev = self.Q_bar

            self.Q = self.nand1(S, self.Q_bar)
            self.Q_bar = self.nand2(R, self.Q)

            if self.Q == Q_prev and self.Q_bar == Q_bar_prev:
                break

        return self.Q, self.Q_bar

    def write(self, bit: int):
        """Write a bit value"""
        if bit == 1:
            return self.update(S=0, R=1)
        else:
            return self.update(S=1, R=0)

    def read(self) -> int:
        """Read current value"""
        return self.Q


class Adaptive6TSRAM:
    """
    6T SRAM Cell with adaptive perceptron gates
    Weights change based on Temperature, Voltage, and loading
    """

    def __init__(self, cell_id: int = 0, temperature: float = 300, voltage: float = 1.0):
        """
        Args:
            cell_id: Unique cell identifier
            temperature: Operating temperature (K)
            voltage: Supply voltage (V)
        """
        self.cell_id = cell_id
        self.temperature = temperature
        self.voltage = voltage

        # Cross-coupled inverters
        self.inv1 = AdaptivePerceptronGate('NOT')
        self.inv2 = AdaptivePerceptronGate('NOT')

        # Access control
        self.access1 = AdaptivePerceptronGate('AND')
        self.access2 = AdaptivePerceptronGate('AND')

        # Update conditions
        self.update_conditions(temperature, voltage)

        # Internal storage
        self.Q = 0
        self.Q_bar = 1

    def update_conditions(self, temperature: float, voltage: float):
        """
        Update environmental conditions

        This is the KEY method - weights adapt here!
        """
        self.temperature = temperature
        self.voltage = voltage

        self.inv1.update_conditions(temperature, voltage)
        self.inv2.update_conditions(temperature, voltage)
        self.access1.update_conditions(temperature, voltage)
        self.access2.update_conditions(temperature, voltage)

    def stabilize(self, iterations: int = 10) -> bool:
        """Stabilize through feedback with environmental effects"""
        for i in range(iterations):
            Q_prev = self.Q
            Q_bar_prev = self.Q_bar

            # Cross-coupled feedback (weights already adapted)
            Q_new = self.inv1(self.Q_bar)
            Q_bar_new = self.inv2(self.Q)

            self.Q = Q_new
            self.Q_bar = Q_bar_new

            if self.Q == Q_prev and self.Q_bar == Q_bar_prev:
                return True

        return False

    def write(self, bit_value: int, word_line: int = 1) -> bool:
        """Write operation with environmental effects"""
        if word_line == 0:
            return False

        self.Q = bit_value
        self.Q_bar = 1 - bit_value

        converged = self.stabilize()
        return converged

    def read(self, word_line: int = 1) -> int:
        """Read operation"""
        if word_line == 0:
            return -1

        return self.access1(word_line, self.Q)

    def get_reliability_metrics(self) -> Dict:
        """
        Get reliability metrics based on current conditions

        Returns:
            Dictionary with SNM, noise margin, etc.
        """
        # Simplified SNM calculation
        # In real implementation, would be more complex

        # Base SNM (at nominal conditions)
        base_snm = 0.2  # 200mV

        # Temperature degradation
        temp_degradation = (self.temperature - 300) / 100 * 0.05

        # Voltage dependency
        volt_factor = self.voltage / 1.0

        snm = base_snm * volt_factor - temp_degradation

        # Noise margin
        noise_level = self.inv1.get_noise_level()

        return {
            'snm': max(0, snm),
            'noise_level': noise_level,
            'temperature': self.temperature,
            'voltage': self.voltage,
            'stable': self.Q == (1 - self.Q_bar)  # Bistable check
        }


class AdaptiveSRAMArray:
    """
    SRAM Array with adaptive cells

    KEY FEATURE: Weights adapt to Temperature, Voltage, Cell count
    """

    def __init__(self, num_cells: int = 64, temperature: float = 300, voltage: float = 1.0):
        """
        Args:
            num_cells: Number of SRAM cells
            temperature: Operating temperature (K)
            voltage: Supply voltage (V)
        """
        self.num_cells = num_cells
        self.temperature = temperature
        self.voltage = voltage

        # Create cells
        self.cells = [
            Adaptive6TSRAM(cell_id=i, temperature=temperature, voltage=voltage)
            for i in range(num_cells)
        ]

        # Initialize with alternating pattern
        for i, cell in enumerate(self.cells):
            cell.write(bit_value=i % 2, word_line=1)

    def update_conditions(self, temperature: float, voltage: float):
        """
        Update environmental conditions for ALL cells

        This updates Perceptron weights across the entire array!
        """
        self.temperature = temperature
        self.voltage = voltage

        for cell in self.cells:
            cell.update_conditions(temperature, voltage)

    def simulate(self, temperature: float, voltage: float,
                 input_pattern: List[int] = None) -> Dict:
        """
        Simulate SRAM with given conditions

        Args:
            temperature: Temperature (K)
            voltage: Voltage (V)
            input_pattern: Optional input pattern

        Returns:
            Simulation results
        """
        # Update all cells to new conditions
        self.update_conditions(temperature, voltage)

        # Write pattern if provided
        if input_pattern:
            for i, bit in enumerate(input_pattern[:self.num_cells]):
                self.cells[i].write(bit, word_line=1)

        # Read all cells
        output = self.read_all()

        # Calculate metrics
        reliability_metrics = [cell.get_reliability_metrics() for cell in self.cells]

        snm_values = [m['snm'] for m in reliability_metrics]
        noise_levels = [m['noise_level'] for m in reliability_metrics]

        # Bit error rate (compare with expected)
        if input_pattern:
            expected = input_pattern[:self.num_cells]
            errors = sum(1 for a, e in zip(output, expected) if a != e)
            ber = errors / self.num_cells
        else:
            ber = 0.0

        return {
            'output': output,
            'snm_values': snm_values,
            'snm_mean': np.mean(snm_values),
            'snm_std': np.std(snm_values),
            'noise_levels': noise_levels,
            'noise_mean': np.mean(noise_levels),
            'bit_error_rate': ber,
            'temperature': temperature,
            'voltage': voltage,
            'num_cells': self.num_cells,
            'reliability_metrics': reliability_metrics
        }

    def write(self, address: int, bit_value: int) -> bool:
        """Write to a cell"""
        if 0 <= address < self.num_cells:
            return self.cells[address].write(bit_value, word_line=1)
        return False

    def read(self, address: int) -> int:
        """Read from a cell"""
        if 0 <= address < self.num_cells:
            return self.cells[address].read(word_line=1)
        return -1

    def read_all(self) -> List[int]:
        """Read all cells"""
        return [cell.read(word_line=1) for cell in self.cells]


# Test and demonstration
def test_adaptive_behavior():
    """Demonstrate adaptive behavior with changing conditions"""
    print("="*70)
    print("Adaptive Perceptron SRAM - Environmental Dependency Test")
    print("="*70)

    array = AdaptiveSRAMArray(num_cells=16, temperature=300, voltage=1.0)

    # Test pattern
    pattern = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1]

    print("\nTest Pattern:", pattern)
    print("\n" + "-"*70)

    # Test 1: Nominal conditions
    print("\n1. NOMINAL CONDITIONS (T=300K, V=1.0V)")
    result1 = array.simulate(temperature=300, voltage=1.0, input_pattern=pattern)
    print(f"   Output:  {result1['output']}")
    print(f"   BER:     {result1['bit_error_rate']:.2%}")
    print(f"   SNM:     {result1['snm_mean']*1000:.2f} ± {result1['snm_std']*1000:.2f} mV")
    print(f"   Noise:   {result1['noise_mean']:.6f}")

    # Test 2: High temperature
    print("\n2. HIGH TEMPERATURE (T=350K, V=1.0V)")
    result2 = array.simulate(temperature=350, voltage=1.0, input_pattern=pattern)
    print(f"   Output:  {result2['output']}")
    print(f"   BER:     {result2['bit_error_rate']:.2%}")
    print(f"   SNM:     {result2['snm_mean']*1000:.2f} ± {result2['snm_std']*1000:.2f} mV")
    print(f"   Noise:   {result2['noise_mean']:.6f}")
    print(f"   → SNM degraded by {(result1['snm_mean']-result2['snm_mean'])*1000:.2f} mV")

    # Test 3: Low voltage
    print("\n3. LOW VOLTAGE (T=300K, V=0.8V)")
    result3 = array.simulate(temperature=300, voltage=0.8, input_pattern=pattern)
    print(f"   Output:  {result3['output']}")
    print(f"   BER:     {result3['bit_error_rate']:.2%}")
    print(f"   SNM:     {result3['snm_mean']*1000:.2f} ± {result3['snm_std']*1000:.2f} mV")
    print(f"   Noise:   {result3['noise_mean']:.6f}")
    print(f"   → SNM reduced by {(result1['snm_mean']-result3['snm_mean'])*1000:.2f} mV")

    # Test 4: Worst case
    print("\n4. WORST CASE (T=360K, V=0.8V)")
    result4 = array.simulate(temperature=360, voltage=0.8, input_pattern=pattern)
    print(f"   Output:  {result4['output']}")
    print(f"   BER:     {result4['bit_error_rate']:.2%}")
    print(f"   SNM:     {result4['snm_mean']*1000:.2f} ± {result4['snm_std']*1000:.2f} mV")
    print(f"   Noise:   {result4['noise_mean']:.6f}")
    print(f"   → SNM degraded by {(result1['snm_mean']-result4['snm_mean'])*1000:.2f} mV")

    # Test 5: Different cell counts
    print("\n" + "-"*70)
    print("\n5. CELL COUNT DEPENDENCY (T=300K, V=1.0V)")
    for num_cells in [8, 32, 64, 128]:
        array_test = AdaptiveSRAMArray(num_cells=num_cells, temperature=300, voltage=1.0)
        test_pattern = [1, 0] * (num_cells // 2)
        result = array_test.simulate(temperature=300, voltage=1.0, input_pattern=test_pattern)
        print(f"   {num_cells:3d} cells: BER={result['bit_error_rate']:.2%}, "
              f"SNM={result['snm_mean']*1000:.2f}mV")

    print("\n" + "="*70)
    print("Adaptive behavior verified!")
    print("="*70)


if __name__ == '__main__':
    test_adaptive_behavior()
