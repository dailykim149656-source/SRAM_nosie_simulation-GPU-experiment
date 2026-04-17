import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from main_advanced import AdvancedSRAMArray, PerceptronGateFunction, AdvancedSRAMCell
from reliability_model import ReliabilityModel
from lifetime_service import (
    DEFAULT_DUTY_CYCLE,
    DEFAULT_FAILURE_RATE,
    predict_lifetime_native_first,
    summarize_lifetime_runtime,
)
import matplotlib

# ============================================================================
# 한글 폰트 설정
# ============================================================================
def set_korean_font():
    """한글 폰트 자동 감지 및 설정"""
    font_candidates = [
        'Malgun Gothic',
        'Noto Sans CJK KR',
        'NanumGothic',
        'DejaVu Sans'
    ]
    try:
        font_list = [f.name for f in matplotlib.font_manager.fontManager.ttflist]
        for font in font_candidates:
            if font in font_list:
                plt.rcParams['font.sans-serif'] = font
                plt.rcParams['axes.unicode_minus'] = False
                return font
    except:
        pass
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()

# ============================================================================
# Streamlit 페이지 설정
# ============================================================================
st.set_page_config(
    page_title="🔌 SRAM 시뮬레이터 (완전통합)",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔌 고급 SRAM 노이즈 & 신뢰성 통합 시뮬레이터")
st.markdown("""
**퍼셉트론 기반 노이즈 모델 + SNM/Variability/Thermal/Retention/신뢰성 분석**
""")

# ============================================================================
# 사이드바 설정
# ============================================================================
with st.sidebar:
    st.header("⚙️ 시뮬레이션 파라미터")

    # 시뮬레이션 종류 선택
    sim_type = st.radio("분석 유형 선택", [
        "📈 기본 노이즈 시뮬레이션",
        "📊 SNM 분석",
        "🎲 Variability 분석",
        "🌊 Thermal/Shot Noise",
        "⏱️ Retention Mode",
        "🔄 Process Corner",
        "🔥 신뢰성 분석 (NBTI/HCI)"
    ])

    st.divider()

    # 기본 파라미터
    st.subheader("기본 조건")
    temperature = st.slider("온도 (K)", 260, 360, 310, 5)
    voltage = st.slider("공급 전압 (V)", 0.8, 1.2, 1.0, 0.05)
    num_cells = st.slider("SRAM 셀 개수", 8, 128, 32, 8)

    st.divider()

    # 고급 옵션
    st.subheader("🔬 고급 옵션")
    variability_enable = st.checkbox("Variability 모델링", value=True)
    monte_carlo_runs = st.slider("Monte Carlo 반복", 1, 100, 10, 10)
    process_corner = st.checkbox("Process Corner (FF/TT/SS)", value=False)

    st.divider()

    # 디바이스 파라미터
    st.subheader("📐 트랜지스터 파라미터")
    width = st.number_input("Width (μm)", 0.1, 5.0, 1.0, 0.1)
    length = st.number_input("Length (μm)", 0.1, 5.0, 1.0, 0.1)

    st.divider()

    # 입력 데이터
    st.subheader("📊 입력 데이터")
    data_type = st.radio("데이터 타입", ["랜덤", "올 0", "올 1", "체크보드"])

    if data_type == "랜덤":
        input_data = np.random.randint(0, 2, num_cells).tolist()
    elif data_type == "올 0":
        input_data = [0] * num_cells
    elif data_type == "올 1":
        input_data = [1] * num_cells
    else:
        input_data = [(i % 2) for i in range(num_cells)]

# ============================================================================
# 시뮬레이션 실행
# ============================================================================

# 기본 SRAM 배열 초기화
sram_array = AdvancedSRAMArray(num_cells=num_cells, width=width, length=length)

# 신뢰성 모델 초기화
reliability_model = ReliabilityModel()

# ============================================================================
# TAB 1: 기본 노이즈 시뮬레이션
# ============================================================================
if sim_type == "📈 기본 노이즈 시뮬레이션":
    st.header("📈 기본 노이즈 시뮬레이션")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("온도", f"{temperature} K", f"{temperature - 273.15:.0f}°C")
    with col2:
        st.metric("전압", f"{voltage:.2f} V")
    with col3:
        st.metric("셀 개수", num_cells)
    with col4:
        st.metric("Variability", "활성" if variability_enable else "비활성")

    st.divider()

    # 시뮬레이션 실행
    with st.spinner('시뮬레이션 실행 중...'):
        result = sram_array.simulate(temperature, voltage, input_data, 
                                    variability_enable=variability_enable,
                                    monte_carlo_runs=monte_carlo_runs)

    col1, col2 = st.columns(2)

    with col1:
        # 3D 노이즈 표면
        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection='3d')

        temps = np.linspace(280, 340, 30)
        volts = np.linspace(0.8, 1.2, 30)
        temps_grid, volts_grid = np.meshgrid(temps, volts)

        noise_surface = np.zeros_like(temps_grid)
        for i, t in enumerate(temps):
            for j, v in enumerate(volts):
                perceptron = sram_array.perceptron
                noise_surface[j, i] = perceptron.forward(t, v) * 100

        surf = ax.plot_surface(temps_grid, volts_grid, noise_surface, cmap='viridis', alpha=0.8)
        ax.set_xlabel('온도 (K)')
        ax.set_ylabel('전압 (V)')
        ax.set_zlabel('노이즈 (mV)')
        ax.set_title('3D 노이즈 표면 (퍼셉트론 기반)')
        fig.colorbar(surf, ax=ax, shrink=0.5)

        st.pyplot(fig)
        plt.close()

    with col2:
        # BER 히트맵
        fig, ax = plt.subplots(figsize=(10, 7))

        temps_hm = np.linspace(280, 340, 20)
        volts_hm = np.linspace(0.8, 1.2, 20)
        ber_map = np.zeros((len(volts_hm), len(temps_hm)))

        for i, t in enumerate(temps_hm):
            for j, v in enumerate(volts_hm):
                result_tmp = sram_array.simulate(t, v, input_data, monte_carlo_runs=5)
                ber_map[j, i] = result_tmp['bit_error_rate'] * 100

        im = ax.imshow(ber_map, extent=[temps_hm[0], temps_hm[-1], volts_hm[0], volts_hm[-1]],
                       aspect='auto', cmap='RdYlGn_r', origin='lower')
        ax.set_xlabel('온도 (K)')
        ax.set_ylabel('전압 (V)')
        ax.set_title('BER 히트맵 (온도 x 전압)')
        plt.colorbar(im, ax=ax, label='BER (%)')

        st.pyplot(fig)
        plt.close()

    # 결과 메트릭
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("BER", f"{result['bit_error_rate']*100:.2f}%")
    with col2:
        st.metric("평균 노이즈", f"{np.mean(result['noise_values'])*1000:.2f} mV")
    with col3:
        st.metric("비트 에러", result['bit_errors'])
    with col4:
        st.metric("신뢰도", f"{(1-result['bit_error_rate'])*100:.1f}%")

# ============================================================================
# TAB 2: SNM 분석
# ============================================================================
elif sim_type == "📊 SNM 분석":
    st.header("📊 Static Noise Margin (SNM) 분석")

    with st.spinner('SNM 분석 중...'):
        result = sram_array.simulate(temperature, voltage, input_data, 
                                    variability_enable=variability_enable,
                                    monte_carlo_runs=monte_carlo_runs)

    if result['snm_values']:
        col1, col2 = st.columns(2)

        with col1:
            # SNM 히스토그램
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(result['snm_values'], bins=20, color='skyblue', edgecolor='black', alpha=0.7)
            ax.axvline(np.mean(result['snm_values']), color='red', linestyle='--', 
                      linewidth=2, label=f'평균: {np.mean(result["snm_values"]):.4f}V')
            ax.set_xlabel('SNM (V)')
            ax.set_ylabel('빈도')
            ax.set_title('SNM 분포')
            ax.legend()
            ax.grid(alpha=0.3)

            st.pyplot(fig)
            plt.close()

        with col2:
            # 버터플라이 곡선
            cell = sram_array.cells[0]
            snm, v_range, v2_inv1 = cell.calculate_snm(voltage)

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(v_range, v2_inv1, 'b-', linewidth=2, label='인버터 1')
            ax.plot(v2_inv1, v_range, 'r-', linewidth=2, label='인버터 2')
            ax.plot([0, voltage], [0, voltage], 'k--', alpha=0.5)
            ax.set_xlabel('V1 (V)')
            ax.set_ylabel('V2 (V)')
            ax.set_title(f'인버터 버터플라이 곡선 (SNM={snm:.4f}V)')
            ax.legend()
            ax.grid(alpha=0.3)
            ax.set_xlim(0, voltage)
            ax.set_ylim(0, voltage)

            st.pyplot(fig)
            plt.close()

        st.info(f"**평균 SNM: {np.mean(result['snm_values']):.4f} V**")
    else:
        st.warning("Variability 모델링을 활성화하세요.")

# ============================================================================
# TAB 3: Variability 분석
# ============================================================================
elif sim_type == "🎲 Variability 분석":
    st.header("🎲 Monte Carlo Variability 분석")

    with st.spinner('Variability 분석 중...'):
        result = sram_array.simulate(temperature, voltage, input_data, 
                                    variability_enable=True,
                                    monte_carlo_runs=monte_carlo_runs)

    col1, col2 = st.columns(2)

    with col1:
        # BER 분포
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(np.array(result['monte_carlo_ber'])*100, bins=20, 
               color='coral', edgecolor='black', alpha=0.7)
        ax.axvline(result['bit_error_rate']*100, color='red', linestyle='--', 
                  linewidth=2, label=f'평균 BER: {result["bit_error_rate"]*100:.2f}%')
        ax.set_xlabel('BER (%)')
        ax.set_ylabel('빈도')
        ax.set_title(f'BER 분포 (Monte Carlo {monte_carlo_runs}회)')
        ax.legend()
        ax.grid(alpha=0.3)

        st.pyplot(fig)
        plt.close()

    with col2:
        # Pelgrom 곡선
        areas = np.logspace(-1, 1, 50)
        sigma_vth = 5.0 / np.sqrt(areas)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(areas, sigma_vth, 'b-', linewidth=2)
        ax.scatter([width*length], [5.0/np.sqrt(width*length)], 
                  color='red', s=200, zorder=5, label=f'현재: {width*length:.2f}μm²')
        ax.set_xscale('log')
        ax.set_xlabel('트랜지스터 면적 (μm²)')
        ax.set_ylabel('σ_Vth (mV)')
        ax.set_title('Pelgrom 법칙')
        ax.legend()
        ax.grid(alpha=0.3, which='both')

        st.pyplot(fig)
        plt.close()

    # 메트릭
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("평균 BER", f"{result['bit_error_rate']*100:.2f}%")
    with col2:
        st.metric("σ_Vth", f"{5.0/np.sqrt(width*length):.2f} mV")
    with col3:
        st.metric("신뢰구간 (95%)", f"±{result['ber_confidence_95']*100:.2f}%")
    with col4:
        st.metric("표준편차", f"{result['ber_std']*100:.3f}%")

# ============================================================================
# TAB 4: Thermal/Shot Noise
# ============================================================================
elif sim_type == "🌊 Thermal/Shot Noise":
    st.header("🌊 Thermal/Shot Noise (Euler-Maruyama)")

    cell = sram_array.cells[0]
    v_trajectory = cell.thermal_shot_noise_euler_maruyama(temperature, voltage, n_steps=500)

    col1, col2 = st.columns(2)

    with col1:
        # 전압 궤적
        fig, ax = plt.subplots(figsize=(10, 6))
        time_axis = np.arange(len(v_trajectory)) * cell.dt * 1e9
        ax.plot(time_axis, v_trajectory, 'b-', linewidth=1, alpha=0.8)
        ax.axhline(voltage if cell.stored_bit else 0, color='red', 
                  linestyle='--', label='목표 전압')
        ax.set_xlabel('시간 (ns)')
        ax.set_ylabel('전압 (V)')
        ax.set_title('Thermal/Shot Noise 궤적')
        ax.legend()
        ax.grid(alpha=0.3)

        st.pyplot(fig)
        plt.close()

    with col2:
        # 전압 분포
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(v_trajectory, bins=30, color='green', edgecolor='black', alpha=0.7)
        ax.axvline(np.mean(v_trajectory), color='red', linestyle='--', 
                  linewidth=2, label=f'평균: {np.mean(v_trajectory):.4f}V')
        ax.set_xlabel('전압 (V)')
        ax.set_ylabel('빈도')
        ax.set_title('전압 분포')
        ax.legend()
        ax.grid(alpha=0.3)

        st.pyplot(fig)
        plt.close()

    # 메트릭
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("평균 전압", f"{np.mean(v_trajectory):.6f} V")
    with col2:
        st.metric("표준편차", f"{np.std(v_trajectory):.6f} V")
    with col3:
        st.metric("최대값", f"{np.max(v_trajectory):.6f} V")
    with col4:
        st.metric("최소값", f"{np.min(v_trajectory):.6f} V")

# ============================================================================
# TAB 5: Retention Mode
# ============================================================================
elif sim_type == "⏱️ Retention Mode":
    st.header("⏱️ Retention Mode 분석")

    cell = sram_array.cells[0]
    retention_result = cell.retention_mode_analysis(voltage, temperature, time_steps=1000)

    col1, col2 = st.columns(2)

    with col1:
        # 전압 궤적
        fig, ax = plt.subplots(figsize=(10, 6))
        time_axis = np.arange(len(retention_result['voltage_trajectory'])) * cell.dt * 1e6
        ax.plot(time_axis, retention_result['voltage_trajectory'], 'b-', linewidth=1, alpha=0.8)
        ax.axhline(retention_result['unstable_equilibrium'], color='red', 
                  linestyle='--', label=f'불안정점: {retention_result["unstable_equilibrium"]:.3f}V')
        ax.set_xlabel('시간 (μs)')
        ax.set_ylabel('전압 (V)')
        ax.set_title('Retention Mode 궤적')
        ax.legend()
        ax.grid(alpha=0.3)

        st.pyplot(fig)
        plt.close()

    with col2:
        # Quasi-potential
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(retention_result['voltage_trajectory'], retention_result['quasi_potential'], 
               'g-', linewidth=2)
        ax.set_xlabel('전압 (V)')
        ax.set_ylabel('Quasi-potential')
        ax.set_title('Quasi-potential 분포')
        ax.grid(alpha=0.3)

        st.pyplot(fig)
        plt.close()

    # 메트릭
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("평균 편차", f"{retention_result['mean_deviation']:.6f} V")
    with col2:
        st.metric("최대 편차", f"{retention_result['max_deviation']:.6f} V")
    with col3:
        st.metric("실패 확률", f"{retention_result['retention_failure_prob']*100:.2f}%")

# ============================================================================
# TAB 6: Process Corner
# ============================================================================
elif sim_type == "🔄 Process Corner":
    st.header("🔄 Process Corner 분석 (FF/TT/SS)")

    with st.spinner('Process Corner 분석 중...'):
        corner_results = sram_array.process_corner_analysis(temperature, voltage, input_data)

    corners = list(corner_results.keys())
    bers = [corner_results[c]['ber']*100 for c in corners]
    ber_stds = [corner_results[c]['ber_std']*100 for c in corners]

    col1, col2 = st.columns(2)

    with col1:
        # BER 비교
        fig, ax = plt.subplots(figsize=(10, 6))
        x_pos = np.arange(len(corners))
        bars = ax.bar(x_pos, bers, yerr=ber_stds, capsize=5, 
                     color=['skyblue', 'green', 'coral'], edgecolor='black', alpha=0.7)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(corners)
        ax.set_ylabel('BER (%)')
        ax.set_title('Process Corner별 BER')
        ax.grid(axis='y', alpha=0.3)

        for bar, ber in zip(bars, bers):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{ber:.2f}%', ha='center', va='bottom')

        st.pyplot(fig)
        plt.close()

    with col2:
        # Corner 조건 테이블
        st.markdown("#### Corner 조건")
        corner_data = []
        for corner in corners:
            corner_data.append({
                "Corner": corner,
                "전압 (V)": f"{corner_results[corner]['voltage']:.2f}",
                "온도 (K)": f"{corner_results[corner]['temperature']:.0f}",
                "BER (%)": f"{corner_results[corner]['ber']*100:.2f}"
            })
        st.dataframe(corner_data, use_container_width=True, hide_index=True)

# ============================================================================
# TAB 7: 신뢰성 분석 (NBTI/HCI)
# ============================================================================
elif sim_type == "🔥 신뢰성 분석 (NBTI/HCI)":
    st.header("🔥 NBTI/HCI 신뢰성 분석")

    ctrl_col1, ctrl_col2 = st.columns(2)
    with ctrl_col1:
        duty_cycle = st.slider(
            "Duty Cycle",
            min_value=0.05,
            max_value=1.0,
            value=DEFAULT_DUTY_CYCLE,
            step=0.05,
        )
    with ctrl_col2:
        failure_rate = st.number_input(
            "허용 Failure Rate",
            min_value=0.001,
            max_value=0.200,
            value=DEFAULT_FAILURE_RATE,
            step=0.001,
            format="%.3f",
        )

    target_survival_percent = (1.0 - failure_rate) * 100.0

    reliability_analysis_type = st.selectbox("신뢰성 분석 종류", [
        "📈 장기 열화 예측",
        "⏱️ 수명 분석",
        "🌡️ 온도 민감도",
        "🔧 공정 최적화"
    ])

    # ====== 장기 열화 예측 ======
    if reliability_analysis_type == "📈 장기 열화 예측":
        st.subheader("📈 장기 열화 예측 (NBTI + HCI)")

        time_range = np.logspace(0, 10, 100)
        nbti_shifts = []
        hci_shifts = []
        total_shifts = []

        for t in time_range:
            total, nbti, hci = reliability_model.calculate_total_vth_shift(
                temperature, voltage, voltage, 0.4, width, t
            )
            nbti_shifts.append(nbti * 1000)
            hci_shifts.append(hci * 1000)
            total_shifts.append(total * 1000)

        time_years = time_range / (365.25 * 24 * 3600)

        col1, col2 = st.columns(2)

        with col1:
            # Vth 시프트 곡선
            fig, ax = plt.subplots(figsize=(11, 6))
            ax.semilogx(time_years, nbti_shifts, 'b-', linewidth=2.5, label='NBTI (+Vth)', marker='o', markersize=4)
            ax.semilogx(time_years, hci_shifts, 'r-', linewidth=2.5, label='HCI (-Vth)', marker='s', markersize=4)
            ax.semilogx(time_years, total_shifts, 'g--', linewidth=2.5, label='합계', marker='^', markersize=4)
            ax.axhline(0, color='black', linestyle='-', alpha=0.3)
            ax.set_xlabel('시간 (년)')
            ax.set_ylabel('Vth 시프트 (mV)')
            ax.set_title(f'NBTI/HCI 열화 (T={temperature}K, V={voltage}V)')
            ax.legend()
            ax.grid(alpha=0.3, which='both')

            st.pyplot(fig)
            plt.close()

        with col2:
            # SNM 마진 감소
            nominal_snm = 0.2
            snm_margin = nominal_snm - np.abs(total_shifts) / 1000
            snm_margin = np.maximum(snm_margin, 0)

            fig, ax = plt.subplots(figsize=(11, 6))
            ax.semilogx(time_years, snm_margin * 1000, 'purple', linewidth=2.5, marker='o', markersize=4)
            ax.fill_between(time_years, snm_margin * 1000, alpha=0.2, color='purple')
            ax.axhline(50, color='orange', linestyle='--', linewidth=2, label='경고 (50 mV)')
            ax.axhline(30, color='red', linestyle='--', linewidth=2, label='실패 (30 mV)')
            ax.set_xlabel('시간 (년)')
            ax.set_ylabel('SNM 마진 (mV)')
            ax.set_title(f'SNM 마진 감소 (초기: {nominal_snm*1000:.0f} mV)')
            ax.legend()
            ax.grid(alpha=0.3, which='both')
            ax.set_ylim(bottom=0)

            st.pyplot(fig)
            plt.close()

        # 통계
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("NBTI ΔVth (10년)", f"+{nbti_shifts[-1]:.2f} mV")
        with col2:
            st.metric("HCI ΔVth (10년)", f"{hci_shifts[-1]:.2f} mV")
        with col3:
            st.metric("총 열화 (10년)", f"{total_shifts[-1]:.2f} mV")
        with col4:
            remaining_snm = nominal_snm - np.abs(total_shifts[-1]) / 1000
            st.metric("남은 SNM", f"{remaining_snm*1000:.1f} mV")

    # ====== 수명 분석 ======
    elif reliability_analysis_type == "⏱️ 수명 분석":
        st.subheader("⏱️ 배열 단위 수명 분석")

        with st.spinner('수명 분석 중...'):
            array_pred = predict_lifetime_native_first(
                temperature=temperature,
                width=width,
                num_cells=num_cells,
                duty_cycle=duty_cycle,
                failure_rate=failure_rate,
                vgs=voltage,
                vds=voltage,
                vth=0.4,
                compute_mode="auto",
                latency_mode="interactive",
            )

        st.caption(f"실행 소스: {summarize_lifetime_runtime(array_pred)}")
        if array_pred.get("_exec", {}).get("fallback"):
            st.info(f"Fallback 실행: {array_pred.get('fallback_notice', 'native 경로를 사용할 수 없어 Python으로 실행했습니다.')}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 기본 정보")
            st.write(f"**목표 수명 ({target_survival_percent:.1f}% 생존)**: {array_pred['lifetime_at_failure_rate']:.2f}년")
            st.write(f"**평균 수명**: {array_pred['mean_lifetime']:.2f}년")
            st.write(f"**표준편차**: {array_pred['std_lifetime']:.2f}년")
            st.write(f"**최소 수명**: {array_pred['min_lifetime']:.2f}년")
            st.write(f"**최대 수명**: {array_pred['max_lifetime']:.2f}년")
            st.write(f"**90% 신뢰도 참조**: {array_pred['t_90pct']:.2f}년")
            st.write(f"**99% 신뢰도 참조**: {array_pred['t_99pct']:.2f}년")
            st.write(f"**고장률**: {array_pred['failure_rate_fit']:.0f} FIT")

        with col2:
            st.markdown("#### 수명 해석")
            if array_pred['lifetime_at_failure_rate'] > 10:
                st.success("✅ 우수한 수명 (10년 이상)")
            elif array_pred['lifetime_at_failure_rate'] > 5:
                st.info("ℹ️ 적절한 수명 (5-10년)")
            else:
                st.warning("⚠️ 낮은 수명 (5년 이하)")

        # 수명 분포
        col1, col2 = st.columns(2)

        with col1:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(array_pred['cell_lifetimes'], bins=15, color='skyblue', 
                   edgecolor='black', alpha=0.7)
            ax.axvline(np.mean(array_pred['cell_lifetimes']), color='red', 
                       linestyle='--', linewidth=2, label=f"평균: {np.mean(array_pred['cell_lifetimes']):.2f}년")
            ax.axvline(
                array_pred['lifetime_at_failure_rate'],
                color='green',
                linestyle='-.',
                linewidth=2,
                label=f"목표: {array_pred['lifetime_at_failure_rate']:.2f}년",
            )
            ax.set_xlabel('수명 (년)')
            ax.set_ylabel('셀 개수')
            ax.set_title(f'{num_cells}개 셀의 수명 분포')
            ax.legend()
            ax.grid(alpha=0.3)

            st.pyplot(fig)
            plt.close()

        with col2:
            # 신뢰도 함수
            t_range = np.linspace(0, 2*array_pred['mean_lifetime'], 100)
            shape = 2.0
            scale = array_pred['mean_lifetime']
            reliability_func = np.exp(-(t_range/scale)**shape)

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(t_range, reliability_func * 100, 'b-', linewidth=2.5)
            ax.axhline(90, color='green', linestyle='--', alpha=0.7, label='90% 신뢰도')
            ax.axhline(99, color='orange', linestyle='--', alpha=0.7, label='99% 신뢰도')
            ax.axhline(
                target_survival_percent,
                color='purple',
                linestyle='-.',
                alpha=0.8,
                label=f'목표 생존율 {target_survival_percent:.1f}%',
            )
            ax.axvline(
                array_pred['lifetime_at_failure_rate'],
                color='purple',
                linestyle='-.',
                alpha=0.8,
            )
            ax.fill_between(t_range, reliability_func * 100, alpha=0.2, color='blue')
            ax.set_xlabel('시간 (년)')
            ax.set_ylabel('신뢰도 (%)')
            ax.set_title('배열 신뢰도 함수 (Weibull)')
            ax.legend()
            ax.grid(alpha=0.3)
            ax.set_ylim(0, 105)

            st.pyplot(fig)
            plt.close()

    # ====== 온도 민감도 ======
    elif reliability_analysis_type == "🌡️ 온도 민감도":
        st.subheader("🌡️ 온도 민감도 분석")

        temps = [280, 300, 310, 330, 350, 360]

        with st.spinner('온도 분석 중...'):
            temp_results = [
                predict_lifetime_native_first(
                    temperature=temp_point,
                    width=width,
                    num_cells=num_cells,
                    duty_cycle=duty_cycle,
                    failure_rate=failure_rate,
                    vgs=voltage,
                    vds=voltage,
                    vth=0.4,
                    compute_mode="auto",
                    latency_mode="interactive",
                )
                for temp_point in temps
            ]
            temp_analysis = {
                'temperatures': temps,
                'mean_lifetimes': [float(r['mean_lifetime']) for r in temp_results],
                'target_lifetimes': [float(r['lifetime_at_failure_rate']) for r in temp_results],
                't_90pct': [float(r['t_90pct']) for r in temp_results],
                't_99pct': [float(r['t_99pct']) for r in temp_results],
                'failure_rate': [float(r['failure_rate_fit']) for r in temp_results],
                'runtime_summary': [summarize_lifetime_runtime(r) for r in temp_results],
                'fallback_used': any(bool(r.get('_exec', {}).get('fallback')) for r in temp_results),
            }

        st.caption(f"실행 소스 예시: {temp_analysis['runtime_summary'][0]}")
        if temp_analysis['fallback_used']:
            st.info("온도 민감도 분석 중 일부 또는 전체 포인트가 Python fallback으로 실행되었습니다.")

        col1, col2 = st.columns(2)

        with col1:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(temps, temp_analysis['target_lifetimes'], 'b-o', linewidth=2.5, markersize=8, label='목표 수명')
            ax.fill_between(temps, temp_analysis['t_99pct'], alpha=0.2, color='blue', label='99% 신뢰도 참조')
            ax.axhline(10, color='green', linestyle='--', linewidth=2, label='10년 목표')
            ax.set_xlabel('온도 (K)')
            ax.set_ylabel('수명 (년)')
            ax.set_title(f'온도에 따른 목표 수명 ({target_survival_percent:.1f}% 생존)')
            ax.legend()
            ax.grid(alpha=0.3)

            st.pyplot(fig)
            plt.close()

        with col2:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.semilogy(temps, temp_analysis['failure_rate'], 'r-s', linewidth=2.5, markersize=8)
            ax.axhline(1000, color='orange', linestyle='--', linewidth=2, label='1000 FIT')
            ax.set_xlabel('온도 (K)')
            ax.set_ylabel('고장률 (FIT)')
            ax.set_title('온도에 따른 고장률')
            ax.legend()
            ax.grid(alpha=0.3, which='both')

            st.pyplot(fig)
            plt.close()

        # 테이블
        st.markdown("#### 온도별 신뢰성")
        table_data = []
        for t, lifetime, mean_lifetime, t90, fr in zip(temps, temp_analysis['target_lifetimes'],
                                        temp_analysis['mean_lifetimes'],
                                        temp_analysis['t_90pct'],
                                        temp_analysis['failure_rate']):
            table_data.append({
                '온도 (K)': t,
                '온도 (°C)': f"{t - 273.15:.0f}",
                '목표 수명 (년)': f"{lifetime:.2f}",
                '평균 수명 (년)': f"{mean_lifetime:.2f}",
                '90% 수명 (년)': f"{t90:.2f}",
                '고장률 (FIT)': f"{fr:.0f}"
            })
        st.dataframe(table_data, use_container_width=True, hide_index=True)

    # ====== 공정 최적화 ======
    elif reliability_analysis_type == "🔧 공정 최적화":
        st.subheader("🔧 공정 최적화 (트랜지스터 폭 vs 신뢰성)")

        width_range = np.linspace(0.5, 3.0, 20)

        with st.spinner('공정 최적화 중...'):
            target_lifetimes = []
            mean_lifetimes = []
            t90_lifetimes = []
            failure_rates = []
            runtime_summaries = []
            fallback_used = False

            for w in width_range:
                pred = predict_lifetime_native_first(
                    temperature=temperature,
                    width=w,
                    num_cells=num_cells,
                    duty_cycle=duty_cycle,
                    failure_rate=failure_rate,
                    vgs=voltage,
                    vds=voltage,
                    vth=0.4,
                    compute_mode="auto",
                    latency_mode="interactive",
                )
                target_lifetimes.append(pred['lifetime_at_failure_rate'])
                mean_lifetimes.append(pred['mean_lifetime'])
                t90_lifetimes.append(pred['t_90pct'])
                failure_rates.append(pred['failure_rate_fit'])
                runtime_summaries.append(summarize_lifetime_runtime(pred))
                fallback_used = fallback_used or bool(pred.get('_exec', {}).get('fallback'))

        st.caption(f"실행 소스 예시: {runtime_summaries[0]}")
        if fallback_used:
            st.info("공정 최적화 분석 중 일부 또는 전체 포인트가 Python fallback으로 실행되었습니다.")

        col1, col2 = st.columns(2)

        with col1:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(width_range, target_lifetimes, 'b-o', linewidth=2.5, markersize=6, label='목표 수명')
            ax.fill_between(width_range, t90_lifetimes, alpha=0.2, color='blue', label='90% 신뢰도 참조')

            optimal_idx = np.argmax(target_lifetimes)
            ax.scatter(width_range[optimal_idx], target_lifetimes[optimal_idx], 
                      s=300, color='red', marker='*', zorder=5, label='최적 크기')

            ax.set_xlabel('트랜지스터 폭 (μm)')
            ax.set_ylabel('수명 (년)')
            ax.set_title(f'폭에 따른 목표 수명 ({target_survival_percent:.1f}% 생존)')
            ax.legend()
            ax.grid(alpha=0.3)

            st.pyplot(fig)
            plt.close()

            st.success(f"**최적 트랜지스터 폭: {width_range[optimal_idx]:.2f} μm** "
                      f"(목표 수명: {target_lifetimes[optimal_idx]:.2f}년)")

        with col2:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.semilogy(width_range, failure_rates, 'r-s', linewidth=2.5, markersize=6)
            ax.axhline(1000, color='orange', linestyle='--', linewidth=2, label='1000 FIT')
            ax.set_xlabel('트랜지스터 폭 (μm)')
            ax.set_ylabel('고장률 (FIT)')
            ax.set_title('폭에 따른 고장률')
            ax.legend()
            ax.grid(alpha=0.3, which='both')

            st.pyplot(fig)
            plt.close()

# ============================================================================
# 푸터
# ============================================================================
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
<small>고급 SRAM 노이즈 & 신뢰성 통합 시뮬레이터 | 퍼셉트론 기반</small><br/>
<small>SNM·Variability·Thermal·Retention·NBTI/HCI 완전 통합 | Python + Streamlit</small>
</div>
""", unsafe_allow_html=True)
