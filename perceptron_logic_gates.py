"""
Perceptron-Based Logic Gates Implementation
- NAND, NOR, NOT gates using Perceptron
- SR Latch using Cross-coupled NAND gates
- 6T SRAM Cell using Perceptron gates
"""

import numpy as np
from typing import Tuple, List

class PerceptronGate:
    """
    Single Perceptron implementing a logic gate
    Trained using truth table
    """

    def __init__(self, gate_type: str = 'NAND', learning_rate: float = 0.1, epochs: int = 1000):
        """
        Args:
            gate_type: 'NAND', 'NOR', 'NOT', 'AND', 'OR'
            learning_rate: Learning rate for training
            epochs: Number of training iterations
        """
        self.gate_type = gate_type.upper()
        self.learning_rate = learning_rate
        self.epochs = epochs

        # Initialize weights
        if self.gate_type == 'NOT':
            self.W = np.random.randn(1) * 0.1
            self.b = np.random.randn() * 0.1
        else:
            self.W = np.random.randn(2) * 0.1
            self.b = np.random.randn() * 0.1

        # Train the gate
        self.train()

    def activation(self, z: float) -> int:
        """Step activation function"""
        return 1 if z >= 0 else 0

    def get_truth_table(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get truth table for the gate type"""
        if self.gate_type == 'NAND':
            X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
            y = np.array([1, 1, 1, 0])  # NAND truth table

        elif self.gate_type == 'NOR':
            X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
            y = np.array([1, 0, 0, 0])  # NOR truth table

        elif self.gate_type == 'AND':
            X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
            y = np.array([0, 0, 0, 1])  # AND truth table

        elif self.gate_type == 'OR':
            X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
            y = np.array([0, 1, 1, 1])  # OR truth table

        elif self.gate_type == 'NOT':
            X = np.array([[0], [1]])
            y = np.array([1, 0])  # NOT truth table

        else:
            raise ValueError(f"Unknown gate type: {self.gate_type}")

        return X, y

    def train(self):
        """Train perceptron using truth table"""
        X, y = self.get_truth_table()

        for epoch in range(self.epochs):
            errors = 0
            for i in range(len(X)):
                # Forward pass
                z = np.dot(X[i], self.W) + self.b
                y_pred = self.activation(z)

                # Calculate error
                error = y[i] - y_pred

                if error != 0:
                    errors += 1
                    # Update weights
                    self.W += self.learning_rate * error * X[i]
                    self.b += self.learning_rate * error

            # Early stopping if perfect
            if errors == 0:
                break

    def forward(self, *inputs) -> int:
        """
        Compute gate output

        Args:
            *inputs: Gate inputs (1 for NOT, 2 for others)

        Returns:
            Gate output (0 or 1)
        """
        inputs = np.array(inputs)

        if self.gate_type == 'NOT' and len(inputs) != 1:
            raise ValueError("NOT gate requires exactly 1 input")
        elif self.gate_type != 'NOT' and len(inputs) != 2:
            raise ValueError(f"{self.gate_type} gate requires exactly 2 inputs")

        z = np.dot(inputs, self.W) + self.b
        return self.activation(z)

    def __call__(self, *inputs) -> int:
        """Allow gate(A, B) syntax"""
        return self.forward(*inputs)


class SRLatch:
    """
    SR Latch implemented with cross-coupled NAND gates

    Truth Table:
    S R | Q Q'
    ----+-----
    0 0 | Invalid
    0 1 | 1 0  (Set)
    1 0 | 0 1  (Reset)
    1 1 | Hold
    """

    def __init__(self):
        """Initialize SR Latch with two NAND gates"""
        self.nand1 = PerceptronGate('NAND')
        self.nand2 = PerceptronGate('NAND')

        # Internal state
        self.Q = 0
        self.Q_bar = 1

    def update(self, S: int, R: int, stabilize_iterations: int = 10) -> Tuple[int, int]:
        """
        Update latch state

        Args:
            S: Set signal (active low)
            R: Reset signal (active low)
            stabilize_iterations: Number of feedback iterations

        Returns:
            (Q, Q_bar)
        """
        # Invalid state check
        if S == 0 and R == 0:
            raise ValueError("Invalid SR Latch state: S=0, R=0")

        # Simulate cross-coupled feedback
        for _ in range(stabilize_iterations):
            Q_prev = self.Q
            Q_bar_prev = self.Q_bar

            # NAND gate equations
            self.Q = self.nand1(S, self.Q_bar)
            self.Q_bar = self.nand2(R, self.Q)

            # Check convergence
            if self.Q == Q_prev and self.Q_bar == Q_bar_prev:
                break

        return self.Q, self.Q_bar

    def set(self):
        """Set Q=1"""
        return self.update(S=0, R=1)

    def reset(self):
        """Reset Q=0"""
        return self.update(S=1, R=0)

    def hold(self):
        """Maintain current state"""
        return self.update(S=1, R=1)

    def write(self, bit: int):
        """Write a bit value"""
        if bit == 1:
            return self.set()
        else:
            return self.reset()

    def read(self) -> int:
        """Read current value"""
        return self.Q


class Perceptron6TSRAM:
    """
    6T SRAM Cell using Perceptron gates

    Structure:
    - 2 Cross-coupled inverters (storage)
    - 2 Access transistors (word line control)

    This is a TRUE perceptron-based SRAM implementation!
    """

    def __init__(self, cell_id: int = 0):
        """
        Initialize 6T SRAM cell

        Args:
            cell_id: Unique cell identifier
        """
        self.cell_id = cell_id

        # Cross-coupled inverters using NOT gates
        self.inv1 = PerceptronGate('NOT')
        self.inv2 = PerceptronGate('NOT')

        # Access control using AND gates
        # (Word Line AND internal value)
        self.access1 = PerceptronGate('AND')
        self.access2 = PerceptronGate('AND')

        # Internal storage nodes
        self.Q = 0
        self.Q_bar = 1

    def stabilize(self, iterations: int = 10) -> bool:
        """
        Stabilize internal state through cross-coupled feedback

        Args:
            iterations: Maximum feedback iterations

        Returns:
            True if converged, False if oscillating
        """
        for i in range(iterations):
            Q_prev = self.Q
            Q_bar_prev = self.Q_bar

            # Cross-coupled inverter feedback
            Q_new = self.inv1(self.Q_bar)
            Q_bar_new = self.inv2(self.Q)

            self.Q = Q_new
            self.Q_bar = Q_bar_new

            # Check convergence
            if self.Q == Q_prev and self.Q_bar == Q_bar_prev:
                return True  # Converged

        return False  # Did not converge (metastable?)

    def write(self, bit_value: int, word_line: int = 1) -> bool:
        """
        Write operation

        Args:
            bit_value: Value to write (0 or 1)
            word_line: Word line signal (1 = active)

        Returns:
            True if write successful
        """
        if word_line == 0:
            return False  # Word line not active

        # Force the new value
        self.Q = bit_value
        self.Q_bar = 1 - bit_value

        # Let it stabilize through feedback
        converged = self.stabilize()

        return converged

    def read(self, word_line: int = 1) -> int:
        """
        Read operation

        Args:
            word_line: Word line signal (1 = active)

        Returns:
            Stored bit value (or -1 if word line inactive)
        """
        if word_line == 0:
            return -1  # Word line not active

        # Access through word line
        output = self.access1(word_line, self.Q)

        return output

    def hold(self):
        """
        Hold current state (refresh through feedback)
        """
        return self.stabilize()

    def get_state(self) -> Tuple[int, int]:
        """Get internal state (Q, Q_bar)"""
        return self.Q, self.Q_bar


class PerceptronSRAMArray:
    """
    SRAM Array using Perceptron-based 6T cells

    This is a TRUE perceptron-based SRAM array!
    """

    def __init__(self, num_cells: int = 64):
        """
        Initialize SRAM array

        Args:
            num_cells: Number of SRAM cells
        """
        self.num_cells = num_cells
        self.cells = [Perceptron6TSRAM(cell_id=i) for i in range(num_cells)]

        # Initialize with alternating pattern
        for i, cell in enumerate(self.cells):
            cell.write(bit_value=i % 2, word_line=1)

    def write(self, address: int, bit_value: int) -> bool:
        """
        Write to a cell

        Args:
            address: Cell address
            bit_value: Value to write

        Returns:
            True if successful
        """
        if 0 <= address < self.num_cells:
            return self.cells[address].write(bit_value, word_line=1)
        return False

    def read(self, address: int) -> int:
        """
        Read from a cell

        Args:
            address: Cell address

        Returns:
            Stored value (-1 if invalid address)
        """
        if 0 <= address < self.num_cells:
            return self.cells[address].read(word_line=1)
        return -1

    def read_all(self) -> List[int]:
        """Read all cells"""
        return [cell.read(word_line=1) for cell in self.cells]

    def write_pattern(self, pattern: str):
        """
        Write a bit pattern

        Args:
            pattern: Binary string (e.g., '10101010')
        """
        for i, bit_char in enumerate(pattern[:self.num_cells]):
            if bit_char in ['0', '1']:
                self.write(i, int(bit_char))

    def get_bit_error_rate(self, expected_pattern: List[int]) -> float:
        """
        Calculate bit error rate

        Args:
            expected_pattern: Expected bit pattern

        Returns:
            BER (0.0 to 1.0)
        """
        actual = self.read_all()
        errors = sum(1 for a, e in zip(actual, expected_pattern[:self.num_cells]) if a != e)
        return errors / self.num_cells


# Test and verification functions
def test_perceptron_gates():
    """Test all perceptron gates"""
    print("="*60)
    print("Testing Perceptron Logic Gates")
    print("="*60)

    # Test NAND
    nand = PerceptronGate('NAND')
    print("\nNAND Gate:")
    print(f"  0 NAND 0 = {nand(0, 0)} (expected: 1)")
    print(f"  0 NAND 1 = {nand(0, 1)} (expected: 1)")
    print(f"  1 NAND 0 = {nand(1, 0)} (expected: 1)")
    print(f"  1 NAND 1 = {nand(1, 1)} (expected: 0)")

    # Test NOR
    nor = PerceptronGate('NOR')
    print("\nNOR Gate:")
    print(f"  0 NOR 0 = {nor(0, 0)} (expected: 1)")
    print(f"  0 NOR 1 = {nor(0, 1)} (expected: 0)")
    print(f"  1 NOR 0 = {nor(1, 0)} (expected: 0)")
    print(f"  1 NOR 1 = {nor(1, 1)} (expected: 0)")

    # Test NOT
    not_gate = PerceptronGate('NOT')
    print("\nNOT Gate:")
    print(f"  NOT 0 = {not_gate(0)} (expected: 1)")
    print(f"  NOT 1 = {not_gate(1)} (expected: 0)")


def test_sr_latch():
    """Test SR Latch"""
    print("\n" + "="*60)
    print("Testing SR Latch")
    print("="*60)

    latch = SRLatch()

    print("\nInitial state:", latch.read())

    print("\nSet operation:")
    latch.set()
    print(f"  Q = {latch.Q}, Q_bar = {latch.Q_bar} (expected: Q=1, Q_bar=0)")

    print("\nReset operation:")
    latch.reset()
    print(f"  Q = {latch.Q}, Q_bar = {latch.Q_bar} (expected: Q=0, Q_bar=1)")

    print("\nHold operation:")
    latch.set()
    print(f"  After set: Q = {latch.Q}")
    latch.hold()
    print(f"  After hold: Q = {latch.Q} (should remain 1)")


def test_6t_sram():
    """Test 6T SRAM Cell"""
    print("\n" + "="*60)
    print("Testing 6T SRAM Cell")
    print("="*60)

    cell = Perceptron6TSRAM(cell_id=0)

    print("\nWrite 1:")
    cell.write(1, word_line=1)
    print(f"  Stored: {cell.read(word_line=1)} (expected: 1)")
    print(f"  Internal: Q={cell.Q}, Q_bar={cell.Q_bar}")

    print("\nWrite 0:")
    cell.write(0, word_line=1)
    print(f"  Stored: {cell.read(word_line=1)} (expected: 0)")
    print(f"  Internal: Q={cell.Q}, Q_bar={cell.Q_bar}")

    print("\nHold state:")
    cell.write(1, word_line=1)
    cell.hold()
    print(f"  After hold: {cell.read(word_line=1)} (should remain 1)")


def test_sram_array():
    """Test SRAM Array"""
    print("\n" + "="*60)
    print("Testing SRAM Array")
    print("="*60)

    array = PerceptronSRAMArray(num_cells=16)

    print("\nInitial pattern:")
    print(f"  {array.read_all()}")

    print("\nWrite pattern '10110010':")
    array.write_pattern('10110010')
    print(f"  {array.read_all()[:8]}")

    print("\nRead specific addresses:")
    for i in range(8):
        print(f"  Cell[{i}] = {array.read(i)}")

    print("\nBit Error Rate:")
    expected = [1, 0, 1, 1, 0, 0, 1, 0] + [0]*8
    ber = array.get_bit_error_rate(expected)
    print(f"  BER = {ber:.2%}")


if __name__ == '__main__':
    # Run all tests
    test_perceptron_gates()
    test_sr_latch()
    test_6t_sram()
    test_sram_array()

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)
