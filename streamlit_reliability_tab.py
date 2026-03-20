import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from reliability_model import ReliabilityModel, ReliabilityAwareSRAMCell, LifetimePredictor
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

st.set_page_config(page_title="SRAM 신뢰성 분석", layout="wide")

st.title("⏱️ SRAM 신뢰성 분석 (NBTI/HCI)")
st.markdown("**NBTI (음의 바이어스 온도 불안정성) 및 HCI (핫 캐리어 주입) 열화 분석**")

# 사이드바
st.sidebar.header("⚙️ 신뢰성 분석 파라미터")

# 기본 파라미터
temperature = st.sidebar.slider("온도 (K)", 280, 360, 330, 5)
vgs = st.sidebar.slider("게이트 전압 (V)", 0.0, 1.2, 1.0, 0.1)
vds = st.sidebar.slider("드레인 전압 (V)", 0.0, 1.2, 1.0, 0.1)
width = st.sidebar.slider("트랜지스터 폭 (μm)", 0.5, 3.0, 1.0, 0.1)

# 분석 타입
analysis_type = st.sidebar.selectbox(
    "분석 타입",
    ["장기 열화 예측", "수명 분석", "온도 민감도", "공정 최적화"]
)

# ============================================================================
# 탭 1: 장기 열화 예측
# ============================================================================

if analysis_type == "장기 열화 예측":
    st.subheader("📈 장기 열화 예측 (NBTI + HCI)")

    reliability = ReliabilityModel()

    # 예측 시간 범위
    time_range = np.logspace(0, 10, 100)  # 1초 ~ 10년

    nbti_shifts = []
    hci_shifts = []
    total_shifts = []

    for t in time_range:
        total, nbti, hci = reliability.calculate_total_vth_shift(
            temperature, vgs, vds, 0.4, width, t
        )
        nbti_shifts.append(nbti * 1000)  # mV로 변환
        hci_shifts.append(hci * 1000)
        total_shifts.append(total * 1000)

    # 시간 축 변환 (년)
    time_years = time_range / (365.25 * 24 * 3600)

    col1, col2 = st.columns(2)

    with col1:
        # Vth 시프트 곡선
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.semilogx(time_years, nbti_shifts, 'b-', linewidth=2.5, label='NBTI (+Vth)', marker='o', markersize=4)
        ax.semilogx(time_years, hci_shifts, 'r-', linewidth=2.5, label='HCI (-Vth)', marker='s', markersize=4)
        ax.semilogx(time_years, total_shifts, 'g--', linewidth=2.5, label='합계', marker='^', markersize=4)

        ax.axhline(0, color='black', linestyle='-', alpha=0.3)
        ax.set_xlabel('시간 (년)', fontsize=12)
        ax.set_ylabel('Vth 시프트 (mV)', fontsize=12)
        ax.set_title(f'NBTI/HCI 열화 (T={temperature}K, Vgs={vgs}V, W={width}μm)', fontsize=13)
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3, which='both')

        st.pyplot(fig)
        plt.close()

    with col2:
        # SNM 마진 감소
        nominal_snm = 0.2  # V
        snm_margin = nominal_snm - np.abs(total_shifts) / 1000
        snm_margin = np.maximum(snm_margin, 0)

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.semilogx(time_years, snm_margin * 1000, 'purple', linewidth=2.5, marker='o', markersize=4)
        ax.fill_between(time_years, snm_margin * 1000, alpha=0.3, color='purple')

        # 위험 영역
        ax.axhline(50, color='orange', linestyle='--', linewidth=2, label='경고 (50 mV)')
        ax.axhline(30, color='red', linestyle='--', linewidth=2, label='실패 (30 mV)')

        ax.set_xlabel('시간 (년)', fontsize=12)
        ax.set_ylabel('SNM 마진 (mV)', fontsize=12)
        ax.set_title(f'SNM 마진 감소 (초기: {nominal_snm*1000:.0f} mV)', fontsize=13)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, which='both')
        ax.set_ylim(bottom=0)

        st.pyplot(fig)
        plt.close()

    # 통계 정보
    st.markdown("#### 10년 후 열화 통계")
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

    with col_stat1:
        st.metric("NBTI ΔVth", f"+{nbti_shifts[-1]:.2f} mV")

    with col_stat2:
        st.metric("HCI ΔVth", f"{hci_shifts[-1]:.2f} mV")

    with col_stat3:
        st.metric("총 열화", f"{total_shifts[-1]:.2f} mV")

    with col_stat4:
        remaining_snm = nominal_snm - np.abs(total_shifts[-1]) / 1000
        st.metric("남은 SNM", f"{remaining_snm*1000:.1f} mV")

# ============================================================================
# 탭 2: 수명 분석
# ============================================================================

elif analysis_type == "수명 분석":
    st.subheader("⏱️ SRAM 셀 수명 분석")

    st.info("**수명 정의**: SNM이 30mV 이하로 떨어지는 시점")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 기본 정보")

        cell = ReliabilityAwareSRAMCell(width=width)
        lifetime = cell.estimate_lifetime(temperature, vgs, vds)

        st.write(f"**예상 수명 (단일 셀)**: {lifetime:.2f}년")
        st.write(f"**온도**: {temperature}K ({temperature - 273.15:.0f}°C)")
        st.write(f"**게이트 전압**: {vgs}V")
        st.write(f"**드레인 전압**: {vds}V")
        st.write(f"**트랜지스터 폭**: {width}μm")

        # 수명 해석
        if lifetime > 5:
            st.success("✅ 장기 신뢰성 우수")
        elif lifetime > 2:
            st.warning("⚠️ 적절한 신뢰성 수준")
        else:
            st.error("🔴 신뢰성 문제")

    with col2:
        st.markdown("#### 배열 단위 분석 (32 cells)")

        predictor = LifetimePredictor(num_cells=32, width=width)
        array_pred = predictor.predict_array_lifetime(temperature)

        st.write(f"**평균 수명**: {array_pred['mean_lifetime']:.2f}년")
        st.write(f"**표준편차**: {array_pred['std_lifetime']:.2f}년")
        st.write(f"**최소 수명**: {array_pred['min_lifetime']:.2f}년")
        st.write(f"**최대 수명**: {array_pred['max_lifetime']:.2f}년")
        st.write(f"**90% 신뢰도**: {array_pred['t_90pct']:.2f}년")
        st.write(f"**99% 신뢰도**: {array_pred['t_99pct']:.2f}년")
        st.write(f"**고장률**: {array_pred['failure_rate_fit']:.0f} FIT")

    # 수명 분포 히스토그램
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Weibull 분포
    lifetimes = array_pred['cell_lifetimes']
    ax1.hist(lifetimes, bins=15, color='skyblue', edgecolor='black', alpha=0.7)
    ax1.axvline(np.mean(lifetimes), color='red', linestyle='--', linewidth=2, 
               label=f'평균: {np.mean(lifetimes):.2f}년')
    ax1.set_xlabel('수명 (년)')
    ax1.set_ylabel('셀 개수')
    ax1.set_title('32개 셀의 수명 분포')
    ax1.legend()
    ax1.grid(alpha=0.3)

    # 신뢰도 함수 (Weibull)
    t_range = np.linspace(0, 2*np.mean(lifetimes), 100)
    shape = 2.0
    scale = np.mean(lifetimes)
    reliability_func = np.exp(-(t_range/scale)**shape)

    ax2.plot(t_range, reliability_func * 100, 'b-', linewidth=2.5)
    ax2.axhline(90, color='green', linestyle='--', alpha=0.7, label='90% 신뢰도')
    ax2.axhline(99, color='orange', linestyle='--', alpha=0.7, label='99% 신뢰도')
    ax2.fill_between(t_range, reliability_func * 100, alpha=0.2, color='blue')
    ax2.set_xlabel('시간 (년)')
    ax2.set_ylabel('신뢰도 (%)')
    ax2.set_title('배열 신뢰도 함수 (Weibull)')
    ax2.legend()
    ax2.grid(alpha=0.3)
    ax2.set_ylim(0, 105)

    st.pyplot(fig)
    plt.close()

# ============================================================================
# 탭 3: 온도 민감도
# ============================================================================

elif analysis_type == "온도 민감도":
    st.subheader("🌡️ 온도 민감도 분석")

    # 온도 범위
    temps = [280, 300, 310, 330, 350, 360]

    predictor = LifetimePredictor(num_cells=32, width=width)
    temp_analysis = predictor.analyze_temperature_sensitivity(temps)

    col1, col2 = st.columns(2)

    with col1:
        # 수명 vs 온도
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(temps, temp_analysis['mean_lifetimes'], 'b-o', linewidth=2.5, 
               markersize=8, label='평균 수명')
        ax.fill_between(temps, temp_analysis['t_99pct'], alpha=0.2, color='blue', 
                       label='99% 신뢰도')

        # 산업 표준 (10년 목표)
        ax.axhline(10, color='green', linestyle='--', linewidth=2, label='10년 목표')

        ax.set_xlabel('온도 (K)', fontsize=12)
        ax.set_ylabel('수명 (년)', fontsize=12)
        ax.set_title('온도에 따른 예상 수명', fontsize=13)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, max(temp_analysis['mean_lifetimes']) * 1.2)

        st.pyplot(fig)
        plt.close()

    with col2:
        # 고장률 vs 온도 (로그)
        fig, ax = plt.subplots(figsize=(12, 6))

        fr_fit = temp_analysis['failure_rate']
        ax.semilogy(temps, fr_fit, 'r-s', linewidth=2.5, markersize=8)

        # 산업 표준 (1000 FIT)
        ax.axhline(1000, color='orange', linestyle='--', linewidth=2, label='고장률 1000 FIT')

        ax.set_xlabel('온도 (K)', fontsize=12)
        ax.set_ylabel('고장률 (FIT)', fontsize=12)
        ax.set_title('온도에 따른 고장률', fontsize=13)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, which='both')

        st.pyplot(fig)
        plt.close()

    # 테이블
    st.markdown("#### 온도별 신뢰성 지표")

    table_data = []
    for temp, lifetime, t90, fr in zip(
        temps,
        temp_analysis['mean_lifetimes'],
        temp_analysis['t_90pct'],
        temp_analysis['failure_rate']
    ):
        table_data.append({
            '온도 (K)': temp,
            '온도 (°C)': f"{temp - 273.15:.0f}",
            '평균 수명 (년)': f"{lifetime:.2f}",
            '90% 수명 (년)': f"{t90:.2f}",
            '고장률 (FIT)': f"{fr:.0f}"
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)

# ============================================================================
# 탭 4: 공정 최적화
# ============================================================================

elif analysis_type == "공정 최적화":
    st.subheader("🔧 공정 최적화 (트랜지스터 크기 vs 신뢰성)")

    # 트랜지스터 크기 스캔
    width_range = np.linspace(0.5, 3.0, 20)

    mean_lifetimes = []
    t90_lifetimes = []
    failure_rates = []

    for w in width_range:
        predictor = LifetimePredictor(num_cells=32, width=w)
        pred = predictor.predict_array_lifetime(temperature)
        mean_lifetimes.append(pred['mean_lifetime'])
        t90_lifetimes.append(pred['t_90pct'])
        failure_rates.append(pred['failure_rate_fit'])

    col1, col2 = st.columns(2)

    with col1:
        # 수명 vs 트랜지스터 폭
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(width_range, mean_lifetimes, 'b-o', linewidth=2.5, markersize=6, 
               label='평균 수명')
        ax.fill_between(width_range, t90_lifetimes, alpha=0.2, color='blue', 
                       label='90% 신뢰도')

        # 최적점 표시
        optimal_idx = np.argmax(mean_lifetimes)
        ax.scatter(width_range[optimal_idx], mean_lifetimes[optimal_idx], 
                  s=300, color='red', marker='*', zorder=5, label='최적 크기')

        ax.set_xlabel('트랜지스터 폭 (μm)', fontsize=12)
        ax.set_ylabel('수명 (년)', fontsize=12)
        ax.set_title('트랜지스터 폭에 따른 수명', fontsize=13)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)

        st.pyplot(fig)
        plt.close()

        st.success(f"**최적 트랜지스터 폭: {width_range[optimal_idx]:.2f} μm** "
                  f"(수명: {mean_lifetimes[optimal_idx]:.2f}년)")

    with col2:
        # 고장률 vs 폭 (로그)
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.semilogy(width_range, failure_rates, 'r-s', linewidth=2.5, markersize=6)

        # 산업 표준
        ax.axhline(1000, color='orange', linestyle='--', linewidth=2, label='1000 FIT')

        ax.set_xlabel('트랜지스터 폭 (μm)', fontsize=12)
        ax.set_ylabel('고장률 (FIT)', fontsize=12)
        ax.set_title('트랜지스터 폭에 따른 고장률', fontsize=13)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, which='both')

        st.pyplot(fig)
        plt.close()

# 푸터
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
<small>NBTI/HCI 신뢰성 분석 모듈 | 온도 기반 열화 예측 | Python + Streamlit</small>
</div>
""", unsafe_allow_html=True)
