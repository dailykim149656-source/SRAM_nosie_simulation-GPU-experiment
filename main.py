import numpy as np
import json
from typing import Tuple, Dict, List, Optional

from perceptron_calibration import load_and_apply_perceptron_calibration

class PerceptronGateFunction:
    """
    퍼셉트론 기반의 Gate 함수로 노이즈 가중치를 계산하는 클래스
    온도와 전압 조건에 따라 비선형 노이즈를 생성
    """

    def __init__(
        self,
        input_dim: int = 2,
        hidden_dim: int = 16,
        use_calibration: bool = True,
        calibration_path: Optional[str] = None,
    ):
        """
        Args:
            input_dim: 입력 차원 (온도, 전압)
            hidden_dim: 은닉층 뉴런 개수
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        # 가중치 초기화 (Xavier initialization)
        self.W1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(1.0 / input_dim)
        self.b1 = np.zeros(hidden_dim)

        self.W2 = np.random.randn(hidden_dim, 1) * np.sqrt(1.0 / hidden_dim)
        self.b2 = np.zeros(1)

        # 정규화 파라미터
        self.temp_mean = 310  # 중심 온도 (K)
        self.temp_std = 30
        self.volt_mean = 1.0  # 중심 전압 (V)
        self.volt_std = 0.15
        self.calibration_loaded = False

        if use_calibration:
            self.calibration_loaded = load_and_apply_perceptron_calibration(
                self,
                path=calibration_path,
            )

    def relu(self, x: np.ndarray) -> np.ndarray:
        """ReLU 활성화 함수"""
        return np.maximum(0, x)

    def sigmoid(self, x: np.ndarray) -> np.ndarray:
        """시그모이드 활성화 함수"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def normalize_inputs(self, temperature: float, voltage: float) -> np.ndarray:
        """
        입력 정규화 (평균 0, 표준편차 1)

        Args:
            temperature: 온도 (K)
            voltage: 전압 (V)

        Returns:
            정규화된 입력 배열
        """
        norm_temp = (temperature - self.temp_mean) / self.temp_std
        norm_volt = (voltage - self.volt_mean) / self.volt_std
        return np.array([norm_temp, norm_volt])

    def forward(self, temperature: float, voltage: float) -> float:
        """
        순전파: 온도와 전압으로부터 노이즈 가중치 계산

        Args:
            temperature: 온도 (K)
            voltage: 전압 (V)

        Returns:
            정규화된 노이즈 가중치 (0~1)
        """
        # 입력 정규화
        x = self.normalize_inputs(temperature, voltage)

        # 은닉층
        z1 = np.dot(x, self.W1) + self.b1
        a1 = self.relu(z1)

        # 출력층
        z2 = np.dot(a1, self.W2) + self.b2
        output = self.sigmoid(z2)

        return float(output[0])


class SRAMCell:
    """
    6T SRAM 셀 모델
    온도 및 전압 변화에 따른 노이즈 특성 반영
    """

    def __init__(self, perceptron: PerceptronGateFunction):
        """
        Args:
            perceptron: 노이즈 계산용 퍼셉트론
        """
        self.perceptron = perceptron
        self.stored_bit = 0  # 저장된 비트값

        # SRAM 파라미터
        self.Vdd = 1.0  # 공급 전압 (V)
        self.Vth = 0.4  # 임계값 (V)
        self.noise_floor = 0.05  # 기본 노이즈 레벨

    def calculate_noise_weight(self, temperature: float, voltage: float) -> float:
        """
        퍼셉트론을 통해 온도/전압 의존성 노이즈 가중치 계산

        Args:
            temperature: 온도 (K)
            voltage: 공급 전압 (V)

        Returns:
            노이즈 가중치
        """
        return self.perceptron.forward(temperature, voltage)

    def generate_noise(self, temperature: float, voltage: float, 
                      input_signal: float) -> float:
        """
        노이즈 생성 (온도, 전압, 입력 신호 의존)

        Args:
            temperature: 온도 (K)
            voltage: 공급 전압 (V)
            input_signal: 입력 신호 (0 또는 1)

        Returns:
            생성된 노이즈
        """
        # 퍼셉트론 기반 가중치
        perceptron_weight = self.calculate_noise_weight(temperature, voltage)

        # 온도 의존성: 온도가 높을수록 노이즈 증가
        temp_factor = (temperature - 273.15) / 100.0  # 정규화

        # 전압 의존성: 전압이 낮을수록 노이즈 상대적으로 증가
        volt_factor = (self.Vdd - voltage) / self.Vdd

        # 통합 노이즈
        base_noise = self.noise_floor * (1 + perceptron_weight)
        total_noise = base_noise * (1 + 0.5 * temp_factor) * (1 + 0.3 * volt_factor)

        # 입력 신호의 영향 (신호 변환 시 더 큰 노이즈)
        if input_signal != self.stored_bit:
            total_noise *= 1.5

        return total_noise

    def read_cell(self, temperature: float, voltage: float, 
                  noise_enable: bool = True) -> Tuple[float, float]:
        """
        SRAM 셀 읽기

        Args:
            temperature: 온도 (K)
            voltage: 공급 전압 (V)
            noise_enable: 노이즈 포함 여부

        Returns:
            (출력값, 노이즈량) 튜플
        """
        noise = 0.0
        if noise_enable:
            noise = self.generate_noise(temperature, voltage, self.stored_bit)

        # 출력값 (0.0~1.0 범위로 정규화)
        output = float(self.stored_bit)
        if noise_enable:
            output = np.clip(output + np.random.normal(0, noise), 0, 1)

        return output, noise

    def write_cell(self, bit_value: int, temperature: float, voltage: float) -> bool:
        """
        SRAM 셀 쓰기

        Args:
            bit_value: 쓸 비트값 (0 또는 1)
            temperature: 온도 (K)
            voltage: 공급 전압 (V)

        Returns:
            쓰기 성공 여부
        """
        # 낮은 전압에서 쓰기 실패 가능성
        write_margin = voltage / self.Vdd
        write_noise = self.generate_noise(temperature, voltage, bit_value)

        # 쓰기 성공 확률
        success_prob = write_margin * (1 - write_noise)

        if np.random.random() < success_prob:
            self.stored_bit = bit_value
            return True
        else:
            return False


class SRAMArray:
    """
    SRAM 어레이 (복수 셀)
    """

    def __init__(self, num_cells: int = 64):
        """
        Args:
            num_cells: 셀 개수
        """
        self.num_cells = num_cells
        self.perceptron = PerceptronGateFunction()
        self.cells = [SRAMCell(self.perceptron) for _ in range(num_cells)]

        # 초기화: 임의의 데이터로 초기화
        for i, cell in enumerate(self.cells):
            cell.stored_bit = i % 2

    def simulate(self, temperature: float, voltage: float,
                 input_data: List[int], noise_enable: bool = True) -> Dict:
        """
        SRAM 어레이 시뮬레이션

        Args:
            temperature: 온도 (K)
            voltage: 공급 전압 (V)
            input_data: 입력 데이터 리스트
            noise_enable: 노이즈 포함 여부

        Returns:
            시뮬레이션 결과 딕셔너리
        """
        results = {
            'temperature': temperature,
            'voltage': voltage,
            'input_data': input_data[:self.num_cells],
            'output_data': [],
            'noise_values': [],
            'bit_errors': 0
        }

        for i in range(min(len(input_data), self.num_cells)):
            cell = self.cells[i]

            # 쓰기
            write_success = cell.write_cell(input_data[i], temperature, voltage)

            # 읽기
            output, noise = cell.read_cell(temperature, voltage, noise_enable)

            results['output_data'].append(output)
            results['noise_values'].append(noise)

            # 비트 에러 계산
            if (output > 0.5 and input_data[i] == 0) or (output <= 0.5 and input_data[i] == 1):
                results['bit_errors'] += 1

        results['bit_error_rate'] = results['bit_errors'] / self.num_cells if self.num_cells > 0 else 0

        return results


# 테스트 코드
if __name__ == "__main__":
    # 시뮬레이션 초기화
    sram_array = SRAMArray(num_cells=32)

    # 테스트 데이터
    test_data = [1, 0, 1, 1, 0, 0, 1, 0] * 4

    # 다양한 조건에서 시뮬레이션
    temperatures = [290, 310, 330]  # K
    voltages = [0.9, 1.0, 1.1]      # V

    print("SRAM 시뮬레이션 결과:")
    print("-" * 60)

    for temp in temperatures:
        for volt in voltages:
            result = sram_array.simulate(temp, volt, test_data, noise_enable=True)
            print(f"온도: {temp}K, 전압: {volt}V")
            print(f"  비트 에러율: {result['bit_error_rate']:.4f}")
            print(f"  평균 노이즈: {np.mean(result['noise_values']):.4f}")
            print()
