"""
AutoHeal-Py: Intelligent Runtime Resilience Framework for Microservices

A lightweight Python framework that autonomously detects fragile service calls
at runtime and injects resilience patterns without code changes or redeployment.

Patent-worthy innovation: Autonomous detection and injection of resilience patterns.
"""

__version__ = "0.1.0"
__author__ = "AutoHeal-Py Team"

from .monitor import install_monitor, get_metrics, calculate_failure_rate

__all__ = [
    "install_monitor",
    "get_metrics", 
    "calculate_failure_rate"
]
