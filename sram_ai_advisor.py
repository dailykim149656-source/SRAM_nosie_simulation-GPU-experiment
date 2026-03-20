"""
SRAM AI Advisor - Research Analysis Integration
"""

import os
import json
import time
import numpy as np
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()


class SRAMAdvisor:
    """Research-analysis wrapper for SRAM guidance and recommendations."""

    def __init__(self):
        """Initialize the AI client and validate credentials."""
        self.client = None
        self.model = "gpt-4o-mini"
        self.available = False
        self.connection_status = "Not configured"
        self._connected = False
        self._last_connection_ts = 0.0
        self._conn_check_ttl_sec = 300
        self._connection_error = None

        try:
            api_key = (os.getenv("AZURE_OPENAI_KEY") or "").strip()
            azure_endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()

            if not api_key or not azure_endpoint:
                self.connection_status = "Missing AI service credentials"
                return

            if self._is_placeholder_value(api_key) or self._is_placeholder_value(azure_endpoint):
                self.connection_status = "AI credentials appear to contain placeholder values"
                return

            self.client = AzureOpenAI(
                api_key=api_key,
                api_version="2024-10-21",
                azure_endpoint=azure_endpoint,
            )
            self.available = True
            self.connection_status = "Configured (not validated)"
        except Exception as e:
            self.connection_status = f"AI service connection check failed: {e}"
            print(f"AI service connection check failed: {e}")

    def is_connected(self) -> bool:
        """Return whether a recent connectivity check has passed."""
        return self._connected and (time.time() - self._last_connection_ts) <= self._conn_check_ttl_sec

    def get_connection_status(self) -> str:
        """Return most-recent connection status message."""
        return self.connection_status

    def _should_validate_connection(self, force: bool = False) -> bool:
        if not self.available or self.client is None:
            return False
        if force:
            return True
        if not self._connected:
            return True
        return (time.time() - self._last_connection_ts) > self._conn_check_ttl_sec

    def ensure_connection(self, force: bool = False) -> bool:
        """Validate connectivity lazily before making real API calls."""
        if not self.available or self.client is None:
            self.connection_status = "AI service credentials are not configured"
            return False

        if not self._should_validate_connection(force=force):
            return True

        try:
            models = self.client.models.list()
            list(models)
            self._connected = True
            self._last_connection_ts = time.time()
            self.connection_status = "Connected"
            self._connection_error = None
            return True
        except Exception as e:
            self._connected = False
            self._last_connection_ts = time.time()
            self._connection_error = str(e)
            self.connection_status = f"AI service connection check failed: {e}"
            print(f"AI service connection check failed: {e}")
            return False

    def _is_placeholder_value(self, value: str) -> bool:
        lowered = (value or "").strip().lower()
        if not lowered:
            return True
        placeholder_patterns = (
            "your",
            "replace",
            "placeholder",
            "changeme",
            "<your",
            "xxx",
            "todo",
        )
        if lowered in {"xxx", "your-key", "your-key-here", "your_key", "changeme"}:
            return True
        return any(token in lowered for token in placeholder_patterns)

    def _validate_connection(self):
        """Validate AI service connectivity before exposing the advisor as available."""
        return self.ensure_connection(force=True)

    def analyze_research_data(self, data_points):
        """Run AI analysis on research SNM training data."""
        if not self.available:
            return f"AI research analysis service is not available. ({self.connection_status})"

        if not self.ensure_connection():
            return f"AI research analysis service is not available. ({self.connection_status})"

        if len(data_points) < 2:
            return "Need at least 2 data points for analysis"

        try:
            temps = [d["temperature"] for d in data_points]
            volts = [d["voltage"] for d in data_points]
            errors = [abs(d["snm_pred"] - d["snm_actual"]) for d in data_points]

            summary = f"""
Research SRAM Test Data Summary:

Data Points: {len(data_points)}
Temperature Range: {min(temps):.0f}K to {max(temps):.0f}K
Voltage Range: {min(volts):.2f}V to {max(volts):.2f}V

Error Analysis:
- Average Error: {np.mean(errors)*1000:.2f} mV
- Max Error: {max(errors)*1000:.2f} mV
- Min Error: {min(errors)*1000:.2f} mV

Recent measurements:
{json.dumps(data_points[-3:], indent=2)}

Based on this data, what are the 3 most important test conditions to run next
to improve SNM prediction accuracy? Explain your reasoning using semiconductor physics.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert SRAM design engineer with 20 years of experience.
You understand SNM (Static Noise Margin), temperature dependencies, voltage scaling,
Pelgrom mismatch, and process variations.
Provide recommendations based on semiconductor physics, not guessing.""",
                    },
                    {"role": "user", "content": summary},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            return response.choices[0].message.content
        except Exception as e:
            self._connected = False
            self.connection_status = f"Runtime error: {e}"
            return f"Error calling AI research analysis service: {str(e)}"

    def explain_error(self, error_mV, data_point):
        """Explain a prediction error for a single sample."""
        if not self.available:
            return f"AI research analysis service is not available. ({self.connection_status})"

        if not self.ensure_connection():
            return f"AI research analysis service is not available. ({self.connection_status})"

        try:
            query = f"""
Why is there a {error_mV:.1f} mV prediction error at these conditions?
- Temperature: {data_point["temperature"]}K
- Voltage: {data_point["voltage"]}V
- Cells: {data_point["num_cells"]}

Possible causes:
1. Measurement uncertainty
2. Pelgrom mismatch (process variation)
3. Temperature/voltage scaling accuracy
4. Model limitation (corner not trained yet)

Explain briefly using physics.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an SRAM physics expert"},
                    {"role": "user", "content": query},
                ],
                max_tokens=300,
            )

            return response.choices[0].message.content
        except Exception as e:
            self._connected = False
            self.connection_status = f"Runtime error: {e}"
            return f"Error: {str(e)}"
