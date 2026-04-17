import numpy as np
from typing import Dict, Tuple, List
import matplotlib.pyplot as plt

class ReliabilityModel:
    """
    NBTI (Negative Bias Temperature Instability) & HCI (Hot Carrier Injection)
    모델을 통합한 반도체 신뢰성 분석
    """

    def __init__(self):
        """NBTI/HCI 모델 파라미터 초기화"""

        # ============ NBTI 파라미터 ============
        # Vth 증가: ΔVth_NBTI = A * t^n * exp(Ea/kT) * (Vgs - Vth)^m
        self.A_nbti = 1e-12  # 프리팩터
        self.n_nbti = 0.25   # 시간 지수 (t^0.25 법칙)
        self.m_nbti = 2.0    # 게이트 오버드라이브 지수
        self.Ea_nbti = 0.12  # 활성화 에너지 (eV)

        # ============ HCI 파라미터 ============
        # Vth 감소: ΔVth_HCI = B * t^q * exp(-Eb/kT) * (I_d/W)^r
        self.A_hci = 1e-15   # 프리팩터
        self.q_hci = 0.33    # 시간 지수 (t^0.33 법칙)
        self.r_hci = 1.5     # 드레인 전류 지수
        self.Eb_hci = 0.20   # 활성화 에너지 (eV)

        # 물리 상수
        self.k_B = 1.38e-23  # Boltzmann constant (J/K)
        self.q_e = 1.6e-19   # 전자 전하 (C)

    def calculate_nbti_vth_shift(self, temperature: float, 
                                 vgs: float, vth: float,
                                 stress_time: float) -> float:
        """
        NBTI Vth 시프트 계산

        Args:
            temperature: 온도 (K)
            vgs: 게이트-소스 전압 (V)
            vth: 임계 전압 (V)
            stress_time: 스트레스 시간 (초)

        Returns:
            ΔVth_NBTI (V)
        """
        # 게이트 오버드라이브
        vgo = vgs - vth

        # 온도 의존성: exp(Ea / kT)
        temp_factor = np.exp(self.Ea_nbti / (self.k_B * temperature / self.q_e))

        # 시간 의존성: t^n
        if stress_time <= 0:
            time_factor = 0
        else:
            time_factor = stress_time ** self.n_nbti

        # Vgs 의존성: Vgo^m
        voltage_factor = max(vgo, 0) ** self.m_nbti

        # 전체 계산
        delta_vth_nbti = self.A_nbti * time_factor * temp_factor * voltage_factor

        return delta_vth_nbti

    def calculate_hci_vth_shift(self, temperature: float,
                                drain_current: float, width: float,
                                stress_time: float) -> float:
        """
        HCI Vth 시프트 계산 (음수 - 감소)

        Args:
            temperature: 온도 (K)
            drain_current: 드레인 전류 (A)
            width: 트랜지스터 폭 (μm)
            stress_time: 스트레스 시간 (초)

        Returns:
            ΔVth_HCI (V, 음수)
        """
        # 정규화된 드레인 전류
        id_normalized = drain_current / (width * 1e-6)  # A/μm로 정규화

        # 온도 의존성: exp(-Eb / kT)
        temp_factor = np.exp(-self.Eb_hci / (self.k_B * temperature / self.q_e))

        # 시간 의존성: t^q
        if stress_time <= 0:
            time_factor = 0
        else:
            time_factor = stress_time ** self.q_hci

        # 드레인 전류 의존성: (Id/W)^r
        current_factor = max(id_normalized, 0) ** self.r_hci

        # 전체 계산 (음수)
        delta_vth_hci = -self.A_hci * time_factor * temp_factor * current_factor

        return delta_vth_hci

    def calculate_total_vth_shift(self, temperature: float,
                                  vgs: float, vds: float,
                                  vth: float, width: float,
                                  stress_time: float) -> Tuple[float, float, float]:
        """
        총 Vth 시프트 계산 (NBTI + HCI)

        Returns:
            (total_vth_shift, nbti_shift, hci_shift)
        """
        # NBTI 계산
        delta_vth_nbti = self.calculate_nbti_vth_shift(temperature, vgs, vth, stress_time)

        # HCI 드레인 전류 추정 (간단한 모델)
        # Id = (W/L) * un * Cox / 2 * (Vgs - Vth)^2 (선형 영역)
        un = 500  # n채널 이동도 (cm^2/Vs)
        cox = 1.7e-3  # 산화막 커패시턴스 (F/m^2)
        l_eff = 1.0  # 유효 채널 길이 (μm)

        vgo = max(vgs - vth, 0)

        if vds > vgo:  # 포화 영역
            drain_current = (width * 1e-6 / (l_eff * 1e-6)) *                            un * cox / 2 * vgo ** 2
        else:  # 선형 영역
            drain_current = (width * 1e-6 / (l_eff * 1e-6)) *                            un * cox * (vgo * vds - vds ** 2 / 2)

        # HCI 계산
        delta_vth_hci = self.calculate_hci_vth_shift(temperature, drain_current, width, stress_time)

        # 총합
        total_shift = delta_vth_nbti + delta_vth_hci

        return total_shift, delta_vth_nbti, delta_vth_hci

    def project_degradation(self, temperature: float, vgs: float, vds: float,
                           vth: float, width: float,
                           max_stress_time: float = 3.15e9) -> Dict:
        """
        장기 열화 예측 (10년 등)

        Args:
            max_stress_time: 최대 스트레스 시간 (초) - 기본값: 10년

        Returns:
            다양한 시간 포인트에서의 열화 결과
        """
        # 시간 포인트 (로그 스케일)
        time_points = np.logspace(0, np.log10(max_stress_time), 50)

        results = {
            'time': [],
            'total_vth_shift': [],
            'nbti_shift': [],
            'hci_shift': [],
            'remaining_margin': []
        }

        # 초기 SNM 마진 가정
        initial_margin = 0.2  # V

        for t in time_points:
            total_shift, nbti_shift, hci_shift = self.calculate_total_vth_shift(
                temperature, vgs, vds, vth, width, t
            )

            results['time'].append(t)
            results['total_vth_shift'].append(total_shift)
            results['nbti_shift'].append(nbti_shift)
            results['hci_shift'].append(hci_shift)
            results['remaining_margin'].append(initial_margin - abs(total_shift))

        return results


class ReliabilityAwareSRAMCell:
    """
    신뢰성 모델을 포함한 고급 SRAM 셀
    """

    def __init__(self, width: float = 1.0, length: float = 1.0):
        self.width = width
        self.length = length
        self.reliability_model = ReliabilityModel()

        # 셀 상태
        self.stored_bit = 0
        self.stress_time = 0  # 누적 스트레스 시간
        self.initial_vth_nmos = 0.4
        self.initial_vth_pmos = -0.4
        self.vth_nmos = self.initial_vth_nmos   # NMOS 임계 전압
        self.vth_pmos = self.initial_vth_pmos  # PMOS 임계 전압

    def stress_cell(self, temperature: float, vgs: float, vds: float,
                   stress_duration: float) -> Dict:
        """
        셀에 스트레스 적용 및 열화 계산

        Args:
            temperature: 온도 (K)
            vgs: 게이트-소스 전압 (V)
            vds: 드레인-소스 전압 (V)
            stress_duration: 스트레스 지속 시간 (초)

        Returns:
            열화 정보
        """
        # 누적 스트레스 시간 업데이트
        self.stress_time += stress_duration

        # NMOS 열화
        nmos_shift, nbti, hci = self.reliability_model.calculate_total_vth_shift(
            temperature, vgs, vds, self.initial_vth_nmos, self.width, self.stress_time
        )

        # PMOS 열화 (반대 극성)
        pmos_shift, nbti_p, hci_p = self.reliability_model.calculate_total_vth_shift(
            temperature, -vgs, -vds, -self.initial_vth_pmos, self.width, self.stress_time
        )

        # 누적 스트레스 시간에 대한 총 열화를 기준 상태에 재적용한다.
        self.vth_nmos = self.initial_vth_nmos + nmos_shift
        self.vth_pmos = self.initial_vth_pmos - pmos_shift  # 반대 극성

        return {
            'nmos_vth_shift': nmos_shift,
            'pmos_vth_shift': pmos_shift,
            'total_vth_shift': nmos_shift + pmos_shift,
            'stress_time': self.stress_time,
            'vth_nmos': self.vth_nmos,
            'vth_pmos': self.vth_pmos
        }

    def calculate_snm_degradation(self, nominal_snm: float = 0.2) -> float:
        """
        열화에 따른 SNM 감소 추정
        """
        # Vth 시프트로 인한 SNM 감소 (선형 근사)
        vth_shift_effect = (self.vth_nmos - 0.4) + abs(self.vth_pmos + 0.4)

        snm_degraded = nominal_snm - 0.05 * vth_shift_effect

        return max(snm_degraded, 0)

    def estimate_lifetime(self, temperature: float, vgs: float = 1.0,
                         vds: float = 1.0, failure_threshold: float = 0.1) -> float:
        """
        기대 수명 추정 (이진 탐색)

        Args:
            failure_threshold: 실패 임계 SNM (V)

        Returns:
            수명 (년)
        """
        # 이진 탐색
        t_min, t_max = 1, 3.15e9  # 1초 ~ 100년

        for _ in range(50):  # 50번 반복으로 충분
            t_mid = (t_min + t_max) / 2

            total_shift, _, _ = self.reliability_model.calculate_total_vth_shift(
                temperature, vgs, vds, self.vth_nmos, self.width, t_mid
            )

            snm = 0.2 - 0.05 * abs(total_shift)

            if snm < failure_threshold:
                t_max = t_mid
            else:
                t_min = t_mid

        # 초 → 년 변환
        lifetime_seconds = (t_min + t_max) / 2
        lifetime_years = lifetime_seconds / (365.25 * 24 * 3600)

        return lifetime_years


class LifetimePredictor:
    """
    배열 단위 수명 예측 및 신뢰성 분석
    """

    def __init__(self, num_cells: int = 32, width: float = 1.0):
        self.num_cells = num_cells
        self.cells = [ReliabilityAwareSRAMCell(width) for _ in range(num_cells)]
        self.reliability_model = ReliabilityModel()

    def predict_array_lifetime(self, temperature: float, 
                               duty_cycle: float = 0.5,
                               failure_rate: float = 0.01) -> Dict:
        """
        배열 단위 수명 예측

        Args:
            duty_cycle: 작동 주기 (0~1)
            failure_rate: 실패 허용 비율 (예: 1%)
        """
        if not 0 < duty_cycle <= 1:
            raise ValueError("duty_cycle must be in the range (0, 1].")
        if not 0 < failure_rate < 1:
            raise ValueError("failure_rate must be in the range (0, 1).")

        lifetimes = []

        for cell in self.cells:
            lifetime = cell.estimate_lifetime(temperature)
            lifetimes.append(lifetime)

        stress_lifetimes = np.array(lifetimes, dtype=float)
        lifetimes = stress_lifetimes / float(duty_cycle)

        # 통계
        mean_lifetime = np.mean(lifetimes)
        std_lifetime = np.std(lifetimes)

        # Weibull 분포로 신뢰도 함수 추정
        # 신뢰도 R(t) = exp(-(t/λ)^k)
        shape_param = 2.0  # Weibull shape parameter
        scale_param = mean_lifetime

        # 신뢰도 90%, 99% 시간 계산
        t_90pct = scale_param * (-np.log(0.9)) ** (1/shape_param)
        t_99pct = scale_param * (-np.log(0.99)) ** (1/shape_param)
        lifetime_at_failure_rate = scale_param * (-np.log(1.0 - failure_rate)) ** (1 / shape_param)

        # 고장률 (FIT: Failures In Time per 10^9 hours)
        failure_rate_fit = 1e9 / (mean_lifetime * 365.25 * 24)

        return {
            'mean_lifetime': mean_lifetime,
            'std_lifetime': std_lifetime,
            'min_lifetime': np.min(lifetimes),
            'max_lifetime': np.max(lifetimes),
            't_90pct': t_90pct,
            't_99pct': t_99pct,
            'lifetime_at_failure_rate': lifetime_at_failure_rate,
            'failure_rate_fit': failure_rate_fit,
            'cell_lifetimes': lifetimes,
            'duty_cycle': float(duty_cycle),
            'accepted_failure_rate': float(failure_rate),
        }

    def analyze_temperature_sensitivity(self, temperatures: List[float] = None) -> Dict:
        """
        온도 민감도 분석
        """
        if temperatures is None:
            temperatures = [280, 310, 340, 360]

        results = {
            'temperatures': temperatures,
            'mean_lifetimes': [],
            't_90pct': [],
            'failure_rate': []
        }

        for temp in temperatures:
            prediction = self.predict_array_lifetime(temp)
            results['mean_lifetimes'].append(prediction['mean_lifetime'])
            results['t_90pct'].append(prediction['t_90pct'])
            results['failure_rate'].append(prediction['failure_rate_fit'])

        return results


# 테스트 코드
if __name__ == "__main__":
    print("NBTI/HCI 신뢰성 분석 테스트")
    print("=" * 70)

    # 1. 기본 Vth 시프트 계산
    print("\n[1] NBTI/HCI Vth 시프트 (10년 스트레스)")
    reliability = ReliabilityModel()

    stress_time = 10 * 365.25 * 24 * 3600  # 10년 (초)
    total_shift, nbti_shift, hci_shift = reliability.calculate_total_vth_shift(
        temperature=330,  # 57°C
        vgs=1.0, vds=1.0, vth=0.4,
        width=1.0, stress_time=stress_time
    )

    print(f"NBTI ΔVth: +{nbti_shift*1000:.2f} mV")
    print(f"HCI ΔVth: {hci_shift*1000:.2f} mV")
    print(f"Total ΔVth: {total_shift*1000:.2f} mV")

    # 2. 수명 예측
    print("\n[2] 셀 단위 수명 예측")
    cell = ReliabilityAwareSRAMCell(width=1.0)
    lifetime = cell.estimate_lifetime(temperature=330)
    print(f"기대 수명: {lifetime:.1f}년")

    # 3. 배열 단위 신뢰성
    print("\n[3] 배열 단위 신뢰성 분석 (32 cells)")
    predictor = LifetimePredictor(num_cells=32)
    array_prediction = predictor.predict_array_lifetime(temperature=330)
    print(f"평균 수명: {array_prediction['mean_lifetime']:.1f}년")
    print(f"표준편차: {array_prediction['std_lifetime']:.1f}년")
    print(f"90% 신뢰도 수명: {array_prediction['t_90pct']:.1f}년")
    print(f"99% 신뢰도 수명: {array_prediction['t_99pct']:.1f}년")
    print(f"고장률: {array_prediction['failure_rate_fit']:.1f} FIT")

    # 4. 온도 민감도
    print("\n[4] 온도 민감도 분석")
    temp_analysis = predictor.analyze_temperature_sensitivity()
    print("\n온도(K)  수명(년)  90%수명(년)  고장률(FIT)")
    print("─" * 50)
    for temp, lifetime, t90, fr in zip(
        temp_analysis['temperatures'],
        temp_analysis['mean_lifetimes'],
        temp_analysis['t_90pct'],
        temp_analysis['failure_rate']
    ):
        print(f"{temp:.0f}      {lifetime:>7.1f}    {t90:>7.1f}       {fr:>7.0f}")
