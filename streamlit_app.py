import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from main import SRAMArray, PerceptronGateFunction
import json
import matplotlib

# ============================================================================
# 한글 폰트 설정
# ============================================================================
def set_korean_font():
    """한글 폰트 자동 감지 및 설정"""
    font_candidates = [
        'Malgun Gothic',           # Windows 기본 한글 폰트
        'Noto Sans CJK KR',        # Noto Sans 한글
        'NanumGothic',             # 나눔 고딕
        'Noto Serif CJK KR',       # Noto Serif 한글
        'DejaVu Sans'              # 기본 폰트
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

    # 폰트 설정 실패 시 기본값
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False

# 폰트 설정 실행
set_korean_font()

# ============================================================================
# Streamlit 앱 시작
# ============================================================================

st.set_page_config(page_title="SRAM 노이즈 시뮬레이션", layout="wide")

# 타이틀
st.title("🔌 SRAM 노이즈 시뮬레이션 (퍼셉트론 기반)")
st.markdown("온도와 전압 조건에서 노이즈 가중치를 반영한 SRAM 셀 시뮬레이션")

# 사이드바 - 입력 파라미터
st.sidebar.header("⚙️ 시뮬레이션 파라미터")

# 온도 입력
temperature = st.sidebar.slider(
    "온도 (K)",
    min_value=260,
    max_value=360,
    value=310,
    step=5,
    help="SRAM 작동 온도 범위"
)

# 전압 입력
voltage = st.sidebar.slider(
    "공급 전압 (V)",
    min_value=0.8,
    max_value=1.2,
    value=1.0,
    step=0.05,
    help="SRAM 공급 전압"
)

# 셀 개수
num_cells = st.sidebar.slider(
    "SRAM 셀 개수",
    min_value=8,
    max_value=128,
    value=32,
    step=8
)

# 노이즈 활성화
noise_enable = st.sidebar.checkbox("노이즈 포함", value=True)

# 입력 데이터 선택
st.sidebar.subheader("📊 입력 데이터")
data_type = st.sidebar.radio(
    "데이터 타입 선택",
    ["랜덤", "올 0", "올 1", "체크보드 패턴", "커스텀"]
)

if data_type == "랜덤":
    input_data = np.random.randint(0, 2, num_cells).tolist()
elif data_type == "올 0":
    input_data = [0] * num_cells
elif data_type == "올 1":
    input_data = [1] * num_cells
elif data_type == "체크보드 패턴":
    input_data = [(i % 2) for i in range(num_cells)]
else:  # 커스텀
    custom_input = st.sidebar.text_input(
        "바이너리 패턴 입력 (예: 10101010)",
        value="10101010"
    )
    try:
        input_data = [int(bit) for bit in custom_input if bit in '01']
        while len(input_data) < num_cells:
            input_data.extend(input_data)
        input_data = input_data[:num_cells]
    except:
        input_data = [0] * num_cells

# SRAM 초기화
sram_array = SRAMArray(num_cells=num_cells)

# 시뮬레이션 실행
result = sram_array.simulate(temperature, voltage, input_data, noise_enable=noise_enable)

# ============================================================================
# 메인 영역
# ============================================================================

# Row 1: 시뮬레이션 결과 요약
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "🌡️ 온도",
        f"{temperature} K",
        f"{temperature - 273.15:.1f}°C"
    )

with col2:
    st.metric(
        "⚡ 전압",
        f"{voltage:.2f} V",
        f"{(voltage - 1.0) * 100:+.0f}%"
    )

with col3:
    st.metric(
        "❌ 비트 에러",
        result['bit_errors'],
        f"{result['bit_error_rate']*100:.2f}%"
    )

with col4:
    avg_noise = np.mean(result['noise_values'])
    st.metric(
        "🔊 평균 노이즈",
        f"{avg_noise:.4f}",
        f"Max: {max(result['noise_values']):.4f}"
    )

# Divider
st.divider()

# ============================================================================
# Tab 1: 3D 표면 그래프 (노이즈 vs 온도/전압)
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 3D 노이즈 맵",
    "🔌 회로 시뮬레이션",
    "📊 상세 분석",
    "ℹ️ 정보"
])

with tab1:
    st.subheader("3D 표면 그래프: 노이즈 vs 온도/전압")

    # 3D 데이터 생성
    perceptron = PerceptronGateFunction()

    temps = np.linspace(260, 360, 30)
    volts = np.linspace(0.8, 1.2, 30)
    T, V = np.meshgrid(temps, volts)

    Z = np.zeros_like(T, dtype=float)
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            Z[i, j] = perceptron.forward(T[i, j], V[i, j])

    # 3D 플롯
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')

    surf = ax.plot_surface(T, V, Z, cmap='viridis', alpha=0.8, edgecolor='none')

    # 현재 포인트 표시
    current_z = perceptron.forward(temperature, voltage)
    ax.scatter([temperature], [voltage], [current_z], color='red', s=200, 
               label=f'현재 조건 (T={temperature}K, V={voltage}V)', marker='o')

    ax.set_xlabel('온도 (K)', fontsize=10)
    ax.set_ylabel('전압 (V)', fontsize=10)
    ax.set_zlabel('노이즈 가중치', fontsize=10)
    ax.set_title('노이즈 가중치 맵 (온도 & 전압 의존성)', fontsize=12, fontweight='bold')

    fig.colorbar(surf, ax=ax, label='노이즈 가중치')
    ax.legend()

    st.pyplot(fig)
    plt.close()

    st.info(
        f"현재 설정에서의 노이즈 가중치: **{current_z:.4f}**"
        f"이 값은 퍼셉트론의 출력으로, 온도가 높고 전압이 낮을수록 노이즈가 증가하는 경향을 보입니다."
    )

with tab2:
    st.subheader("🔌 SRAM 셀 회로 시뮬레이션")

    col_circuit1, col_circuit2 = st.columns(2)

    with col_circuit1:
        # 입출력 비교 그래프
        st.markdown("#### 입출력 데이터 비교")

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6))

        cell_indices = np.arange(min(32, len(result['output_data'])))

        # 입력 데이터
        ax1.bar(cell_indices, result['input_data'][:32], color='blue', alpha=0.7, label='입력')
        ax1.set_ylabel('비트값', fontsize=10)
        ax1.set_title(f'입력 데이터 (온도: {temperature}K, 전압: {voltage}V)', fontsize=11)
        ax1.set_ylim(-0.1, 1.1)
        ax1.set_xticks(range(0, 32, 4))
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)

        # 출력 데이터 (노이즈 포함)
        colors = ['red' if abs(result['output_data'][i] - result['input_data'][i]) > 0.3 
                  else 'green' for i in range(min(32, len(result['output_data'])))]
        ax2.bar(cell_indices, result['output_data'][:32], color=colors, alpha=0.7, label='출력')
        ax2.set_xlabel('셀 번호', fontsize=10)
        ax2.set_ylabel('비트값', fontsize=10)
        ax2.set_title('출력 데이터 (노이즈 반영)', fontsize=11)
        ax2.set_ylim(-0.1, 1.1)
        ax2.set_xticks(range(0, 32, 4))
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col_circuit2:
        # 노이즈 분포
        st.markdown("#### 셀별 노이즈 분포")

        fig, ax = plt.subplots(figsize=(12, 4))

        cell_indices = np.arange(min(32, len(result['noise_values'])))
        noise_values = result['noise_values'][:32]

        colors_noise = plt.cm.RdYlGn_r(np.linspace(0, 1, len(noise_values)))
        ax.bar(cell_indices, noise_values, color=colors_noise, alpha=0.8)
        ax.axhline(y=np.mean(noise_values), color='red', linestyle='--', linewidth=2, label=f'평균: {np.mean(noise_values):.4f}')
        ax.set_xlabel('셀 번호', fontsize=10)
        ax.set_ylabel('노이즈 크기', fontsize=10)
        ax.set_title('셀별 노이즈 분포', fontsize=11)
        ax.set_xticks(range(0, 32, 4))
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

with tab3:
    st.subheader("📊 상세 분석")

    col_analysis1, col_analysis2 = st.columns(2)

    with col_analysis1:
        st.markdown("#### 통계 정보")

        stats_data = {
            "메트릭": [
                "총 셀 개수",
                "입력 데이터 (1의 개수)",
                "출력 데이터 (1의 개수)",
                "비트 에러 개수",
                "비트 에러율",
                "평균 노이즈",
                "최대 노이즈",
                "최소 노이즈",
                "표준편차"
            ],
            "값": [
                num_cells,
                sum(result['input_data']),
                sum([1 for x in result['output_data'] if x > 0.5]),
                result['bit_errors'],
                f"{result['bit_error_rate']*100:.2f}%",
                f"{np.mean(result['noise_values']):.6f}",
                f"{max(result['noise_values']):.6f}",
                f"{min(result['noise_values']):.6f}",
                f"{np.std(result['noise_values']):.6f}"
            ]
        }

        st.dataframe(stats_data, use_container_width=True, hide_index=True)

    with col_analysis2:
        st.markdown("#### 온도/전압 스윕 분석")

        temps_sweep = np.linspace(280, 350, 15)
        volts_sweep = np.linspace(0.85, 1.15, 15)

        ber_grid = np.zeros((len(volts_sweep), len(temps_sweep)))
        noise_grid = np.zeros((len(volts_sweep), len(temps_sweep)))

        sram_sweep = SRAMArray(num_cells=32)

        for i, v_temp in enumerate(temps_sweep):
            for j, v_volt in enumerate(volts_sweep):
                result_sweep = sram_sweep.simulate(v_temp, v_volt, input_data, noise_enable=True)
                ber_grid[j, i] = result_sweep['bit_error_rate']
                noise_grid[j, i] = np.mean(result_sweep['noise_values'])

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # BER 히트맵
        im1 = ax1.contourf(temps_sweep, volts_sweep, ber_grid * 100, levels=15, cmap='RdYlGn_r')
        ax1.plot([temperature], [voltage], 'b*', markersize=15, label='현재 포인트')
        ax1.set_xlabel('온도 (K)', fontsize=10)
        ax1.set_ylabel('전압 (V)', fontsize=10)
        ax1.set_title('비트 에러율 (BER) 히트맵', fontsize=11)
        ax1.legend()
        cbar1 = plt.colorbar(im1, ax=ax1)
        cbar1.set_label('BER (%)', fontsize=10)

        # 노이즈 히트맵
        im2 = ax2.contourf(temps_sweep, volts_sweep, noise_grid, levels=15, cmap='viridis')
        ax2.plot([temperature], [voltage], 'r*', markersize=15, label='현재 포인트')
        ax2.set_xlabel('온도 (K)', fontsize=10)
        ax2.set_ylabel('전압 (V)', fontsize=10)
        ax2.set_title('평균 노이즈 히트맵', fontsize=11)
        ax2.legend()
        cbar2 = plt.colorbar(im2, ax=ax2)
        cbar2.set_label('노이즈 크기', fontsize=10)

        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

with tab4:
    st.subheader("ℹ️ 시뮬레이션 정보")

    st.markdown("""
    ### 🔧 기술 설명

    #### 1. **퍼셉트론 기반 Gate 함수**
    - 2층 다층 퍼셉트론(MLP)으로 온도와 전압의 비선형 관계를 모델링
    - 입력층: 온도, 전압 (정규화됨)
    - 은닉층: 16개 뉴런, ReLU 활성화 함수
    - 출력층: 1개 뉴런, 시그모이드 활성화 함수 (0~1 범위)

    #### 2. **노이즈 모델링**
    - **기본 노이즈**: 퍼셉트론 출력으로부터 계산
    - **온도 의존성**: 온도 증가 시 노이즈 선형 증가
    - **전압 의존성**: 전압 감소 시 노이즈 상대적으로 증가
    - **신호 변환 노이즈**: 셀의 저장값과 다른 값 쓰기 시 1.5배 증폭

    #### 3. **SRAM 셀 동작**
    - **읽기**: 저장된 비트값에 노이즈를 더하여 출력
    - **쓰기**: 낮은 전압에서 실패 가능성 있음 (success_prob 계산)
    - **비트 에러**: 입출력 비트값 차이로 계산

    #### 4. **주요 파라미터**
    - 온도 범위: 260~360 K (-13~87°C)
    - 전압 범위: 0.8~1.2 V
    - 셀 개수: 8~128개
    - 기본 노이즈 레벨: 0.05 (5%)

    ### 📊 결과 해석

    **비트 에러율 (BER)**
    - 낮은 BER: 안정적인 동작 영역
    - 높은 BER: 불안정한 영역 (낮은 전압, 높은 온도)

    **노이즈 분포**
    - 빨강색: 높은 노이즈 (위험)
    - 초록색: 낮은 노이즈 (안전)

    ### 💾 응용 분야
    - SRAM 신뢰성 분석
    - 저전압 설계 검증
    - 온도 범위 결정
    - 마진 분석
    """)

# 푸터
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <small>SRAM 노이즈 시뮬레이션 | 퍼셉트론 기반 노이즈 모델링 | Python + Streamlit</small>
    </div>
    """,
    unsafe_allow_html=True
)
