#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SRAM 시뮬레이션 예제 실행 스크립트
다양한 조건에서 SRAM 시뮬레이션을 실행하고 결과를 분석합니다.
"""

import numpy as np
from main import SRAMArray, PerceptronGateFunction
import sys

def print_header(text):
    """헤더 출력"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_result(result, title):
    """결과 출력"""
    print(f"\n{title}")
    print("-" * 70)
    print(f"  온도: {result['temperature']} K ({result['temperature']-273.15:.1f}°C)")
    print(f"  전압: {result['voltage']} V")
    print(f"  셀 개수: {len(result['input_data'])}")
    print(f"  비트 에러: {result['bit_errors']}/{len(result['input_data'])}")
    print(f"  비트 에러율 (BER): {result['bit_error_rate']*100:.4f}%")
    print(f"  평균 노이즈: {np.mean(result['noise_values']):.6f}")
    print(f"  최대 노이즈: {max(result['noise_values']):.6f}")
    print(f"  최소 노이즈: {min(result['noise_values']):.6f}")
    print(f"  표준편차: {np.std(result['noise_values']):.6f}")

def example1_basic_simulation():
    """예제 1: 기본 시뮬레이션"""
    print_header("예제 1: 기본 SRAM 시뮬레이션")

    sram = SRAMArray(num_cells=32)
    data = [1, 0] * 16

    result = sram.simulate(310, 1.0, data, noise_enable=True)
    print_result(result, "기본 조건 (T=310K, V=1.0V)")

    print(f"\n  입력 데이터: {result['input_data'][:16]}...")
    print(f"  출력 데이터: {[f'{x:.2f}' for x in result['output_data'][:16]]}...")

def example2_temperature_sweep():
    """예제 2: 온도 스윕"""
    print_header("예제 2: 온도 변화에 따른 영향 분석")

    sram = SRAMArray(num_cells=32)
    data = [1, 0] * 16

    print("\n온도를 260K에서 360K까지 변화시키며 분석:")
    print("-" * 70)

    temperatures = [260, 290, 310, 330, 360]

    for temp in temperatures:
        result = sram.simulate(temp, 1.0, data, noise_enable=True)
        print(f"  {temp}K: BER={result['bit_error_rate']*100:.3f}%, "
              f"avg_noise={np.mean(result['noise_values']):.6f}")

def example3_voltage_sweep():
    """예제 3: 전압 스윕"""
    print_header("예제 3: 전압 변화에 따른 영향 분석")

    sram = SRAMArray(num_cells=32)
    data = [1, 0] * 16

    print("\n전압을 0.8V에서 1.2V까지 변화시키며 분석:")
    print("-" * 70)

    voltages = [0.80, 0.90, 1.00, 1.10, 1.20]

    for volt in voltages:
        result = sram.simulate(310, volt, data, noise_enable=True)
        print(f"  {volt:.2f}V: BER={result['bit_error_rate']*100:.3f}%, "
              f"avg_noise={np.mean(result['noise_values']):.6f}")

def example4_pvt_analysis():
    """예제 4: PVT (Process, Voltage, Temperature) 분석"""
    print_header("예제 4: PVT 코너 분석")

    sram = SRAMArray(num_cells=32)
    data = [1, 0] * 16

    corners = [
        ("TT (Typical-Typical)", 310, 1.00),
        ("FF (Fast-Fast)", 290, 1.10),
        ("SS (Slow-Slow)", 330, 0.90),
        ("FS (Fast-Slow)", 290, 0.90),
        ("SF (Slow-Fast)", 330, 1.10),
    ]

    print("\nPVT 코너별 분석:")
    print("-" * 70)

    for corner_name, temp, volt in corners:
        result = sram.simulate(temp, volt, data, noise_enable=True)
        print(f"  {corner_name:20} (T={temp}K, V={volt}V): "
              f"BER={result['bit_error_rate']*100:.3f}%")

def example5_pattern_sensitivity():
    """예제 5: 데이터 패턴에 따른 민감도"""
    print_header("예제 5: 데이터 패턴에 따른 노이즈 민감도")

    sram = SRAMArray(num_cells=32)
    patterns = {
        "올 0": [0] * 32,
        "올 1": [1] * 32,
        "체크보드": [i % 2 for i in range(32)],
        "반복 001": [0, 0, 1] * 10 + [0, 0],
        "반복 011": [0, 1, 1] * 10 + [0, 1],
    }

    print("\n패턴별 노이즈 영향도 분석 (T=310K, V=1.0V):")
    print("-" * 70)

    for pattern_name, data in patterns.items():
        result = sram.simulate(310, 1.0, data, noise_enable=True)
        print(f"  {pattern_name:15}: BER={result['bit_error_rate']*100:.3f}%, "
              f"avg_noise={np.mean(result['noise_values']):.6f}")

def example6_perceptron_analysis():
    """예제 6: 퍼셉트론 분석"""
    print_header("예제 6: 퍼셉트론 기반 노이즈 가중치 분석")

    perceptron = PerceptronGateFunction()

    print("\n온도와 전압에 따른 노이즈 가중치 (퍼셉트론 출력):")
    print("-" * 70)
    print(f"{'온도 (K)':>10} | {'전압 (V)':>10} | {'노이즈 가중치':>15}")
    print("-" * 70)

    for temp in range(280, 360, 20):
        for volt in [0.9, 1.0, 1.1]:
            weight = perceptron.forward(temp, volt)
            print(f"{temp:10d} | {volt:10.2f} | {weight:15.6f}")

def example7_stress_test():
    """예제 7: 극단 조건 스트레스 테스트"""
    print_header("예제 7: 극단 조건 스트레스 테스트")

    sram = SRAMArray(num_cells=64)
    data = [1, 0] * 32

    stress_conditions = [
        ("안전 영역", 310, 1.00),
        ("제한 영역 (저전압)", 310, 0.85),
        ("제한 영역 (고온)", 350, 1.00),
        ("위험 영역", 360, 0.80),
    ]

    print("\n극단 조건에서의 동작 특성:")
    print("-" * 70)

    for condition_name, temp, volt in stress_conditions:
        result = sram.simulate(temp, volt, data, noise_enable=True)
        status = "✓ 안전" if result['bit_error_rate'] < 0.01 else "⚠ 위험"
        print(f"  {condition_name:20} (T={temp}K, V={volt:.2f}V): "
              f"BER={result['bit_error_rate']*100:.2f}% {status}")

def main():
    """메인 함수"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "SRAM 노이즈 시뮬레이션 예제 실행" + " "*22 + "║")
    print("║" + " "*12 + "퍼셉트론 기반 노이즈 모델링 및 분석" + " "*20 + "║")
    print("╚" + "="*68 + "╝")

    examples = [
        ("1", "기본 시뮬레이션", example1_basic_simulation),
        ("2", "온도 스윕 분석", example2_temperature_sweep),
        ("3", "전압 스윕 분석", example3_voltage_sweep),
        ("4", "PVT 코너 분석", example4_pvt_analysis),
        ("5", "데이터 패턴 민감도", example5_pattern_sensitivity),
        ("6", "퍼셉트론 분석", example6_perceptron_analysis),
        ("7", "스트레스 테스트", example7_stress_test),
    ]

    print("\n실행할 예제를 선택하세요:")
    for num, name, _ in examples:
        print(f"  {num}. {name}")
    print("  0. 모든 예제 실행")
    print("  q. 종료")

    while True:
        choice = input("\n선택 (0-7, q): ").strip().lower()

        if choice == 'q':
            print("\n프로그램을 종료합니다.")
            break
        elif choice == '0':
            for _, _, example_func in examples:
                example_func()
            input("\n모든 예제 실행이 완료되었습니다. 엔터를 눌러 계속...")
            break
        elif choice in [str(i) for i in range(1, 8)]:
            example_num = int(choice)
            examples[example_num - 1][2]()
            input("\n엔터를 눌러 계속...")
            break
        else:
            print("잘못된 입력입니다. 다시 선택해주세요.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자 중단으로 프로그램을 종료합니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n오류 발생: {e}")
        sys.exit(1)
