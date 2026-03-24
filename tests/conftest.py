import pytest
import sys
import os

# Add the parent directory to sys.path to allow importing autoheal
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from autoheal.monitor import TelemetryMonitor
from autoheal.detector import HealthDetector
from autoheal.injector import PatternInjector

@pytest.fixture
def monitor():
    """Provides a fresh TelemetryMonitor instance for each test."""
    return TelemetryMonitor(window_seconds=60)

@pytest.fixture
def detector(monitor):
    """Provides a HealthDetector instance linked to the test monitor."""
    return HealthDetector(monitor)

@pytest.fixture
def injector():
    """Provides a fresh PatternInjector instance."""
    return PatternInjector()
