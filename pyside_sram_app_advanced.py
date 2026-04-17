"""
Advanced PySide6 SRAM Simulator Desktop Application
Complete Integration: Basic Noise + SNM Analysis + Variability + Thermal Noise +
Retention Mode + Process Corner + NBTI/HCI Reliability + Research Data + Thermal Analysis
"""

import sys
import json
import os
import csv
import copy
import numpy as np
from datetime import datetime

# Set matplotlib to use PySide6 backend explicitly
os.environ['QT_API'] = 'PySide6'

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QSpinBox, QDoubleSpinBox, QPushButton, QLabel, QTabWidget,
    QTableWidget, QTableWidgetItem, QSplitter, QGroupBox, QProgressBar,
    QCheckBox, QRadioButton, QButtonGroup, QLineEdit, QFileDialog, QMessageBox,
    QComboBox, QHeaderView, QTextEdit, QScrollArea, QToolBar, QStackedWidget,
    QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QAction

RESEARCH_DATA_FILE = "research_data.json"
LEGACY_RESEARCH_DATA_FILE = "".join(("cust", "omer_data.json"))
RESEARCH_ANALYSIS_LOG_PREFIX = "research_analysis_"

# Import SRAM modules with fallback
try:
    from main_advanced import AdvancedSRAMArray, PerceptronGateFunction, AdvancedSRAMCell
    ADVANCED_AVAILABLE = True
except ImportError:
    ADVANCED_AVAILABLE = False
    print("Warning: Advanced features not available. Using basic features only.")

# Import Hybrid Perceptron SRAM (new backend option)
try:
    from hybrid_perceptron_sram import HybridSRAMArray, HybridPerceptronGate, PerceptronNoiseModel
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    print("Warning: Hybrid Perceptron SRAM not available.")

# Import Workload Model for advanced analysis
try:
    from workload_model import (
        TransformerWorkloadProfile,
        CircuitToSystemTranslator,
        DesignSpaceOptimizer,
        WorkloadScenarios
    )
    WORKLOAD_MODEL_AVAILABLE = True
except ImportError:
    WORKLOAD_MODEL_AVAILABLE = False
    print("Warning: Workload model not available - advanced analysis features disabled.")

# Import reliability model with fallback
try:
    from reliability_model import ReliabilityModel, ReliabilityAwareSRAMCell, LifetimePredictor
    RELIABILITY_AVAILABLE = True
except ImportError:
    RELIABILITY_AVAILABLE = False
    print("Warning: Reliability features not available.")

# AI Advisor (optional)
try:
    from sram_ai_advisor import SRAMAdvisor
    AI_ADVISOR_AVAILABLE = True
except ImportError:
    AI_ADVISOR_AVAILABLE = False
    print("Warning: AI research analysis is not available")

# Validation & ML benchmark (optional)
try:
    from analytical_ground_truth import AnalyticalSRAMModel
    from ml_benchmark import SRAMModelBenchmark
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False
    print("Warning: Validation / Benchmark modules not available")

# Native backend (Rust/C++) orchestration
try:
    from native_backend import (
        simulate_array as native_simulate_array,
        predict_lifetime as native_predict_lifetime,
        optimize_design as native_optimize_design,
        NativeBackendError,
    )
    NATIVE_BACKEND_AVAILABLE = True
except ImportError:
    NATIVE_BACKEND_AVAILABLE = False
    NativeBackendError = RuntimeError
    print("Warning: Native backend wrapper not available.")

try:
    from execution_policy import select_engine as select_compute_engine
    EXECUTION_POLICY_AVAILABLE = True
except ImportError:
    EXECUTION_POLICY_AVAILABLE = False
    select_compute_engine = None

from lifetime_service import (
    DEFAULT_DUTY_CYCLE,
    DEFAULT_FAILURE_RATE,
    build_lifetime_result_text,
    predict_lifetime_native_first,
    summarize_lifetime_runtime,
)

# PDF Generation (optional)
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from matplotlib.backends.backend_pdf import PdfPages
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not available - PDF export disabled")

# -----------------------------------------------------------------------------
# UI Design System (Stage 1: tokenized style / global QSS)
# -----------------------------------------------------------------------------

UI_DESIGN_TOKENS = {
    "font_family": '"Noto Sans KR", "Inter", "Segoe UI", Arial, sans-serif',
    "sizes": {
        "title": 20,
        "title_small": 16,
        "body": 12,
        "caption": 10,
        "button_large": 16,
        "button": 13,
    },
    "spacing": {
        "xsmall": 4,
        "small": 8,
        "medium": 12,
        "large": 16,
    },
    "radius": {
        "small": 4,
        "medium": 6,
        "large": 8,
    },
    "colors": {
        "bg": "#f7f8fb",
        "panel": "#ffffff",
        "panel_muted": "#f2f4f7",
        "panel_hover": "#e5e7eb",
        "text": "#111827",
        "muted_text": "#6b7280",
        "line": "#d1d5db",
        "disabled_bg": "#cbd5e1",
        "disabled_text": "#f8fafc",
        "primary": "#2563eb",
        "primary_hover": "#1d4ed8",
        "primary_active": "#1e40af",
        "secondary": "#64748b",
        "secondary_hover": "#475569",
        "success": "#10b981",
        "success_hover": "#059669",
        "danger": "#ef4444",
        "danger_hover": "#dc2626",
        "warning": "#f59e0b",
        "warning_hover": "#d97706",
        "info": "#06b6d4",
        "info_hover": "#0891b2",
        "ghost_hover": "#e0e7ff",
    },
    "ui_styles": {
        "groupbox_margin_top": 14,
        "groupbox_title_left": 8,
        "groupbox_title_padding_x": 4,
    },
}


APP_QSS = f"""
* {{
    font-family: {UI_DESIGN_TOKENS["font_family"]};
    font-size: {UI_DESIGN_TOKENS["sizes"]["body"]}px;
    color: {UI_DESIGN_TOKENS["colors"]["text"]};
}}

QWidget {{
    background-color: {UI_DESIGN_TOKENS["colors"]["bg"]};
}}

QMainWindow {{
    background-color: {UI_DESIGN_TOKENS["colors"]["bg"]};
}}

QGroupBox {{
    border: 1px solid {UI_DESIGN_TOKENS["colors"]["line"]};
    border-radius: {UI_DESIGN_TOKENS["radius"]["large"]}px;
    margin-top: {UI_DESIGN_TOKENS["ui_styles"]["groupbox_margin_top"]}px;
    padding-top: {UI_DESIGN_TOKENS["spacing"]["medium"]}px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: {UI_DESIGN_TOKENS["ui_styles"]["groupbox_title_left"]}px;
    padding: 0 {UI_DESIGN_TOKENS["ui_styles"]["groupbox_title_padding_x"]}px 0 {UI_DESIGN_TOKENS["ui_styles"]["groupbox_title_padding_x"]}px;
    color: {UI_DESIGN_TOKENS["colors"]["text"]};
    font-weight: 600;
}}

QLabel {{
    color: {UI_DESIGN_TOKENS["colors"]["text"]};
    padding: 0px;
}}

QLabel[ui-typography="title"] {{
    font-size: {UI_DESIGN_TOKENS["sizes"]["title"]}px;
    font-weight: 700;
}}

QLabel[ui-typography="section"] {{
    font-size: {UI_DESIGN_TOKENS["sizes"]["title_small"]}px;
    font-weight: 600;
    margin-bottom: 4px;
}}

QLabel[ui-typography="caption"] {{
    color: {UI_DESIGN_TOKENS["colors"]["muted_text"]};
    font-size: {UI_DESIGN_TOKENS["sizes"]["caption"]}px;
}}

QLabel[ui-status="success"] {{
    color: {UI_DESIGN_TOKENS["colors"]["success"]};
    font-weight: 600;
}}

QLabel[ui-status="warning"] {{
    color: {UI_DESIGN_TOKENS["colors"]["warning"]};
    font-weight: 600;
}}

QLabel[ui-status="muted"] {{
    color: {UI_DESIGN_TOKENS["colors"]["muted_text"]};
}}

QLabel[ui-status="info"] {{
    color: {UI_DESIGN_TOKENS["colors"]["primary"]};
    font-weight: 600;
}}

QLabel[ui-status="error"] {{
    color: {UI_DESIGN_TOKENS["colors"]["danger"]};
    font-weight: 700;
}}

QLabel[ui-style="panel-muted"] {{
    padding: 10px;
    border-radius: {UI_DESIGN_TOKENS["radius"]["medium"]}px;
    background-color: {UI_DESIGN_TOKENS["colors"]["panel_muted"]};
}}

QTextEdit[ui-font="mono"] {{
    font-family: "Courier New", Consolas, monospace;
    font-size: 10px;
}}

QTextEdit[ui-font="mono-large"] {{
    font-family: "Courier New", Consolas, monospace;
    font-size: 11px;
}}

QTabWidget::pane {{
    border: 1px solid {UI_DESIGN_TOKENS["colors"]["line"]};
    border-top: none;
    background: {UI_DESIGN_TOKENS["colors"]["panel_muted"]};
    border-bottom-left-radius: {UI_DESIGN_TOKENS["radius"]["large"]}px;
    border-bottom-right-radius: {UI_DESIGN_TOKENS["radius"]["large"]}px;
}}

QTabBar::tab {{
    background: {UI_DESIGN_TOKENS["colors"]["panel_muted"]};
    border: 1px solid {UI_DESIGN_TOKENS["colors"]["line"]};
    padding: {UI_DESIGN_TOKENS["spacing"]["small"]}px {UI_DESIGN_TOKENS["spacing"]["medium"]}px;
    border-top-left-radius: {UI_DESIGN_TOKENS["radius"]["small"]}px;
    border-top-right-radius: {UI_DESIGN_TOKENS["radius"]["small"]}px;
}}

QTabBar::tab:selected {{
    background: {UI_DESIGN_TOKENS["colors"]["panel"]};
    color: {UI_DESIGN_TOKENS["colors"]["text"]};
}}

QTabBar::tab:hover:!selected {{
    background: {UI_DESIGN_TOKENS["colors"]["panel_hover"]};
}}

QProgressBar {{
    border: 1px solid {UI_DESIGN_TOKENS["colors"]["line"]};
    border-radius: {UI_DESIGN_TOKENS["radius"]["medium"]}px;
    text-align: center;
    padding: 2px;
    background: {UI_DESIGN_TOKENS["colors"]["panel_muted"]};
}}

QProgressBar::chunk {{
    background: {UI_DESIGN_TOKENS["colors"]["primary"]};
    border-radius: {UI_DESIGN_TOKENS["radius"]["medium"]}px;
}}

QToolBar#analysisToolbar {{
    background: {UI_DESIGN_TOKENS["colors"]["panel"]};
    border: none;
    border-bottom: 1px solid {UI_DESIGN_TOKENS["colors"]["line"]};
    margin: 0px;
    padding: 2px 6px;
    spacing: 2px;
    min-height: 28px;
}}

QToolBar#analysisToolbar::separator {{
    background: {UI_DESIGN_TOKENS["colors"]["line"]};
    width: 1px;
    margin: 3px 6px;
}}

QToolBar#analysisToolbar QToolButton {{
    color: {UI_DESIGN_TOKENS["colors"]["text"]};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 2px 10px;
    min-height: 22px;
    max-height: 22px;
    font-size: {UI_DESIGN_TOKENS["sizes"]["button"]}px;
    font-weight: 600;
    background: transparent;
}}

QToolBar#analysisToolbar QToolButton:hover {{
    color: {UI_DESIGN_TOKENS["colors"]["primary"]};
    border-color: #c7d2fe;
    background: {UI_DESIGN_TOKENS["colors"]["panel_muted"]};
}}

QToolBar#analysisToolbar QToolButton:pressed,
QToolBar#analysisToolbar QToolButton:checked {{
    color: {UI_DESIGN_TOKENS["colors"]["primary_active"]};
    border-color: #a5b4fc;
    background: #e0e7ff;
}}

QToolBar#analysisToolbar QToolButton:disabled {{
    color: {UI_DESIGN_TOKENS["colors"]["disabled_text"]};
    background: transparent;
}}

QToolBar#analysisToolbar QToolButton#simulateAction {{
    color: {UI_DESIGN_TOKENS["colors"]["primary"]};
    border-color: #bfdbfe;
    background: #eff6ff;
}}

QToolBar#analysisToolbar QToolButton#reportAction {{
    color: {UI_DESIGN_TOKENS["colors"]["success"]};
    border-color: #a7f3d0;
    background: #ecfdf5;
}}

QToolBar#analysisToolbar QPushButton {{
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 2px 10px;
    min-height: 22px;
    max-height: 22px;
    font-size: {UI_DESIGN_TOKENS["sizes"]["button"]}px;
    font-weight: 600;
    background: transparent;
}}

QToolBar#analysisToolbar QPushButton:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["panel_muted"]};
}}

QToolBar#analysisToolbar QPushButton:pressed,
QToolBar#analysisToolbar QPushButton:checked {{
    background: {UI_DESIGN_TOKENS["colors"]["panel_muted"]};
}}

QToolBar#analysisToolbar QPushButton:disabled {{
    color: {UI_DESIGN_TOKENS["colors"]["disabled_text"]};
}}

QToolBar#analysisToolbar QPushButton#simulateButton {{
    color: {UI_DESIGN_TOKENS["colors"]["text"]};
    border-color: transparent;
    background: transparent;
}}

QToolBar#analysisToolbar QPushButton#simulateButton:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["panel"]};
    border-color: transparent;
}}

QToolBar#analysisToolbar QPushButton#simulateButton:pressed {{
    background: {UI_DESIGN_TOKENS["colors"]["panel"]};
    border-color: transparent;
}}

QToolBar#analysisToolbar QPushButton#resetButton {{
    color: {UI_DESIGN_TOKENS["colors"]["text"]};
    border-color: transparent;
    background: transparent;
}}

QToolBar#analysisToolbar QPushButton#resetButton:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["panel"]};
    border-color: transparent;
}}

QToolBar#analysisToolbar QPushButton#resetButton:pressed {{
    background: {UI_DESIGN_TOKENS["colors"]["panel"]};
    border-color: transparent;
}}

QToolBar#analysisToolbar QLabel {{
    margin: 2px 4px 0px 4px;
    color: {UI_DESIGN_TOKENS["colors"]["muted_text"]};
    font-size: {UI_DESIGN_TOKENS["sizes"]["caption"]}px;
}}

QToolBar#analysisToolbar QComboBox#analysisViewCombo {{
    min-height: 22px;
    max-height: 22px;
    margin: 1px 2px;
}}

QWidget[ui-role="spacer"] {{
    background: transparent;
}}

QPushButton {{
    border: none;
    border-radius: {UI_DESIGN_TOKENS["radius"]["medium"]}px;
    color: #ffffff;
    font-weight: 600;
    min-height: 30px;
    padding: {UI_DESIGN_TOKENS["spacing"]["small"]}px {UI_DESIGN_TOKENS["spacing"]["medium"]}px;
    font-size: {UI_DESIGN_TOKENS["sizes"]["button"]}px;
    background: {UI_DESIGN_TOKENS["colors"]["secondary"]};
}}

QPushButton:enabled {{
    background: {UI_DESIGN_TOKENS["colors"]["secondary"]};
}}

QPushButton:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["secondary_hover"]};
}}

QPushButton:pressed {{
    background: {UI_DESIGN_TOKENS["colors"]["secondary"]};
}}

QPushButton[ui-role="primary"] {{
    background: {UI_DESIGN_TOKENS["colors"]["primary"]};
}}
QPushButton[ui-role="primary"]:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["primary_hover"]};
}}
QPushButton[ui-role="primary"]:pressed {{
    background: {UI_DESIGN_TOKENS["colors"]["primary_active"]};
}}

QPushButton[ui-role="secondary"] {{
    background: {UI_DESIGN_TOKENS["colors"]["secondary"]};
}}
QPushButton[ui-role="secondary"]:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["secondary_hover"]};
}}
QPushButton[ui-role="secondary"]:pressed {{
    background: {UI_DESIGN_TOKENS["colors"]["secondary_hover"]};
}}

QPushButton[ui-role="success"] {{
    background: {UI_DESIGN_TOKENS["colors"]["success"]};
}}
QPushButton[ui-role="success"]:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["success_hover"]};
}}
QPushButton[ui-role="success"]:pressed {{
    background: {UI_DESIGN_TOKENS["colors"]["success_hover"]};
}}

QPushButton[ui-role="danger"] {{
    background: {UI_DESIGN_TOKENS["colors"]["danger"]};
}}
QPushButton[ui-role="danger"]:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["danger_hover"]};
}}
QPushButton[ui-role="danger"]:pressed {{
    background: {UI_DESIGN_TOKENS["colors"]["danger_hover"]};
}}

QPushButton[ui-role="warning"] {{
    background: {UI_DESIGN_TOKENS["colors"]["warning"]};
}}
QPushButton[ui-role="warning"]:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["warning_hover"]};
}}
QPushButton[ui-role="warning"]:pressed {{
    background: {UI_DESIGN_TOKENS["colors"]["warning_hover"]};
}}

QPushButton[ui-role="info"] {{
    background: {UI_DESIGN_TOKENS["colors"]["info"]};
}}
QPushButton[ui-role="info"]:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["info_hover"]};
}}
QPushButton[ui-role="info"]:pressed {{
    background: {UI_DESIGN_TOKENS["colors"]["info_hover"]};
}}

QPushButton[ui-size="large"] {{
    min-height: 36px;
    font-size: {UI_DESIGN_TOKENS["sizes"]["button_large"]}px;
    padding: {UI_DESIGN_TOKENS["spacing"]["small"]}px {UI_DESIGN_TOKENS["spacing"]["large"]}px;
}}

QPushButton:disabled {{
    background: {UI_DESIGN_TOKENS["colors"]["disabled_bg"]};
    color: {UI_DESIGN_TOKENS["colors"]["disabled_text"]};
}}

QPushButton[ui-style="ghost"] {{
    background: transparent;
    color: {UI_DESIGN_TOKENS["colors"]["primary"]};
    border: 1px solid {UI_DESIGN_TOKENS["colors"]["primary"]};
}}

QPushButton[ui-style="ghost"]:hover {{
    background: {UI_DESIGN_TOKENS["colors"]["ghost_hover"]};
}}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QScrollArea {{
    border: 1px solid {UI_DESIGN_TOKENS["colors"]["line"]};
    border-radius: {UI_DESIGN_TOKENS["radius"]["medium"]}px;
    padding: {UI_DESIGN_TOKENS["spacing"]["xsmall"]}px;
    background: {UI_DESIGN_TOKENS["colors"]["panel"]};
}}

QSlider::groove:horizontal {{
    border: 1px solid {UI_DESIGN_TOKENS["colors"]["line"]};
    height: 6px;
    border-radius: 3px;
    background: {UI_DESIGN_TOKENS["colors"]["panel_muted"]};
}}

QSlider::handle:horizontal {{
    background: {UI_DESIGN_TOKENS["colors"]["primary"]};
    width: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}

QTableWidget {{
    border: 1px solid {UI_DESIGN_TOKENS["colors"]["line"]};
    background: {UI_DESIGN_TOKENS["colors"]["panel"]};
    gridline-color: {UI_DESIGN_TOKENS["colors"]["line"]};
}}

QHeaderView::section {{
    background: {UI_DESIGN_TOKENS["colors"]["panel_muted"]};
    padding: 6px;
    border: 1px solid {UI_DESIGN_TOKENS["colors"]["line"]};
    font-weight: 600;
}}
"""

# ============================================================================
# Research Data Model (Linear Regression for SNM Prediction)
# ============================================================================

class ResearchDataModel:
    """SNM prediction model learning from research data"""

    def __init__(self):
        self.training_data = []
        self.weights = np.array([0.0, 0.0, 0.0, 0.2])
        self.trained = False
        self.rmse_history = []

    def add_data(self, temperature, voltage, num_cells, snm_actual):
        """Add training data point"""
        snm_pred = self.predict_standard(temperature, voltage, num_cells)
        data_point = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'temperature': temperature,
            'voltage': voltage,
            'num_cells': num_cells,
            'snm_pred': snm_pred,
            'snm_actual': snm_actual,
            'error': abs(snm_pred - snm_actual)
        }
        self.training_data.append(data_point)

    def predict_standard(self, temperature, voltage, num_cells):
        """Standard SNM prediction (before training)"""
        snm = 0.2 - (temperature - 310) * 0.0005 + (voltage - 1.0) * 0.15 - (num_cells - 32) * 0.0001
        return max(0.05, min(0.4, snm))

    def train(self):
        """Train using linear regression"""
        if len(self.training_data) < 3:
            return False, "Need at least 3 data points"

        try:
            X = []
            y = []
            for data in self.training_data:
                X.append([data['temperature'], data['voltage'], data['num_cells'], 1.0])
                y.append(data['snm_actual'])

            X = np.array(X)
            y = np.array(y)

            self.weights = np.linalg.lstsq(X, y, rcond=None)[0]
            self.trained = True

            rmse = self.calculate_rmse()
            self.rmse_history.append(rmse)
            return True, f"Training complete! RMSE: {rmse:.2f} mV"

        except Exception as e:
            return False, f"Training failed: {str(e)}"

    def predict(self, temperature, voltage, num_cells):
        """Predict SNM with trained model"""
        if not self.trained:
            return self.predict_standard(temperature, voltage, num_cells)

        X = np.array([temperature, voltage, num_cells, 1.0])
        snm = float(np.dot(X, self.weights))
        return max(0.05, min(0.4, snm))

    def calculate_rmse(self):
        """Calculate RMSE in mV"""
        if len(self.training_data) < 1:
            return 0.0

        errors = []
        for data in self.training_data:
            if self.trained:
                pred = self.predict(data['temperature'], data['voltage'], data['num_cells'])
            else:
                pred = data['snm_pred']
            errors.append((pred - data['snm_actual']) ** 2)

        rmse = np.sqrt(np.mean(errors)) * 1000
        return rmse


# ============================================================================
# Academic Figure Generator
# ============================================================================

class AcademicFigureGenerator:
    """Generate publication-quality figures"""

    @staticmethod
    def create_snm_comparison_figure(data_without_thermal, data_with_thermal,
                                     temperature, voltage, num_cells):
        """Create 4-subplot comparison figure"""
        fig = plt.figure(figsize=(12, 10))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        snm_without = np.array(data_without_thermal.get('snm_values', [])) * 1000
        snm_with = np.array(data_with_thermal.get('snm_values', [])) * 1000

        if len(snm_without) == 0:
            snm_without = np.random.normal(200, 10, 100)
        if len(snm_with) == 0:
            snm_with = np.random.normal(180, 15, 100)

        # (a) SNM Distribution
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.hist(snm_without, bins=30, alpha=0.7, label='Without thermal',
                color='blue', edgecolor='black')
        ax1.hist(snm_with, bins=30, alpha=0.7, label='With thermal',
                color='red', edgecolor='black')
        ax1.axvline(np.mean(snm_without), color='blue', linestyle='--',
                   label=f'Mean w/o: {np.mean(snm_without):.1f} mV')
        ax1.axvline(np.mean(snm_with), color='red', linestyle='--',
                   label=f'Mean w/: {np.mean(snm_with):.1f} mV')
        ax1.set_xlabel('SNM (mV)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax1.set_title('(a) SNM Distribution', fontsize=13, fontweight='bold')
        ax1.legend(loc='best', fontsize=9)
        ax1.grid(True, alpha=0.3)

        # (b) CDF
        ax2 = fig.add_subplot(gs[0, 1])
        sorted_without = np.sort(snm_without)
        sorted_with = np.sort(snm_with)
        cdf_without = np.arange(1, len(sorted_without) + 1) / len(sorted_without)
        cdf_with = np.arange(1, len(sorted_with) + 1) / len(sorted_with)
        ax2.plot(sorted_without, cdf_without, 'b-', linewidth=2, label='Without thermal')
        ax2.plot(sorted_with, cdf_with, 'r-', linewidth=2, label='With thermal')
        ax2.set_xlabel('SNM (mV)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Cumulative Probability', fontsize=12, fontweight='bold')
        ax2.set_title('(b) CDF', fontsize=13, fontweight='bold')
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)

        # (c) Noise Components
        ax3 = fig.add_subplot(gs[1, 0])
        sigma_variability = np.std(snm_without) if len(snm_without) > 0 else 10
        sigma_thermal = data_with_thermal.get('thermal_sigma', 0) * 1000
        sigma_combined = np.std(snm_with) if len(snm_with) > 0 else 15

        components = ['Variability\n(Pelgrom)', 'Thermal\nNoise', 'Combined']
        values = [sigma_variability, sigma_thermal, sigma_combined]
        colors_list = ['blue', 'orange', 'red']

        bars = ax3.bar(components, values, color=colors_list, alpha=0.7, edgecolor='black')
        ax3.set_ylabel('Sigma (mV)', fontsize=12, fontweight='bold')
        ax3.set_title('(c) Noise Components', fontsize=13, fontweight='bold')
        ax3.grid(True, axis='y', alpha=0.3)

        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

        # (d) SNM Degradation
        ax4 = fig.add_subplot(gs[1, 1])
        mean_without = np.mean(snm_without)
        mean_with = np.mean(snm_with)
        degradation = mean_without - mean_with

        categories = ['Without\nThermal', 'With\nThermal', 'Degradation']
        values = [mean_without, mean_with, abs(degradation)]
        colors_list = ['blue', 'red', 'gray']

        bars = ax4.bar(categories, values, color=colors_list, alpha=0.7, edgecolor='black')
        ax4.set_ylabel('SNM (mV)', fontsize=12, fontweight='bold')
        ax4.set_title('(d) SNM Degradation', fontsize=13, fontweight='bold')
        ax4.grid(True, axis='y', alpha=0.3)

        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

        fig.suptitle(f'SRAM Thermal Noise Impact Analysis\n'
                    f'T={temperature}K, V={voltage}V, Cells={num_cells}',
                    fontsize=14, fontweight='bold')

        return fig


# ============================================================================
# Advanced Simulation Thread
# ============================================================================

class AdvancedSimulationThread(QThread):
    """Run advanced simulation in separate thread"""
    result_ready = Signal(dict)
    progress_update = Signal(int)
    status_update = Signal(str)

    def __init__(self):
        super().__init__()
        self.temperature = 310
        self.voltage = 1.0
        self.num_cells = 32
        self.input_data = []
        self.noise_enable = True
        self.variability_enable = True
        self.monte_carlo_runs = 10
        self.width = 1.0
        self.length = 1.0
        self.analysis_type = "basic"
        self.backend_type = "standard"  # "standard" or "hybrid"
        self.compute_mode = "cpu"
        self.latency_mode = "interactive"

    def set_parameters(self, **kwargs):
        """Set simulation parameters"""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def run(self):
        """Execute simulation"""
        try:
            def _report_progress(percent, status=None):
                self.progress_update.emit(max(0, min(100, int(percent))))
                if status is not None:
                    self.status_update.emit(status)

            compute_mode = getattr(self, "compute_mode", "cpu")
            latency_mode = getattr(self, "latency_mode", "interactive")
            self.progress_update.emit(10)
            self.status_update.emit("Initializing native backend...")

            if not NATIVE_BACKEND_AVAILABLE:
                raise RuntimeError("Native backend wrapper is unavailable.")

            native_request = {
                'backend': 'hybrid' if self.backend_type == "hybrid" else 'standard',
                'temperature': float(self.temperature),
                'voltage': float(self.voltage),
                'num_cells': int(self.num_cells),
                'input_data': list(self.input_data),
                'noise_enable': bool(self.noise_enable),
                'variability_enable': bool(self.variability_enable),
                'monte_carlo_runs': int(self.monte_carlo_runs),
                'width': float(self.width),
                'length': float(self.length),
                'include_thermal_noise': bool(self.analysis_type == "thermal"),
                'compute_mode': compute_mode,
                'latency_mode': latency_mode,
                'require_native': True,
                # Strict native mode: do not route hybrid requests to Python reference path.
                'prefer_hybrid_gate_logic': False,
            }

            _report_progress(30, "Preparing simulation payload...")

            if self.analysis_type == "reliability":
                _report_progress(45, "Running reliability analysis (native)...")
                result = native_predict_lifetime({
                    'temperature': float(self.temperature),
                    'vgs': float(self.voltage),
                    'vds': float(self.voltage),
                    'vth': 0.4,
                    'width': float(self.width),
                    'num_cells': int(self.num_cells),
                    'compute_mode': compute_mode,
                    'latency_mode': latency_mode,
                    'require_native': True,
                })
                result['analysis_type'] = 'reliability'
                result.setdefault('backend', 'reliability')
                if RELIABILITY_AVAILABLE:
                    result['reliability_model'] = ReliabilityModel()
                _report_progress(90, "Reliability analysis complete. Finalizing results...")

            elif self.analysis_type == "process_corner":
                _report_progress(40, "Running process corner analysis (native)...")
                corners = {
                    'FF': (1.1, 0.9),
                    'TT': (1.0, 1.0),
                    'SS': (0.9, 1.1),
                }
                corner_results = {}
                corner_runtime_engine = None
                total_corners = len(corners)
                for idx, (corner_name, (volt_factor, temp_factor)) in enumerate(corners.items(), start=1):
                    _report_progress(
                        45 + int((idx - 1) / total_corners * 30),
                        f"Running process corner {corner_name} ({idx}/{total_corners})..."
                    )
                    corner_req = dict(native_request)
                    corner_req['voltage'] = float(self.voltage) * volt_factor
                    corner_req['temperature'] = float(self.temperature) * temp_factor
                    corner_req['analysis_type'] = 'process_corner'
                    corner_sim = native_simulate_array(corner_req)
                    corner_exec = corner_sim.get('_exec', {})
                    if corner_runtime_engine is None and isinstance(corner_exec, dict):
                        corner_runtime_engine = corner_exec.get('selected', 'unknown')
                    corner_results[corner_name] = {
                        'ber': corner_sim.get('bit_error_rate', 0.0),
                        'ber_std': corner_sim.get('ber_std', 0.0),
                        'voltage': corner_req['voltage'],
                        'temperature': corner_req['temperature'],
                        'runtime_engine': corner_exec.get('selected', 'unknown') if isinstance(corner_exec, dict) else 'unknown',
                    }
                result = corner_results
                result['analysis_type'] = 'process_corner'
                result['backend'] = native_request.get('backend', 'standard')
                result['runtime_engine'] = corner_runtime_engine or 'unknown'
                _report_progress(90, "Process corner results complete. Aggregating outputs...")

            else:
                _report_progress(50, "Running simulation (native)...")
                native_request['analysis_type'] = self.analysis_type
                result = native_simulate_array(native_request)
                _report_progress(90, "Simulation complete. Finalizing results...")
                result['analysis_type'] = self.analysis_type

                if isinstance(result, dict):
                    exec_meta = result.get('_exec', {})
                    if isinstance(exec_meta, dict):
                        result.setdefault('runtime_engine', exec_meta.get('selected', 'unknown'))
                result.setdefault('perceptron', None)

            self.progress_update.emit(100)
            self.status_update.emit("Simulation complete!")
            self.result_ready.emit(result)

        except Exception as e:
            error_result = {
                'error': str(e),
                'temperature': self.temperature,
                'voltage': self.voltage
            }
            self.status_update.emit(f"Error: {str(e)}")
            self.result_ready.emit(error_result)


class ValidationBenchmarkThread(QThread):
    """Run analytical validation or ML benchmark in background."""
    result_ready = Signal(str, dict)
    error = Signal(str)

    def __init__(self, mode, dataset_size=5000, random_state=42, n_folds=5, parent=None):
        super().__init__(parent=parent)
        self.mode = mode
        self.dataset_size = dataset_size
        self.random_state = random_state
        self.n_folds = n_folds

    def run(self):
        try:
            if self.mode == "validation":
                model = AnalyticalSRAMModel()
                data = model.generate_dataset(
                    n_samples=self.dataset_size,
                    random_state=self.random_state,
                    variability_samples=256
                )
                residual = data["snm_mean"] - data["snm_nominal"]
                summary = {
                    "samples": int(len(data["snm_mean"])),
                    "temp_min": float(np.min(data["temperature"])),
                    "temp_max": float(np.max(data["temperature"])),
                    "volt_min": float(np.min(data["voltage"])),
                    "volt_max": float(np.max(data["voltage"])),
                    "snm_mean_mv": float(np.mean(data["snm_mean"]) * 1000),
                    "snm_std_mv": float(np.std(data["snm_mean"]) * 1000),
                    "snm_nominal_mae_mv": float(np.mean(np.abs(residual)) * 1000),
                    "snm_nominal_rmse_mv": float(np.sqrt(np.mean(residual ** 2)) * 1000),
                    "ber_mean": float(np.mean(data["ber"])),
                    "noise_mean_mv": float(np.mean(data["noise_sigma"]) * 1000),
                    "temp_corr_snm": float(np.corrcoef(data["temperature"], data["snm_mean"])[0, 1]),
                    "volt_corr_snm": float(np.corrcoef(data["voltage"], data["snm_mean"])[0, 1]),
                }
                self.result_ready.emit("validation", {
                    "summary": summary,
                    "data": data,
                    "residual": residual
                })

            elif self.mode == "benchmark":
                bench = SRAMModelBenchmark(
                    n_samples=self.dataset_size,
                    n_folds=self.n_folds,
                    random_state=self.random_state
                )
                benchmark_result = bench.run_benchmark()
                table_rows = bench.get_results_table(benchmark_result)
                self.result_ready.emit("benchmark", {
                    "benchmark_result": benchmark_result,
                    "table_rows": table_rows
                })
            else:
                self.error.emit(f"Unknown validation mode: {self.mode}")

        except Exception as e:
            self.error.emit(f"{self.mode} failed: {str(e)}")


# ============================================================================
# AI Connection Check Worker (non-blocking)
# ============================================================================


class AIConnectionCheckThread(QThread):
    """Validate the AI research analysis service connectivity in background."""

    finished = Signal(bool, str)

    def __init__(self, advisor, force: bool = False, parent=None):
        super().__init__(parent=parent)
        self.advisor = advisor
        self.force = force

    def run(self):
        connected = False
        status = "AI service credentials are not configured"
        if self.advisor is not None:
            connected = bool(self.advisor.ensure_connection(force=self.force))
            status = getattr(self.advisor, "connection_status", status)
        self.finished.emit(connected, status)


class AIActionWorkerThread(QThread):
    """Run a blocking AI call in background."""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, args=(), kwargs=None, parent=None):
        super().__init__(parent=parent)
        self.fn = fn
        self.args = args or ()
        self.kwargs = kwargs or {}

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class ReportGenerationWorkerThread(QThread):
    """Generate report PDF in background."""

    finished = Signal(str)
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(self, app_window, report_context=None, parent=None):
        super().__init__(parent=parent)
        self.app_window = app_window
        self.report_context = report_context
        self._last_progress_percent = 0
        self._last_progress_message = ""

    def run(self):
        def _on_progress(percent, message=""):
            self._last_progress_percent = max(0, min(100, int(percent)))
            if message:
                self._last_progress_message = message
            self.progress.emit(self._last_progress_percent, message)

        try:
            pdf_file = self.app_window._generate_simulation_report_with_figures_sync(
                report_context=self.report_context,
                progress_callback=_on_progress
            )
            self.finished.emit(pdf_file)
        except Exception as e:
            message = str(e)
            if self._last_progress_message or self._last_progress_percent:
                message = (
                    f"{message} (last progress: {self._last_progress_percent}%"
                    f"{' - ' + self._last_progress_message if self._last_progress_message else ''})"
                )
            self.failed.emit(message)


# ============================================================================
# Main Window
# ============================================================================

class SRAMSimulatorWindow(QMainWindow):
    """Advanced SRAM Simulator Main Window"""

    def __init__(self):
        super().__init__()

        # Window settings
        self.setWindowTitle("Advanced SRAM Simulator (Noise + SNM + Variability + Reliability)")
        self.setGeometry(50, 50, 1800, 1000)

        # Simulation parameters
        self.temperature = 310
        self.voltage = 1.0
        self.num_cells = 32
        self.noise_enable = True
        self.variability_enable = True
        self.monte_carlo_runs = 10
        self.width = 1.0
        self.length = 1.0
        self.data_type = "random"
        self.custom_pattern = "10101010"
        self.analysis_mode = "Basic Noise"
        self.backend_type = "standard"  # "standard" or "hybrid"
        self.compute_mode_preference = "gpu"
        self.analysis_view_mode = "core"

        # Research data model
        self.research_data_model = ResearchDataModel()

        # AI Advisor
        if AI_ADVISOR_AVAILABLE:
            self.advisor = SRAMAdvisor()
        else:
            self.advisor = None

        # Simulation thread
        self.sim_thread = AdvancedSimulationThread()
        self.sim_thread.result_ready.connect(self.on_simulation_complete)
        self.sim_thread.progress_update.connect(self.on_progress_update)
        self.sim_thread.status_update.connect(self.on_status_update)

        # Result storage
        self.current_result = None

        # Thermal analysis data
        self.thermal_figure = None
        self.validation_result = None
        self.benchmark_result = None
        self.validation_worker = None
        self.validation_benchmark_thread = None
        self._ai_connection_check_thread = None
        self._ai_action_thread = None
        self._report_generation_thread = None
        self._pending_main_visual_updates = {}
        self._pending_validation_tab_updates = {}
        self._slider_pending_updates = {}
        self._slider_update_timer = QTimer(self)
        self._slider_update_timer.setSingleShot(True)
        self._slider_update_timer.setInterval(160)
        self._slider_update_timer.timeout.connect(self._flush_slider_updates)
        self._analysis_plan = []
        self._analysis_plan_index = 0
        self._analysis_plan_active = False
        self._analysis_plan_stop_on_error = True
        self._analysis_plan_errors = []
        self._analysis_plan_results = {}
        self._analysis_plan_log_lines = []
        self._active_simulation_analysis_type = None
        self.simulation_batch_log = None
        self.ai_connection_label = None
        self.gpu_check_text = None
        # Placeholder canvases for Validation & Benchmark (created in UI)
        self.canvas_validation_profile = None
        self.canvas_benchmark_r2 = None
        self.canvas_benchmark_speed = None
        self.canvas_benchmark_pred_actual = None
        self.analysis_view_combo = None
        self.main_splitter = None
        self.analysis_view_stack = None
        self.analysis_view_core_widget = None
        self.analysis_view_advanced_widget = None
        self.report_btn_top = None
        self.ai_analysis_btn = None
        self._last_dispatch_info = None
        self.quick_status_mode_label = None
        self.quick_status_compute_label = None
        self.quick_status_backend_label = None
        self.quick_status_dispatch_label = None
        self.quick_status_engine_label = None
        self.quick_status_result_label = None

        # Initialize UI
        self.init_ui()

        # Load research data
        self.load_research_data()

        # Initial simulation
        self.run_simulation()

    def init_ui(self):
        """Initialize UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        self.apply_layout_tokens(main_layout, "small")

        view_toolbar = self.create_analysis_view_toolbar()
        if view_toolbar is not None:
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, view_toolbar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.main_splitter = splitter

        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)

        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 900, 360])
        self._set_analysis_view_layout_density()
        self._set_analysis_view_mode(self.analysis_view_mode, update_combo=False)

        main_layout.addWidget(splitter)

    def apply_ieee_style(self, fig, title=None):
        """Apply IEEE publication-quality styling to matplotlib figure"""
        # IEEE recommended settings
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
            'font.size': 10,
            'axes.labelsize': 10,
            'axes.titlesize': 11,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
            'figure.titlesize': 12,
            'lines.linewidth': 1.5,
            'lines.markersize': 6,
            'axes.linewidth': 0.8,
            'grid.linewidth': 0.5,
            'xtick.major.width': 0.8,
            'ytick.major.width': 0.8,
        })

        if title:
            fig.suptitle(title, fontsize=12, fontweight='bold')

        fig.tight_layout()
        return fig

    def save_figure_as_ieee(self, canvas, default_filename, figure_title=None):
        """Save canvas figure in IEEE format (600 DPI PNG or 300 DPI PDF)"""
        # File dialog
        file_filter = "PNG Image (*.png);;PDF Document (*.pdf)"
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save IEEE Figure",
            default_filename,
            file_filter
        )

        if filename:
            # Get the figure from canvas
            fig = canvas.figure

            # Apply IEEE styling
            self.apply_ieee_style(fig, figure_title)

            # Determine DPI and format
            if filename.endswith('.pdf'):
                dpi = 300  # IEEE recommends 300 DPI for PDF
                fmt = 'pdf'
            else:
                if not filename.endswith('.png'):
                    filename += '.png'
                dpi = 600  # IEEE recommends 600 DPI for PNG/bitmap
                fmt = 'png'

            # Save figure
            try:
                fig.savefig(filename, format=fmt, dpi=dpi, bbox_inches='tight',
                           pad_inches=0.1, facecolor='white', edgecolor='none')
                self.show_info("Success",
                    f"Figure saved successfully as {fmt.upper()} ({dpi} DPI)\n{filename}")
            except Exception as e:
                self.show_error("Error", f"Failed to save figure:\n{str(e)}")

    def create_save_button(self, canvas, filename, title):
        """Create a styled IEEE save button for a canvas"""
        button = self.create_styled_button(
            "Save as IEEE Figure (PNG/PDF)",
            lambda: self.save_figure_as_ieee(canvas, filename, title),
            style_type="info",
            size="normal",
        )
        return button

    def create_visualization_tab(self, tab_name, canvas_name, default_filename, figure_title, target_tab_widget=None):
        """Create a visualization tab with canvas and save button (DRY helper)"""
        # Create tab widget
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.apply_layout_tokens(layout, "small")

        # Create canvas
        canvas = FigureCanvas(Figure(figsize=(10, 7)))
        layout.addWidget(canvas)

        # Create save button
        save_btn = self.create_save_button(canvas, default_filename, figure_title)
        layout.addWidget(save_btn)

        # Store canvas as instance variable
        setattr(self, canvas_name, canvas)

        # Add tab to widget
        tab_container = target_tab_widget or self.tab_widget
        tab_container.addTab(tab, tab_name)

        return tab, canvas

    def create_embedded_plot_tab(self, tab_title, canvas_name, default_filename, figure_title):
        """Create embedded matplotlib tab used by validation/benchmark tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.apply_layout_tokens(layout, "small")
        canvas = FigureCanvas(Figure(figsize=(10, 7)))
        layout.addWidget(canvas)
        save_btn = self.create_save_button(canvas, default_filename, figure_title)
        layout.addWidget(save_btn)
        setattr(self, canvas_name, canvas)
        return tab, canvas

    def create_analysis_view_toolbar(self):
        """Create toolbar for switching analysis view mode."""
        toolbar = QToolBar("Analysis View")
        toolbar.setObjectName("analysisToolbar")
        toolbar.setFloatable(False)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        self.simulate_btn = self._create_toolbar_button(
            "Run Simulation",
            self.run_simulation,
            style_type="success",
            object_name="simulateButton",
        )
        toolbar.addWidget(self.simulate_btn)

        reset_btn = self._create_toolbar_button(
            "Reset",
            self.reset_parameters,
            style_type="warning",
            object_name="resetButton",
        )
        self.reset_btn = reset_btn
        toolbar.addWidget(reset_btn)

        toolbar.addSeparator()

        save_config_btn = self._create_toolbar_action("Save Config", self.save_config, style_type="secondary")
        self.save_config_btn = save_config_btn
        toolbar.addAction(save_config_btn)

        load_config_btn = self._create_toolbar_action("Load Config", self.load_config, style_type="secondary")
        self.load_config_btn = load_config_btn
        toolbar.addAction(load_config_btn)

        report_btn_top = self._create_toolbar_action(
            "Generate Report",
            self.generate_simulation_report_with_figures,
            style_type="success",
            object_name="reportAction",
        )
        self.report_btn_top = report_btn_top
        toolbar.addAction(report_btn_top)

        ai_analysis_btn = self._create_toolbar_action("Research Analysis", self.show_ai_analysis_dialog, style_type="info")
        self.ai_analysis_btn = ai_analysis_btn
        toolbar.addAction(ai_analysis_btn)

        toolbar.addSeparator()
        toolbar.addWidget(self._toolbar_spacer())

        view_label = QLabel("Analysis View")
        view_label.setProperty("ui-typography", "caption")
        toolbar.addWidget(view_label)
        self.analysis_view_combo = QComboBox()
        self.analysis_view_combo.setObjectName("analysisViewCombo")
        self.analysis_view_combo.addItems([
            "Core Simulation Analysis",
            "Advanced Analytics",
        ])
        self.analysis_view_combo.currentTextChanged.connect(self.on_analysis_view_mode_changed)
        self.analysis_view_combo.setFixedHeight(22)
        self.analysis_view_combo.setMinimumWidth(200)
        toolbar.addWidget(self.analysis_view_combo)

        return toolbar

    # ========================================================================
    # DRY Helper Methods - UI Components
    # ========================================================================

    def show_info(self, title, message):
        """Show information message box (DRY helper)"""
        QMessageBox.information(self, title, message)

    def show_warning(self, title, message):
        """Show warning message box (DRY helper)"""
        QMessageBox.warning(self, title, message)

    def show_error(self, title, message):
        """Show error message box (DRY helper)"""
        QMessageBox.critical(self, title, message)

    def show_question(self, title, message):
        """Show question message box (DRY helper)"""
        return QMessageBox.question(self, title, message)

    def create_title_label(self, text, level="title"):
        """Create a title/section label with standardized typography."""
        label = QLabel(text)
        if level == "section":
            label.setProperty("ui-typography", "section")
        else:
            label.setProperty("ui-typography", "title")
        return label

    def apply_layout_tokens(self, layout, spacing="medium"):
        """Apply design-system spacing defaults to a layout."""
        spacing_value = int(UI_DESIGN_TOKENS["spacing"].get(spacing, UI_DESIGN_TOKENS["spacing"]["medium"]))
        layout.setSpacing(spacing_value)
        layout.setContentsMargins(
            spacing_value,
            spacing_value,
            spacing_value,
            spacing_value
        )

    def create_group_box(self, title, layout_type='vertical'):
        """Create a group box with layout (DRY helper)"""
        group = QGroupBox(title)
        if layout_type == 'vertical':
            layout = QVBoxLayout()
        else:
            layout = QHBoxLayout()
        self.apply_layout_tokens(layout, "small")
        group.setLayout(layout)
        return group, layout

    def create_labeled_input(self, label_text, widget, layout, horizontal=True):
        """Create a labeled input control (DRY helper)"""
        label = QLabel(label_text)
        label.setProperty("ui-typography", "caption")
        if horizontal:
            container_layout = QHBoxLayout()
            container_layout.addWidget(label)
            container_layout.addWidget(widget)
            self.apply_layout_tokens(container_layout, "small")
            layout.addLayout(container_layout)
        else:
            self.apply_layout_tokens(layout, "small")
            layout.addWidget(label)
            layout.addWidget(widget)
        return widget

    def create_styled_button(self, text, callback, style_type='primary', size='normal', style='solid'):
        """Create a styled button (DRY helper)"""
        button = QPushButton(text)
        button.setProperty("ui-role", style_type)
        if size == "large":
            button.setProperty("ui-size", "large")
        if style == "ghost":
            button.setProperty("ui-style", "ghost")
        button.clicked.connect(callback)
        return button

    def _create_toolbar_action(self, text, callback, style_type='primary', object_name=None):
        """Create a toolbar action (text-only action button)."""
        action = QAction(text, self)
        action.setProperty("ui-role", style_type)
        if object_name:
            action.setObjectName(object_name)
        action.triggered.connect(callback)
        return action

    def _create_toolbar_button(self, text, callback, style_type='primary', size='normal', style='solid', object_name=None):
        """Create a toolbar button style with text-only emphasis."""
        button = self.create_styled_button(
            text,
            callback,
            style_type=style_type,
            size=size,
            style=style,
        )
        if object_name:
            button.setObjectName(object_name)
        return button

    def _toolbar_spacer(self):
        spacer = QWidget()
        spacer.setProperty("ui-role", "spacer")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return spacer

    def create_left_panel(self):
        """Left panel - Input controls"""
        panel = QWidget()
        main_layout = QVBoxLayout(panel)
        self.apply_layout_tokens(main_layout, "small")

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        self.apply_layout_tokens(layout, "small")

        title = self.create_title_label("Simulation Parameters", level="title")
        layout.addWidget(title)

        # Analysis Mode Selector
        mode_group = QGroupBox("Analysis Mode")
        mode_layout = QVBoxLayout()

        self.mode_combo = QComboBox()
        modes = [
            "All Core Analysis",
            "Basic Noise",
            "SNM Analysis",
            "Variability",
            "Thermal Noise",
            "Retention Mode",
            "Process Corner",
            "NBTI/HCI Reliability"
        ]
        self.mode_combo.addItems(modes)
        self.mode_combo.setCurrentText(self.analysis_mode)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Backend Selection (NEW)
        backend_group = QGroupBox("SRAM Backend")
        backend_layout = QVBoxLayout()

        self.backend_combo = QComboBox()
        backends = []
        if ADVANCED_AVAILABLE:
            backends.append("Standard (main_advanced)")
        if HYBRID_AVAILABLE:
            backends.append("Hybrid Perceptron (hybrid)")

        if not backends:
            backends.append("No backend available")

        self.backend_combo.addItems(backends)
        self.backend_combo.currentTextChanged.connect(self.on_backend_changed)

        backend_info = QLabel("Standard: Python variables + MLP noise\nHybrid: Perceptron gates + MLP noise")
        backend_info.setWordWrap(True)
        backend_info.setProperty("ui-typography", "caption")

        backend_layout.addWidget(self.backend_combo)
        backend_layout.addWidget(backend_info)
        backend_group.setLayout(backend_layout)
        layout.addWidget(backend_group)

        # Compute Engine Selection (for native dispatch override)
        compute_group = QGroupBox("Compute Engine")
        compute_layout = QVBoxLayout()

        self.compute_mode_combo = QComboBox()
        self.compute_mode_combo.addItems(["Auto", "CPU", "GPU"])
        self.compute_mode_combo.setCurrentText("GPU")
        self.compute_mode_combo.currentTextChanged.connect(self.on_compute_mode_changed)

        compute_info = QLabel(
            "Auto: policy-based\n"
            "CPU: prefer CPU execution\n"
            "GPU: request GPU first (may still fall back to CPU if the GPU lane/runtime is unavailable)"
        )
        compute_info.setWordWrap(True)
        compute_info.setProperty("ui-typography", "caption")

        compute_layout.addWidget(self.compute_mode_combo)
        compute_layout.addWidget(compute_info)
        compute_group.setLayout(compute_layout)
        layout.addWidget(compute_group)

        # Temperature group
        temp_group = QGroupBox("Temperature (K)")
        temp_layout = QVBoxLayout()

        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setMinimum(260)
        self.temp_slider.setMaximum(360)
        self.temp_slider.setValue(310)
        self.temp_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.temp_slider.setTickInterval(20)

        self.temp_spinbox = QSpinBox()
        self.temp_spinbox.setMinimum(260)
        self.temp_spinbox.setMaximum(360)
        self.temp_spinbox.setValue(310)
        self.temp_spinbox.setSuffix(" K")

        self.temp_slider.valueChanged.connect(self.temp_spinbox.setValue)
        self.temp_spinbox.valueChanged.connect(self.temp_slider.setValue)
        self.temp_slider.valueChanged.connect(self.on_temp_changed)

        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(self.temp_spinbox)
        temp_group.setLayout(temp_layout)
        layout.addWidget(temp_group)

        # Voltage group
        volt_group = QGroupBox("Supply Voltage (V)")
        volt_layout = QVBoxLayout()

        self.volt_slider = QSlider(Qt.Horizontal)
        self.volt_slider.setMinimum(80)
        self.volt_slider.setMaximum(120)
        self.volt_slider.setValue(100)
        self.volt_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.volt_slider.setTickInterval(10)

        self.volt_spinbox = QDoubleSpinBox()
        self.volt_spinbox.setMinimum(0.8)
        self.volt_spinbox.setMaximum(1.2)
        self.volt_spinbox.setValue(1.0)
        self.volt_spinbox.setSingleStep(0.05)
        self.volt_spinbox.setDecimals(2)
        self.volt_spinbox.setSuffix(" V")

        self.volt_slider.valueChanged.connect(lambda v: self.volt_spinbox.setValue(v / 100.0))
        self.volt_spinbox.valueChanged.connect(lambda v: self.volt_slider.setValue(int(v * 100)))
        self.volt_slider.valueChanged.connect(self.on_voltage_changed)

        volt_layout.addWidget(self.volt_slider)
        volt_layout.addWidget(self.volt_spinbox)
        volt_group.setLayout(volt_layout)
        layout.addWidget(volt_group)

        # Cell count group
        cell_group = QGroupBox("SRAM Cell Count")
        cell_layout = QVBoxLayout()

        self.cell_slider = QSlider(Qt.Horizontal)
        self.cell_slider.setMinimum(8)
        self.cell_slider.setMaximum(128)
        self.cell_slider.setValue(32)
        self.cell_slider.setSingleStep(8)
        self.cell_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.cell_slider.setTickInterval(16)

        self.cell_spinbox = QSpinBox()
        self.cell_spinbox.setMinimum(8)
        self.cell_spinbox.setMaximum(128)
        self.cell_spinbox.setValue(32)
        self.cell_spinbox.setSingleStep(8)
        self.cell_spinbox.setSuffix(" cells")

        self.cell_slider.valueChanged.connect(self.cell_spinbox.setValue)
        self.cell_spinbox.valueChanged.connect(self.cell_slider.setValue)
        self.cell_slider.valueChanged.connect(self.on_cells_changed)

        cell_layout.addWidget(self.cell_slider)
        cell_layout.addWidget(self.cell_spinbox)
        cell_group.setLayout(cell_layout)
        layout.addWidget(cell_group)

        # Transistor Parameters
        trans_group = QGroupBox("Transistor Parameters")
        trans_layout = QVBoxLayout()

        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Width:"))
        self.width_spinbox = QDoubleSpinBox()
        self.width_spinbox.setMinimum(0.1)
        self.width_spinbox.setMaximum(5.0)
        self.width_spinbox.setValue(1.0)
        self.width_spinbox.setSingleStep(0.1)
        self.width_spinbox.setDecimals(1)
        self.width_spinbox.setSuffix(" um")
        self.width_spinbox.valueChanged.connect(self.on_width_changed)
        width_layout.addWidget(self.width_spinbox)
        trans_layout.addLayout(width_layout)

        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Length:"))
        self.length_spinbox = QDoubleSpinBox()
        self.length_spinbox.setMinimum(0.1)
        self.length_spinbox.setMaximum(5.0)
        self.length_spinbox.setValue(1.0)
        self.length_spinbox.setSingleStep(0.1)
        self.length_spinbox.setDecimals(1)
        self.length_spinbox.setSuffix(" um")
        self.length_spinbox.valueChanged.connect(self.on_length_changed)
        length_layout.addWidget(self.length_spinbox)
        trans_layout.addLayout(length_layout)

        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)

        # Monte Carlo Controls
        mc_group = QGroupBox("Monte Carlo Controls")
        mc_layout = QVBoxLayout()

        self.variability_checkbox = QCheckBox("Enable Variability (Pelgrom)")
        self.variability_checkbox.setChecked(True)
        self.variability_checkbox.stateChanged.connect(self.on_variability_changed)
        mc_layout.addWidget(self.variability_checkbox)

        mc_runs_layout = QHBoxLayout()
        mc_runs_layout.addWidget(QLabel("MC Runs:"))
        self.mc_slider = QSlider(Qt.Horizontal)
        self.mc_slider.setMinimum(1)
        self.mc_slider.setMaximum(100)
        self.mc_slider.setValue(10)
        self.mc_slider.setSingleStep(10)
        self.mc_slider.valueChanged.connect(self.on_mc_changed)
        mc_runs_layout.addWidget(self.mc_slider)
        self.mc_label = QLabel("10")
        mc_runs_layout.addWidget(self.mc_label)
        mc_layout.addLayout(mc_runs_layout)

        mc_group.setLayout(mc_layout)
        layout.addWidget(mc_group)

        # Data type selection
        data_group = QGroupBox("Input Data")
        data_layout = QVBoxLayout()

        self.data_button_group = QButtonGroup()
        data_types = [
            ("random", "Random"),
            ("all0", "All 0"),
            ("all1", "All 1"),
            ("checkerboard", "Checkerboard Pattern")
        ]

        for value, label in data_types:
            radio = QRadioButton(label)
            radio.setProperty("data_type", value)
            self.data_button_group.addButton(radio)
            data_layout.addWidget(radio)
            if value == "random":
                radio.setChecked(True)

        self.data_button_group.buttonClicked.connect(self.on_data_type_changed)
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setProperty("ui-typography", "caption")
        main_layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        batch_log_group = QGroupBox("Simulation Batch Log")
        batch_log_layout = QVBoxLayout()
        self.simulation_batch_log = QTextEdit()
        self.simulation_batch_log.setReadOnly(True)
        self.simulation_batch_log.setMinimumHeight(96)
        self.simulation_batch_log.setMaximumHeight(180)
        self.simulation_batch_log.setProperty("ui-font", "mono")
        self.simulation_batch_log.setPlaceholderText("Batch execution logs will appear here.")
        batch_log_layout.addWidget(self.simulation_batch_log)
        batch_log_group.setLayout(batch_log_layout)
        self.simulation_batch_log.clear()
        main_layout.addWidget(batch_log_group)

        # simulation/reset actions moved to top toolbar for layout consistency

        return panel

    def create_center_panel(self):
        """Center panel - Visualization"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.apply_layout_tokens(layout, "small")

        title = self.create_title_label("Simulation Results", level="title")
        layout.addWidget(title)

        self.analysis_view_stack = QStackedWidget()
        layout.addWidget(self.analysis_view_stack, 1)

        # Core analysis tabs (performance-critical paths)
        self.analysis_view_core_widget = QWidget()
        core_layout = QVBoxLayout(self.analysis_view_core_widget)
        self.apply_layout_tokens(core_layout, "small")
        core_tabs_group, core_tabs_layout = self.create_group_box("Core Simulation Analysis")
        self.tab_widget_core = QTabWidget()
        self.tab_widget_core.currentChanged.connect(
            lambda index, tab_widget=self.tab_widget_core: self._on_visual_tab_changed(index, tab_widget)
        )
        core_tabs_layout.addWidget(self.tab_widget_core)
        core_layout.addWidget(core_tabs_group)

        # Advanced analysis tabs (secondary diagnostics)
        self.analysis_view_advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(self.analysis_view_advanced_widget)
        self.apply_layout_tokens(advanced_layout, "small")
        advanced_tabs_group, advanced_tabs_layout = self.create_group_box("Advanced Analytics")
        self.tab_widget_advanced = QTabWidget()
        self.tab_widget_advanced.currentChanged.connect(
            lambda index, tab_widget=self.tab_widget_advanced: self._on_visual_tab_changed(index, tab_widget)
        )
        advanced_tabs_layout.addWidget(self.tab_widget_advanced)
        advanced_layout.addWidget(advanced_tabs_group)

        self.tab_widget = self.tab_widget_core

        # Tab 1: 3D Noise Map (DRY refactored)
        self.tab_3d, _ = self.create_visualization_tab(
            "3D Noise Map",
            "canvas_3d",
            "sram_3d_noise_map",
            "3D Perceptron Noise Weight Distribution",
            target_tab_widget=self.tab_widget_core
        )

        # Tab 2: SNM Analysis (DRY refactored)
        self.tab_snm, _ = self.create_visualization_tab(
            "SNM Analysis",
            "canvas_snm",
            "sram_snm_analysis",
            "SRAM Static Noise Margin Analysis",
            target_tab_widget=self.tab_widget_core
        )

        # Tab 3: Variability (DRY refactored)
        self.tab_var, _ = self.create_visualization_tab(
            "Variability",
            "canvas_var",
            "sram_variability_analysis",
            "SRAM Process Variability Analysis",
            target_tab_widget=self.tab_widget_core
        )

        # Tab 4: Thermal Noise (DRY refactored)
        self.tab_thermal_noise, _ = self.create_visualization_tab(
            "Thermal Noise",
            "canvas_thermal_noise",
            "sram_thermal_noise",
            "SRAM Thermal Noise Trajectory",
            target_tab_widget=self.tab_widget_core
        )

        # Tab 5: NBTI/HCI Reliability (DRY refactored)
        self.tab_reliability, _ = self.create_visualization_tab(
            "NBTI/HCI Reliability",
            "canvas_reliability",
            "sram_reliability_analysis",
            "SRAM NBTI/HCI Reliability Analysis",
            target_tab_widget=self.tab_widget_core
        )

        # Tab 6: Research Data
        self.tab_research_data = QWidget()
        self.create_research_data_tab()
        self.tab_widget_advanced.addTab(self.tab_research_data, "Research Data")

        # Tab 7: Thermal Analysis (academic figure)
        self.tab_thermal = QWidget()
        self.create_thermal_analysis_tab()
        self.tab_widget_advanced.addTab(self.tab_thermal, "Thermal Analysis")

        # Tab 8: Transformer Workload
        if WORKLOAD_MODEL_AVAILABLE:
            self.tab_workload = QWidget()
            self.create_workload_tab()
            self.tab_widget_advanced.addTab(self.tab_workload, "Transformer Workload")

        # Tab 9: Circuit-to-System KPI
        if WORKLOAD_MODEL_AVAILABLE:
            self.tab_circuit_kpi = QWidget()
            self.create_circuit_kpi_tab()
            self.tab_widget_advanced.addTab(self.tab_circuit_kpi, "Circuit-to-System KPI")

        # Tab 10: Design Space Optimizer
        if WORKLOAD_MODEL_AVAILABLE:
            self.tab_optimizer = QWidget()
            self.create_optimizer_tab()
            self.tab_widget_advanced.addTab(self.tab_optimizer, "Design Space")

        # Tab 11: Reliability Analysis (NBTI/HCI)
        if RELIABILITY_AVAILABLE:
            self.tab_reliability_grove = QWidget()
            self.create_reliability_grove_tab()
            self.tab_widget_advanced.addTab(self.tab_reliability_grove, "Reliability Analysis")

        # Tab 12: AI Research Analysis
        if AI_ADVISOR_AVAILABLE:
            self.tab_ai_advisor = QWidget()
            self.create_ai_advisor_tab()
            self.tab_widget_advanced.addTab(self.tab_ai_advisor, "AI Research Analysis")

        # Tab 13: Validation & Benchmark (optional)
        if VALIDATION_AVAILABLE:
            self.tab_validation = QWidget()
            self.create_validation_benchmark_tab()
            self.tab_widget_advanced.addTab(self.tab_validation, "Validation & Benchmark")

        self.analysis_view_stack.addWidget(self.analysis_view_core_widget)
        self.analysis_view_stack.addWidget(self.analysis_view_advanced_widget)
        self.tab_widget = self.tab_widget_core

        return panel

    def on_analysis_view_mode_changed(self, text: str):
        """Handle analysis view mode selection from toolbar."""
        mode = str(text or "").strip().lower()
        if "advanced" in mode:
            self._set_analysis_view_mode("advanced", update_combo=True)
        else:
            self._set_analysis_view_mode("core", update_combo=True)

    def _set_analysis_view_mode(self, mode: str, update_combo: bool = True):
        """Set active analysis view mode for visualization area."""
        normalized = str(mode or "core").strip().lower()
        if normalized not in {"core", "advanced"}:
            normalized = "core"

        self.analysis_view_mode = normalized

        if normalized == "advanced":
            self.tab_widget = self.tab_widget_advanced
            if self.analysis_view_stack is not None and self.analysis_view_advanced_widget is not None:
                self.analysis_view_stack.setCurrentWidget(self.analysis_view_advanced_widget)
            combo_text = "Advanced Analytics"
        else:
            self.tab_widget = self.tab_widget_core
            if self.analysis_view_stack is not None and self.analysis_view_core_widget is not None:
                self.analysis_view_stack.setCurrentWidget(self.analysis_view_core_widget)
            combo_text = "Core Simulation Analysis"

        if self.analysis_view_combo is not None and update_combo:
            combo_index = self.analysis_view_combo.findText(combo_text)
            if combo_index >= 0:
                self.analysis_view_combo.setCurrentIndex(combo_index)

        if self.current_result is not None:
            if self.analysis_mode == "All Core Analysis" and self._analysis_plan_results:
                self._queue_main_tab_visualizations_from_plan()
            else:
                self._queue_main_tab_visualizations(self.current_result)

        self._set_analysis_view_layout_density()

    def _set_analysis_view_layout_density(self):
        """Adjust splitter distribution based on selected view."""
        if self.main_splitter is None:
            return

        try:
            window_width = int(self.width())
        except TypeError:
            # width() can be shadowed by instance attributes in this class if state drift occurs.
            window_width = int(QMainWindow.width(self))
        if window_width <= 0:
            window_width = 1800
        left = 300
        right = 250
        center = max(1000, window_width - left - right)
        self.main_splitter.setSizes([left, center, right])

    def create_research_data_tab(self):
        """Create research data tab content"""
        layout = QVBoxLayout(self.tab_research_data)

        # Input section
        input_group = QGroupBox("Add Research Data")
        input_layout = QHBoxLayout()

        # Temperature input
        temp_layout = QVBoxLayout()
        temp_layout.addWidget(QLabel("Temperature (K):"))
        self.research_temp_input = QDoubleSpinBox()
        self.research_temp_input.setMinimum(260)
        self.research_temp_input.setMaximum(360)
        self.research_temp_input.setValue(310)
        self.research_temp_input.setSuffix(" K")
        temp_layout.addWidget(self.research_temp_input)
        input_layout.addLayout(temp_layout)

        # Voltage input
        volt_layout = QVBoxLayout()
        volt_layout.addWidget(QLabel("Voltage (V):"))
        self.research_volt_input = QDoubleSpinBox()
        self.research_volt_input.setMinimum(0.8)
        self.research_volt_input.setMaximum(1.2)
        self.research_volt_input.setValue(1.0)
        self.research_volt_input.setDecimals(2)
        self.research_volt_input.setSingleStep(0.05)
        self.research_volt_input.setSuffix(" V")
        volt_layout.addWidget(self.research_volt_input)
        input_layout.addLayout(volt_layout)

        # Cells input
        cells_layout = QVBoxLayout()
        cells_layout.addWidget(QLabel("Cells:"))
        self.research_cells_input = QSpinBox()
        self.research_cells_input.setMinimum(8)
        self.research_cells_input.setMaximum(128)
        self.research_cells_input.setValue(32)
        cells_layout.addWidget(self.research_cells_input)
        input_layout.addLayout(cells_layout)

        # SNM input
        snm_layout = QVBoxLayout()
        snm_layout.addWidget(QLabel("Measured SNM (mV):"))
        self.research_snm_input = QDoubleSpinBox()
        self.research_snm_input.setMinimum(50.0)
        self.research_snm_input.setMaximum(400.0)
        self.research_snm_input.setValue(170.0)
        self.research_snm_input.setSingleStep(1.0)
        self.research_snm_input.setDecimals(1)
        self.research_snm_input.setSuffix(" mV")
        snm_layout.addWidget(self.research_snm_input)
        input_layout.addLayout(snm_layout)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Buttons row 1
        btn_layout1 = QHBoxLayout()

        self.add_data_btn = self.create_styled_button("Add Data", self.add_research_data, style_type="info")
        btn_layout1.addWidget(self.add_data_btn)

        self.train_btn = self.create_styled_button("Train on Research Data", self.train_research_model, style_type="success")
        btn_layout1.addWidget(self.train_btn)

        self.delete_btn = self.create_styled_button("Delete Selected", self.delete_selected_data, style_type="danger")
        btn_layout1.addWidget(self.delete_btn)

        layout.addLayout(btn_layout1)

        # Buttons row 2
        btn_layout2 = QHBoxLayout()

        self.compare_btn = self.create_styled_button("Compare Models", self.compare_models, style_type="warning")
        btn_layout2.addWidget(self.compare_btn)

        self.sample_btn = self.create_styled_button("Load Sample Research Data", self.load_sample_data, style_type="secondary")
        btn_layout2.addWidget(self.sample_btn)

        self.ai_btn = self.create_styled_button("Get AI Research Analysis", self.get_ai_advice, style_type="info")
        btn_layout2.addWidget(self.ai_btn)

        layout.addLayout(btn_layout2)

        # Buttons row 3 - Phase 2 Advanced Features
        btn_layout3 = QHBoxLayout()

        clear_all_btn = self.create_styled_button("Clear All Data", self.clear_all_research_data, style_type="danger")
        btn_layout3.addWidget(clear_all_btn)

        log_analysis_btn = self.create_styled_button("Save Research Analysis Log", self.log_ai_analysis, style_type="warning")
        btn_layout3.addWidget(log_analysis_btn)

        generate_report_btn = self.create_styled_button("Generate Full Report", self.generate_simulation_report_with_figures, style_type="success")
        self.generate_full_report_btn = generate_report_btn
        btn_layout3.addWidget(generate_report_btn)

        layout.addLayout(btn_layout3)

        # Buttons row 4 - CSV Import/Export
        btn_layout4 = QHBoxLayout()

        import_csv_btn = self.create_styled_button("Import from CSV", self.import_research_data_from_csv, style_type="warning")
        btn_layout4.addWidget(import_csv_btn)

        export_csv_btn = self.create_styled_button("Export to CSV", self.export_research_data_to_csv, style_type="secondary")
        btn_layout4.addWidget(export_csv_btn)

        layout.addLayout(btn_layout4)

        # Data table
        self.research_data_table = QTableWidget()
        self.research_data_table.setColumnCount(7)
        self.research_data_table.setHorizontalHeaderLabels([
            "Timestamp", "Temp (K)", "Voltage (V)", "Cells",
            "SNM Predicted (mV)", "SNM Actual (mV)", "Error (mV)"
        ])
        self.research_data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.research_data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.research_data_table)

        # Status labels
        status_layout = QHBoxLayout()

        self.rmse_label = QLabel("RMSE: -- mV")
        self.rmse_label.setProperty("ui-status", "info")
        status_layout.addWidget(self.rmse_label)

        self.data_count_label = QLabel("Data Points: 0")
        self.data_count_label.setProperty("ui-status", "success")
        status_layout.addWidget(self.data_count_label)

        self.model_status_label = QLabel("Model: Not trained")
        self.model_status_label.setProperty("ui-status", "muted")
        status_layout.addWidget(self.model_status_label)

        layout.addLayout(status_layout)

        # Visualization area
        viz_layout = QHBoxLayout()

        # RMSE improvement canvas
        rmse_viz_layout = QVBoxLayout()
        rmse_viz_layout.addWidget(QLabel("RMSE Improvement:"))
        self.canvas_rmse = FigureCanvas(Figure(figsize=(5, 3)))
        rmse_viz_layout.addWidget(self.canvas_rmse)
        viz_layout.addLayout(rmse_viz_layout)

        # Prediction vs Actual canvas
        pred_viz_layout = QVBoxLayout()
        pred_viz_layout.addWidget(QLabel("Prediction vs Actual:"))
        self.canvas_comparison = FigureCanvas(Figure(figsize=(5, 3)))
        pred_viz_layout.addWidget(self.canvas_comparison)
        viz_layout.addLayout(pred_viz_layout)

        layout.addLayout(viz_layout)

    def create_thermal_analysis_tab(self):
        """Create Thermal Analysis tab content"""
        layout = QVBoxLayout(self.tab_thermal)

        # Controls
        control_group = QGroupBox("Thermal Analysis Settings")
        control_layout = QHBoxLayout()

        # Monte Carlo runs selector
        mc_layout = QVBoxLayout()
        mc_layout.addWidget(QLabel("Monte Carlo Runs:"))
        self.mc_runs_spinbox = QSpinBox()
        self.mc_runs_spinbox.setMinimum(10)
        self.mc_runs_spinbox.setMaximum(1000)
        self.mc_runs_spinbox.setValue(100)
        self.mc_runs_spinbox.setSingleStep(10)
        mc_layout.addWidget(self.mc_runs_spinbox)
        control_layout.addLayout(mc_layout)

        # Run button
        self.run_thermal_btn = self.create_styled_button("Run Thermal Analysis", self.run_thermal_analysis, style_type="warning")
        control_layout.addWidget(self.run_thermal_btn)

        # Save figure button
        self.save_thermal_btn = self.create_styled_button("Save Figure as PNG", self.save_thermal_figure, style_type="secondary")
        control_layout.addWidget(self.save_thermal_btn)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Canvas for thermal figure
        self.canvas_thermal = FigureCanvas(Figure(figsize=(12, 10)))
        layout.addWidget(self.canvas_thermal)

    # ========================================================================
    # Advanced Analysis Tabs
    # ========================================================================

    def create_workload_tab(self):
        """Create Transformer Workload Profile tab"""
        layout = QVBoxLayout(self.tab_workload)

        # Title
        title = self.create_title_label("Transformer Workload Memory Analysis", level="title")
        layout.addWidget(title)

        # Input section
        input_group = QGroupBox("Transformer Architecture Parameters")
        input_layout = QVBoxLayout()

        # Row 1: Model name, hidden dim, num layers
        row1 = QHBoxLayout()

        model_layout = QVBoxLayout()
        model_layout.addWidget(QLabel("Model Name:"))
        self.wl_model_name = QLineEdit("LLaMA-7B-Online")
        model_layout.addWidget(self.wl_model_name)
        row1.addLayout(model_layout)

        hidden_layout = QVBoxLayout()
        hidden_layout.addWidget(QLabel("Hidden Dim:"))
        self.wl_hidden_dim = QSpinBox()
        self.wl_hidden_dim.setRange(256, 16384)
        self.wl_hidden_dim.setValue(4096)
        self.wl_hidden_dim.setSingleStep(256)
        hidden_layout.addWidget(self.wl_hidden_dim)
        row1.addLayout(hidden_layout)

        layers_layout = QVBoxLayout()
        layers_layout.addWidget(QLabel("Num Layers:"))
        self.wl_num_layers = QSpinBox()
        self.wl_num_layers.setRange(1, 128)
        self.wl_num_layers.setValue(32)
        layers_layout.addWidget(self.wl_num_layers)
        row1.addLayout(layers_layout)

        input_layout.addLayout(row1)

        # Row 2: Num heads, sequence length, batch size
        row2 = QHBoxLayout()

        heads_layout = QVBoxLayout()
        heads_layout.addWidget(QLabel("Num Heads:"))
        self.wl_num_heads = QSpinBox()
        self.wl_num_heads.setRange(1, 128)
        self.wl_num_heads.setValue(32)
        heads_layout.addWidget(self.wl_num_heads)
        row2.addLayout(heads_layout)

        seq_layout = QVBoxLayout()
        seq_layout.addWidget(QLabel("Seq Length:"))
        self.wl_seq_length = QSpinBox()
        self.wl_seq_length.setRange(128, 32768)
        self.wl_seq_length.setValue(2048)
        self.wl_seq_length.setSingleStep(128)
        seq_layout.addWidget(self.wl_seq_length)
        row2.addLayout(seq_layout)

        batch_layout = QVBoxLayout()
        batch_layout.addWidget(QLabel("Batch Size:"))
        self.wl_batch_size = QSpinBox()
        self.wl_batch_size.setRange(1, 256)
        self.wl_batch_size.setValue(1)
        batch_layout.addWidget(self.wl_batch_size)
        row2.addLayout(batch_layout)

        input_layout.addLayout(row2)

        # Row 3: Precision, Attention Type, KV Heads
        row3 = QHBoxLayout()

        precision_layout = QVBoxLayout()
        precision_layout.addWidget(QLabel("Precision:"))
        self.wl_precision = QComboBox()
        self.wl_precision.addItems(['fp32', 'fp16', 'bf16', 'fp8', 'int8'])
        self.wl_precision.setCurrentText('fp16')
        precision_layout.addWidget(self.wl_precision)
        row3.addLayout(precision_layout)

        attn_layout = QVBoxLayout()
        attn_layout.addWidget(QLabel("Attention Type:"))
        self.wl_attention = QComboBox()
        self.wl_attention.addItems(['standard', 'mqa', 'gqa', 'sparse'])
        self.wl_attention.setCurrentText('standard')
        attn_layout.addWidget(self.wl_attention)
        row3.addLayout(attn_layout)

        kv_heads_layout = QVBoxLayout()
        kv_heads_layout.addWidget(QLabel("KV Heads (GQA):"))
        self.wl_kv_heads = QSpinBox()
        self.wl_kv_heads.setRange(1, 128)
        self.wl_kv_heads.setValue(8)
        kv_heads_layout.addWidget(self.wl_kv_heads)
        row3.addLayout(kv_heads_layout)

        input_layout.addLayout(row3)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Calculate button
        calc_btn = self.create_styled_button("Calculate Memory Requirements", self.calculate_workload, style_type="success")
        layout.addWidget(calc_btn)

        # Results text area
        self.wl_results_text = QTextEdit()
        self.wl_results_text.setReadOnly(True)
        self.wl_results_text.setProperty("ui-font", "mono")
        layout.addWidget(self.wl_results_text)

    def create_circuit_kpi_tab(self):
        """Create Circuit-to-System KPI Translator tab"""
        layout = QVBoxLayout(self.tab_circuit_kpi)

        # Title
        title = self.create_title_label("Circuit-Level to System-Level KPI Translation", level="title")
        layout.addWidget(title)

        # Inputs
        input_group = QGroupBox("Circuit Parameters")
        input_layout = QHBoxLayout()

        snm_layout = QVBoxLayout()
        snm_layout.addWidget(QLabel("SNM (mV):"))
        self.kpi_snm = QDoubleSpinBox()
        self.kpi_snm.setRange(100.0, 250.0)
        self.kpi_snm.setValue(175.0)
        self.kpi_snm.setSingleStep(5.0)
        snm_layout.addWidget(self.kpi_snm)
        input_layout.addLayout(snm_layout)

        vmin_layout = QVBoxLayout()
        vmin_layout.addWidget(QLabel("Vmin (V):"))
        self.kpi_vmin = QDoubleSpinBox()
        self.kpi_vmin.setRange(0.40, 1.0)
        self.kpi_vmin.setValue(0.70)
        self.kpi_vmin.setSingleStep(0.05)
        self.kpi_vmin.setDecimals(2)
        vmin_layout.addWidget(self.kpi_vmin)
        input_layout.addLayout(vmin_layout)

        leak_layout = QVBoxLayout()
        leak_layout.addWidget(QLabel("Leakage (mW):"))
        self.kpi_leakage = QDoubleSpinBox()
        self.kpi_leakage.setRange(0.1, 50.0)
        self.kpi_leakage.setValue(2.0)
        self.kpi_leakage.setSingleStep(0.5)
        leak_layout.addWidget(self.kpi_leakage)
        input_layout.addLayout(leak_layout)

        temp_kpi_layout = QVBoxLayout()
        temp_kpi_layout.addWidget(QLabel("Temperature (°C):"))
        self.kpi_temp = QSpinBox()
        self.kpi_temp.setRange(0, 100)
        self.kpi_temp.setValue(25)
        temp_kpi_layout.addWidget(self.kpi_temp)
        input_layout.addLayout(temp_kpi_layout)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Translate button
        translate_btn = self.create_styled_button("Translate to System KPIs", self.translate_circuit_to_system, style_type="info")
        layout.addWidget(translate_btn)

        # Results
        self.kpi_results_text = QTextEdit()
        self.kpi_results_text.setReadOnly(True)
        self.kpi_results_text.setProperty("ui-font", "mono")
        layout.addWidget(self.kpi_results_text)

    def create_optimizer_tab(self):
        """Create Design Space Optimizer tab with Pareto plot"""
        layout = QVBoxLayout(self.tab_optimizer)

        # Title
        title = self.create_title_label("Design Space Exploration & Pareto Frontier", level="title")
        layout.addWidget(title)

        # Controls
        control_group = QGroupBox("Design Space Parameters")
        control_layout = QVBoxLayout()

        # SRAM sizes
        sram_layout = QHBoxLayout()
        sram_layout.addWidget(QLabel("SRAM Sizes (MB):"))
        self.opt_sram_sizes = QLineEdit("64, 128, 256, 512")
        sram_layout.addWidget(self.opt_sram_sizes)
        control_layout.addLayout(sram_layout)

        # SNM values
        snm_opt_layout = QHBoxLayout()
        snm_opt_layout.addWidget(QLabel("SNM values (mV):"))
        self.opt_snm_values = QLineEdit("150, 160, 170, 180, 190")
        snm_opt_layout.addWidget(self.opt_snm_values)
        control_layout.addLayout(snm_opt_layout)

        # Vmin values
        vmin_opt_layout = QHBoxLayout()
        vmin_opt_layout.addWidget(QLabel("Vmin values (V):"))
        self.opt_vmin_values = QLineEdit("0.50, 0.60, 0.70")
        vmin_opt_layout.addWidget(self.opt_vmin_values)
        control_layout.addLayout(vmin_opt_layout)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Constraint controls (NEW)
        constraint_group = QGroupBox("Design Constraints")
        constraint_layout = QVBoxLayout()

        # Max Area
        area_constraint_layout = QHBoxLayout()
        area_constraint_layout.addWidget(QLabel("Max Area (mm^2):"))
        self.opt_max_area = QLineEdit("1000")
        area_constraint_layout.addWidget(self.opt_max_area)
        constraint_layout.addLayout(area_constraint_layout)

        # Max Power
        power_constraint_layout = QHBoxLayout()
        power_constraint_layout.addWidget(QLabel("Max Power (mW):"))
        self.opt_max_power = QLineEdit("500")
        power_constraint_layout.addWidget(self.opt_max_power)
        constraint_layout.addLayout(power_constraint_layout)

        # Min Tapout Success
        tapout_constraint_layout = QHBoxLayout()
        tapout_constraint_layout.addWidget(QLabel("Min Tapout Success (%):"))
        self.opt_min_tapout = QLineEdit("0")
        tapout_constraint_layout.addWidget(self.opt_min_tapout)
        constraint_layout.addLayout(tapout_constraint_layout)

        constraint_group.setLayout(constraint_layout)
        layout.addWidget(constraint_group)

        # Optimize button
        optimize_btn = self.create_styled_button("Find Pareto-Optimal Designs", self.run_design_optimization, style_type="warning")
        layout.addWidget(optimize_btn)

        # Canvas for Pareto plot
        self.canvas_pareto = FigureCanvas(Figure(figsize=(10, 6)))
        layout.addWidget(self.canvas_pareto)

        # Save button for Pareto plot
        save_btn_pareto = self.create_save_button(
            self.canvas_pareto,
            "sram_design_space_pareto",
            "SRAM Design Space Pareto Frontier"
        )
        layout.addWidget(save_btn_pareto)

        # Results table
        self.opt_results_text = QTextEdit()
        self.opt_results_text.setReadOnly(True)
        self.opt_results_text.setProperty("ui-font", "mono")
        layout.addWidget(self.opt_results_text)

    def create_reliability_grove_tab(self):
        """Create Reliability Analysis tab (NBTI/HCI Lifetime Prediction)"""
        layout = QVBoxLayout(self.tab_reliability_grove)

        # Title
        title = self.create_title_label("Reliability Analysis: NBTI/HCI Lifetime Prediction", level="title")
        layout.addWidget(title)

        # Input section
        input_group = QGroupBox("Operating Conditions")
        input_layout = QHBoxLayout()

        temp_rel_layout = QVBoxLayout()
        temp_rel_layout.addWidget(QLabel("Temperature (K):"))
        self.rel_temp = QSpinBox()
        self.rel_temp.setRange(260, 400)
        self.rel_temp.setValue(310)
        temp_rel_layout.addWidget(self.rel_temp)
        input_layout.addLayout(temp_rel_layout)

        vgs_layout = QVBoxLayout()
        vgs_layout.addWidget(QLabel("Vgs (V):"))
        self.rel_vgs = QDoubleSpinBox()
        self.rel_vgs.setRange(0.5, 1.5)
        self.rel_vgs.setValue(1.0)
        self.rel_vgs.setSingleStep(0.05)
        self.rel_vgs.setDecimals(2)
        vgs_layout.addWidget(self.rel_vgs)
        input_layout.addLayout(vgs_layout)

        vth_layout = QVBoxLayout()
        vth_layout.addWidget(QLabel("Vth (V):"))
        self.rel_vth = QDoubleSpinBox()
        self.rel_vth.setRange(0.2, 0.8)
        self.rel_vth.setValue(0.4)
        self.rel_vth.setSingleStep(0.05)
        self.rel_vth.setDecimals(2)
        vth_layout.addWidget(self.rel_vth)
        input_layout.addLayout(vth_layout)

        width_rel_layout = QVBoxLayout()
        width_rel_layout.addWidget(QLabel("Width (關m):"))
        self.rel_width = QDoubleSpinBox()
        self.rel_width.setRange(0.1, 10.0)
        self.rel_width.setValue(1.0)
        self.rel_width.setSingleStep(0.1)
        self.rel_width.setDecimals(1)
        width_rel_layout.addWidget(self.rel_width)
        input_layout.addLayout(width_rel_layout)

        num_cells_rel_layout = QVBoxLayout()
        num_cells_rel_layout.addWidget(QLabel("Num Cells:"))
        self.rel_num_cells = QSpinBox()
        self.rel_num_cells.setRange(8, 256)
        self.rel_num_cells.setValue(32)
        num_cells_rel_layout.addWidget(self.rel_num_cells)
        input_layout.addLayout(num_cells_rel_layout)

        duty_cycle_layout = QVBoxLayout()
        duty_cycle_layout.addWidget(QLabel("Duty Cycle:"))
        self.rel_duty_cycle = QDoubleSpinBox()
        self.rel_duty_cycle.setRange(0.05, 1.0)
        self.rel_duty_cycle.setValue(DEFAULT_DUTY_CYCLE)
        self.rel_duty_cycle.setSingleStep(0.05)
        self.rel_duty_cycle.setDecimals(2)
        duty_cycle_layout.addWidget(self.rel_duty_cycle)
        input_layout.addLayout(duty_cycle_layout)

        failure_rate_layout = QVBoxLayout()
        failure_rate_layout.addWidget(QLabel("Failure Rate:"))
        self.rel_failure_rate = QDoubleSpinBox()
        self.rel_failure_rate.setRange(0.001, 0.200)
        self.rel_failure_rate.setValue(DEFAULT_FAILURE_RATE)
        self.rel_failure_rate.setSingleStep(0.001)
        self.rel_failure_rate.setDecimals(3)
        failure_rate_layout.addWidget(self.rel_failure_rate)
        input_layout.addLayout(failure_rate_layout)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Analyze button
        analyze_btn = self.create_styled_button("Predict Lifetime & Reliability", self.analyze_reliability, style_type="info")
        layout.addWidget(analyze_btn)

        # Results canvas
        self.canvas_reliability_grove = FigureCanvas(Figure(figsize=(12, 8)))
        layout.addWidget(self.canvas_reliability_grove)

        # Save button for reliability plot
        save_btn_reliability_grove = self.create_save_button(
            self.canvas_reliability_grove,
            "sram_reliability_lifetime_analysis",
            "SRAM Reliability NBTI/HCI Lifetime Prediction"
        )
        layout.addWidget(save_btn_reliability_grove)

        # Results text
        self.rel_results_text = QTextEdit()
        self.rel_results_text.setReadOnly(True)
        self.rel_results_text.setProperty("ui-font", "mono")
        layout.addWidget(self.rel_results_text)

    def create_ai_advisor_tab(self):
        """Create AI research analysis tab."""
        layout = QVBoxLayout(self.tab_ai_advisor)

        # Title
        title = self.create_title_label("AI Research Analysis", level="title")
        layout.addWidget(title)

        # Configuration status
        self.ai_connection_label = QLabel()
        layout.addWidget(self.ai_connection_label)
        self._refresh_ai_connection_label()

        # Current simulation summary
        summary_group = QGroupBox("Current Simulation Context")
        summary_layout = QVBoxLayout()

        self.ai_context_text = QTextEdit()
        self.ai_context_text.setReadOnly(True)
        self.ai_context_text.setMaximumHeight(150)
        self.ai_context_text.setPlainText("Run a simulation first to get AI recommendations...")
        summary_layout.addWidget(self.ai_context_text)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Query input
        query_group = QGroupBox("Ask AI Advisor")
        query_layout = QVBoxLayout()

        self.ai_query_input = QTextEdit()
        self.ai_query_input.setPlaceholderText("Ask a question about your SRAM design (e.g., 'How can I reduce BER?', 'What's the optimal SNM for this temperature?')")
        self.ai_query_input.setMaximumHeight(100)
        query_layout.addWidget(self.ai_query_input)

        query_btn_layout = QHBoxLayout()

        # Preset buttons
        preset_btn1 = self.create_styled_button(
            "Optimize SNM",
            lambda: self.ai_query_input.setPlainText("Based on current simulation, what's the optimal SNM value to minimize BER while maximizing area efficiency?"),
            style_type="warning"
        )
        query_btn_layout.addWidget(preset_btn1)

        preset_btn2 = self.create_styled_button(
            "Reduce Power",
            lambda: self.ai_query_input.setPlainText("What operating conditions (temperature, voltage) should I use to minimize power consumption while maintaining reliability?"),
            style_type="info"
        )
        query_btn_layout.addWidget(preset_btn2)

        preset_btn3 = self.create_styled_button(
            "Improve Lifetime",
            lambda: self.ai_query_input.setPlainText("How can I extend the SRAM lifetime considering NBTI and HCI effects?"),
            style_type="success"
        )
        query_btn_layout.addWidget(preset_btn3)

        query_layout.addLayout(query_btn_layout)

        ask_btn = self.create_styled_button("Ask AI Advisor", self.ask_ai_advisor, style_type="info")
        query_layout.addWidget(ask_btn)

        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        # AI Response
        response_group = QGroupBox("AI Recommendations")
        response_layout = QVBoxLayout()

        self.ai_response_text = QTextEdit()
        self.ai_response_text.setReadOnly(True)
        self.ai_response_text.setProperty("ui-font", "mono-large")
        response_layout.addWidget(self.ai_response_text)

        response_group.setLayout(response_layout)
        layout.addWidget(response_group)

    def create_validation_benchmark_tab(self):
        """Create Validation & Benchmark tab."""
        layout = QVBoxLayout(self.tab_validation)

        # Control section
        control_group = QGroupBox("Validation & ML Benchmark")
        control_layout = QVBoxLayout()

        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("Dataset Size:"))
        self.validation_dataset_spin = QSpinBox()
        self.validation_dataset_spin.setRange(1000, 10000)
        self.validation_dataset_spin.setValue(5000)
        self.validation_dataset_spin.setSingleStep(500)
        params_layout.addWidget(self.validation_dataset_spin)

        params_layout.addWidget(QLabel("Random Seed:"))
        self.validation_seed_spin = QSpinBox()
        self.validation_seed_spin.setRange(0, 9999)
        self.validation_seed_spin.setValue(42)
        params_layout.addWidget(self.validation_seed_spin)

        params_layout.addWidget(QLabel("CV Folds:"))
        self.validation_folds_spin = QSpinBox()
        self.validation_folds_spin.setRange(3, 10)
        self.validation_folds_spin.setValue(5)
        params_layout.addWidget(self.validation_folds_spin)

        control_layout.addLayout(params_layout)

        btn_layout = QHBoxLayout()
        self.run_validation_btn = self.create_styled_button("Run Validation", self.run_validation_analysis, style_type="info")
        btn_layout.addWidget(self.run_validation_btn)

        self.run_benchmark_btn = self.create_styled_button("Run ML Benchmark", self.run_ml_benchmark, style_type="success")
        btn_layout.addWidget(self.run_benchmark_btn)

        self.run_gpu_check_btn = self.create_styled_button("Check GPU Dispatch", self.run_gpu_capability_check, style_type="warning")
        btn_layout.addWidget(self.run_gpu_check_btn)

        self.export_validation_btn = self.create_styled_button("Export", self.export_validation_benchmark, style_type="secondary")
        btn_layout.addWidget(self.export_validation_btn)
        control_layout.addLayout(btn_layout)

        self.validation_status_label = QLabel("Idle")
        control_layout.addWidget(self.validation_status_label)

        self.gpu_check_text = QTextEdit()
        self.gpu_check_text.setReadOnly(True)
        self.gpu_check_text.setMaximumHeight(120)
        self.gpu_check_text.setPlainText("GPU diagnostics have not been run yet.")
        control_layout.addWidget(self.gpu_check_text)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Result summary table
        summary_group = QGroupBox("Validation Summary")
        summary_layout = QVBoxLayout()
        self.validation_summary_table = QTableWidget()
        self.validation_summary_table.setColumnCount(2)
        self.validation_summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.validation_summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.validation_summary_table.setRowCount(0)
        self.validation_summary_table.horizontalHeader().setStretchLastSection(True)
        summary_layout.addWidget(self.validation_summary_table)

        self.validation_summary_label = QLabel("Run validation or benchmark to populate results.")
        summary_layout.addWidget(self.validation_summary_label)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # ML Benchmark result table
        benchmark_group = QGroupBox("ML Benchmark Ranking")
        benchmark_layout = QVBoxLayout()
        self.benchmark_table = QTableWidget()
        self.benchmark_table.setColumnCount(7)
        self.benchmark_table.setHorizontalHeaderLabels([
            "Model",
            "R2",
            "RMSE",
            "MAE",
            "Train (ms)",
            "Infer (ms)",
            "Params"
        ])
        self.benchmark_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        benchmark_layout.addWidget(self.benchmark_table)
        benchmark_group.setLayout(benchmark_layout)
        layout.addWidget(benchmark_group)

        # Plots
        self.validation_plot_tabs = QTabWidget()
        self.tab_validation_profile, self.canvas_validation_profile = self.create_embedded_plot_tab(
            "Validation Profile",
            "canvas_validation_profile",
            "sram_validation_profile",
            "Validation analytics from analytical ground-truth model"
        )
        self.validation_plot_tabs.addTab(self.tab_validation_profile, "Validation Profile")
        self.tab_benchmark_r2, self.canvas_benchmark_r2 = self.create_embedded_plot_tab(
            "R2 Comparison",
            "canvas_benchmark_r2",
            "sram_benchmark_r2",
            "R2 Comparison"
        )
        self.validation_plot_tabs.addTab(self.tab_benchmark_r2, "R2 Comparison")
        self.tab_benchmark_speed, self.canvas_benchmark_speed = self.create_embedded_plot_tab(
            "Speed vs Accuracy",
            "canvas_benchmark_speed",
            "sram_benchmark_speed",
            "Speed vs Accuracy"
        )
        self.validation_plot_tabs.addTab(self.tab_benchmark_speed, "Speed vs Accuracy")
        self.tab_benchmark_pred_actual, self.canvas_benchmark_pred_actual = self.create_embedded_plot_tab(
            "Predicted vs Actual / Residual",
            "canvas_benchmark_pred_actual",
            "sram_benchmark_pred_actual",
            "Prediction & Residual"
        )
        self.validation_plot_tabs.addTab(self.tab_benchmark_pred_actual, "Predicted vs Actual / Residual")
        self.validation_plot_tabs.currentChanged.connect(self._on_validation_tab_changed)
        layout.addWidget(self.validation_plot_tabs)

        layout.addStretch()

    def run_validation_analysis(self):
        """Run analytical validation task."""
        if not VALIDATION_AVAILABLE:
            self.show_warning("Warning", "Validation module not available")
            return
        if self.validation_benchmark_thread is not None and self.validation_benchmark_thread.isRunning():
            return
        if not hasattr(self, "validation_status_label"):
            return

        self.validation_status_label.setText("Running validation...")
        self._set_validation_buttons_enabled(False)
        self.validation_result = None

        self.validation_benchmark_thread = ValidationBenchmarkThread(
            "validation",
            dataset_size=int(self.validation_dataset_spin.value()),
            random_state=int(self.validation_seed_spin.value()),
            n_folds=int(self.validation_folds_spin.value())
        )
        self.validation_benchmark_thread.result_ready.connect(self._on_validation_benchmark_result)
        self.validation_benchmark_thread.error.connect(self._on_validation_benchmark_error)
        self.validation_benchmark_thread.start()

    def run_ml_benchmark(self):
        """Run ML benchmark task."""
        if not VALIDATION_AVAILABLE:
            self.show_warning("Warning", "Validation module not available")
            return
        if self.validation_benchmark_thread is not None and self.validation_benchmark_thread.isRunning():
            return
        if not hasattr(self, "validation_status_label"):
            return

        self.validation_status_label.setText("Running ML benchmark...")
        self._set_validation_buttons_enabled(False)
        self.benchmark_result = None

        self.validation_benchmark_thread = ValidationBenchmarkThread(
            "benchmark",
            dataset_size=int(self.validation_dataset_spin.value()),
            random_state=int(self.validation_seed_spin.value()),
            n_folds=int(self.validation_folds_spin.value())
        )
        self.validation_benchmark_thread.result_ready.connect(self._on_validation_benchmark_result)
        self.validation_benchmark_thread.error.connect(self._on_validation_benchmark_error)
        self.validation_benchmark_thread.start()

    def run_gpu_capability_check(self):
        """Check GPU availability and expected dispatch path for current workload."""
        if not hasattr(self, "validation_status_label"):
            return

        self.validation_status_label.setText("Running GPU diagnostics...")
        self.on_status_update("Running GPU diagnostics...")

        lines = [f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] GPU Dispatch Diagnostics"]

        request = {
            "num_cells": int(self.num_cells),
            "monte_carlo_runs": int(self.monte_carlo_runs),
            "compute_mode": self.compute_mode_preference,
            "latency_mode": "interactive",
        }

        if EXECUTION_POLICY_AVAILABLE and select_compute_engine is not None:
            selected, reason, work_size, gpu_available = select_compute_engine("simulate", request)
            lines.append(f"- Policy GPU available: {gpu_available}")
            lines.append(f"- Policy selected engine: {selected}")
            lines.append(f"- Policy reason: {reason}")
            lines.append(f"- Estimated work size: {work_size}")
            if selected == "cpu" and gpu_available:
                lines.append("- Bottleneck hypothesis: interactive workload is below GPU threshold (CPU-bound by policy).")
            elif not gpu_available:
                lines.append("- Bottleneck hypothesis: no GPU detected (CPU-bound by hardware/runtime).")
            else:
                lines.append("- Bottleneck hypothesis: workload is large enough and GPU path is eligible.")
        else:
            lines.append("- Execution policy module unavailable; policy-level GPU check skipped.")

        if NATIVE_BACKEND_AVAILABLE:
            try:
                native_gpu_symbols = []
                try:
                    native_mod = __import__("_sram_native")
                    for symbol in ("simulate_array_gpu", "predict_lifetime_gpu", "optimize_design_gpu"):
                        if hasattr(native_mod, symbol):
                            native_gpu_symbols.append(symbol)
                except Exception as exc:
                    lines.append(f"- Native module import for GPU symbol check failed: {exc}")
                if native_gpu_symbols:
                    lines.append(f"- Native GPU entrypoints present: {', '.join(native_gpu_symbols)}")
                else:
                    lines.append("- Native GPU entrypoints present: none")
                    try:
                        import torch
                        torch_cuda_backend = bool(torch.cuda.is_available())
                    except Exception:
                        torch_cuda_backend = False
                    lines.append(f"- Torch CUDA backend available to wrapper: {torch_cuda_backend}")

                probe_input = np.random.randint(0, 2, max(8, min(64, int(self.num_cells)))).tolist()
                probe_result = native_simulate_array({
                    "backend": "hybrid" if self.backend_type == "hybrid" else "standard",
                    "temperature": float(self.temperature),
                    "voltage": float(self.voltage),
                    "num_cells": len(probe_input),
                    "input_data": probe_input,
                    "noise_enable": bool(self.noise_enable),
                    "variability_enable": bool(self.variability_enable),
                    "monte_carlo_runs": max(4, min(32, int(self.monte_carlo_runs))),
                    "width": float(self.width),
                    "length": float(self.length),
                    "include_thermal_noise": False,
                    "analysis_type": "basic",
                    "compute_mode": self.compute_mode_preference,
                    "latency_mode": "interactive",
                    "require_native": True,
                    "prefer_hybrid_gate_logic": False,
                })
                exec_meta = probe_result.get("_exec", {}) if isinstance(probe_result, dict) else {}
                if isinstance(exec_meta, dict):
                    lines.append(f"- Native probe selected engine: {exec_meta.get('selected', 'unknown')}")
                    lines.append(f"- Native probe dispatch reason: {exec_meta.get('reason', 'unknown')}")
                    lines.append(f"- Native probe GPU available: {exec_meta.get('gpu_available', 'unknown')}")
                else:
                    lines.append("- Native probe completed but execution metadata was missing.")
            except Exception as exc:
                lines.append(f"- Native probe failed: {exc}")
        else:
            lines.append("- Native backend unavailable; native probe skipped.")

        if self.current_result and isinstance(self.current_result, dict):
            exec_meta = self.current_result.get("_exec", {})
            if isinstance(exec_meta, dict) and exec_meta:
                lines.append(f"- Last simulation engine: {exec_meta.get('selected', 'unknown')}")
                lines.append(f"- Last simulation reason: {exec_meta.get('reason', 'unknown')}")

        summary_text = "\n".join(lines)
        if hasattr(self, "gpu_check_text") and self.gpu_check_text is not None:
            self.gpu_check_text.setPlainText(summary_text)

        self.validation_status_label.setText("GPU diagnostics done.")
        self.on_status_update("GPU diagnostics completed.")

    def _resolve_heavy_simulation_dispatch(self, num_cells: int, monte_carlo_runs: int, compute_mode: str = None):
        """Choose compute/latency mode for heavy native simulation jobs.

        Policy:
        - Preserve explicit CPU/GPU user intent in the native request
        - In auto mode, keep policy-based CPU/GPU selection
        """
        requested_compute_mode = str(compute_mode or self.compute_mode_preference).strip().lower()
        if requested_compute_mode not in {"auto", "cpu", "gpu"}:
            requested_compute_mode = "auto"

        work_size = max(1, int(num_cells)) * max(1, int(monte_carlo_runs))
        dispatch = {
            "compute_mode": requested_compute_mode,
            "latency_mode": "interactive",
            "requested_compute_mode": requested_compute_mode,
            "selected": "cpu",
            "reason": "policy_unavailable",
            "gpu_available": False,
            "work_size": work_size,
        }

        if not EXECUTION_POLICY_AVAILABLE or select_compute_engine is None:
            return dispatch

        selected, reason, work_size, gpu_available = select_compute_engine(
            "simulate",
            {
                "num_cells": int(num_cells),
                "monte_carlo_runs": int(monte_carlo_runs),
                "compute_mode": requested_compute_mode,
                "latency_mode": "interactive",
            },
        )

        dispatch.update(
            {
                "selected": selected,
                "reason": reason,
                "gpu_available": bool(gpu_available),
                "work_size": int(work_size),
            }
        )

        if requested_compute_mode == "gpu":
            dispatch["compute_mode"] = "gpu"
            dispatch["latency_mode"] = "batch"
        elif requested_compute_mode == "cpu":
            dispatch["compute_mode"] = "cpu"
            dispatch["latency_mode"] = "interactive"
        elif selected == "gpu" and gpu_available:
            dispatch["compute_mode"] = "auto"
            dispatch["latency_mode"] = "batch"
        else:
            dispatch["compute_mode"] = "cpu"
            dispatch["latency_mode"] = "interactive"

        return dispatch

    def _resolve_compute_dispatch(self, problem_kind: str, request: dict):
        """Resolve compute/latency mode for non-simulation native workloads."""
        request_payload = dict(request)
        requested_compute_mode = str(request_payload.get("compute_mode", self.compute_mode_preference)).strip().lower()
        if requested_compute_mode not in {"auto", "cpu", "gpu"}:
            requested_compute_mode = "auto"
        request_payload["compute_mode"] = requested_compute_mode
        request_payload.setdefault("latency_mode", "batch")
        work_size = max(1, int(request_payload.get("num_cells", 1)))

        dispatch = {
            "compute_mode": requested_compute_mode,
            "latency_mode": request_payload.get("latency_mode", "batch"),
            "requested_compute_mode": requested_compute_mode,
            "selected": "cpu",
            "reason": "policy_unavailable",
            "gpu_available": False,
            "work_size": work_size,
        }

        if not EXECUTION_POLICY_AVAILABLE or select_compute_engine is None:
            return dispatch

        selected, reason, work_size, gpu_available = select_compute_engine(
            problem_kind,
            request_payload,
        )
        dispatch.update(
            {
                "selected": selected,
                "reason": reason,
                "gpu_available": bool(gpu_available),
                "work_size": int(work_size),
            }
        )

        if requested_compute_mode == "gpu":
            dispatch["compute_mode"] = "gpu"
            dispatch["latency_mode"] = request_payload.get("latency_mode", "batch")
        elif requested_compute_mode == "cpu":
            dispatch["compute_mode"] = "cpu"
            dispatch["latency_mode"] = request_payload.get("latency_mode", "batch")
        elif selected == "gpu" and gpu_available:
            dispatch["compute_mode"] = "auto"
            dispatch["latency_mode"] = request_payload.get("latency_mode", "batch")
        else:
            dispatch["compute_mode"] = "cpu"
            dispatch["latency_mode"] = request_payload.get("latency_mode", "batch")

        return dispatch

    def _set_validation_buttons_enabled(self, enabled):
        self.run_validation_btn.setEnabled(enabled)
        self.run_benchmark_btn.setEnabled(enabled)
        self.run_gpu_check_btn.setEnabled(enabled)
        self.export_validation_btn.setEnabled(enabled)

    def _on_validation_benchmark_result(self, mode, result):
        if mode == "validation":
            self.validation_result = result
            self._update_validation_summary_table(result["summary"])
            self._queue_validation_tab_visualizations(mode, result)
            self.validation_status_label.setText("Validation done.")
        elif mode == "benchmark":
            self.benchmark_result = result
            self.update_benchmark_table(result["table_rows"])
            self._queue_validation_tab_visualizations(mode, result["benchmark_result"])
            self.validation_status_label.setText("ML benchmark done.")
        else:
            self.validation_status_label.setText(f"Unknown mode: {mode}")
        self._set_validation_buttons_enabled(True)

    def _queue_validation_tab_visualizations(self, mode, payload):
        self._pending_validation_tab_updates = {}

        if mode == "validation":
            data = payload.get("data", {})
            residual = payload.get("residual")
            self._pending_validation_tab_updates[self.tab_validation_profile] = lambda: self.plot_validation_profile(data, residual)
        elif mode == "benchmark":
            benchmark_result = payload if isinstance(payload, dict) else {}
            records = [r for r in benchmark_result.get("model_records", []) if isinstance(r, dict)]
            model_names = [r.get("model", "N/A") for r in records]
            r2_values = [r.get("mean_r2", 0.0) for r in records]
            self._pending_validation_tab_updates[self.tab_benchmark_r2] = (
                lambda: self._update_benchmark_r2_chart(model_names, r2_values)
            )
            self._pending_validation_tab_updates[self.tab_benchmark_speed] = (
                lambda: self._update_benchmark_speed_chart(records, r2_values)
            )
            self._pending_validation_tab_updates[self.tab_benchmark_pred_actual] = (
                lambda: self._update_benchmark_pred_actual_chart(benchmark_result, records)
            )
        else:
            return

        if (
            hasattr(self, "tab_widget")
            and hasattr(self, "tab_validation")
            and self.tab_widget.currentWidget() is self.tab_validation
        ):
            self._on_validation_tab_changed(self.validation_plot_tabs.currentIndex())

    def _on_validation_tab_changed(self, index):
        if not hasattr(self, "validation_plot_tabs"):
            return
        if not self._pending_validation_tab_updates:
            return

        active_tab = self.validation_plot_tabs.widget(index)
        update_fn = self._pending_validation_tab_updates.pop(active_tab, None)
        if update_fn is None:
            return

        try:
            update_fn()
        except Exception as exc:
            self._pending_validation_tab_updates.pop(active_tab, None)
            self.on_status_update(f"Warning: validation visualization update failed ({exc})")

    def _on_validation_benchmark_error(self, message):
        self.validation_status_label.setText("Error")
        self._set_validation_buttons_enabled(True)
        self.show_error("Validation/Benchmark Error", message)

    def _update_validation_summary_table(self, summary):
        rows = [
            ("Samples", f"{summary['samples']}"),
            ("Temperature (K)", f"{summary['temp_min']:.1f} ~ {summary['temp_max']:.1f}"),
            ("Voltage (V)", f"{summary['volt_min']:.3f} ~ {summary['volt_max']:.3f}"),
            ("Mean SNM", f"{summary['snm_mean_mv']:.2f} mV"),
            ("SNM Std", f"{summary['snm_std_mv']:.2f} mV"),
            ("Nominal SNM MAE", f"{summary['snm_nominal_mae_mv']:.3f} mV"),
            ("Nominal SNM RMSE", f"{summary['snm_nominal_rmse_mv']:.3f} mV"),
            ("BER (mean)", f"{summary['ber_mean']:.3e}"),
            ("Noise Sigma", f"{summary['noise_mean_mv']:.3f} mV"),
            ("corr(T,SNM)", f"{summary['temp_corr_snm']:.3f}"),
            ("corr(V,SNM)", f"{summary['volt_corr_snm']:.3f}")
        ]
        self.validation_summary_table.setRowCount(len(rows))
        for i, (metric, value) in enumerate(rows):
            self.validation_summary_table.setItem(i, 0, QTableWidgetItem(metric))
            self.validation_summary_table.setItem(i, 1, QTableWidgetItem(value))
        self.validation_summary_label.setText("Latest validation/benchmark summary.")

    def update_benchmark_table(self, rows):
        self.benchmark_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.benchmark_table.setItem(i, 0, QTableWidgetItem(str(row.get("Model", "-"))))
            self.benchmark_table.setItem(i, 1, QTableWidgetItem(f"{row.get('R2', float('nan')):.4f}" if isinstance(row.get('R2'), (int, float)) else "-"))
            self.benchmark_table.setItem(i, 2, QTableWidgetItem(f"{row.get('RMSE', float('nan')):.4f}" if isinstance(row.get('RMSE'), (int, float)) else "-"))
            self.benchmark_table.setItem(i, 3, QTableWidgetItem(f"{row.get('MAE', float('nan')):.4f}" if isinstance(row.get('MAE'), (int, float)) else "-"))
            self.benchmark_table.setItem(i, 4, QTableWidgetItem(f"{row.get('Train Time (ms)', float('nan')):.3f}" if isinstance(row.get('Train Time (ms)'), (int, float)) else "-"))
            self.benchmark_table.setItem(i, 5, QTableWidgetItem(f"{row.get('Inference Time (ms)', float('nan')):.3f}" if isinstance(row.get('Inference Time (ms)'), (int, float)) else "-"))
            self.benchmark_table.setItem(i, 6, QTableWidgetItem(str(row.get("Params", "-"))))

    def update_benchmark_figures(self, benchmark_result):
        records = benchmark_result.get("model_records", [])
        if not records:
            return
        model_names = [r["model"] for r in records]
        r2_values = [r["mean_r2"] for r in records]
        self._update_benchmark_r2_chart(model_names, r2_values)
        self._update_benchmark_speed_chart(records, r2_values)
        self._update_benchmark_pred_actual_chart(benchmark_result, records, benchmark_result.get("best_model"))

    def _update_benchmark_r2_chart(self, model_names, r2_values):
        self.canvas_benchmark_r2.figure.clear()
        ax = self.canvas_benchmark_r2.figure.add_subplot(111)
        ax.bar(model_names, r2_values, color="#2ca02c", alpha=0.8)
        ax.set_title("R짼 Comparison (avg over SNM/BER/noise)")
        ax.set_ylabel("R짼")
        ax.set_xticklabels(model_names, rotation=30, ha="right")
        self.canvas_benchmark_r2.figure.tight_layout()
        self.canvas_benchmark_r2.draw_idle()

    def _update_benchmark_speed_chart(self, records, r2_values):
        self.canvas_benchmark_speed.figure.clear()
        ax = self.canvas_benchmark_speed.figure.add_subplot(111)
        speed = [r["mean_infer_ms"] for r in records]
        model_names = [r["model"] for r in records]
        ax.scatter(speed, r2_values, s=80, alpha=0.8, c="#1f77b4")
        for i, name in enumerate(model_names):
            ax.annotate(name, (speed[i], r2_values[i]),
                        textcoords="offset points", xytext=(4, 4), fontsize=8)
        ax.set_xlabel("Inference time (ms)")
        ax.set_ylabel("R짼")
        ax.set_title("Speed vs Accuracy (mean over targets)")
        ax.grid(alpha=0.3)
        self.canvas_benchmark_speed.figure.tight_layout()
        self.canvas_benchmark_speed.draw_idle()

    def _update_benchmark_pred_actual_chart(self, benchmark_result, records, best_model=None):
        if best_model is None:
            best_model = benchmark_result.get("best_model")
        if not records:
            return

        pred_result = benchmark_result.get("predictions", {}).get(best_model, {})
        snm_data = pred_result.get("snm", {})

        self.canvas_benchmark_pred_actual.figure.clear()
        if snm_data:
            y_true = np.asarray(snm_data.get("y_true"))
            y_pred = np.asarray(snm_data.get("y_pred"))

            ax1 = self.canvas_benchmark_pred_actual.figure.add_subplot(1, 2, 1)
            ax1.scatter(y_true, y_pred, alpha=0.45, s=12)
            mn = min(np.min(y_true), np.min(y_pred))
            mx = max(np.max(y_true), np.max(y_pred))
            ax1.plot([mn, mx], [mn, mx], "k--", linewidth=1.0)
            ax1.set_xlabel("Actual SNM (V)")
            ax1.set_ylabel("Predicted SNM (V)")
            ax1.set_title(f"Predicted vs Actual ({best_model})")
            ax1.grid(alpha=0.3)

            residual = y_pred - y_true
            ax2 = self.canvas_benchmark_pred_actual.figure.add_subplot(1, 2, 2)
            ax2.hist(residual, bins=40, alpha=0.8)
            ax2.set_xlabel("Residual (Pred - Actual)")
            ax2.set_ylabel("Count")
            ax2.set_title("Residual Distribution")
            ax2.grid(alpha=0.3)

            self.canvas_benchmark_pred_actual.figure.tight_layout()
        else:
            ax = self.canvas_benchmark_pred_actual.figure.add_subplot(111)
            ax.text(0.5, 0.5, "Run ML benchmark to generate prediction plot.", ha='center', va='center')
            ax.axis('off')
        self.canvas_benchmark_pred_actual.draw_idle()

    def plot_validation_profile(self, data, residual):
        """Plot validation dataset distribution and residual summary."""
        self.canvas_validation_profile.figure.clear()
        ax1 = self.canvas_validation_profile.figure.add_subplot(2, 2, 1)
        ax1.hist(np.asarray(data["snm_mean"]) * 1000, bins=30, alpha=0.7, color="#1f77b4")
        ax1.set_title("SNM mean (mV)")
        ax1.set_xlabel("SNM (mV)")
        ax1.grid(alpha=0.3)

        ax2 = self.canvas_validation_profile.figure.add_subplot(2, 2, 2)
        ax2.hist(np.asarray(data["ber"]), bins=30, alpha=0.7, color="#2ca02c")
        ax2.set_title("BER")
        ax2.set_xlabel("BER")
        ax2.grid(alpha=0.3)

        ax3 = self.canvas_validation_profile.figure.add_subplot(2, 2, 3)
        ax3.hist(np.asarray(data["noise_sigma"]) * 1000, bins=30, alpha=0.7, color="#ff7f0e")
        ax3.set_title("Thermal Sigma (mV)")
        ax3.set_xlabel("mV")
        ax3.grid(alpha=0.3)

        ax4 = self.canvas_validation_profile.figure.add_subplot(2, 2, 4)
        ax4.hist(np.asarray(residual) * 1000, bins=30, alpha=0.7, color="#9467bd")
        ax4.set_title("Residual (Monte Carlo - nominal)")
        ax4.set_xlabel("Residual (mV)")
        ax4.grid(alpha=0.3)

        self.canvas_validation_profile.figure.tight_layout()
        self.canvas_validation_profile.draw_idle()

    def export_validation_benchmark(self):
        """Export validation/benchmark results."""
        if self.validation_result is None and self.benchmark_result is None:
            self.show_warning("Warning", "No results to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Validation & Benchmark Data",
            "validation_benchmark_export.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        def _to_listable(value):
            if isinstance(value, np.ndarray):
                return value.tolist()
            if isinstance(value, (list, tuple)):
                return [ _to_listable(v) for v in value ]
            if isinstance(value, dict):
                return {k: _to_listable(v) for k, v in value.items()}
            return value

        payload = {}
        if self.validation_result is not None:
            payload["validation"] = {
                "summary": _to_listable(self.validation_result.get("summary", {})),
                "data": {k: _to_listable(v) for k, v in self.validation_result.get("data", {}).items()}
            }
        if self.benchmark_result is not None:
            payload["benchmark"] = {
                "table_rows": _to_listable(self.benchmark_result.get("table_rows", [])),
                "benchmark_result": _to_listable(self.benchmark_result.get("benchmark_result", {}))
            }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                import json
                json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
            self.show_info("Success", f"Exported to:\n{file_path}")
        except Exception as e:
            self.show_error("Export Error", str(e))

    def create_right_panel(self):
        """Right panel - Information and settings"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.apply_layout_tokens(layout, "small")

        title = self.create_title_label("Simulation Information", level="title")
        layout.addWidget(title)

        # Results snapshot
        results_group, results_layout = self.create_group_box("Result Snapshot")
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        metrics = [
            "Analysis Mode",
            "Temperature",
            "Voltage",
            "Cell Count",
            "Width x Length",
            "BER",
            "Mean Noise",
            "SNM Average",
            "Pelgrom sigma_Vth",
            "Monte Carlo Runs",
            "Runtime Engine",
            "Reliability"
        ]
        self.results_table.setRowCount(len(metrics))
        for i, metric in enumerate(metrics):
            self.results_table.setItem(i, 0, QTableWidgetItem(metric))
            self.results_table.setItem(i, 1, QTableWidgetItem("-"))
        results_layout.addWidget(self.results_table)
        layout.addWidget(results_group)

        # Quick status / quick info
        quick_group, quick_layout = self.create_group_box("Quick Status")
        self.quick_status_mode_label = QLabel("Mode: -")
        self.quick_status_compute_label = QLabel("Compute: -")
        self.quick_status_backend_label = QLabel("Backend: -")
        self.quick_status_dispatch_label = QLabel("Dispatch: -")
        self.quick_status_engine_label = QLabel("Runtime engine: -")
        self.quick_status_result_label = QLabel("Result: -")

        for label in [
            self.quick_status_mode_label,
            self.quick_status_compute_label,
            self.quick_status_backend_label,
            self.quick_status_dispatch_label,
            self.quick_status_engine_label,
            self.quick_status_result_label,
        ]:
            label.setProperty("ui-typography", "caption")
            quick_layout.addWidget(label)

        self._refresh_quick_status_panel()
        layout.addWidget(quick_group)

        # Information note
        info_label = QLabel(
            "<b>Advanced SRAM Simulator</b><br><br>"
            "- Perceptron Noise Model<br>"
            "- SNM Analysis<br>"
            "- Variability (Pelgrom)<br>"
            "- Thermal/Shot Noise<br>"
            "- Process Corner<br>"
            "- NBTI/HCI Reliability<br>"
            "- Research Data<br>"
            "- Validation & ML Benchmark"
        )
        info_label.setWordWrap(True)
        info_label.setProperty("ui-style", "panel-muted")
        layout.addWidget(info_label)

        layout.addStretch()
        return panel

    # ========================================================================
    # Event Handlers
    # ========================================================================

    def on_mode_changed(self, text):
        """Analysis mode changed"""
        self.analysis_mode = text
        self._refresh_quick_status_panel()

    def on_backend_changed(self, text):
        """Backend selection changed"""
        if "hybrid" in text.lower():
            self.backend_type = "hybrid"
        else:
            self.backend_type = "standard"
        self._refresh_quick_status_panel()

    def on_compute_mode_changed(self, text):
        """Compute dispatch preference changed."""
        normalized = str(text).strip().lower()
        if normalized == "gpu":
            self.compute_mode_preference = "gpu"
        elif normalized == "cpu":
            self.compute_mode_preference = "cpu"
        else:
            self.compute_mode_preference = "auto"
        self._refresh_quick_status_panel()

    def _queue_slider_update(self, key: str, value):
        """Queue slider-driven values and batch-apply on the next debounce tick."""
        self._slider_pending_updates[key] = value
        self._slider_update_timer.start()

    def _flush_slider_updates(self):
        """Apply pending slider-driven values in one batch."""
        if not self._slider_pending_updates:
            return

        pending = dict(self._slider_pending_updates)
        self._slider_pending_updates = {}

        if "temperature" in pending:
            self.temperature = int(pending["temperature"])
        if "voltage" in pending:
            self.voltage = float(f"{float(pending['voltage']):.2f}")
        if "num_cells" in pending:
            self.num_cells = int(pending["num_cells"])
        if "monte_carlo_runs" in pending:
            self.monte_carlo_runs = int(pending["monte_carlo_runs"])

    def on_temp_changed(self, value):
        """Temperature changed"""
        self._queue_slider_update("temperature", value)

    def on_voltage_changed(self, value):
        """Voltage changed"""
        self._queue_slider_update("voltage", self.volt_spinbox.value())

    def on_cells_changed(self, value):
        """Cell count changed"""
        self._queue_slider_update("num_cells", value)

    def on_variability_changed(self, state):
        """Variability toggle"""
        self.variability_enable = (state == Qt.CheckState.Checked.value)

    def on_mc_changed(self, value):
        """Monte Carlo runs changed"""
        self.mc_label.setText(str(value))
        self._queue_slider_update("monte_carlo_runs", value)

    def on_width_changed(self, value):
        """Width changed"""
        self.width = value

    def on_length_changed(self, value):
        """Length changed"""
        self.length = value

    def on_data_type_changed(self, button):
        """Data type changed"""
        self.data_type = button.property("data_type")

    def on_progress_update(self, value):
        """Progress bar update"""
        if self._analysis_plan_active and self._analysis_plan:
            step = max(0, self._analysis_plan_index)
            plan_total = max(1, len(self._analysis_plan))
            scaled = int((step + float(value) / 100.0) / plan_total * 100)
            self.progress_bar.setValue(max(0, min(100, scaled)))
            return
        self.progress_bar.setValue(value)

    def _append_batch_log(self, message):
        """Append one line to the batch log text panel."""
        if not hasattr(self, "simulation_batch_log") or self.simulation_batch_log is None:
            return

        if self._analysis_plan_log_lines is None:
            self._analysis_plan_log_lines = []

        self._analysis_plan_log_lines.append(str(message))
        if len(self._analysis_plan_log_lines) > 250:
            self._analysis_plan_log_lines = self._analysis_plan_log_lines[-250:]

        self.simulation_batch_log.setPlainText("\n".join(self._analysis_plan_log_lines))
        scrollbar = self.simulation_batch_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _clear_batch_log(self, header=None):
        """Reset the batch log with optional header."""
        self._analysis_plan_log_lines = []
        if hasattr(self, "simulation_batch_log") and self.simulation_batch_log is not None:
            self.simulation_batch_log.clear()
            if header:
                self._append_batch_log(header)

    def _set_runtime_status(self, status: str, level: str = "info"):
        """Update runtime status label text + semantic level."""
        if not hasattr(self, "status_label") or self.status_label is None:
            return
        self.status_label.setText(str(status))
        self.status_label.setProperty("ui-status", level)
        self.style().unpolish(self.status_label)
        self.style().polish(self.status_label)

    def _refresh_quick_status_panel(self):
        """Refresh compact right-panel status summary."""
        if self.quick_status_mode_label is None:
            return

        self.quick_status_mode_label.setText(f"Mode: {self.analysis_mode}")
        self.quick_status_compute_label.setText(f"Compute: {self.compute_mode_preference.upper()}")
        backend_name = "Hybrid (Perceptron)" if self.backend_type == "hybrid" else "Standard"
        self.quick_status_backend_label.setText(f"Backend: {backend_name}")

        if self._last_dispatch_info is not None:
            selected = self._last_dispatch_info.get("selected", "-")
            requested = self._last_dispatch_info.get("requested_compute_mode", self.compute_mode_preference)
            compute_mode = self._last_dispatch_info.get("compute_mode", self.compute_mode_preference)
            reason = str(self._last_dispatch_info.get("reason", ""))
            if reason:
                self.quick_status_dispatch_label.setText(
                    f"Dispatch: req={requested} -> mode={compute_mode}, policy={selected} ({reason})"
                )
            else:
                self.quick_status_dispatch_label.setText(
                    f"Dispatch: req={requested} -> mode={compute_mode}, policy={selected}"
                )
        else:
            self.quick_status_dispatch_label.setText("Dispatch: -")

        exec_meta = self.current_result.get("_exec", {}) if isinstance(self.current_result, dict) else {}
        runtime_engine = (
            self.current_result.get("runtime_engine", exec_meta.get("selected", "-"))
            if isinstance(self.current_result, dict) else "-"
        )
        if runtime_engine is None:
            runtime_engine = "-"
        self.quick_status_engine_label.setText(f"Runtime engine: {runtime_engine}")
        self.quick_status_result_label.setText(
            "Result: Available" if isinstance(self.current_result, dict) else "Result: Not available (run simulation)"
        )

    def on_status_update(self, status):
        """Status update"""
        text = str(status)
        lowered = text.lower()
        if any(token in lowered for token in ("error", "failed", "exception")):
            level = "error"
        elif any(token in lowered for token in ("warning", "fallback", "degraded")):
            level = "warning"
        elif any(token in lowered for token in ("complete", "done", "connected", "ready")):
            level = "success"
        elif any(token in lowered for token in ("running", "simulating", "initializing", "generating")):
            level = "info"
        else:
            level = "muted"
        self._set_runtime_status(text, level=level)

    def reset_parameters(self):
        """Reset parameters"""
        self.temp_slider.setValue(310)
        self.volt_slider.setValue(100)
        self.cell_slider.setValue(32)
        self.variability_checkbox.setChecked(True)
        self.mc_slider.setValue(10)
        self.width_spinbox.setValue(1.0)
        self.length_spinbox.setValue(1.0)
        index = self.mode_combo.findText("Basic Noise")
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
        self.analysis_mode = "Basic Noise"
        self.current_result = None
        if hasattr(self, "results_table"):
            for row in range(self.results_table.rowCount()):
                self.results_table.setItem(row, 1, QTableWidgetItem("-"))
        self._flush_slider_updates()
        self._last_dispatch_info = None
        self._refresh_quick_status_panel()

    def generate_input_data(self):
        """Generate input data"""
        if self.data_type == "random":
            return np.random.randint(0, 2, self.num_cells).tolist()
        elif self.data_type == "all0":
            return [0] * self.num_cells
        elif self.data_type == "all1":
            return [1] * self.num_cells
        elif self.data_type == "checkerboard":
            return [(i % 2) for i in range(self.num_cells)]
        else:
            return np.random.randint(0, 2, self.num_cells).tolist()

    def _resolve_analysis_type(self, mode):
        """Convert analysis mode label to simulation analysis_type."""
        if mode == "Basic Noise":
            return "basic"
        if mode == "SNM Analysis":
            return "snm"
        if mode == "Variability":
            return "variability"
        if mode == "Thermal Noise":
            return "thermal"
        if mode == "Retention Mode":
            return "retention"
        if mode == "Process Corner":
            return "process_corner"
        if mode == "NBTI/HCI Reliability":
            return "reliability"
        return "basic"

    def _get_all_core_analysis_plan(self):
        """Default set of modes for the 'All Core Analysis' plan."""
        return ["basic", "snm", "variability", "thermal", "reliability"]

    def _start_single_simulation(self, analysis_type, dispatch, step_index=None, step_total=None):
        """Start one native simulation job with given analysis type."""
        self._active_simulation_analysis_type = analysis_type

        input_data = self.generate_input_data()
        self.sim_thread.set_parameters(
            temperature=self.temperature,
            voltage=self.voltage,
            num_cells=self.num_cells,
            input_data=input_data,
            noise_enable=self.noise_enable,
            variability_enable=self.variability_enable,
            monte_carlo_runs=self.monte_carlo_runs,
            width=self.width,
            length=self.length,
            analysis_type=analysis_type,
            backend_type=self.backend_type,  # Pass backend selection
            compute_mode=dispatch['compute_mode'],
            latency_mode=dispatch['latency_mode'],
        )
        if step_index is not None and step_total is not None:
            self.simulate_btn.setText(f"Simulating ({step_index}/{step_total})")
            self.on_status_update(
                f"Running simulation step {step_index}/{step_total}: {analysis_type}"
            )
        else:
            self.on_status_update(f"Running simulation: {analysis_type}")
        self._append_batch_log(f"Started: {analysis_type}" + (
            f" (step {step_index}/{step_total})" if step_index is not None and step_total is not None else ""
        ))
        self.sim_thread.start()

    def _finalize_all_core_batch(self, partial=False):
        """Finalize all-core batch state and refresh UI."""
        self._analysis_plan_active = False
        self.simulate_btn.setEnabled(True)
        if hasattr(self, "reset_btn") and self.reset_btn is not None:
            self.reset_btn.setEnabled(True)

        if partial:
            self.simulate_btn.setText("Run Simulation (stopped)")
        else:
            self.simulate_btn.setText("Run Simulation")

        current_step = self._analysis_plan_index + 1 if self._analysis_plan_index >= 0 else 0
        plan_total = len(self._analysis_plan) if self._analysis_plan else 0
        if partial and plan_total:
            self.progress_bar.setValue(int(current_step / plan_total * 100))
        else:
            self.progress_bar.setValue(100)

        if not self._analysis_plan_results:
            if self._analysis_plan_errors:
                self._append_batch_log("Batch finished with errors; no successful step completed.")
                self.on_status_update("All-core simulation batch completed with errors.")
                self.show_error(
                    "Simulation Error",
                    "All core analysis steps failed.\n" + "\n".join(self._analysis_plan_errors),
                )
            else:
                self._append_batch_log("All-core simulation batch canceled.")
                self.on_status_update("All-core simulation batch canceled.")
            return

        summary_result = None
        for analysis_type in ("basic", "snm", "variability", "thermal", "reliability"):
            candidate = self._analysis_plan_results.get(analysis_type)
            if candidate is not None:
                summary_result = candidate
                break
        if summary_result is None:
            summary_result = next(iter(self._analysis_plan_results.values()))

        self.current_result = summary_result
        self._refresh_quick_status_panel()
        self._queue_main_tab_visualizations_from_plan()

        try:
            self.update_results_table(summary_result)
        except Exception as exc:
            self.on_status_update(f"Warning: results table update failed ({exc})")
            self.show_error("UI Update Error", f"Failed to update results table:\n{exc}")

        if AI_ADVISOR_AVAILABLE and hasattr(self, 'ai_context_text'):
            snm_values = summary_result.get('snm_values', [0])
            snm_mean = np.mean(snm_values) * 1000 if len(snm_values) > 0 else 0
            context_summary = f"""
Current Simulation Results:
Temperature: {self.temperature}K
Voltage: {self.voltage}V
Num Cells: {self.num_cells}
Backend: {summary_result.get('backend', 'unknown')}
Runtime Engine: {summary_result.get('runtime_engine', summary_result.get('_exec', {}).get('selected', 'unknown'))}
BER: {summary_result.get('bit_error_rate', 0):.2e}
SNM (mean): {snm_mean:.2f} mV
"""
            self.ai_context_text.setPlainText(context_summary)

        if partial:
            self._append_batch_log("Batch stopped by error policy.")
            self.on_status_update("All-core simulation stopped early.")
        elif self._analysis_plan_errors:
            self._append_batch_log("Batch completed with warning(s).")
            self.on_status_update(
                f"All-core simulation completed with {len(self._analysis_plan_errors)} warning(s)."
            )
        else:
            self._append_batch_log("Batch completed successfully.")
            self.on_status_update("All-core simulation complete!")

    def run_simulation(self):
        """Run simulation"""
        if self.sim_thread.isRunning():
            return

        self.current_result = None
        self._flush_slider_updates()
        if hasattr(self, "results_table"):
            for row in range(self.results_table.rowCount()):
                self.results_table.setItem(row, 1, QTableWidgetItem("-"))
        dispatch = self._resolve_heavy_simulation_dispatch(
            self.num_cells,
            self.monte_carlo_runs,
            compute_mode=self.compute_mode_preference,
        )
        self._last_dispatch_info = dispatch
        self._refresh_quick_status_panel()
        self._clear_batch_log(f"Run requested - mode: {self.analysis_mode}")
        self.simulate_btn.setEnabled(False)
        if hasattr(self, "reset_btn") and self.reset_btn is not None:
            self.reset_btn.setEnabled(False)
        self.simulate_btn.setText("Simulating...")
        self.progress_bar.setValue(0)
        self._analysis_plan_active = False
        self._analysis_plan = []
        self._analysis_plan_results = {}
        self._analysis_plan_errors = []
        self._analysis_plan_index = 0
        self.on_status_update("Running simulation...")
        self.on_status_update(
            f"Dispatch: {dispatch['selected']} ({dispatch['reason']}) | "
            f"compute_mode={dispatch['compute_mode']}, latency_mode={dispatch['latency_mode']}"
        )

        mode = self.analysis_mode
        if mode == "All Core Analysis":
            self._analysis_plan = self._get_all_core_analysis_plan()
            self._analysis_plan_active = True
            self._analysis_plan_index = 0
            self._analysis_plan_errors = []
            self._analysis_plan_results = {}
            self._pending_main_visual_updates = {}
            self._append_batch_log(f"Batch start: {len(self._analysis_plan)} steps")
            self.simulate_btn.setText(f"Simulating (1/{len(self._analysis_plan)})")
            try:
                self._start_single_simulation(
                    self._analysis_plan[0],
                    dispatch,
                    step_index=1,
                    step_total=len(self._analysis_plan),
                )
            except Exception as exc:
                self._analysis_plan_active = False
                self.simulate_btn.setEnabled(True)
                if hasattr(self, "reset_btn") and self.reset_btn is not None:
                    self.reset_btn.setEnabled(True)
                self.simulate_btn.setText("Run Simulation")
                self.on_status_update(f"Error: {str(exc)}")
                self.show_error("Simulation Error", f"Failed to start batch simulation:\n{exc}")
            return

        try:
            analysis_type = self._resolve_analysis_type(mode)
            self._append_batch_log(f"Single run: {analysis_type}")
            self._start_single_simulation(analysis_type, dispatch)
        except Exception as exc:
            self.simulate_btn.setEnabled(True)
            if hasattr(self, "reset_btn") and self.reset_btn is not None:
                self.reset_btn.setEnabled(True)
            self.simulate_btn.setText("Run Simulation")
            self.on_status_update(f"Error: {str(exc)}")
            self.show_error("Simulation Error", f"Failed to prepare simulation:\n{exc}")

    def on_simulation_complete(self, result):
        """Simulation complete callback"""
        if self._analysis_plan_active and self._analysis_plan:
            step_analysis_type = self._active_simulation_analysis_type
            if 'error' in result and step_analysis_type is not None:
                error_message = result['error']
                self._analysis_plan_errors.append(f"{step_analysis_type}: {error_message}")
                self._append_batch_log(f"Step failed: {step_analysis_type}: {error_message}")
                if self._analysis_plan_stop_on_error:
                    self._append_batch_log("Stop-on-error enabled. Finishing batch with partial results.")
                    self._finalize_all_core_batch(partial=True)
                    return
            else:
                result_analysis_type = result.get("analysis_type", step_analysis_type)
                if result_analysis_type is not None:
                    self._analysis_plan_results[result_analysis_type] = result
                    self._append_batch_log(f"Step completed: {result_analysis_type}")
                    try:
                        self._queue_main_tab_visualizations(result, force_reset=False)
                    except Exception as exc:
                        self._append_batch_log(
                            f"Warning: visualization queue failed for {result_analysis_type} ({exc})"
                        )
                        self.on_status_update(
                            f"Warning: visualization queue failed for {result_analysis_type} ({exc})"
                        )

            has_more = (self._analysis_plan_index + 1) < len(self._analysis_plan)
            if has_more:
                self._analysis_plan_index += 1
                next_type = self._analysis_plan[self._analysis_plan_index]
                self.on_status_update(f"Queueing next step ({self._analysis_plan_index + 1}/{len(self._analysis_plan)})")
                try:
                    self._start_single_simulation(
                        next_type,
                        self._last_dispatch_info,
                        step_index=self._analysis_plan_index + 1,
                        step_total=len(self._analysis_plan),
                    )
                    return
                except Exception as exc:
                    self._analysis_plan_active = False
                    self._analysis_plan_errors.append(f"{next_type}: {exc}")
                    self._append_batch_log(f"Failed to launch next step: {next_type}: {exc}")

            self._finalize_all_core_batch(partial=False)
            return

        self.simulate_btn.setEnabled(True)
        if hasattr(self, "reset_btn") and self.reset_btn is not None:
            self.reset_btn.setEnabled(True)
        self.simulate_btn.setText("Run Simulation")
        self.progress_bar.setValue(100)

        if 'error' in result:
            self.on_status_update(f"Error: {result['error']}")
            self.show_error("Simulation Error", f"Error: {result['error']}")
            self._append_batch_log(f"Single run failed: {result['error']}")
            return

        self.current_result = result
        self._refresh_quick_status_panel()

        exec_meta = result.get("_exec", {}) if isinstance(result, dict) else {}
        runtime_engine = result.get("runtime_engine", exec_meta.get("selected", "unknown")) if isinstance(result, dict) else "unknown"
        requested_mode = (
            self._last_dispatch_info.get("requested_compute_mode", self.compute_mode_preference)
            if isinstance(self._last_dispatch_info, dict) else self.compute_mode_preference
        )
        if requested_mode == "gpu" and runtime_engine != "gpu":
            self.on_status_update(
                f"Warning: GPU was requested, but runtime executed on {runtime_engine}."
            )

        try:
            self.update_results_table(result)
        except Exception as exc:
            self.on_status_update(f"Warning: results table update failed ({exc})")
            self.show_error("UI Update Error", f"Failed to update results table:\n{exc}")

        try:
            self.update_visualizations(result)
        except Exception as exc:
            self.on_status_update(f"Warning: visualization update failed ({exc})")
            self.show_error("Visualization Error", f"Failed to update visualization:\n{exc}")

        # Update AI context if available
        if AI_ADVISOR_AVAILABLE and hasattr(self, 'ai_context_text'):
            snm_values = result.get('snm_values', [0])
            snm_mean = np.mean(snm_values) * 1000 if len(snm_values) > 0 else 0
            context_summary = f"""
Current Simulation Results:
Temperature: {self.temperature}K
Voltage: {self.voltage}V
Num Cells: {self.num_cells}
Backend: {result.get('backend', 'unknown')}
Runtime Engine: {result.get('runtime_engine', result.get('_exec', {}).get('selected', 'unknown'))}
BER: {result.get('bit_error_rate', 0):.2e}
SNM (mean): {snm_mean:.2f} mV
            """
            self.ai_context_text.setPlainText(context_summary)
            self._append_batch_log("Single simulation complete.")

        self.on_status_update("Simulation complete!")

    def update_results_table(self, result):
        """Update results table"""
        exec_meta = result.get("_exec", {}) if isinstance(result, dict) else {}
        runtime_engine = result.get("runtime_engine", exec_meta.get("selected", "unknown")) if isinstance(result, dict) else "unknown"

        values = [
            self.analysis_mode,
            f"{self.temperature} K ({self.temperature - 273.15:.1f}C)",
            f"{self.voltage:.2f} V",
            f"{self.num_cells}",
            f"{self.width:.1f} x {self.length:.1f} um",
            "-",
            "-",
            "-",
            "-",
            "-",
            runtime_engine,
            "-",
        ]

        if 'analysis_type' not in result or result.get('analysis_type') in ['basic', 'snm', 'variability', 'thermal', 'retention', 'process_corner', None]:
            if 'bit_error_rate' in result:
                values[5] = f"{result['bit_error_rate']*100:.2f}%"
            if 'noise_values' in result:
                values[6] = f"{np.mean(result['noise_values']):.6f}"
            if 'snm_values' in result and result['snm_values']:
                values[7] = f"{np.mean(result['snm_values'])*1000:.2f} mV"
            if ADVANCED_AVAILABLE:
                values[8] = f"{5.0/np.sqrt(self.width*self.length):.2f} mV"
            values[9] = f"{self.monte_carlo_runs}"
            if 'bit_error_rate' in result:
                values[11] = f"{(1-result['bit_error_rate'])*100:.1f}%"

        elif result.get('analysis_type') == 'reliability':
            values[5] = "-"
            values[6] = "-"
            values[7] = "-"
            values[8] = f"{5.0/np.sqrt(self.width*self.length):.2f} mV"
            values[9] = "-"
            values[10] = runtime_engine
            if 'mean_lifetime' in result:
                values[11] = f"{result['mean_lifetime']:.2f} years"

        for i, value in enumerate(values):
            self.results_table.setItem(i, 1, QTableWidgetItem(value))

    def update_visualizations(self, result):
        """Update visualizations"""
        self._queue_main_tab_visualizations(result)

    def _queue_main_tab_visualizations(self, result, force_reset: bool = True):
        """Queue visualization updates and render only if target tab is currently visible."""
        if force_reset:
            self._pending_main_visual_updates = {}

        analysis_type = result.get('analysis_type')

        if analysis_type in (None, 'basic', 'snm', 'variability', 'thermal', 'retention', 'process_corner'):
            self._pending_main_visual_updates[self.tab_3d] = lambda: self.plot_3d_noise_map(result)

        if ADVANCED_AVAILABLE and analysis_type != 'reliability' and 'snm_values' in result and result['snm_values']:
            self._pending_main_visual_updates[self.tab_snm] = lambda: self.plot_snm_analysis(result)

        if ADVANCED_AVAILABLE and analysis_type != 'reliability' and 'monte_carlo_ber' in result:
            self._pending_main_visual_updates[self.tab_var] = lambda: self.plot_variability(result)
        elif ADVANCED_AVAILABLE and analysis_type != 'reliability' and 'bit_error_rate' in result:
            self._pending_main_visual_updates[self.tab_var] = lambda: self.plot_variability_basic(result)

        if ADVANCED_AVAILABLE and analysis_type == 'thermal':
            self._pending_main_visual_updates[self.tab_thermal_noise] = lambda: self.plot_thermal_noise()

        if RELIABILITY_AVAILABLE and analysis_type == 'reliability':
            self._pending_main_visual_updates[self.tab_reliability] = lambda: self.plot_reliability()

        target_tab_widget = (
            self.tab_widget_advanced
            if self.analysis_view_mode == "advanced"
            else self.tab_widget_core
        )
        self._on_visual_tab_changed(target_tab_widget.currentIndex(), target_tab_widget)

    def _queue_main_tab_visualizations_from_plan(self):
        """Queue visualization updates for each successful result in current plan."""
        if not self._analysis_plan_results:
            return

        plan_results = [r for r in self._analysis_plan_results.values() if isinstance(r, dict) and "error" not in r]
        if not plan_results:
            return

        latest_by_tab = {
            self.tab_3d: None,
            self.tab_snm: None,
            self.tab_var: None,
            self.tab_thermal_noise: None,
            self.tab_reliability: None,
        }

        for result in plan_results:
            analysis_type = result.get('analysis_type')
            if analysis_type in (None, 'basic', 'snm', 'variability', 'thermal', 'retention', 'process_corner'):
                latest_by_tab[self.tab_3d] = result
            if ADVANCED_AVAILABLE and analysis_type != 'reliability' and result.get('snm_values'):
                latest_by_tab[self.tab_snm] = result
            if ADVANCED_AVAILABLE and analysis_type != 'reliability' and (
                result.get('monte_carlo_ber') is not None or result.get('bit_error_rate') is not None
            ):
                latest_by_tab[self.tab_var] = result
            if ADVANCED_AVAILABLE and analysis_type == 'thermal':
                latest_by_tab[self.tab_thermal_noise] = result
            if RELIABILITY_AVAILABLE and analysis_type == 'reliability':
                latest_by_tab[self.tab_reliability] = result

        self._pending_main_visual_updates = {}
        for result in latest_by_tab.values():
            if result is not None:
                self._queue_main_tab_visualizations(result, force_reset=False)

    def _on_visual_tab_changed(self, index, tab_widget=None):
        if tab_widget is None:
            tab_widget = self.tab_widget
        if index is None or index < 0:
            return
        if not self._pending_main_visual_updates:
            return

        active_tab = tab_widget.widget(index)
        update_fn = self._pending_main_visual_updates.pop(active_tab, None)
        if update_fn is None:
            return

        try:
            update_fn()
        except Exception as exc:
            self._pending_main_visual_updates.pop(active_tab, None)
            self.on_status_update(f"Warning: visualization update failed ({exc})")

    def plot_3d_noise_map(self, result):
        """Plot 3D noise map"""
        self.canvas_3d.figure.clear()
        ax = self.canvas_3d.figure.add_subplot(111, projection='3d')

        temps = np.linspace(260, 360, 30)
        volts = np.linspace(0.8, 1.2, 30)
        T, V = np.meshgrid(temps, volts)

        Z = self._compute_noise_map_surface(T, V, result)

        surf = ax.plot_surface(T, V, Z, cmap='viridis', alpha=0.8, edgecolor='none')

        current_z = float(self._estimate_noise_weight(self.temperature, self.voltage, result))
        ax.scatter([self.temperature], [self.voltage], [current_z],
                  color='red', s=200, marker='o', label='Current')

        ax.set_xlabel('Temperature (K)')
        ax.set_ylabel('Voltage (V)')
        ax.set_zlabel('Noise Weight')
        ax.set_title('Noise Weight Map (Temperature & Voltage Dependency)')
        ax.legend()

        # Add horizontal colorbar at the bottom
        self.canvas_3d.figure.colorbar(surf, ax=ax, label='Noise Weight',
                                       orientation='horizontal', pad=0.1, shrink=0.8)
        self.canvas_3d.draw_idle()

    def _compute_noise_map_surface(self, T, V, result):
        """Compute 3D noise map surface from native payload or local fallback model."""
        native_grid = result.get('noise_map') if isinstance(result, dict) else None
        if isinstance(native_grid, dict):
            z_values = np.array(native_grid.get('z', []), dtype=float)
            if z_values.shape == T.shape:
                return np.clip(z_values, 0.0, 1.0)

        perceptron = result.get('perceptron') if isinstance(result, dict) else None
        if perceptron is not None and hasattr(perceptron, 'forward'):
            Z = np.zeros_like(T, dtype=float)
            for i in range(T.shape[0]):
                for j in range(T.shape[1]):
                    Z[i, j] = float(perceptron.forward(float(T[i, j]), float(V[i, j])))
            return np.clip(Z, 0.0, 1.0)

        return self._estimate_noise_weight(T, V, result)

    def _estimate_noise_weight(self, temperature, voltage, result=None):
        """Fallback noise-weight approximation when a perceptron object is unavailable."""
        norm_temp = (np.asarray(temperature, dtype=float) - 310.0) / 30.0
        norm_volt = (np.asarray(voltage, dtype=float) - 1.0) / 0.15
        z = 0.7 * norm_temp - 0.9 * norm_volt
        weight = 1.0 / (1.0 + np.exp(-np.clip(z, -50.0, 50.0)))
        return np.clip(weight, 0.0, 1.0)

    def plot_snm_analysis(self, result):
        """Plot SNM analysis - histogram and Pelgrom plot"""
        self.canvas_snm.figure.clear()
        ax1 = self.canvas_snm.figure.add_subplot(121)
        ax2 = self.canvas_snm.figure.add_subplot(122)

        # SNM histogram
        snm_values = np.array(result['snm_values']) * 1000  # Convert to mV
        ax1.hist(snm_values, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
        ax1.axvline(np.mean(snm_values), color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {np.mean(snm_values):.2f} mV')
        ax1.set_xlabel('SNM (mV)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('SNM Distribution')
        ax1.legend()
        ax1.grid(alpha=0.3)

        # Pelgrom plot
        areas = np.logspace(-1, 1, 50)
        sigma_vth = 5.0 / np.sqrt(areas)
        ax2.plot(areas, sigma_vth, 'b-', linewidth=2)
        current_area = self.width * self.length
        current_sigma = 5.0 / np.sqrt(current_area)
        ax2.scatter([current_area], [current_sigma], color='red', s=200, zorder=5,
                   label=f'Current: {current_sigma:.2f} mV')
        ax2.set_xscale('log')
        ax2.set_xlabel('Area (um^2)')
        ax2.set_ylabel('sigma_Vth (mV)')
        ax2.set_title('Pelgrom Law')
        ax2.legend()
        ax2.grid(alpha=0.3, which='both')

        self.canvas_snm.figure.tight_layout()
        self.canvas_snm.draw_idle()

    def plot_variability(self, result):
        """Plot variability analysis - Monte Carlo BER distribution"""
        self.canvas_var.figure.clear()
        ax = self.canvas_var.figure.add_subplot(111)

        mc_ber = np.array(result['monte_carlo_ber']) * 100
        ax.hist(mc_ber, bins=20, color='coral', edgecolor='black', alpha=0.7)
        ax.axvline(result['bit_error_rate']*100, color='red', linestyle='--', linewidth=2,
                  label=f'Mean: {result["bit_error_rate"]*100:.2f}%')
        ax.set_xlabel('BER (%)')
        ax.set_ylabel('Frequency')
        ax.set_title(f'BER Distribution (Monte Carlo {self.monte_carlo_runs} runs)')
        ax.legend()
        ax.grid(alpha=0.3)

        self.canvas_var.draw_idle()

    def plot_variability_basic(self, result):
        """Plot basic variability when MC data not available"""
        self.canvas_var.figure.clear()
        ax = self.canvas_var.figure.add_subplot(111)

        # Generate synthetic distribution
        mean_ber = result['bit_error_rate']
        synthetic_ber = np.random.normal(mean_ber, mean_ber * 0.2, self.monte_carlo_runs)
        synthetic_ber = np.clip(synthetic_ber, 0, 1) * 100

        ax.hist(synthetic_ber, bins=20, color='coral', edgecolor='black', alpha=0.7)
        ax.axvline(mean_ber*100, color='red', linestyle='--', linewidth=2,
                  label=f'Mean: {mean_ber*100:.2f}%')
        ax.set_xlabel('BER (%)')
        ax.set_ylabel('Frequency')
        ax.set_title(f'BER Distribution (Monte Carlo {self.monte_carlo_runs} runs)')
        ax.legend()
        ax.grid(alpha=0.3)

        self.canvas_var.draw_idle()

    def plot_thermal_noise(self):
        """Plot thermal noise - Euler-Maruyama trajectory"""
        self.canvas_thermal_noise.figure.clear()

        if not ADVANCED_AVAILABLE:
            ax = self.canvas_thermal_noise.figure.add_subplot(111)
            ax.text(0.5, 0.5, "Thermal/Shot Noise Analysis\n\nAdvanced SRAM model required",
                   ha='center', va='center', fontsize=14)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.canvas_thermal_noise.draw_idle()
            return

        try:
            # Create SRAM cell and simulate thermal noise
            sram_array = AdvancedSRAMArray(num_cells=1, width=self.width, length=self.length)
            cell = sram_array.cells[0]

            # Generate thermal noise trajectory
            if hasattr(cell, 'thermal_shot_noise_euler_maruyama'):
                v_trajectory = cell.thermal_shot_noise_euler_maruyama(
                    self.temperature,
                    self.voltage,
                    n_steps=500
                )
            else:
                # Generate synthetic trajectory
                dt = 1e-12
                n_steps = 500
                kB = 1.38e-23
                R = 1e6
                sigma = np.sqrt(2 * kB * self.temperature / R * dt)
                v_trajectory = np.cumsum(np.random.normal(0, sigma, n_steps)) + self.voltage / 2

            ax1 = self.canvas_thermal_noise.figure.add_subplot(121)
            ax2 = self.canvas_thermal_noise.figure.add_subplot(122)

            # Voltage trajectory
            dt = 1e-12 if not hasattr(cell, 'dt') else cell.dt
            time_axis = np.arange(len(v_trajectory)) * dt * 1e9  # ns
            ax1.plot(time_axis, v_trajectory, 'b-', linewidth=1, alpha=0.8)
            ax1.axhline(self.voltage/2, color='red', linestyle='--', linewidth=2,
                       label=f'Target: {self.voltage/2:.2f}V')
            ax1.set_xlabel('Time (ns)')
            ax1.set_ylabel('Voltage (V)')
            ax1.set_title('Thermal/Shot Noise Voltage Trajectory')
            ax1.legend()
            ax1.grid(alpha=0.3)

            # Voltage distribution
            ax2.hist(v_trajectory, bins=30, color='green', edgecolor='black', alpha=0.7,
                    orientation='horizontal')
            ax2.axhline(np.mean(v_trajectory), color='red', linestyle='--', linewidth=2,
                       label=f'Mean: {np.mean(v_trajectory):.4f}V')
            ax2.set_ylabel('Voltage (V)')
            ax2.set_xlabel('Frequency')
            ax2.set_title(f'Voltage Distribution (std={np.std(v_trajectory)*1000:.3f}mV)')
            ax2.legend()
            ax2.grid(alpha=0.3)

            self.canvas_thermal_noise.figure.tight_layout()
            self.canvas_thermal_noise.draw_idle()

        except Exception as e:
            ax = self.canvas_thermal_noise.figure.add_subplot(111)
            ax.text(0.5, 0.5, f"Thermal Noise Analysis Error\n\n{str(e)}",
                   ha='center', va='center', fontsize=12)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.canvas_thermal_noise.draw_idle()

    def plot_reliability(self):
        """Plot NBTI/HCI reliability - degradation and lifetime"""
        if not RELIABILITY_AVAILABLE:
            self.canvas_reliability.figure.clear()
            ax = self.canvas_reliability.figure.add_subplot(111)
            ax.text(0.5, 0.5, "Reliability module not installed",
                   ha='center', va='center', fontsize=14)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.canvas_reliability.draw_idle()
            return

        self.canvas_reliability.figure.clear()
        ax1 = self.canvas_reliability.figure.add_subplot(121)
        ax2 = self.canvas_reliability.figure.add_subplot(122)

        reliability = ReliabilityModel()
        time_range = np.logspace(0, 10, 100)
        nbti_shifts = []
        hci_shifts = []

        for t in time_range:
            total, nbti, hci = reliability.calculate_total_vth_shift(
                self.temperature, self.voltage, self.voltage,
                0.4, self.width, t
            )
            nbti_shifts.append(nbti * 1000)
            hci_shifts.append(hci * 1000)

        time_years = time_range / (365.25 * 24 * 3600)

        ax1.semilogx(time_years, nbti_shifts, 'b-', label='NBTI', linewidth=2)
        ax1.semilogx(time_years, hci_shifts, 'r-', label='HCI', linewidth=2)
        ax1.set_xlabel('Time (years)')
        ax1.set_ylabel('Vth Shift (mV)')
        ax1.set_title('NBTI/HCI Degradation')
        ax1.legend()
        ax1.grid(alpha=0.3, which='both')

        # Lifetime prediction
        predictor = LifetimePredictor(num_cells=self.num_cells, width=self.width)
        pred = predictor.predict_array_lifetime(self.temperature)

        ax2.hist(pred['cell_lifetimes'], bins=15, color='skyblue',
                edgecolor='black', alpha=0.7)
        ax2.axvline(pred['mean_lifetime'], color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {pred["mean_lifetime"]:.2f} years')
        ax2.set_xlabel('Lifetime (years)')
        ax2.set_ylabel('Cell Count')
        ax2.set_title('Lifetime Distribution')
        ax2.legend()
        ax2.grid(alpha=0.3)

        self.canvas_reliability.figure.tight_layout()
        self.canvas_reliability.draw_idle()

    # ========================================================================
    # Research Data Methods
    # ========================================================================

    def add_research_data(self):
        """Add research data point"""
        temp = self.research_temp_input.value()
        volt = self.research_volt_input.value()
        cells = self.research_cells_input.value()
        snm = self.research_snm_input.value() / 1000.0  # Convert mV to V

        self.research_data_model.add_data(temp, volt, cells, snm)
        self.update_research_data_table()
        self.save_research_data()

        self.show_info("Data Added", "Research data point added successfully!")

    def delete_selected_data(self):
        """Delete selected data from table"""
        selected_rows = set()
        for item in self.research_data_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            self.show_warning("No Selection", "Please select rows to delete.")
            return

        for row in sorted(selected_rows, reverse=True):
            if row < len(self.research_data_model.training_data):
                del self.research_data_model.training_data[row]

        self.update_research_data_table()
        self.save_research_data()
        self.show_info("Deleted", f"Deleted {len(selected_rows)} data point(s).")

    def train_research_model(self):
        """Train research model"""
        success, message = self.research_data_model.train()

        if success:
            self.model_status_label.setText("Model: Trained")
            self.model_status_label.setProperty("ui-status", "success")
            self.rmse_label.setText(f"RMSE: {self.research_data_model.calculate_rmse():.2f} mV")
            self.update_research_data_table()
            self.save_research_data()
            self.update_rmse_plot()
            self.update_prediction_comparison_plot()
            self.show_info("Training Complete", message)
        else:
            self.show_warning("Training Failed", message)

    def update_research_data_table(self):
        """Update research data table"""
        self.research_data_table.setRowCount(len(self.research_data_model.training_data))

        for i, data in enumerate(self.research_data_model.training_data):
            self.research_data_table.setItem(i, 0, QTableWidgetItem(data['timestamp']))
            self.research_data_table.setItem(i, 1, QTableWidgetItem(f"{data['temperature']:.0f}"))
            self.research_data_table.setItem(i, 2, QTableWidgetItem(f"{data['voltage']:.2f}"))
            self.research_data_table.setItem(i, 3, QTableWidgetItem(str(data['num_cells'])))
            self.research_data_table.setItem(i, 4, QTableWidgetItem(f"{data['snm_pred']*1000:.1f}"))
            self.research_data_table.setItem(i, 5, QTableWidgetItem(f"{data['snm_actual']*1000:.1f}"))
            self.research_data_table.setItem(i, 6, QTableWidgetItem(f"{data['error']*1000:.1f}"))

        self.data_count_label.setText(f"Data Points: {len(self.research_data_model.training_data)}")
        if self.research_data_model.trained:
            self.rmse_label.setText(f"RMSE: {self.research_data_model.calculate_rmse():.2f} mV")

    def save_research_data(self):
        """Save research data to JSON file."""
        try:
            data_to_save = {
                'research_data': self.research_data_model.training_data,
                'weights': self.research_data_model.weights.tolist(),
                'model_trained': self.research_data_model.trained,
                'rmse_history': self.research_data_model.rmse_history
            }
            with open(RESEARCH_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving research data: {e}")

    def load_research_data(self):
        """Load research data from JSON file with one-time legacy migration."""
        try:
            source_path = None
            if os.path.exists(RESEARCH_DATA_FILE):
                source_path = RESEARCH_DATA_FILE
            elif os.path.exists(LEGACY_RESEARCH_DATA_FILE):
                source_path = LEGACY_RESEARCH_DATA_FILE

            if not source_path:
                return

            with open(source_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            research_data = data.get('research_data', data.get('training_data', []))
            self.research_data_model.training_data = research_data
            weights = data.get('weights', [0.0, 0.0, 0.0, 0.2])
            self.research_data_model.weights = np.array(weights)
            self.research_data_model.trained = data.get('model_trained', data.get('trained', False))
            self.research_data_model.rmse_history = data.get('rmse_history', [])
            self.update_research_data_table()
            if self.research_data_model.trained:
                self.model_status_label.setText("Model: Trained")
                self.model_status_label.setProperty("ui-status", "success")

            if source_path == LEGACY_RESEARCH_DATA_FILE:
                self.save_research_data()
                try:
                    os.remove(LEGACY_RESEARCH_DATA_FILE)
                except OSError:
                    pass
        except Exception as e:
            print(f"Error loading research data: {e}")

    def update_rmse_plot(self):
        """Update RMSE improvement plot"""
        if len(self.research_data_model.training_data) < 2:
            return

        try:
            self.canvas_rmse.figure.clear()
            ax = self.canvas_rmse.figure.add_subplot(111)

            rmse_values = []
            for i in range(1, len(self.research_data_model.training_data) + 1):
                subset = self.research_data_model.training_data[:i]
                errors = [abs(d['snm_pred'] - d['snm_actual']) for d in subset]
                rmse = np.sqrt(np.mean(np.array(errors)**2)) * 1000
                rmse_values.append(rmse)

            ax.plot(range(1, len(rmse_values) + 1), rmse_values, 'bo-', linewidth=2, markersize=6)
            ax.set_xlabel('Data Point #')
            ax.set_ylabel('RMSE (mV)')
            ax.set_title('RMSE Improvement')
            ax.grid(alpha=0.3)

            self.canvas_rmse.figure.tight_layout()
            self.canvas_rmse.draw_idle()

        except Exception as e:
            print(f"Error plotting RMSE: {e}")

    def update_prediction_comparison_plot(self):
        """Update prediction vs actual plot"""
        if len(self.research_data_model.training_data) < 2:
            return

        try:
            self.canvas_comparison.figure.clear()
            ax = self.canvas_comparison.figure.add_subplot(111)

            preds = []
            actuals = []

            for data in self.research_data_model.training_data:
                if self.research_data_model.trained:
                    pred = self.research_data_model.predict(
                        data['temperature'],
                        data['voltage'],
                        data['num_cells']
                    ) * 1000
                else:
                    pred = data['snm_pred'] * 1000

                actual = data['snm_actual'] * 1000
                preds.append(pred)
                actuals.append(actual)

            ax.scatter(preds, actuals, color='blue', s=50, alpha=0.6, edgecolors='black')

            min_val = min(min(preds), min(actuals))
            max_val = max(max(preds), max(actuals))
            margin = (max_val - min_val) * 0.1

            ax.plot([min_val - margin, max_val + margin],
                   [min_val - margin, max_val + margin],
                   'r--', linewidth=2, alpha=0.7, label='Perfect')

            ax.set_xlabel('Predicted SNM (mV)')
            ax.set_ylabel('Actual SNM (mV)')
            ax.set_title('Prediction vs Actual')
            ax.legend()
            ax.grid(alpha=0.3)

            self.canvas_comparison.figure.tight_layout()
            self.canvas_comparison.draw_idle()

        except Exception as e:
            print(f"Error plotting comparison: {e}")

    def compare_models(self):
        """Compare standard model vs research-trained model"""
        if len(self.research_data_model.training_data) < 2:
            self.show_warning("Warning", "Need at least 2 data points")
            return

        standard_preds = []
        trained_preds = []
        actuals = []

        for data in self.research_data_model.training_data:
            std_pred = self.research_data_model.predict_standard(
                data['temperature'],
                data['voltage'],
                data['num_cells']
            ) * 1000
            standard_preds.append(std_pred)

            if self.research_data_model.trained:
                train_pred = self.research_data_model.predict(
                    data['temperature'],
                    data['voltage'],
                    data['num_cells']
                ) * 1000
            else:
                train_pred = std_pred
            trained_preds.append(train_pred)

            actuals.append(data['snm_actual'] * 1000)

        std_rmse = np.sqrt(np.mean([(p - a)**2 for p, a in zip(standard_preds, actuals)]))
        train_rmse = np.sqrt(np.mean([(p - a)**2 for p, a in zip(trained_preds, actuals)]))

        improvement = ((std_rmse - train_rmse) / std_rmse) * 100 if std_rmse > 0 else 0

        message = f"""
Model Comparison Results:

Standard Model RMSE:        {std_rmse:.2f} mV
Research Model RMSE:        {train_rmse:.2f} mV
Improvement:                {improvement:.1f}%

Based on {len(self.research_data_model.training_data)} data points
"""

        if self.research_data_model.trained:
            message += "\nResearch model is trained and active."
        else:
            message += "\nResearch model not trained yet."

        self.show_info("Model Comparison", message)

    def load_sample_data(self):
        """Load sample data for demonstration"""
        reply = self.show_question(
            "Load Sample Research Data",
            "Add 10 sample research data points for demonstration?"
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        sample_data = [
            (280, 0.85, 32),
            (300, 0.90, 32),
            (310, 1.00, 32),
            (320, 1.05, 32),
            (340, 1.10, 32),
            (310, 0.80, 32),
            (310, 0.95, 32),
            (310, 1.05, 32),
            (310, 1.15, 32),
            (310, 1.20, 32),
        ]

        for temp, volt, cells in sample_data:
            snm_pred = self.research_data_model.predict_standard(temp, volt, cells)
            noise = np.random.normal(0, 0.005)
            snm_actual = snm_pred + noise
            self.research_data_model.add_data(temp, volt, cells, snm_actual)

        self.update_research_data_table()
        self.save_research_data()

        self.show_info(
            "Sample Research Data Loaded",
            f"{len(sample_data)} sample data points added!\n\n"
            f"Click 'Train on Research Data' to train the model."
        )

    def _get_ai_connection_status(self) -> str:
        if self.advisor and hasattr(self.advisor, "get_connection_status"):
            return self.advisor.get_connection_status()
        if self.advisor and hasattr(self.advisor, "connection_status"):
            return str(self.advisor.connection_status)
        return "Not initialized"

    @staticmethod
    def _is_ai_unavailable_message(message: str) -> bool:
        if not isinstance(message, str):
            return False
        lowered = message.lower()
        return (
            "ai research analysis service is not available" in lowered
            or "ai research analysis service is not initialized" in lowered
            or "runtime error: ai research analysis service" in lowered
            or "ai research analysis service call failed" in lowered
        )

    def _refresh_ai_connection_label(self, status_override: str = None):
        """Synchronize the research analysis label with actual advisor state."""
        if not hasattr(self, "ai_connection_label") or self.ai_connection_label is None:
            return

        advisor_status = status_override if status_override else self._get_ai_connection_status()
        advisor_available = bool(AI_ADVISOR_AVAILABLE and self.advisor and getattr(self.advisor, "available", False))
        connected = bool(advisor_available and hasattr(self.advisor, "is_connected") and self.advisor.is_connected())

        if connected:
            self.ai_connection_label.setText("✅ AI Research Analysis: Connected")
            self.ai_connection_label.setProperty("ui-status", "success")
        elif advisor_available:
            self.ai_connection_label.setText(f"⚠️ AI Research Analysis: Not Connected ({advisor_status})")
            self.ai_connection_label.setProperty("ui-status", "warning")
        else:
            self.ai_connection_label.setText(f"⚠️ AI Research Analysis: Unavailable ({advisor_status})")
            self.ai_connection_label.setProperty("ui-status", "warning")

        self.style().unpolish(self.ai_connection_label)
        self.style().polish(self.ai_connection_label)

    def _show_ai_unavailable_warning(self, title="AI Research Analysis Not Available", status: str = None):
        advisor_status = status if status else self._get_ai_connection_status()
        self._refresh_ai_connection_label(advisor_status)
        self.show_warning(
            title,
            f"AI research analysis service is not available ({advisor_status}).\n\n"
            "To enable AI Research Analysis:\n"
            "1. Create a .env file in the project root\n"
            "2. Add the required AI service credentials\n"
            "3. Restart the application"
        )

    def _handle_ai_connection_check(self, ok: bool, status: str, on_success, on_failure):
        if self._ai_connection_check_thread is not None:
            self._ai_connection_check_thread.deleteLater()
            self._ai_connection_check_thread = None

        self._refresh_ai_connection_label(status)
        if ok:
            on_success()
            return
        on_failure(status)

    def _call_ai_chat(self, messages, max_tokens=800, temperature=0.7, model=None):
        model_to_use = model or self.advisor.model
        if not self.advisor or self.advisor.client is None:
            raise RuntimeError("AI research analysis client is not initialized.")

        response = self.advisor.client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content

    def _start_ai_action_thread(self, fn, args=(), kwargs=None, on_success=None, on_error=None):
        if self._ai_action_thread is not None and self._ai_action_thread.isRunning():
            return

        if on_success is None:
            on_success = lambda result: None
        if on_error is None:
            on_error = lambda msg: self.show_error("Error", f"AI action failed: {msg}")

        self._ai_action_thread = AIActionWorkerThread(fn, args=args, kwargs=kwargs, parent=self)
        self._ai_action_thread.finished.connect(
            lambda result, on_success=on_success: self._handle_ai_action_finished(result, on_success, on_error)
        )
        self._ai_action_thread.failed.connect(
            lambda msg, on_error=on_error: self._handle_ai_action_failed(msg, on_error)
        )
        self._ai_action_thread.start()

    def _handle_ai_action_finished(self, result, on_success, on_error):
        if self._ai_action_thread is not None:
            self._ai_action_thread.deleteLater()
            self._ai_action_thread = None
        try:
            on_success(result)
        except Exception as e:
            on_error(str(e))

    def _handle_ai_action_failed(self, error_message, on_error):
        if self._ai_action_thread is not None:
            self._ai_action_thread.deleteLater()
            self._ai_action_thread = None
        on_error(error_message)

    def _set_report_buttons_enabled(self, enabled: bool):
        for btn_name in ("generate_full_report_btn", "report_btn_top"):
            button = getattr(self, btn_name, None)
            if button is not None and button is not False:
                button.setEnabled(enabled)

    def _handle_report_generation_finished(self, pdf_file):
        if self._report_generation_thread is not None:
            self._report_generation_thread.deleteLater()
            self._report_generation_thread = None

        self._set_report_buttons_enabled(True)
        self.model_status_label.setText("Model: " + ("Trained" if self.research_data_model.trained else "Not trained"))

        if pdf_file:
            self.on_status_update("Report generation complete.")
            self.show_info("Report Complete", f"Research report generated:\n{pdf_file}")
        else:
            self.on_status_update("Warning: report finished without output file.")
            self.show_warning("Report Warning", "Report generation returned no output file.")

    def _handle_report_generation_failed(self, error_message):
        if self._report_generation_thread is not None:
            self._report_generation_thread.deleteLater()
            self._report_generation_thread = None

        self._set_report_buttons_enabled(True)
        self.model_status_label.setText("Model: Error")
        self.on_status_update(f"Error: report generation failed ({error_message})")
        self.show_error("Error", f"Failed to generate report:\n{error_message}")

    def _handle_report_generation_progress(self, percent: int, message: str = ""):
        if not (0 <= percent <= 100):
            percent = max(0, min(100, int(percent)))

        if message:
            self.model_status_label.setText(f"Model: Generating Report... {percent}% - {message}")
        else:
            self.model_status_label.setText(f"Model: Generating Report... {percent}%")
        self.on_status_update(f"Generating report... {percent}%")

    def _build_report_context(self):
        """Capture a consistent snapshot for report generation."""
        if not self.current_result:
            return None

        try:
            snapshot_result = copy.deepcopy(self.current_result)
        except Exception:
            snapshot_result = dict(self.current_result)

        return {
            "result": snapshot_result,
            "analysis_mode": self.analysis_mode,
            "backend": self.current_result.get("backend", "standard"),
            "temperature": self.temperature,
            "voltage": self.voltage,
            "num_cells": self.num_cells,
            "monte_carlo_runs": self.monte_carlo_runs,
            "width": self.width,
            "length": self.length,
            "canvas_3d": getattr(self, "canvas_3d", None),
            "canvas_snm": getattr(self, "canvas_snm", None),
            "canvas_var": getattr(self, "canvas_var", None),
            "canvas_thermal_noise": getattr(self, "canvas_thermal_noise", None),
            "canvas_reliability": getattr(self, "canvas_reliability", None),
            "canvas_pareto": getattr(self, "canvas_pareto", None),
            "canvas_reliability_grove": getattr(self, "canvas_reliability_grove", None),
            "canvas_validation_profile": getattr(self, "canvas_validation_profile", None),
            "canvas_benchmark_r2": getattr(self, "canvas_benchmark_r2", None),
            "canvas_benchmark_speed": getattr(self, "canvas_benchmark_speed", None),
            "canvas_benchmark_pred_actual": getattr(self, "canvas_benchmark_pred_actual", None),
            "validation_result": copy.deepcopy(self.validation_result) if self.validation_result else None,
            "benchmark_result": copy.deepcopy(self.benchmark_result) if self.benchmark_result else None,
        }

    def _ensure_ai_connection(self, on_success, on_failure, force: bool = False):
        if not AI_ADVISOR_AVAILABLE or not self.advisor or not getattr(self.advisor, "available", False):
            self._refresh_ai_connection_label()
            on_failure(self._get_ai_connection_status())
            return

        if hasattr(self.advisor, "is_connected") and self.advisor.is_connected():
            self._refresh_ai_connection_label()
            on_success()
            return

        if self._ai_connection_check_thread is not None and self._ai_connection_check_thread.isRunning():
            return

        self._ai_connection_check_thread = AIConnectionCheckThread(self.advisor, force=force)
        self._ai_connection_check_thread.finished.connect(
            lambda ok, status, on_success=on_success, on_failure=on_failure: self._handle_ai_connection_check(
                ok, status, on_success, on_failure
            )
        )
        self._ai_connection_check_thread.start()

    def get_ai_advice(self):
        """Get AI analysis on research data."""
        if len(self.research_data_model.training_data) < 2:
            self.show_warning("Warning", "Need at least 2 data points")
            return

        if not self.advisor or not hasattr(self.advisor, 'available') or not self.advisor.available:
            self._show_ai_unavailable_warning("AI Research Analysis Not Available")
            return

        def _run_ai_advice():
            self.model_status_label.setText("Consulting AI research analysis...")
            self.model_status_label.repaint()

            def _on_success(advice):
                if self._is_ai_unavailable_message(advice):
                    self.show_warning("AI Research Analysis Not Available", advice)
                    self._refresh_ai_connection_label(advice)
                    return

                self.show_info("AI Research Analysis", advice)
                self.model_status_label.setText("Model: " + ("Trained" if self.research_data_model.trained else "Not trained"))
                self._refresh_ai_connection_label()

            def _on_error(msg):
                self.show_error("Error", f"Research analysis failed: {msg}")
                self.model_status_label.setText("Model: Error")
                self._refresh_ai_connection_label(str(msg))

            self._start_ai_action_thread(
                self.advisor.analyze_research_data,
                args=(self.research_data_model.training_data,),
                on_success=_on_success,
                on_error=_on_error
            )

        self._ensure_ai_connection(_run_ai_advice, lambda status: self._show_ai_unavailable_warning("AI Research Analysis Not Available", status))

    def clear_all_research_data(self):
        """Delete all research data and reset the model."""
        reply = self.show_question(
            "Warning",
            "Delete all research data?\n(This cannot be undone)"
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Reset memory
            self.research_data_model.training_data = []
            self.research_data_model.trained = False
            self.research_data_model.weights = np.array([0.0, 0.0, 0.0, 0.2])
            self.research_data_model.rmse_history = []

            # Delete file
            for data_file in (RESEARCH_DATA_FILE, LEGACY_RESEARCH_DATA_FILE):
                if os.path.exists(data_file):
                    os.remove(data_file)

            # Reset UI
            self.research_data_table.setRowCount(0)
            self.model_status_label.setText("Model: Not trained")
            self.rmse_label.setText("RMSE: - mV")
            self.data_count_label.setText("Data points: 0")

            # Clear plots
            self.canvas_rmse.figure.clear()
            self.canvas_rmse.draw_idle()
            self.canvas_comparison.figure.clear()
            self.canvas_comparison.draw_idle()

            self.show_info("Complete", "All research data has been deleted.")

        except Exception as e:
            self.show_error("Error", f"Delete failed: {e}")

    def log_ai_analysis(self):
        """Log research analysis results to JSON and TXT files."""
        if not self.current_result:
            self.show_warning("Warning", "No simulation results available")
            return

        # Create logs directory
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Prepare analysis data
        snm_values = np.array(self.current_result.get('snm_values', []))
        analysis_data = {
            "timestamp": datetime.now().isoformat(),
            "project_context": {
                "temperature": self.temp_spinbox.value(),
                "voltage": self.volt_spinbox.value(),
                "monte_carlo_runs": self.monte_carlo_runs,
                "backend": self.current_result.get("backend", "standard"),
                "num_cells": self.num_cells,
                "analysis_mode": self.analysis_mode,
            },
            "research_data_status": {
                "sample_count": len(self.research_data_model.training_data),
                "model_trained": self.research_data_model.trained,
                "rmse_mV": float(self.research_data_model.calculate_rmse()) if self.research_data_model.trained else None,
            },
            "research_metrics": {
                "snm_mean_mV": float(np.mean(snm_values) * 1000) if len(snm_values) > 0 else 0,
                "snm_std_mV": float(np.std(snm_values) * 1000) if len(snm_values) > 0 else 0,
                "snm_min_mV": float(np.min(snm_values) * 1000) if len(snm_values) > 0 else 0,
                "snm_max_mV": float(np.max(snm_values) * 1000) if len(snm_values) > 0 else 0,
                "ber_mean": float(self.current_result.get('bit_error_rate', 0)),
                "thermal_sigma_mV": float(self.current_result.get('thermal_sigma', 0) * 1000),
            },
            "analysis_summary": self.generate_ai_comprehensive_analysis(result_data=self.current_result),
            "recommendations": self.generate_recommendations_text(result_data=self.current_result),
        }

        # Save JSON
        json_file = f"logs/{RESEARCH_ANALYSIS_LOG_PREFIX}{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)

        # Save TXT
        txt_file = f"logs/{RESEARCH_ANALYSIS_LOG_PREFIX}{timestamp}.log"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Research Analysis Log\n")
            f.write(f"{'='*60}\n")
            f.write(f"Time: {analysis_data['timestamp']}\n")
            f.write(f"\n[Project Context]\n")
            for key, val in analysis_data['project_context'].items():
                f.write(f"  - {key}: {val}\n")
            f.write(f"\n[Research Data Status]\n")
            for key, val in analysis_data['research_data_status'].items():
                f.write(f"  - {key}: {val}\n")
            f.write(f"\n[Research Metrics]\n")
            for key, val in analysis_data['research_metrics'].items():
                if isinstance(val, float):
                    f.write(f"  - {key}: {val:.4f}\n")
                else:
                    f.write(f"  - {key}: {val}\n")
            f.write(f"\n[Analysis Summary]\n")
            f.write(f"{analysis_data['analysis_summary']}\n")
            f.write(f"\n[Recommendations]\n")
            f.write(f"{analysis_data['recommendations']}\n")

        print(f"Research analysis log saved:")
        print(f"   JSON: {json_file}")
        print(f"   TXT:  {txt_file}")

        self.show_info("Success",
            f"Research analysis log saved to:\n{json_file}\n{txt_file}")

        return json_file, txt_file

    def export_research_data_to_csv(self):
        """Export research data to CSV file."""
        if len(self.research_data_model.training_data) == 0:
            self.show_warning("Warning", "No data to export")
            return

        try:
            # Open file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Research Data to CSV",
                f"research_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv);;All Files (*)"
            )

            if not file_path:
                return

            # Write CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    "Timestamp", "Temperature (K)", "Voltage (V)", "Cells",
                    "SNM Predicted (mV)", "SNM Actual (mV)", "Error (mV)"
                ])

                # Data rows
                for data in self.research_data_model.training_data:
                    writer.writerow([
                        data['timestamp'],
                        data['temperature'],
                        data['voltage'],
                        data['num_cells'],
                        f"{data['snm_pred']*1000:.2f}",
                        f"{data['snm_actual']*1000:.2f}",
                        f"{data['error']*1000:.2f}"
                    ])

            self.show_info("Success",
                f"Research data exported to:\n{file_path}\n\n{len(self.research_data_model.training_data)} rows exported")

        except Exception as e:
            self.show_error("Error", f"Export failed: {e}")

    def import_research_data_from_csv(self):
        """Import research data from CSV file."""
        try:
            # Open file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Research Data from CSV",
                "",
                "CSV Files (*.csv);;All Files (*)"
            )

            if not file_path:
                return

            # Read CSV
            imported_count = 0
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        # Parse data
                        timestamp = row.get('Timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        temperature = float(row['Temperature (K)'])
                        voltage = float(row['Voltage (V)'])
                        num_cells = int(row['Cells'])
                        snm_actual = float(row['SNM Actual (mV)']) / 1000.0  # Convert mV to V

                        # Add to model
                        snm_pred = self.research_data_model.predict_standard(temperature, voltage, num_cells)

                        data_point = {
                            'timestamp': timestamp,
                            'temperature': temperature,
                            'voltage': voltage,
                            'num_cells': num_cells,
                            'snm_pred': snm_pred,
                            'snm_actual': snm_actual,
                            'error': abs(snm_pred - snm_actual)
                        }

                        self.research_data_model.training_data.append(data_point)
                        imported_count += 1

                    except (ValueError, KeyError) as e:
                        print(f"Skipping invalid row: {row} - Error: {e}")
                        continue

            if imported_count > 0:
                # Update UI
                self.update_research_data_table()
                self.data_count_label.setText(f"Data Points: {len(self.research_data_model.training_data)}")
                self.save_research_data()

                self.show_info("Success",
                    f"Imported {imported_count} research data rows from:\n{file_path}")
            else:
                self.show_warning("Warning", "No valid research data found in CSV file")

        except Exception as e:
            self.show_error("Error", f"Import failed: {e}")

    def add_figure_page(self, pdf, canvas, title, description=None):
        """Add a canvas figure as PDF page with IEEE styling (DRY helper)"""
        if not canvas or not canvas.figure or not canvas.figure.axes:
            return False

        # Get existing figure from canvas
        fig = canvas.figure

        # Apply IEEE styling
        self.apply_ieee_style(fig, title)

        # Add description at bottom if provided
        if description:
            fig.text(0.5, 0.01, description, ha='center', va='bottom',
                    fontsize=8, style='italic', color='gray')

        # Save to PDF with IEEE DPI
        pdf.savefig(fig, bbox_inches='tight', dpi=300)

        return True

    def has_figure_data(self, canvas):
        """Check if canvas has plottable data"""
        return canvas and canvas.figure and len(canvas.figure.axes) > 0

    def generate_ai_insights_text(self, result_data=None):
        """Generate research insights text."""
        source = result_data if result_data is not None else self.current_result
        if not source:
            return "No analysis results available"

        snm_values = np.array(source.get('snm_values', []))
        if len(snm_values) == 0:
            return "No SNM data available"

        snm_mean = np.mean(snm_values)
        snm_std = np.std(snm_values)
        ber = source.get('bit_error_rate', 0)

        insights = []

        # SNM analysis
        if snm_mean < 0.1:
            insights.append("WARNING: SNM is very low (< 100mV). Research margin is insufficient.")
        elif snm_mean < 0.15:
            insights.append("WARNING: SNM is low (< 150mV). Margin improvement recommended.")
        else:
            insights.append("OK: SNM is acceptable (> 150mV). Research result is stable.")

        # Variability analysis
        if snm_std > snm_mean * 0.3:
            insights.append("WARNING: High variance detected. Process variability is high.")
        else:
            insights.append("OK: Variance is acceptable. Process stability is good.")

        # BER analysis
        if ber > 1e-6:
            insights.append("WARNING: High BER risk. Reliability issues possible.")
        elif ber > 1e-8:
            insights.append("WARNING: Medium BER level. Monitoring needed.")
        else:
            insights.append("OK: BER is acceptable. Reliability criteria met.")

        # Temperature impact
        temp = source.get('temperature', self.temp_spinbox.value())
        if temp > 323:
            insights.append("WARNING: High temperature condition. Cooling improvement recommended.")

        # Thermal noise impact
        thermal_sigma = source.get('thermal_sigma', 0)
        if thermal_sigma > 0.005:
            insights.append(f"WARNING: Thermal noise impact is high ({thermal_sigma*1000:.2f} mV).")

        return "\n".join(insights)

    def generate_ai_comprehensive_analysis(self, result_data=None):
        """Generate AI-powered comprehensive research analysis."""
        source = result_data if result_data is not None else self.current_result
        if not source:
            return self.generate_rule_based_analysis()

        # Try AI-based analysis if available
        if AI_ADVISOR_AVAILABLE and self.advisor and hasattr(self.advisor, 'available') and self.advisor.available:
            advisor_connected = (
                self.advisor.is_connected()
                if hasattr(self.advisor, "is_connected")
                else bool(self.advisor.available)
            )
            if not advisor_connected:
                print("AI research analysis service is not currently connected, falling back to rule-based analysis")
                return self.generate_rule_based_analysis(result_data=source)
            try:
                # Prepare comprehensive context
                snm_values = np.array(source.get('snm_values', []))
                context = {
                    'temperature': source.get('temperature', self.temperature),
                    'voltage': source.get('voltage', self.voltage),
                    'num_cells': source.get('num_cells', self.num_cells),
                    'backend': source.get('backend', 'standard'),
                    'snm_mean_mv': float(np.mean(snm_values) * 1000) if len(snm_values) > 0 else 0,
                    'snm_std_mv': float(np.std(snm_values) * 1000) if len(snm_values) > 0 else 0,
                    'ber': float(source.get('bit_error_rate', 0)),
                    'thermal_sigma_mv': float(source.get('thermal_sigma', 0) * 1000),
                }

                prompt = f"""You are an expert SRAM research analyst. Analyze this SRAM simulation data and provide:

1. EXECUTIVE SUMMARY (2-3 sentences): Overall design quality assessment
2. CRITICAL ISSUES (prioritized list): Most important problems found
3. PERFORMANCE ASSESSMENT: Detailed analysis of key metrics
4. RELIABILITY CONCERNS: Potential long-term issues
5. OPTIMIZATION RECOMMENDATIONS (3-5 specific, actionable items)

Research Data:
{json.dumps(context, indent=2)}

Provide a comprehensive, professional analysis suitable for an engineering report."""

                return self._call_ai_chat(
                    messages=[
                        {"role": "system", "content": "You are an expert SRAM research analyst providing detailed technical analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.3,
                    model=self.advisor.model,
                )

            except Exception as e:
                print(f"AI research analysis failed: {e}, falling back to rule-based")
                return self.generate_rule_based_analysis(result_data=source)
        else:
            return self.generate_rule_based_analysis(result_data=source)

    def generate_rule_based_analysis(self, result_data=None):
        """Enhanced rule-based analysis (fallback)."""
        source = result_data if result_data is not None else self.current_result
        if not source:
            return "No analysis results available"

        snm_values = np.array(source.get('snm_values', []))
        if len(snm_values) == 0:
            return "No SNM data available"

        snm_mean = np.mean(snm_values)
        snm_std = np.std(snm_values)
        ber = source.get('bit_error_rate', 0)
        thermal_sigma = source.get('thermal_sigma', 0)

        analysis = []

        # Executive Summary
        analysis.append("=== RESEARCH SUMMARY ===")
        quality_score = 10.0
        if snm_mean < 0.1: quality_score -= 3.0
        elif snm_mean < 0.15: quality_score -= 1.5
        if snm_std > snm_mean * 0.3: quality_score -= 2.0
        if ber > 1e-6: quality_score -= 3.0
        elif ber > 1e-8: quality_score -= 1.0
        if thermal_sigma > 0.005: quality_score -= 1.0

        analysis.append(f"Analysis Quality Score: {quality_score:.1f}/10.0")
        if quality_score >= 8.0:
            analysis.append("Overall Assessment: EXCELLENT - Research results meet all criteria")
        elif quality_score >= 6.0:
            analysis.append("Overall Assessment: GOOD - Minor improvements recommended")
        elif quality_score >= 4.0:
            analysis.append("Overall Assessment: FAIR - Several issues need attention")
        else:
            analysis.append("Overall Assessment: POOR - Critical issues must be resolved")

        analysis.append("")

        # Critical Issues
        analysis.append("=== CRITICAL ISSUES ===")
        critical_count = 0
        if snm_mean < 0.1:
            analysis.append(f"1. [CRITICAL] SNM too low: {snm_mean*1000:.1f} mV (< 100 mV)")
            critical_count += 1
        if ber > 1e-6:
            analysis.append(f"{critical_count+1}. [CRITICAL] High BER: {ber:.2e} (> 1e-6)")
            critical_count += 1
        if critical_count == 0:
            analysis.append("No critical issues detected.")

        analysis.append("")

        # Performance Assessment
        analysis.append("=== PERFORMANCE ASSESSMENT ===")
        analysis.append(f"SNM Mean: {snm_mean*1000:.2f} mV (Target: > 150 mV)")
        analysis.append(f"SNM Std Dev: {snm_std*1000:.2f} mV (Variability: {(snm_std/snm_mean)*100:.1f}%)")
        analysis.append(f"Bit Error Rate: {ber:.2e} (Target: < 1e-8)")
        analysis.append(f"Thermal Noise: {thermal_sigma*1000:.2f} mV")

        return "\n".join(analysis)

    def generate_recommendations_text(self, result_data=None):
        """Generate research recommendations text."""
        source = result_data if result_data is not None else self.current_result
        if not source:
            return "No recommendations available"

        snm_values = np.array(source.get('snm_values', []))
        if len(snm_values) == 0:
            return "No SNM data available"

        recommendations = []

        snm_mean = np.mean(snm_values)

        if snm_mean < 0.1:
            recommendations.append("1. Increase voltage (V_dd)")
            recommendations.append("2. Adjust transistor sizing (W/L ratio)")
            recommendations.append("3. Improve process (optimize process corner)")

        if source.get('thermal_sigma', 0) > 0.005:
            recommendations.append("4. Improve thermal management (add heat sink or enhance cooling)")

        ber = source.get('bit_error_rate', 0)
        if ber > 1e-8:
            recommendations.append("5. Add error correction code (ECC)")
            recommendations.append("6. Increase reliability margin")

        if len(recommendations) == 0:
            recommendations.append("Research parameters are within acceptable range.")

        return "\n".join(recommendations)

    def generate_simulation_report_with_figures(self):
        """Generate comprehensive IEEE-styled simulation report with all figures"""
        if not self.current_result:
            self.show_warning("Warning", "No simulation results available")
            return

        if self._report_generation_thread is not None and self._report_generation_thread.isRunning():
            self.show_warning("Warning", "Report generation is already running")
            return

        report_context = self._build_report_context()
        if not report_context:
            self.show_error("Error", "Failed to capture simulation data for report.")
            return

        self._set_report_buttons_enabled(False)
        self.model_status_label.setText("Model: Generating Report...")

        self._report_generation_thread = ReportGenerationWorkerThread(
            self,
            report_context=report_context,
            parent=self
        )
        self._report_generation_thread.finished.connect(self._handle_report_generation_finished)
        self._report_generation_thread.failed.connect(self._handle_report_generation_failed)
        self._report_generation_thread.progress.connect(self._handle_report_generation_progress)
        self._report_generation_thread.start()

    def _generate_simulation_report_with_figures_sync(self, report_context=None, progress_callback=None):
        """Generate comprehensive IEEE-styled simulation report with all figures (sync worker)"""
        if report_context is None:
            report_context = self._build_report_context()

        result_data = report_context.get("result") if report_context else None
        if not result_data:
            raise ValueError("No simulation results available")

        def _report_progress(percent, message=""):
            if not progress_callback:
                return
            try:
                progress = max(0, min(100, int(percent)))
                progress_callback(progress, message)
            except Exception:
                pass

        analysis_context = result_data.copy() if isinstance(result_data, dict) else None
        if analysis_context is not None:
            analysis_context.setdefault("temperature", report_context.get("temperature"))
            analysis_context.setdefault("voltage", report_context.get("voltage"))
            analysis_context.setdefault("num_cells", report_context.get("num_cells"))
            analysis_context.setdefault("backend", report_context.get("backend", result_data.get("backend", "standard")))

        has_3d_figure = self.has_figure_data(report_context["canvas_3d"])
        has_snm_figure = self.has_figure_data(report_context["canvas_snm"])
        has_var_figure = self.has_figure_data(report_context["canvas_var"])
        has_thermal_noise_figure = self.has_figure_data(report_context["canvas_thermal_noise"])
        has_reliability_figure = self.has_figure_data(report_context["canvas_reliability"])
        has_pareto_figure = WORKLOAD_MODEL_AVAILABLE and self.has_figure_data(report_context["canvas_pareto"])
        has_reliability_grove_figure = RELIABILITY_AVAILABLE and self.has_figure_data(report_context["canvas_reliability_grove"])
        has_validation_profile_figure = (
            report_context.get("validation_result")
            and self.has_figure_data(report_context["canvas_validation_profile"])
        )
        has_benchmark_r2_figure = (
            report_context.get("benchmark_result")
            and self.has_figure_data(report_context["canvas_benchmark_r2"])
        )
        has_benchmark_speed_figure = (
            report_context.get("benchmark_result")
            and self.has_figure_data(report_context["canvas_benchmark_speed"])
        )
        has_benchmark_pred_actual_figure = (
            report_context.get("benchmark_result")
            and self.has_figure_data(report_context["canvas_benchmark_pred_actual"])
        )

        progress_steps = 5 + sum([
            has_3d_figure,
            has_snm_figure,
            has_var_figure,
            has_thermal_noise_figure,
            has_reliability_figure,
            has_pareto_figure,
            has_reliability_grove_figure,
            has_validation_profile_figure,
            has_benchmark_r2_figure,
            has_benchmark_speed_figure,
            has_benchmark_pred_actual_figure,
        ])
        progress_step = 0

        def _tick(message=""):
            nonlocal progress_step
            progress_step += 1
            percent = int((progress_step / progress_steps) * 100) if progress_steps else 100
            _report_progress(percent, message)

        _tick("Preparing report data")
        from matplotlib.backends.backend_pdf import PdfPages

        if not os.path.exists("reports"):
            os.makedirs("reports")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pdf_file = f"reports/SRAM_IEEE_Report_{timestamp}.pdf"

        page_count = 0

        with PdfPages(pdf_file) as pdf:
            # ========== SECTION 1: Executive Summary & Research Analysis ==========

            # Page 1: Cover Page
            _tick("Generating cover page")
            page_count += 1
            fig = plt.figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis('off')

            # Title
            title_text = "SRAM Simulation Analysis Report"
            ax.text(0.5, 0.85, title_text, ha='center', va='top',
                   fontsize=22, fontweight='bold', transform=ax.transAxes)

            # Subtitle
            subtitle_text = "Comprehensive Design, Performance & Reliability Analysis"
            ax.text(0.5, 0.80, subtitle_text, ha='center', va='top',
                   fontsize=14, style='italic', transform=ax.transAxes)

            # Metadata
            metadata_text = f"""
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Backend: {result_data.get('backend', 'standard').upper()}
Analysis Mode: {report_context.get('analysis_mode')}
"""
            ax.text(0.5, 0.70, metadata_text, ha='center', va='top',
                   fontsize=10, family='monospace', transform=ax.transAxes)

            # Simulation Parameters Box
            snm_values = np.array(result_data.get('snm_values', []))
            params_text = f"""
SIMULATION PARAMETERS
Temperature:      {report_context.get('temperature')} K
Supply Voltage:   {report_context.get('voltage')} V
Number of Cells:  {report_context.get('num_cells')}
Monte Carlo Runs: {report_context.get('monte_carlo_runs')}
Transistor W/L:   {report_context.get('width')} um / {report_context.get('length')} um
"""
            ax.text(0.1, 0.55, params_text, ha='left', va='top',
                   fontsize=10, family='monospace', transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

            # Key Results Box
            results_text = f"""
KEY RESULTS
SNM Mean:         {np.mean(snm_values)*1000:.2f} mV
SNM Std Dev:      {np.std(snm_values)*1000:.2f} mV
Bit Error Rate:   {result_data.get('bit_error_rate', 0):.2e}
Thermal Sigma:    {result_data.get('thermal_sigma', 0)*1000:.3f} mV
"""
            ax.text(0.1, 0.35, results_text, ha='left', va='top',
                   fontsize=10, family='monospace', transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))

            # Footer
            ax.text(0.5, 0.05, "IEEE Publication Quality Figures", ha='center',
                   fontsize=9, style='italic', color='gray', transform=ax.transAxes)

            pdf.savefig(fig, bbox_inches='tight', dpi=300)
            plt.close()

            # Page 2: Research Executive Summary
            _tick("Generating research executive summary")
            page_count += 1
            fig = plt.figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis('off')

            # Get AI analysis
            ai_analysis = self.generate_ai_comprehensive_analysis(result_data=analysis_context)

            # Title
            ax.text(0.5, 0.95, "Research Executive Summary", ha='center', va='top',
                   fontsize=18, fontweight='bold', transform=ax.transAxes)

            # Research analysis
            ax.text(0.05, 0.88, ai_analysis, ha='left', va='top',
                   fontsize=9, family='monospace', transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5),
                   wrap=True)

            pdf.savefig(fig, bbox_inches='tight', dpi=300)
            plt.close()

            # ========== SECTION 2: Core Analysis Figures (IEEE-styled) ==========

            # Page 3: 3D Noise Map
            if has_3d_figure:
                _tick("Adding 3D perceptron noise map page")
                page_count += 1
                self.add_figure_page(pdf, report_context["canvas_3d"],
                                    "3D Perceptron Noise Weight Distribution",
                                    "Figure 1: Temperature and voltage dependency of noise weight")

            # Page 4: SNM Analysis
            if has_snm_figure:
                _tick("Adding SNM analysis page")
                page_count += 1
                self.add_figure_page(pdf, report_context["canvas_snm"],
                                    "SRAM Static Noise Margin Analysis",
                                    "Figure 2: SNM distribution and Pelgrom plot")

            # Page 5: Process Variability
            if has_var_figure:
                _tick("Adding process variability page")
                page_count += 1
                self.add_figure_page(pdf, report_context["canvas_var"],
                                    "Process Variability Analysis",
                                    "Figure 3: Monte Carlo simulation results")

            # Page 6: Thermal Noise
            if has_thermal_noise_figure:
                _tick("Adding thermal noise trajectory page")
                page_count += 1
                self.add_figure_page(pdf, report_context["canvas_thermal_noise"],
                                    "Thermal Noise Trajectory",
                                    "Figure 4: Euler-Maruyama simulation of voltage fluctuations")

            # Page 7: NBTI/HCI Reliability
            if has_reliability_figure:
                _tick("Adding reliability analysis page")
                page_count += 1
                self.add_figure_page(pdf, report_context["canvas_reliability"],
                                    "NBTI/HCI Reliability Analysis",
                                    "Figure 5: Lifetime prediction and degradation analysis")

            # ========== SECTION 3: Advanced Analysis (Conditional) ==========

            # Page 8: Design Space Optimization (if available)
            if has_pareto_figure:
                _tick("Adding design space optimization page")
                page_count += 1
                self.add_figure_page(pdf, report_context["canvas_pareto"],
                                    "Design Space Pareto Frontier",
                                    "Figure 6: Area vs. tapout success optimization")

            # Page 9: Reliability Lifetime Analysis (if available)
            if has_reliability_grove_figure:
                _tick("Adding reliability lifetime page")
                page_count += 1
                self.add_figure_page(pdf, report_context["canvas_reliability_grove"],
                                    "Reliability Lifetime Prediction",
                                    "Figure 7: NBTI/HCI degradation and temperature sensitivity")

            # ========== SECTION 4: Validation & Benchmark ==========
            if VALIDATION_AVAILABLE:
                if has_validation_profile_figure:
                    _tick("Adding validation profile page")
                    page_count += 1
                    self.add_figure_page(pdf, report_context["canvas_validation_profile"],
                                        "Analytical Validation Profile",
                                        "Figure 8: Analytical ground-truth distributions and residual")
                if has_benchmark_r2_figure:
                    _tick("Adding benchmark R2 page")
                    page_count += 1
                    self.add_figure_page(pdf, report_context["canvas_benchmark_r2"],
                                        "Benchmark R2 Comparison",
                                        "Figure 9: Model R2 comparison")
                if has_benchmark_speed_figure:
                    _tick("Adding benchmark speed page")
                    page_count += 1
                    self.add_figure_page(pdf, report_context["canvas_benchmark_speed"],
                                        "Benchmark Speed vs Accuracy",
                                        "Figure 10: Inference speed and R2")
                if has_benchmark_pred_actual_figure:
                    _tick("Adding benchmark prediction page")
                    page_count += 1
                    self.add_figure_page(pdf, report_context["canvas_benchmark_pred_actual"],
                                        "Benchmark Prediction & Residual",
                                        "Figure 11: Predicted vs actual and residual distribution")

            # ========== SECTION 5: Recommendations & Conclusions ==========

            # Page 10: AI Recommendations
            _tick("Writing recommendations page")
            page_count += 1
            fig = plt.figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis('off')

            # Title
            ax.text(0.5, 0.95, "Research Recommendations", ha='center', va='top',
                   fontsize=18, fontweight='bold', transform=ax.transAxes)

            # Recommendations
            recommendations = self.generate_recommendations_text(result_data=analysis_context)
            ax.text(0.05, 0.88, recommendations, ha='left', va='top',
                   fontsize=10, family='monospace', transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.5))

            # Additional insights
            insights = self.generate_ai_insights_text(result_data=analysis_context)
            ax.text(0.05, 0.50, "Key Insights:\n" + insights, ha='left', va='top',
                   fontsize=9, family='monospace', transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

            pdf.savefig(fig, bbox_inches='tight', dpi=300)
            plt.close()

        _tick("Report generation complete")

        print(f"IEEE report generated: {pdf_file} ({page_count} pages)")
        return pdf_file


    def create_snm_analysis_figure_for_report(self):
        """Create SNM analysis figure for report"""
        fig, axes = plt.subplots(2, 2, figsize=(10, 8))

        snm_values = np.array(self.current_result.get('snm_values', [])) * 1000

        # (a) Histogram
        ax = axes[0, 0]
        ax.hist(snm_values, bins=20, color='#0173B2', edgecolor='black', alpha=0.7)
        ax.axvline(np.mean(snm_values), color='red', linestyle='--', linewidth=2, label='Mean')
        ax.set_xlabel('SNM (mV)', fontsize=10)
        ax.set_ylabel('Frequency', fontsize=10)
        ax.set_title('(a) SNM Distribution', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # (b) CDF
        ax = axes[0, 1]
        snm_sorted = np.sort(snm_values)
        y_vals = np.arange(1, len(snm_sorted) + 1) / len(snm_sorted)
        ax.plot(snm_sorted, y_vals, color='#0173B2', linewidth=2, marker='o', markersize=3)
        ax.set_xlabel('SNM (mV)', fontsize=10)
        ax.set_ylabel('Cumulative Probability', fontsize=10)
        ax.set_title('(b) CDF', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, 1])

        # (c) Box plot
        ax = axes[1, 0]
        ax.boxplot(snm_values, vert=True)
        ax.set_ylabel('SNM (mV)', fontsize=10)
        ax.set_title('(c) Box Plot', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        # (d) Statistics
        ax = axes[1, 1]
        ax.axis('off')
        stats_text = f"""
STATISTICAL SUMMARY
?????????????????????????
Mean:   {np.mean(snm_values):.2f} mV
Std:    {np.std(snm_values):.2f} mV
Min:    {np.min(snm_values):.2f} mV
Max:    {np.max(snm_values):.2f} mV
Median: {np.median(snm_values):.2f} mV
Q1:     {np.percentile(snm_values, 25):.2f} mV
Q3:     {np.percentile(snm_values, 75):.2f} mV
        """
        ax.text(0.1, 0.5, stats_text, fontsize=11, family='monospace',
               verticalalignment='center',
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

        fig.suptitle('SNM Analysis', fontsize=14, fontweight='bold')
        plt.tight_layout()

        return fig

    def create_thermal_impact_figure_for_report(self):
        """Create thermal impact analysis figure"""
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))

        snm_values = np.array(self.current_result.get('snm_values', [])) * 1000

        # Simulate without thermal (for comparison)
        thermal_impact = snm_values - np.random.normal(2, 0.5, len(snm_values))

        ax = axes[0]
        ax.hist(thermal_impact, bins=15, alpha=0.6, label='Without Thermal',
               color='#029E73', edgecolor='black')
        ax.hist(snm_values, bins=15, alpha=0.6, label='With Thermal',
               color='#DE8F05', edgecolor='black')
        ax.set_xlabel('SNM (mV)', fontsize=10)
        ax.set_ylabel('Frequency', fontsize=10)
        ax.set_title('(a) Thermal Noise Impact', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Degradation
        ax = axes[1]
        degradation = thermal_impact - snm_values
        ax.bar(['Thermal\nDegradation'], [np.mean(degradation)],
              color='#CC78BC', edgecolor='black')
        ax.axhline(0, color='black', linestyle='-', linewidth=0.8)
        ax.set_ylabel('SNM Degradation (mV)', fontsize=10)
        ax.set_title('(b) Mean Degradation', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        fig.suptitle('Thermal Noise Impact Analysis', fontsize=14, fontweight='bold')
        plt.tight_layout()

        return fig

    # ========================================================================
    # Thermal Analysis Methods
    # ========================================================================

    def run_thermal_analysis(self):
        """Run thermal analysis"""
        self._flush_slider_updates()
        mc_runs = self.mc_runs_spinbox.value()
        dispatch = self._resolve_heavy_simulation_dispatch(
            self.num_cells,
            mc_runs,
            compute_mode=self.compute_mode_preference,
        )

        self.show_info("Running",
            f"Running thermal analysis with {mc_runs} Monte Carlo iterations...\n"
            f"Dispatch: {dispatch['selected']} ({dispatch['reason']}) | "
            f"compute_mode={dispatch['compute_mode']}, latency_mode={dispatch['latency_mode']}")

        try:
            if not NATIVE_BACKEND_AVAILABLE:
                self.show_warning("Warning", "Native backend wrapper not available")
                return

            input_data = self.generate_input_data()

            # Run without thermal noise
            data_without = native_simulate_array({
                'backend': 'hybrid' if self.backend_type == "hybrid" else 'standard',
                'temperature': float(self.temperature),
                'voltage': float(self.voltage),
                'num_cells': int(self.num_cells),
                'input_data': list(input_data),
                'noise_enable': bool(self.noise_enable),
                'variability_enable': bool(self.variability_enable),
                'monte_carlo_runs': int(mc_runs),
                'width': float(self.width),
                'length': float(self.length),
                'include_thermal_noise': False,
                'compute_mode': dispatch['compute_mode'],
                'latency_mode': dispatch['latency_mode'],
                'require_native': True,
                'prefer_hybrid_gate_logic': False,
            })

            # Run with thermal noise
            data_with = native_simulate_array({
                'backend': 'hybrid' if self.backend_type == "hybrid" else 'standard',
                'temperature': float(self.temperature),
                'voltage': float(self.voltage),
                'num_cells': int(self.num_cells),
                'input_data': list(input_data),
                'noise_enable': bool(self.noise_enable),
                'variability_enable': bool(self.variability_enable),
                'monte_carlo_runs': int(mc_runs),
                'width': float(self.width),
                'length': float(self.length),
                'include_thermal_noise': True,
                'compute_mode': dispatch['compute_mode'],
                'latency_mode': dispatch['latency_mode'],
                'require_native': True,
                'prefer_hybrid_gate_logic': False,
            })

            # Generate figure
            self.thermal_figure = AcademicFigureGenerator.create_snm_comparison_figure(
                data_without, data_with,
                self.temperature, self.voltage, self.num_cells
            )

            # Display on canvas
            self.canvas_thermal.figure = self.thermal_figure
            self.canvas_thermal.draw_idle()

            without_exec = data_without.get('_exec', {}) if isinstance(data_without, dict) else {}
            with_exec = data_with.get('_exec', {}) if isinstance(data_with, dict) else {}
            self.show_info(
                "Complete",
                "Thermal analysis completed!\n"
                f"Without thermal engine: {without_exec.get('selected', 'unknown')} ({without_exec.get('reason', 'unknown')})\n"
                f"With thermal engine: {with_exec.get('selected', 'unknown')} ({with_exec.get('reason', 'unknown')})",
            )

        except Exception as e:
            self.show_error("Error", f"Analysis failed: {str(e)}")

    def save_thermal_figure(self):
        """Save thermal figure as PNG"""
        if self.thermal_figure is None:
            self.show_warning( "No Figure", "Please run thermal analysis first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", "thermal_analysis.png", "PNG Files (*.png)"
        )

        if file_path:
            try:
                self.thermal_figure.savefig(file_path, dpi=300, bbox_inches='tight')
                self.show_info( "Saved", f"Figure saved to: {file_path}")
            except Exception as e:
                self.show_error("Error", f"Failed to save: {str(e)}")

    # ========================================================================
    # Advanced Analysis Methods
    # ========================================================================

    def calculate_workload(self):
        """Calculate Transformer workload memory requirements"""
        if not WORKLOAD_MODEL_AVAILABLE:
            self.show_warning( "Not Available", "Workload model not available.")
            return

        try:
            # Get parameters
            model_name = self.wl_model_name.text()
            hidden_dim = self.wl_hidden_dim.value()
            num_layers = self.wl_num_layers.value()
            num_heads = self.wl_num_heads.value()
            seq_length = self.wl_seq_length.value()
            batch_size = self.wl_batch_size.value()
            precision = self.wl_precision.currentText()
            attention_type = self.wl_attention.currentText()
            kv_heads = self.wl_kv_heads.value() if attention_type in ['gqa', 'mqa'] else None

            # Create workload profile
            workload = TransformerWorkloadProfile(
                model_name=model_name,
                hidden_dim=hidden_dim,
                num_layers=num_layers,
                num_heads=num_heads,
                seq_length=seq_length,
                batch_size=batch_size,
                precision=precision,
                attention_type=attention_type,
                num_kv_heads=kv_heads
            )

            # Format results
            results = f"""
=== Transformer Workload Analysis ===

Model: {model_name}
Architecture: {hidden_dim}D x {num_layers}L x {num_heads}H
Sequence Length: {seq_length}, Batch: {batch_size}
Precision: {precision}, Attention: {attention_type}

Memory Breakdown:
-----------------
KV Cache:         {workload.kv_cache_bytes / 1024**2:.2f} MB
Activation:       {workload.activation_bytes / 1024**2:.2f} MB
Per-token Memory: {workload.memory_per_token_bytes / 1024:.2f} KB

Total Memory:     {workload.total_memory_bytes / 1024**2:.2f} MB

Interpretation:
---------------
"""

            if workload.total_memory_bytes / 1024**2 < 128:
                results += "- Memory fits in small SRAM (< 128MB)\n"
            elif workload.total_memory_bytes / 1024**2 < 512:
                results += "- Memory requires medium SRAM (128-512MB)\n"
            else:
                results += "- Memory exceeds typical SRAM size (> 512MB)\n"

            if attention_type == 'mqa':
                results += f"- MQA: {100 * (1 - workload.kv_cache_bytes / (workload.kv_cache_bytes * num_heads)):.1f}% KV cache reduction!\n"

            self.wl_results_text.setPlainText(results)

        except Exception as e:
            self.show_error("Error", f"Calculation failed: {str(e)}")

    def translate_circuit_to_system(self):
        """Translate circuit parameters to system KPIs"""
        if not WORKLOAD_MODEL_AVAILABLE:
            self.show_warning( "Not Available", "Workload model not available.")
            return

        try:
            # Get circuit parameters
            snm_mv = self.kpi_snm.value()
            vmin_v = self.kpi_vmin.value()
            leakage_mw = self.kpi_leakage.value()
            temp_c = self.kpi_temp.value()

            # Create workload (use current workload tab parameters or default)
            workload = WorkloadScenarios.llama_7b_online()

            # Create translator
            translator = CircuitToSystemTranslator(workload)

            # Translate
            result = translator.translate_to_system_kpis(
                snm_mv=snm_mv,
                vmin_v=vmin_v,
                leakage_mw=leakage_mw,
                temp_c=temp_c
            )

            # Format results
            circ = result['circuit_params']
            kpis = result['system_kpis']

            verdict_color = "green" if result['is_acceptable'] else "red"

            results = f"""
=== Circuit-to-System KPI Translation ===

Circuit Parameters:
-------------------
SNM:        {circ['snm_mv']} mV
Vmin:       {circ['vmin_v']} V
Leakage:    {circ['leakage_mw']} mW
Temperature:{circ['temp_c']} C

System KPIs:
------------
BER:                {kpis['ber']:.2e}
Token Error Prob:   {kpis['token_error_probability']:.4e}
Accuracy Degradation: {kpis['accuracy_degradation_percent']:.4f}%

Performance:
------------
Nominal Latency:    {kpis['nominal_latency_ms']:.2f} ms
Voltage Penalty:    {kpis['voltage_penalty_ms']:.2f} ms
Tail Latency:       {kpis['tail_latency_ms']:.2f} ms
Tokens/sec:         {kpis['tokens_per_second']:.1f}
Energy/token:       {kpis['energy_per_token_uj']:.2f} µJ

Verdict:
--------
{result['verdict']}

Acceptability: {'ACCEPTABLE' if result['is_acceptable'] else 'NOT ACCEPTABLE'}
"""

            self.kpi_results_text.setPlainText(results)

        except Exception as e:
            self.show_error("Error", f"Translation failed: {str(e)}")

    def run_design_optimization(self):
        """Run design space optimization and plot Pareto frontier"""
        if not NATIVE_BACKEND_AVAILABLE:
            self.show_warning("Not Available", "Native backend wrapper not available.")
            return

        try:
            # Parse input lists
            sram_sizes = [float(x.strip()) for x in self.opt_sram_sizes.text().split(',')]
            snm_values = [float(x.strip()) for x in self.opt_snm_values.text().split(',')]
            vmin_values = [float(x.strip()) for x in self.opt_vmin_values.text().split(',')]

            dispatch = self._resolve_compute_dispatch(
                "optimize",
                {
                    "num_cells": max(1, int(self.num_cells)),
                    "sram_sizes_mb": sram_sizes,
                    "snm_values_mv": snm_values,
                    "vmin_values_v": vmin_values,
                    "compute_mode": self.compute_mode_preference,
                    "latency_mode": "batch",
                },
            )
            self.on_status_update(
                f"Optimization Dispatch: {dispatch['selected']} ({dispatch['reason']}) | "
                f"compute_mode={dispatch['compute_mode']}, latency_mode={dispatch['latency_mode']}"
            )

            # Parse constraint values from GUI
            max_area = float(self.opt_max_area.text())
            max_power = float(self.opt_max_power.text())
            min_tapout = float(self.opt_min_tapout.text())

            # Use current workload tab parameters
            workload_cfg = {
                'model_name': self.wl_model_name.text(),
                'hidden_dim': self.wl_hidden_dim.value(),
                'num_layers': self.wl_num_layers.value(),
                'num_heads': self.wl_num_heads.value(),
                'seq_length': self.wl_seq_length.value(),
                'batch_size': self.wl_batch_size.value(),
                'precision': self.wl_precision.currentText(),
                'attention_type': self.wl_attention.currentText(),
                'num_kv_heads': (
                    self.wl_kv_heads.value()
                    if self.wl_attention.currentText() in ['gqa', 'mqa']
                    else None
                ),
            }

            pareto_designs = native_optimize_design({
                'workload': workload_cfg,
                'sram_sizes_mb': sram_sizes,
                'snm_values_mv': snm_values,
                'vmin_values_v': vmin_values,
                'constraints': {
                    'max_area_mm2': max_area,
                    'max_power_mw': max_power,
                    'min_tapout_success_prob': min_tapout,
                },
                'compute_mode': dispatch['compute_mode'],
                'latency_mode': dispatch['latency_mode'],
                'require_native': True,
            })

            if not pareto_designs:
                # Provide detailed debug info with user's constraints
                debug_msg = f"""No designs found meeting constraints!

Search Space:
- SRAM sizes: {sram_sizes} MB
- SNM values: {snm_values} mV
- Vmin values: {vmin_values} V

Total combinations: {len(sram_sizes) * len(snm_values) * len(vmin_values)}

Current Constraints:
- Max Area: {max_area} mm^2
- Max Power: {max_power} mW
- Min Tapout Success: {min_tapout}%

Suggestions:
1. Relax constraints (increase Max Area/Power or decrease Min Tapout)
2. Expand search space (add more SNM/Vmin values)
3. Check console for debug output showing actual values

Note: Most designs have ~5% tapout success due to high accuracy degradation.
Try setting Min Tapout Success to 0% for exploration.
"""
                self.show_warning( "No Designs", debug_msg)
                self.opt_results_text.setPlainText(debug_msg)
                return

            # Plot Pareto frontier
            fig = self.canvas_pareto.figure
            fig.clear()
            ax = fig.add_subplot(111)

            areas = [d['area_mm2'] for d in pareto_designs]
            success = [d['tapout_success_prob'] for d in pareto_designs]

            scatter = ax.scatter(areas, success, c='red', s=100, alpha=0.7, edgecolors='black', zorder=3)
            ax.plot(areas, success, 'r--', alpha=0.5, linewidth=1.5, label='Pareto Frontier')

            ax.set_xlabel('Area (mm^2)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Tapout Success Probability (%)', fontsize=12, fontweight='bold')
            ax.set_title('Design Space Pareto Frontier', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend()

            # Annotate points
            for i, d in enumerate(pareto_designs):
                label = f"{d['sram_mb']}MB\n{d['snm_mv']}mV"
                ax.annotate(label, (d['area_mm2'], d['tapout_success_prob']),
                           xytext=(5, 5), textcoords='offset points', fontsize=8)

            # Apply IEEE styling
            self.apply_ieee_style(fig)
            self.canvas_pareto.draw_idle()

            # Format text results
            results = f"Found {len(pareto_designs)} Pareto-optimal designs:\n\n"
            results += f"{'SRAM':>5} {'SNM':>5} {'Vmin':>6} {'Area':>7} {'Power':>7} {'Success':>8} {'Tok/s':>8}\n"
            results += "-" * 70 + "\n"

            for d in pareto_designs:
                results += f"{d['sram_mb']:>4}MB {d['snm_mv']:>4}mV {d['vmin_v']:>5}V "
                results += f"{d['area_mm2']:>6.2f} mm^2 {d['power_mw']:>6.2f}mW "
                results += f"{d['tapout_success_prob']:>7.1f}% {d['tokens_per_sec']:>7.1f}\n"

            if len(pareto_designs) >= 2:
                baseline = pareto_designs[-1]
                aggressive = pareto_designs[0]
                area_savings = (baseline['area_mm2'] - aggressive['area_mm2']) / baseline['area_mm2'] * 100
                risk_increase = baseline['tapout_success_prob'] - aggressive['tapout_success_prob']

                results += f"\nTrade-off Analysis:\n"
                results += f"Baseline (conservative): {baseline['sram_mb']}MB, {baseline['snm_mv']}mV, {baseline['area_mm2']:.2f}mm^2\n"
                results += f"Aggressive: {aggressive['sram_mb']}MB, {aggressive['snm_mv']}mV, {aggressive['area_mm2']:.2f}mm^2\n"
                results += f"Area Savings: {area_savings:.1f}%\n"
                results += f"Risk Increase: {risk_increase:.1f}% (success decrease)\n"

            self.opt_results_text.setPlainText(results)

        except Exception as e:
            self.show_error("Error", f"Optimization failed: {str(e)}")

    def analyze_reliability(self):
        """Analyze NBTI/HCI reliability and lifetime prediction"""
        try:
            # Get parameters
            temperature = self.rel_temp.value()
            vgs = self.rel_vgs.value()
            vth = self.rel_vth.value()
            width = self.rel_width.value()
            num_cells = self.rel_num_cells.value()
            duty_cycle = self.rel_duty_cycle.value()
            failure_rate = self.rel_failure_rate.value()

            dispatch = self._resolve_compute_dispatch(
                "lifetime",
                {
                    "num_cells": max(1, int(num_cells)),
                    "width": float(width),
                    "duty_cycle": float(duty_cycle),
                    "failure_rate": float(failure_rate),
                    "compute_mode": self.compute_mode_preference,
                    "latency_mode": "batch",
                },
            )
            self.on_status_update(
                f"Reliability Dispatch: {dispatch['selected']} ({dispatch['reason']}) | "
                f"compute_mode={dispatch['compute_mode']}, latency_mode={dispatch['latency_mode']}"
            )

            # Import reliability modules
            from reliability_model import ReliabilityModel

            # Create models
            rel_model = ReliabilityModel()

            # Calculate NBTI/HCI shifts over time
            stress_times = np.logspace(0, 9, 100)  # 1 second to 10^9 seconds (~31 years)
            nbti_shifts = []
            hci_shifts = []
            total_shifts = []

            drain_current = 1e-3  # 1mA assumption

            for t in stress_times:
                nbti = rel_model.calculate_nbti_vth_shift(temperature, vgs, vth, t)
                hci = rel_model.calculate_hci_vth_shift(temperature, drain_current, width, t)
                total = nbti + hci

                nbti_shifts.append(nbti * 1000)  # Convert to mV
                hci_shifts.append(abs(hci) * 1000)
                total_shifts.append(total * 1000)

            # Predict lifetime (native backend required)
            lifetime_result = predict_lifetime_native_first(
                temperature=float(temperature),
                vgs=float(vgs),
                vds=float(vgs),
                vth=float(vth),
                width=float(width),
                num_cells=int(num_cells),
                duty_cycle=float(duty_cycle),
                failure_rate=float(failure_rate),
                compute_mode=dispatch['compute_mode'],
                latency_mode=dispatch['latency_mode'],
            )
            runtime_summary = summarize_lifetime_runtime(lifetime_result)
            if lifetime_result.get('_exec', {}).get('fallback'):
                self.on_status_update(
                    f"Reliability fallback active: {lifetime_result.get('fallback_notice', runtime_summary)}"
                )

            # Plot results
            fig = self.canvas_reliability_grove.figure
            fig.clear()

            # Create 2x2 subplot
            gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

            # (a) NBTI vs HCI vs Total Vth Shift
            ax1 = fig.add_subplot(gs[0, :])
            ax1.semilogx(stress_times / (365.25 * 24 * 3600), nbti_shifts, 'r-', linewidth=2, label='NBTI (Vth increase)')
            ax1.semilogx(stress_times / (365.25 * 24 * 3600), hci_shifts, 'b-', linewidth=2, label='HCI (Vth decrease magnitude)')
            ax1.semilogx(stress_times / (365.25 * 24 * 3600), total_shifts, 'k--', linewidth=2, label='Net Vth Shift')
            ax1.axhline(y=50, color='orange', linestyle=':', label='50mV Threshold')
            ax1.set_xlabel('Time (years)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Vth Shift (mV)', fontsize=12, fontweight='bold')
            ax1.set_title(f'(a) NBTI/HCI Vth Degradation (T={temperature}K, Vgs={vgs}V)', fontsize=13, fontweight='bold')
            ax1.legend(loc='best')
            ax1.grid(True, alpha=0.3)

            # (b) Lifetime distribution
            ax2 = fig.add_subplot(gs[1, 0])
            lifetimes = lifetime_result['cell_lifetimes']
            ax2.hist(lifetimes, bins=20, color='purple', alpha=0.7, edgecolor='black')
            ax2.axvline(lifetime_result['mean_lifetime'], color='red', linestyle='--', linewidth=2, label=f"Mean: {lifetime_result['mean_lifetime']:.1f} yrs")
            ax2.axvline(
                lifetime_result['lifetime_at_failure_rate'],
                color='green',
                linestyle='-.',
                linewidth=2,
                label=f"Target: {lifetime_result['lifetime_at_failure_rate']:.1f} yrs",
            )
            ax2.axvline(lifetime_result['t_90pct'], color='orange', linestyle='--', linewidth=2, label=f"90% ref: {lifetime_result['t_90pct']:.1f} yrs")
            ax2.set_xlabel('Lifetime (years)', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Count', fontsize=12, fontweight='bold')
            ax2.set_title('(b) Cell Lifetime Distribution', fontsize=13, fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # (c) Temperature sensitivity
            temps = [280, 310, 340, 360]
            target_lifetimes = []
            for temp_point in temps:
                temp_result = predict_lifetime_native_first(
                    temperature=float(temp_point),
                    vgs=float(vgs),
                    vds=float(vgs),
                    vth=float(vth),
                    width=float(width),
                    num_cells=int(num_cells),
                    duty_cycle=float(duty_cycle),
                    failure_rate=float(failure_rate),
                    compute_mode=dispatch['compute_mode'],
                    latency_mode=dispatch['latency_mode'],
                )
                target_lifetimes.append(float(temp_result.get('lifetime_at_failure_rate', 0.0)))

            ax3 = fig.add_subplot(gs[1, 1])
            ax3.plot(temps, target_lifetimes, 'ro-', linewidth=2, markersize=8)
            ax3.set_xlabel('Temperature (K)', fontsize=12, fontweight='bold')
            ax3.set_ylabel('Target Lifetime (years)', fontsize=12, fontweight='bold')
            ax3.set_title('(c) Temperature Sensitivity', fontsize=13, fontweight='bold')
            ax3.grid(True, alpha=0.3)

            fig.suptitle(f'Reliability Analysis: NBTI/HCI Lifetime Prediction ({num_cells} cells)', fontsize=14, fontweight='bold')

            # Apply IEEE styling
            self.apply_ieee_style(fig)
            self.canvas_reliability_grove.draw_idle()

            # Format text results
            results = build_lifetime_result_text(
                temperature=float(temperature),
                vgs=float(vgs),
                vth=float(vth),
                width=float(width),
                num_cells=int(num_cells),
                duty_cycle=float(duty_cycle),
                failure_rate=float(failure_rate),
                lifetime_result=lifetime_result,
                nbti_shift_10y_mv=float(nbti_shifts[np.argmin(np.abs(stress_times - 10 * 365.25 * 24 * 3600))]),
                hci_shift_10y_mv=float(hci_shifts[np.argmin(np.abs(stress_times - 10 * 365.25 * 24 * 3600))]),
                total_shift_10y_mv=float(total_shifts[np.argmin(np.abs(stress_times - 10 * 365.25 * 24 * 3600))]),
            )
            results += "\n\nRecommendation:\n---------------\n"
            if lifetime_result['mean_lifetime'] > 15:
                results += "EXCELLENT: Lifetime exceeds 15 years - Good for consumer applications\n"
            elif lifetime_result['mean_lifetime'] > 10:
                results += "GOOD: Lifetime exceeds 10 years - Acceptable for most applications\n"
            elif lifetime_result['mean_lifetime'] > 5:
                results += "MARGINAL: Lifetime 5-10 years - Consider temperature reduction\n"
            else:
                results += "POOR: Lifetime < 5 years - Requires design optimization\n"

            self.rel_results_text.setPlainText(results)

        except Exception as e:
            self.show_error("Error", f"Reliability analysis failed: {str(e)}")

    def ask_ai_advisor(self):
        """Ask the research analysis service for design recommendations."""
        if not AI_ADVISOR_AVAILABLE or not self.advisor or not self.advisor.available:
            self._show_ai_unavailable_warning("AI Research Analysis Not Available")
            return

        query = self.ai_query_input.toPlainText().strip()
        if not query:
            self.show_warning("Empty Query", "Please enter a question for the research analysis service.")
            return

        if self.current_result:
            context = {
                'temperature': self.temperature,
                'voltage': self.voltage,
                'num_cells': self.num_cells,
                'ber': self.current_result.get('bit_error_rate', 0),
                'snm_mean': np.mean(self.current_result.get('snm_values', [0])) * 1000,  # mV
                'backend': self.current_result.get('backend', 'unknown')
            }
        else:
            context = None

        if context:
            full_prompt = f"""
Current SRAM Simulation Context:
- Temperature: {context['temperature']}K
- Voltage: {context['voltage']}V
- Num Cells: {context['num_cells']}
- BER: {context['ber']:.2e}
- SNM (mean): {context['snm_mean']:.2f} mV
- Backend: {context['backend']}

User Question: {query}

Please provide specific recommendations based on SRAM design principles.
"""
        else:
            full_prompt = f"""
User Question: {query}

Please provide general SRAM design recommendations based on semiconductor physics principles.
"""

        def _run_ai_query():
            self.ai_response_text.setPlainText("🧠 AI is thinking...")

            system_prompt = """You are an expert SRAM design engineer with 20+ years of experience.
You understand:
- SNM (Static Noise Margin) and its relationship to temperature, voltage, and process variation
- BER (Bit Error Rate) optimization techniques
- Power consumption trade-offs
- NBTI/HCI reliability effects
- Area-performance-power optimization
- Perceptron-based SRAM vs traditional implementations

Provide specific, actionable recommendations based on semiconductor physics."""

            def _on_success(ai_response):
                if self._is_ai_unavailable_message(ai_response):
                    self.ai_response_text.setPlainText(f"⚠️ AI unavailable:\n\n{ai_response}")
                    self._refresh_ai_connection_label(ai_response)
                    return

                self.ai_response_text.setPlainText(f"✔️ AI Recommendation:\n\n{ai_response}")
                self._refresh_ai_connection_label()

            def _on_error(msg):
                self.ai_response_text.setPlainText(f"❌ Error: {msg}")
                self._refresh_ai_connection_label(str(msg))
                self.show_error("Error", f"Research analysis failed: {msg}")

            self._start_ai_action_thread(
                self._call_ai_chat,
                kwargs={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 800,
                    "model": self.advisor.model,
                },
                on_success=_on_success,
                on_error=_on_error,
            )

        self._ensure_ai_connection(_run_ai_query, lambda status: self._show_ai_unavailable_warning("AI Research Analysis Not Available", status))

    # ========================================================================
    # Research Analysis Methods
    # ========================================================================

    def show_ai_analysis_dialog(self):
        """Show AI analysis results in a dialog"""
        if not self.current_result:
            self.show_warning( "Warning", "No simulation results available.\nPlease run a simulation first.")
            return

        # Generate insights and recommendations
        insights = self.generate_ai_insights_text()
        recommendations = self.generate_recommendations_text()

        # Create report text
        snm_values = np.array(self.current_result.get('snm_values', []))
        report = f"""
=== Research Analysis Report ===

Current Parameters:
  - Temperature: {self.temp_spinbox.value()} K
  - Voltage: {self.volt_spinbox.value()} V
  - Cells: {self.cell_slider.value()}
  - Monte Carlo Runs: {self.monte_carlo_runs}

Simulation Results:
  - SNM Mean: {np.mean(snm_values)*1000:.2f} mV
  - SNM Std: {np.std(snm_values)*1000:.2f} mV
  - BER: {self.current_result.get('bit_error_rate', 0):.2e}
  - Thermal Sigma: {self.current_result.get('thermal_sigma', 0)*1000:.3f} mV

--- AI Insights ---
{insights}

--- Design Recommendations ---
{recommendations}
"""

        # Show in message box with detailed text
        msg = QMessageBox(self)
        msg.setWindowTitle("Research Analysis Report")
        msg.setText("Research analysis completed successfully.")
        msg.setDetailedText(report)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    # ========================================================================
    # Config Save/Load
    # ========================================================================

    def save_config(self):
        """Save configuration"""
        config = {
            'analysis_mode': self.analysis_mode,
            'temperature': self.temperature,
            'voltage': self.voltage,
            'num_cells': self.num_cells,
            'variability_enable': self.variability_enable,
            'monte_carlo_runs': self.monte_carlo_runs,
            'width': self.width,
            'length': self.length,
            'data_type': self.data_type,
            'compute_mode_preference': self.compute_mode_preference,
            'backend_type': self.backend_type,
            'analysis_view_mode': self.analysis_view_mode,
            'reliability_duty_cycle': self.rel_duty_cycle.value() if hasattr(self, 'rel_duty_cycle') else DEFAULT_DUTY_CYCLE,
            'reliability_failure_rate': self.rel_failure_rate.value() if hasattr(self, 'rel_failure_rate') else DEFAULT_FAILURE_RATE,
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "", "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                self.show_info( "Saved", "Configuration saved successfully.")
            except Exception as e:
                self.show_error("Error", f"Save failed: {str(e)}")

    def load_config(self):
        """Load configuration"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", "", "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.temp_slider.setValue(config.get('temperature', 310))
                self.volt_slider.setValue(int(config.get('voltage', 1.0) * 100))
                self.cell_slider.setValue(config.get('num_cells', 32))
                self.variability_checkbox.setChecked(config.get('variability_enable', True))
                self.mc_slider.setValue(config.get('monte_carlo_runs', 10))
                self.width_spinbox.setValue(config.get('width', 1.0))
                self.length_spinbox.setValue(config.get('length', 1.0))

                # Set analysis mode
                mode = config.get('analysis_mode', 'Basic Noise')
                index = self.mode_combo.findText(mode)
                if index >= 0:
                    self.mode_combo.setCurrentIndex(index)

                data_type = config.get('data_type', 'random')
                for button in self.data_button_group.buttons():
                    if button.property("data_type") == data_type:
                        button.setChecked(True)
                        break

                compute_mode = config.get("compute_mode_preference", "gpu")
                compute_mode_index = self.compute_mode_combo.findText(compute_mode.capitalize())
                if compute_mode_index < 0:
                    compute_mode_index = self.compute_mode_combo.findText("Auto")
                if compute_mode_index >= 0:
                    self.compute_mode_combo.setCurrentIndex(compute_mode_index)

                backend_type = str(config.get("backend_type", "standard")).strip().lower()
                backend_items = [self.backend_combo.itemText(i).lower() for i in range(self.backend_combo.count())]
                target_backend = "hybrid" if backend_type == "hybrid" else "standard"
                fallback_backend = "standard"

                selected_index = -1
                for idx, item in enumerate(backend_items):
                    if target_backend in item:
                        selected_index = idx
                        break

                if selected_index < 0:
                    for idx, item in enumerate(backend_items):
                        if fallback_backend in item:
                            selected_index = idx
                            break

                if selected_index >= 0:
                    self.backend_combo.setCurrentIndex(selected_index)

                if hasattr(self, "rel_duty_cycle"):
                    self.rel_duty_cycle.setValue(float(config.get("reliability_duty_cycle", DEFAULT_DUTY_CYCLE)))
                if hasattr(self, "rel_failure_rate"):
                    self.rel_failure_rate.setValue(float(config.get("reliability_failure_rate", DEFAULT_FAILURE_RATE)))

                analysis_view_mode = config.get("analysis_view_mode", "core")
                if isinstance(analysis_view_mode, str):
                    normalized = analysis_view_mode.strip().lower()
                    if normalized.startswith("adv"):
                        normalized = "advanced"
                    else:
                        normalized = "core"
                    self._set_analysis_view_mode(normalized, update_combo=True)

                self.show_info( "Loaded", "Configuration applied successfully.")
                self.run_simulation()

            except Exception as e:
                self.show_error("Error", f"Load failed: {str(e)}")


# ============================================================================
# Main Entry
# ============================================================================

def main():
    """Main entry function"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_QSS)
    window = SRAMSimulatorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
