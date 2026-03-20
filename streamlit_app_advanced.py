import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from main_advanced import AdvancedSRAMArray, PerceptronGateFunction, AdvancedSRAMCell
import matplotlib

# 한글 폰트 설정
def set_korean_font():
    font_candidates = ['Malgun Gothic', 'Noto Sans CJK KR', 'NanumGothic', 'DejaVu Sans']
    try:
        font_list = [f.name for f in matplotlib.font_manager.fontManager.ttflist]
        for font in font_candidates:
            if font in font_list:
                plt.rcParams['font.sans-serif'] = font
                plt.rcParams['axes.unicode_minus'] = False
                return
    except:
        pass
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()

st.set_page_config(page_title="고급 SRAM 노이즈 시뮬레이션", layout="wide")

# 타이틀
st.title("🔌 고급 SRAM 노이즈 시뮬레이션 (퍼셉트론 기반)")
st.markdown("**SNM 분석, Variability, Thermal Noise, Retention Mode 통합**")

# 사이드바
st.sidebar.header("⚙️ 시뮬레이션 파라미터")

# 기본 파라미터
temperature = st.sidebar.slider("온도 (K)", 260, 360, 310, 5)
voltage = st.sidebar.slider("공급 전압 (V)", 0.8, 1.2, 1.0, 0.05)
num_cells = st.sidebar.slider("SRAM 셀 개수", 8, 128, 32, 8)

# 고급 옵션
st.sidebar.subheader("🔬 고급 분석")
variability_enable = st.sidebar.checkbox("Variability 모델링 (Pelgrom)", value=True)
monte_carlo_runs = st.sidebar.slider("Monte Carlo 반복 횟수", 1, 100, 10, 10)
process_corner = st.sidebar.checkbox("Process Corner 분석 (FF/TT/SS)", value=False)

# 디바이스 파라미터
st.sidebar.subheader("📐 트랜지스터 파라미터")
width = st.sidebar.number_input("Width (μm)", 0.1, 5.0, 1.0, 0.1)
length = st.sidebar.number_input("Length (μm)", 0.1, 5.0, 1.0, 0.1)

# 입력 데이터
st.sidebar.subheader("📊 입력 데이터")
data_type = st.sidebar.radio("데이터 타입", ["랜덤", "올 0", "올 1", "체크보드"])

if data_type == "랜덤":
    input_data = np.random.randint(0, 2, num_cells).tolist()
elif data_type == "올 0":
    input_data = [0] * num_cells
elif data_type == "올 1":
    input_data = [1] * num_cells
else:
    input_data = [(i % 2) for i in range(num_cells)]

# SRAM 초기화
sram_array = AdvancedSRAMArray(num_cells=num_cells, width=width, length=length)

# 시뮬레이션 실행
with st.spinner('시뮬레이션 실행 중...'):
    result = sram_array.simulate(temperature, voltage, input_data, 
                                 variability_enable=variability_enable,
                                 monte_carlo_runs=monte_carlo_runs)

    if process_corner:
        corner_results = sram_array.process_corner_analysis(temperature, voltage, input_data)

# 메트릭
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("🌡️ 온도", f"{temperature} K", f"{temperature - 273.15:.1f}°C")

with col2:
    st.metric("⚡ 전압", f"{voltage:.2f} V")

with col3:
    st.metric("❌ BER", f"{result['bit_error_rate']*100:.2f}%", 
             f"±{result['ber_confidence_95']*100:.2f}%")

with col4:
    if result['snm_values']:
        st.metric("📊 평균 SNM", f"{np.mean(result['snm_values']):.4f} V")
    else:
        st.metric("📊 평균 SNM", "N/A")

with col5:
    st.metric("🔁 Monte Carlo", f"{monte_carlo_runs}회")

st.divider()

# 탭
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 SNM 분석",
    "🎲 Variability",
    "🌊 Thermal Noise",
    "⏱️ Retention Mode",
    "🔄 Process Corner"
])

with tab1:
    st.subheader("📈 Static Noise Margin (SNM) 분석")

    if result['snm_values']:
        col_snm1, col_snm2 = st.columns(2)

        with col_snm1:
            # SNM 분포 히스토그램
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(result['snm_values'], bins=20, color='skyblue', edgecolor='black', alpha=0.7)
            ax.axvline(np.mean(result['snm_values']), color='red', linestyle='--', 
                      linewidth=2, label=f"평균: {np.mean(result['snm_values']):.4f}V")
            ax.set_xlabel('SNM (V)')
            ax.set_ylabel('빈도')
            ax.set_title('SNM 분포')
            ax.legend()
            ax.grid(alpha=0.3)
            st.pyplot(fig)
            plt.close()

        with col_snm2:
            # 버터플라이 곡선 (대표 셀)
            cell = sram_array.cells[0]
            snm, v_range, v2_inv1 = cell.calculate_snm(voltage)

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(v_range, v2_inv1, 'b-', linewidth=2, label='인버터 1')
            ax.plot(v2_inv1, v_range, 'r-', linewidth=2, label='인버터 2 (역함수)')
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

        st.info(f"**평균 SNM: {np.mean(result['snm_values']):.4f} V** - "
               f"낮은 SNM은 노이즈 면역성 저하를 의미합니다.")
    else:
        st.warning("Variability 모델링을 활성화하세요.")

with tab2:
    st.subheader("🎲 Monte Carlo Variability 분석")

    col_var1, col_var2 = st.columns(2)

    with col_var1:
        # BER 분포 (Monte Carlo)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(np.array(result['monte_carlo_ber'])*100, bins=20, 
               color='coral', edgecolor='black', alpha=0.7)
        ax.axvline(result['bit_error_rate']*100, color='red', linestyle='--', 
                  linewidth=2, label=f"평균 BER: {result['bit_error_rate']*100:.2f}%")
        ax.set_xlabel('BER (%)')
        ax.set_ylabel('빈도')
        ax.set_title(f'BER 분포 (Monte Carlo {monte_carlo_runs}회)')
        ax.legend()
        ax.grid(alpha=0.3)
        st.pyplot(fig)
        plt.close()

    with col_var2:
        # Pelgrom 법칙 시각화
        areas = np.logspace(-1, 1, 50)  # WL 범위
        sigma_vth = 5.0 / np.sqrt(areas)  # mV

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(areas, sigma_vth, 'b-', linewidth=2)
        ax.scatter([width*length], [5.0/np.sqrt(width*length)], 
                  color='red', s=200, zorder=5, label=f'현재: W×L={width*length:.2f}μm²')
        ax.set_xscale('log')
        ax.set_xlabel('트랜지스터 면적 W×L (μm²)')
        ax.set_ylabel('σ_Vth (mV)')
        ax.set_title('Pelgrom 법칙: σ_Vth ∝ 1/√(W×L)')
        ax.legend()
        ax.grid(alpha=0.3, which='both')
        st.pyplot(fig)
        plt.close()

    st.info(f"**Pelgrom σ_Vth: {5.0/np.sqrt(width*length):.2f} mV** - "
           f"작은 트랜지스터일수록 변동성이 증가합니다.")

with tab3:
    st.subheader("🌊 Thermal/Shot Noise (Euler-Maruyama)")

    # 대표 셀의 전압 궤적
    cell = sram_array.cells[0]
    v_trajectory = cell.thermal_shot_noise_euler_maruyama(temperature, voltage, n_steps=500)

    col_thermal1, col_thermal2 = st.columns(2)

    with col_thermal1:
        fig, ax = plt.subplots(figsize=(10, 6))
        time_axis = np.arange(len(v_trajectory)) * cell.dt * 1e9  # ns
        ax.plot(time_axis, v_trajectory, 'b-', linewidth=1, alpha=0.8)
        ax.axhline(voltage if cell.stored_bit else 0, color='red', 
                  linestyle='--', label=f'목표 전압')
        ax.set_xlabel('시간 (ns)')
        ax.set_ylabel('전압 (V)')
        ax.set_title('Thermal/Shot Noise에 의한 전압 궤적')
        ax.legend()
        ax.grid(alpha=0.3)
        st.pyplot(fig)
        plt.close()

    with col_thermal2:
        # 전압 분포
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(v_trajectory, bins=30, color='green', edgecolor='black', alpha=0.7)
        ax.axvline(np.mean(v_trajectory), color='red', linestyle='--', 
                  linewidth=2, label=f'평균: {np.mean(v_trajectory):.4f}V')
        ax.set_xlabel('전압 (V)')
        ax.set_ylabel('빈도')
        ax.set_title('전압 분포 (Thermal/Shot Noise)')
        ax.legend()
        ax.grid(alpha=0.3)
        st.pyplot(fig)
        plt.close()

    st.info(f"**전압 표준편차: {np.std(v_trajectory):.6f} V** - "
           f"온도가 높을수록 열잡음이 증가합니다.")

with tab4:
    st.subheader("⏱️ Retention Mode 분석")

    # Retention 분석
    cell = sram_array.cells[0]
    retention_result = cell.retention_mode_analysis(voltage, temperature, time_steps=1000)

    col_ret1, col_ret2 = st.columns(2)

    with col_ret1:
        # 전압 궤적
        fig, ax = plt.subplots(figsize=(10, 6))
        time_axis = np.arange(len(retention_result['voltage_trajectory'])) * cell.dt * 1e6  # μs
        ax.plot(time_axis, retention_result['voltage_trajectory'], 'b-', linewidth=1, alpha=0.8)
        ax.axhline(retention_result['unstable_equilibrium'], color='red', 
                  linestyle='--', label=f'불안정 평형점: {retention_result["unstable_equilibrium"]:.3f}V')
        ax.set_xlabel('시간 (μs)')
        ax.set_ylabel('전압 (V)')
        ax.set_title('Retention Mode 전압 궤적')
        ax.legend()
        ax.grid(alpha=0.3)
        st.pyplot(fig)
        plt.close()

    with col_ret2:
        # Quasi-potential
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(retention_result['voltage_trajectory'], retention_result['quasi_potential'], 
               'g-', linewidth=2)
        ax.set_xlabel('전압 (V)')
        ax.set_ylabel('Quasi-potential U(v)')
        ax.set_title('Quasi-potential 분포')
        ax.grid(alpha=0.3)
        st.pyplot(fig)
        plt.close()

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("평균 편차", f"{retention_result['mean_deviation']:.6f} V")
    with col_m2:
        st.metric("최대 편차", f"{retention_result['max_deviation']:.6f} V")
    with col_m3:
        st.metric("실패 확률", f"{retention_result['retention_failure_prob']*100:.2f}%")

with tab5:
    st.subheader("🔄 Process Corner 분석 (FF/TT/SS)")

    if process_corner:
        # Corner 비교 바 차트
        corners = list(corner_results.keys())
        bers = [corner_results[c]['ber']*100 for c in corners]
        ber_stds = [corner_results[c]['ber_std']*100 for c in corners]

        col_corner1, col_corner2 = st.columns(2)

        with col_corner1:
            fig, ax = plt.subplots(figsize=(10, 6))
            x_pos = np.arange(len(corners))
            bars = ax.bar(x_pos, bers, yerr=ber_stds, capsize=5, 
                         color=['skyblue', 'green', 'coral'], edgecolor='black', alpha=0.7)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(corners)
            ax.set_ylabel('BER (%)')
            ax.set_title('Process Corner별 BER 비교')
            ax.grid(axis='y', alpha=0.3)

            # 값 표시
            for i, (bar, ber) in enumerate(zip(bars, bers)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + ber_stds[i],
                       f'{ber:.2f}%', ha='center', va='bottom', fontsize=10)

            st.pyplot(fig)
            plt.close()

        with col_corner2:
            # Corner 조건 테이블
            st.markdown("#### Corner 조건")
            corner_data = []
            for corner, data in corner_results.items():
                corner_data.append({
                    "Corner": corner,
                    "전압 (V)": f"{data['voltage']:.2f}",
                    "온도 (K)": f"{data['temperature']:.0f}",
                    "BER (%)": f"{data['ber']*100:.2f}",
                    "σ (%)": f"{data['ber_std']*100:.2f}"
                })
            st.dataframe(corner_data, use_container_width=True, hide_index=True)

        st.info("**SS Corner가 가장 취약** - 느린 트랜지스터에서 BER이 증가합니다.")
    else:
        st.warning("Process Corner 분석을 활성화하세요 (사이드바).")

# 푸터
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
<small>고급 SRAM 노이즈 시뮬레이션 | SNM·Variability·Thermal·Retention 통합 | Python + Streamlit</small>
</div>
""", unsafe_allow_html=True)
