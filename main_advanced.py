import numpy as np
from scipy import stats
from typing import Tuple, Dict, List, Optional
import json

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
        """입력 정규화"""
        norm_temp = (temperature - self.temp_mean) / self.temp_std
        norm_volt = (voltage - self.volt_mean) / self.volt_std
        return np.array([norm_temp, norm_volt])

    def forward(self, temperature: float, voltage: float) -> float:
        """순전파: 온도와 전압으로부터 노이즈 가중치 계산"""
        x = self.normalize_inputs(temperature, voltage)
        z1 = np.dot(x, self.W1) + self.b1
        a1 = self.relu(z1)
        z2 = np.dot(a1, self.W2) + self.b2
        output = self.sigmoid(z2)
        return float(output[0])


class AdvancedSRAMCell:
    """
    확장된 6T SRAM 셀 모델
    - SNM 분석
    - Variability 모델링 (Pelgrom)
    - Thermal/Shot Noise (Euler-Maruyama)
    - Retention Mode 분석
    """
    def __init__(self, perceptron: PerceptronGateFunction, 
                 width: float = 1.0, length: float = 1.0):
        """
        Args:
            perceptron: 노이즈 계산용 퍼셉트론
            width: 트랜지스터 폭 (μm)
            length: 트랜지스터 길이 (μm)
        """
        self.perceptron = perceptron
        self.stored_bit = 0

        # SRAM 파라미터
        self.Vdd = 1.0  # 공급 전압 (V)
        self.Vth = 0.4  # 임계값 (V)
        self.noise_floor = 0.05

        # 디바이스 파라미터
        self.width = width
        self.length = length

        # Variability 파라미터 (Pelgrom 모델)
        self.A_vth = 5.0  # mV·μm (Vth variability)
        self.sigma_vth = self.A_vth / np.sqrt(width * length)  # Pelgrom 법칙

        # SNM 파라미터
        self.beta_n = 2.0  # NMOS 전류 이득 비
        self.beta_p = 1.0  # PMOS 전류 이득 비

        # Thermal noise 파라미터
        self.k_B = 1.38e-23  # Boltzmann constant
        self.dt = 1e-9  # 시간 스텝 (ns)

    def calculate_noise_weight(self, temperature: float, voltage: float) -> float:
        """퍼셉트론을 통해 온도/전압 의존성 노이즈 가중치 계산"""
        return self.perceptron.forward(temperature, voltage)

    def generate_variability_noise(self) -> float:
        """
        공정 변동성 노이즈 생성 (Monte Carlo)
        Pelgrom 법칙: σ_Vth = A_Vth / sqrt(W*L)
        """
        delta_vth = np.random.normal(0, self.sigma_vth / 1000)  # V 단위로 변환
        return delta_vth

    def calculate_snm(self, voltage: float, delta_vth: float = 0.0) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Static Noise Margin (SNM) 계산
        인버터 버터플라이 곡선에서 최대 정사각형 크기

        Returns:
            (SNM 값, V1 배열, V2 배열)
        """
        # 전압 범위
        v_range = np.linspace(0, voltage, 100)

        # 인버터 1: V1 → V2
        v2_inv1 = voltage * (1 - np.tanh(self.beta_n * (v_range - (self.Vth + delta_vth)) / voltage))

        # 인버터 2: V2 → V1 (역함수)
        v1_inv2 = voltage * (1 - np.tanh(self.beta_p * (v_range - (self.Vth - delta_vth)) / voltage))

        # 버터플라이 곡선의 교점 찾기 (안정 평형점)
        diff = np.abs(v2_inv1 - v1_inv2)
        stable_idx = np.argmin(diff)

        # SNM: 두 곡선 사이의 최대 정사각형 크기
        snm = np.min([
            np.max(v2_inv1[stable_idx:] - v_range[stable_idx:]),
            np.max(v_range[:stable_idx] - v2_inv1[:stable_idx])
        ])

        return abs(snm), v_range, v2_inv1

    def thermal_shot_noise_euler_maruyama(self, temperature: float, 
                                           voltage: float, n_steps: int = 100) -> np.ndarray:
        """
        Euler-Maruyama 방법으로 Thermal/Shot Noise 시뮬레이션
        dV = -α*V*dt + σ*sqrt(dt)*W(t)

        Args:
            temperature: 온도 (K)
            voltage: 공급 전압 (V)
            n_steps: 시뮬레이션 스텝 수

        Returns:
            전압 궤적 배열
        """
        # 노이즈 강도 (온도 의존)
        sigma_thermal = np.sqrt(4 * self.k_B * temperature / (voltage + 0.1))

        # Shot noise 강도
        current = voltage / 1000  # 간단한 전류 모델 (mA)
        sigma_shot = np.sqrt(2 * 1.6e-19 * current * 1e-3)

        # 통합 노이즈 강도
        sigma_total = (sigma_thermal + sigma_shot) * 1e3  # 스케일링

        # 초기 전압
        v_trajectory = np.zeros(n_steps)
        v_trajectory[0] = voltage if self.stored_bit else 0.0

        # Euler-Maruyama 시뮬레이션
        alpha = 0.1  # 감쇠 계수
        for i in range(1, n_steps):
            dW = np.random.normal(0, np.sqrt(self.dt))
            dV = -alpha * v_trajectory[i-1] * self.dt + sigma_total * dW
            v_trajectory[i] = v_trajectory[i-1] + dV
            v_trajectory[i] = np.clip(v_trajectory[i], 0, voltage)

        return v_trajectory

    def retention_mode_analysis(self, voltage: float, temperature: float, 
                                time_steps: int = 1000) -> Dict:
        """
        Retention Mode 분석: 저전압 유지 모드에서 노이즈 누적
        Quasi-potential U(v) = -∫f(v)dv 계산

        Returns:
            분석 결과 딕셔너리
        """
        # 전압 궤적 시뮬레이션
        v_trajectory = self.thermal_shot_noise_euler_maruyama(temperature, voltage, time_steps)

        # Quasi-potential 계산 (간단한 2차 포텐셜)
        v_center = voltage / 2
        U = 0.5 * (v_trajectory - v_center)**2

        # 불안정 평형점 (전압 중심)
        unstable_equilibrium = v_center

        # 안정성 메트릭
        mean_deviation = np.mean(np.abs(v_trajectory - (voltage if self.stored_bit else 0)))
        max_deviation = np.max(np.abs(v_trajectory - (voltage if self.stored_bit else 0)))

        return {
            'voltage_trajectory': v_trajectory,
            'quasi_potential': U,
            'unstable_equilibrium': unstable_equilibrium,
            'mean_deviation': mean_deviation,
            'max_deviation': max_deviation,
            'retention_failure_prob': np.mean(U > 0.1 * voltage)  # 임계값 초과 확률
        }

    def generate_noise(self, temperature: float, voltage: float,
                      input_signal: float, include_variability: bool = True) -> float:
        """
        통합 노이즈 생성
        - 기본 노이즈
        - Variability noise
        - Thermal/Shot noise
        """
        # 퍼셉트론 기반 가중치
        perceptron_weight = self.calculate_noise_weight(temperature, voltage)

        # 온도 의존성
        temp_factor = (temperature - 273.15) / 100.0

        # 전압 의존성
        volt_factor = (self.Vdd - voltage) / self.Vdd

        # 기본 노이즈
        base_noise = self.noise_floor * (1 + perceptron_weight)
        total_noise = base_noise * (1 + 0.5 * temp_factor) * (1 + 0.3 * volt_factor)

        # Variability noise 추가
        if include_variability:
            var_noise = abs(self.generate_variability_noise())
            total_noise += var_noise

        # 신호 변환 시 증폭
        if input_signal != self.stored_bit:
            total_noise *= 1.5

        return total_noise

    def read_cell(self, temperature: float, voltage: float,
                 noise_enable: bool = True, variability_enable: bool = True) -> Tuple[float, float, Dict]:
        """
        SRAM 셀 읽기 (확장 버전)

        Returns:
            (출력값, 노이즈량, 추가 분석 결과)
        """
        noise = 0.0
        analysis = {}

        if noise_enable:
            noise = self.generate_noise(temperature, voltage, self.stored_bit, variability_enable)

        # 출력값
        output = float(self.stored_bit)
        if noise_enable:
            output = np.clip(output + np.random.normal(0, noise), 0, 1)

        # SNM 분석
        if variability_enable:
            delta_vth = self.generate_variability_noise()
            snm, _, _ = self.calculate_snm(voltage, delta_vth)
            analysis['snm'] = snm
            analysis['delta_vth'] = delta_vth

        return output, noise, analysis

    def write_cell(self, bit_value: int, temperature: float, voltage: float) -> bool:
        """SRAM 셀 쓰기"""
        write_margin = voltage / self.Vdd
        write_noise = self.generate_noise(temperature, voltage, bit_value)
        success_prob = write_margin * (1 - write_noise)

        if np.random.random() < success_prob:
            self.stored_bit = bit_value
            return True
        return False


class AdvancedSRAMArray:
    """
    확장된 SRAM 어레이
    - Monte Carlo Variability
    - SNM 분석
    - Retention Mode
    - Process Corner (FF/TT/SS)
    """
    def __init__(self, num_cells: int = 64, width: float = 1.0, length: float = 1.0):
        self.num_cells = num_cells
        self.perceptron = PerceptronGateFunction()
        self.cells = [AdvancedSRAMCell(self.perceptron, width, length) for _ in range(num_cells)]

        # 초기화
        for i, cell in enumerate(self.cells):
            cell.stored_bit = i % 2

    def simulate(self, temperature: float, voltage: float,
                input_data: List[int], noise_enable: bool = True,
                variability_enable: bool = True, 
                monte_carlo_runs: int = 1) -> Dict:
        """
        확장된 SRAM 어레이 시뮬레이션

        Args:
            monte_carlo_runs: Monte Carlo 시뮬레이션 반복 횟수
        """
        results = {
            'temperature': temperature,
            'voltage': voltage,
            'input_data': input_data[:self.num_cells],
            'output_data': [],
            'noise_values': [],
            'snm_values': [],
            'bit_errors': 0,
            'monte_carlo_ber': [],
            'retention_analysis': []
        }
        processed_cells = min(len(input_data), self.num_cells)

        # Monte Carlo 시뮬레이션
        for run in range(monte_carlo_runs):
            run_errors = 0
            run_outputs = []

            for i in range(processed_cells):
                cell = self.cells[i]

                # 쓰기
                write_success = cell.write_cell(input_data[i], temperature, voltage)

                # 읽기
                output, noise, analysis = cell.read_cell(temperature, voltage, 
                                                        noise_enable, variability_enable)

                if run == 0:  # 첫 번째 run만 저장
                    results['output_data'].append(output)
                    results['noise_values'].append(noise)
                    if 'snm' in analysis:
                        results['snm_values'].append(analysis['snm'])

                run_outputs.append(output)

                # 비트 에러 계산
                if (output > 0.5 and input_data[i] == 0) or \
                   (output <= 0.5 and input_data[i] == 1):
                    run_errors += 1

            results['monte_carlo_ber'].append(run_errors / processed_cells if processed_cells > 0 else 0.0)

        results['bit_errors'] = int(np.mean(results['monte_carlo_ber']) * processed_cells)
        results['bit_error_rate'] = np.mean(results['monte_carlo_ber'])
        results['ber_std'] = np.std(results['monte_carlo_ber'])
        results['ber_confidence_95'] = 1.96 * results['ber_std'] / np.sqrt(monte_carlo_runs)

        return results

    def process_corner_analysis(self, temperature: float, voltage: float,
                                input_data: List[int]) -> Dict:
        """
        Process Corner 분석 (FF/TT/SS)
        """
        corners = {
            'FF': (1.1, 0.9),  # Fast NMOS, Fast PMOS (높은 전압, 낮은 온도)
            'TT': (1.0, 1.0),  # Typical
            'SS': (0.9, 1.1)   # Slow NMOS, Slow PMOS (낮은 전압, 높은 온도)
        }

        corner_results = {}
        for corner_name, (volt_factor, temp_factor) in corners.items():
            corner_voltage = voltage * volt_factor
            corner_temperature = temperature * temp_factor

            result = self.simulate(corner_temperature, corner_voltage, input_data,
                                 monte_carlo_runs=10)
            corner_results[corner_name] = {
                'ber': result['bit_error_rate'],
                'ber_std': result['ber_std'],
                'voltage': corner_voltage,
                'temperature': corner_temperature
            }

        return corner_results


# 테스트 코드
if __name__ == "__main__":
    print("고급 SRAM 시뮬레이터 테스트")
    print("=" * 70)

    # 시뮬레이션 초기화
    sram_array = AdvancedSRAMArray(num_cells=32, width=1.0, length=1.0)

    # 테스트 데이터
    test_data = [1, 0, 1, 1, 0, 0, 1, 0] * 4

    # 기본 시뮬레이션
    print("\n[1] 기본 시뮬레이션 (Monte Carlo 100회)")
    result = sram_array.simulate(310, 1.0, test_data, monte_carlo_runs=100)
    print(f"BER: {result['bit_error_rate']:.4f} ± {result['ber_confidence_95']:.4f}")
    print(f"평균 SNM: {np.mean(result['snm_values']):.4f} V")

    # Process Corner 분석
    print("\n[2] Process Corner 분석")
    corner_results = sram_array.process_corner_analysis(310, 1.0, test_data)
    for corner, data in corner_results.items():
        print(f"  {corner}: BER={data['ber']:.4f}, V={data['voltage']:.2f}V, T={data['temperature']:.0f}K")
