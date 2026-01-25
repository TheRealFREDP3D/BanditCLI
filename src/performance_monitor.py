"""Performance monitoring and logging module for BanditCLI.

This module provides comprehensive performance monitoring capabilities including:
- Memory usage tracking
- Function execution time profiling
- Cache hit rate monitoring
- SSH connection performance metrics
- Terminal output performance tracking
- Resource usage monitoring

The PerformanceMonitor class provides centralized performance tracking
with configurable logging and alerting capabilities.
"""

import gc
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional

import psutil


@dataclass
class PerformanceMetrics:
    """Data class for performance metrics."""

    memory_usage_mb: float = 0.0
    cache_hit_rate: float = 0.0
    ssh_connection_time_ms: float = 0.0
    terminal_output_lines: int = 0
    function_execution_times: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceAlert:
    """Data class for performance alerts."""

    metric_name: str
    current_value: float
    threshold: float
    severity: str  # "warning", "critical"
    message: str
    timestamp: float = field(default_factory=time.time)


class PerformanceMonitor:
    """Centralized performance monitoring for BanditCLI application.

    Tracks various performance metrics including memory usage, cache performance,
    SSH connection times, and function execution times. Provides configurable
    alerting for performance issues.

    Attributes:
        enabled (bool): Whether monitoring is enabled.
        metrics (PerformanceMetrics): Current performance metrics.
        alerts (deque): Recent performance alerts.
        thresholds (Dict): Performance alert thresholds.
        _lock (threading.Lock): Thread safety for metrics updates.
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialize performance monitor.

        Args:
            enabled: Whether to enable performance monitoring.
        """
        self.enabled = enabled
        self.metrics = PerformanceMetrics()
        self.alerts = deque(maxlen=100)  # Keep last 100 alerts
        self.thresholds = {
            "memory_usage_mb": 500.0,  # Alert if > 500MB
            "cache_hit_rate": 50.0,  # Alert if < 50%
            "ssh_connection_time_ms": 5000.0,  # Alert if > 5s
            "function_execution_time_ms": 1000.0,  # Alert if > 1s
        }
        self._lock = threading.Lock()
        self._function_times: dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self._logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup performance logger with appropriate formatting."""
        logger = logging.getLogger("bandit_performance")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # Use NullHandler to prevent output to stderr/stdout which breaks TUI
            logger.addHandler(logging.NullHandler())

        return logger

    def track_function(self, name: str) -> Callable:
        """Decorator to track function execution time.

        Args:
            name: Name of the function for tracking purposes.

        Returns:
            Decorator function that tracks execution time.
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                if not self.enabled:
                    return func(*args, **kwargs)

                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    execution_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
                    self._record_function_time(name, execution_time)

            return wrapper

        return decorator

    def _record_function_time(self, name: str, execution_time_ms: float) -> None:
        """Record function execution time with thread safety.

        Args:
            name: Function name.
            execution_time_ms: Execution time in milliseconds.
        """
        with self._lock:
            self._function_times[name].append(execution_time_ms)
            self.metrics.function_execution_times[name] = execution_time_ms

            # Check for performance alert
            threshold = self.thresholds.get("function_execution_time_ms", 1000.0)
            if execution_time_ms > threshold:
                self._add_alert(
                    PerformanceAlert(
                        metric_name=f"function_{name}",
                        current_value=execution_time_ms,
                        threshold=threshold,
                        severity="warning",
                        message=f"Function '{name}' took {execution_time_ms:.2f}ms (threshold: {threshold}ms)",
                    )
                )

    def update_memory_usage(self) -> None:
        """Update current memory usage metrics."""
        if not self.enabled:
            return

        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB

            with self._lock:
                self.metrics.memory_usage_mb = memory_mb

            # Check for memory alert
            threshold = self.thresholds.get("memory_usage_mb", 500.0)
            if memory_mb > threshold:
                self._add_alert(
                    PerformanceAlert(
                        metric_name="memory_usage",
                        current_value=memory_mb,
                        threshold=threshold,
                        severity="critical",
                        message=f"Memory usage: {memory_mb:.1f}MB (threshold: {threshold}MB)",
                    )
                )
        except Exception as e:
            self._logger.warning(f"Failed to update memory usage: {e}")

    def update_cache_performance(self, hits: int, misses: int) -> None:
        """Update cache performance metrics.

        Args:
            hits: Number of cache hits.
            misses: Number of cache misses.
        """
        if not self.enabled:
            return

        total = hits + misses
        if total > 0:
            hit_rate = (hits / total) * 100

            with self._lock:
                self.metrics.cache_hit_rate = hit_rate

            # Check for cache performance alert
            threshold = self.thresholds.get("cache_hit_rate", 50.0)
            if hit_rate < threshold:
                self._add_alert(
                    PerformanceAlert(
                        metric_name="cache_hit_rate",
                        current_value=hit_rate,
                        threshold=threshold,
                        severity="warning",
                        message=f"Cache hit rate: {hit_rate:.1f}% (threshold: {threshold}%)",
                    )
                )

    def update_ssh_performance(self, connection_time_ms: float) -> None:
        """Update SSH connection performance metrics.

        Args:
            connection_time_ms: Time taken to establish SSH connection in milliseconds.
        """
        if not self.enabled:
            return

        with self._lock:
            self.metrics.ssh_connection_time_ms = connection_time_ms

        # Check for SSH performance alert
        threshold = self.thresholds.get("ssh_connection_time_ms", 5000.0)
        if connection_time_ms > threshold:
            self._add_alert(
                PerformanceAlert(
                    metric_name="ssh_connection_time",
                    current_value=connection_time_ms,
                    threshold=threshold,
                    severity="warning",
                    message=f"SSH connection time: {connection_time_ms:.2f}ms (threshold: {threshold}ms)",
                )
            )

    def update_terminal_performance(self, lines_count: int) -> None:
        """Update terminal output performance metrics.

        Args:
            lines_count: Number of lines in terminal output.
        """
        if not self.enabled:
            return

        with self._lock:
            self.metrics.terminal_output_lines = lines_count

    def _add_alert(self, alert: PerformanceAlert) -> None:
        """Add performance alert with logging.

        Args:
            alert: Performance alert to add.
        """
        self.alerts.append(alert)

        log_level = logging.WARNING if alert.severity == "warning" else logging.ERROR
        self._logger.log(log_level, f"PERFORMANCE ALERT: {alert.message}")

    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics.

        Returns:
            PerformanceMetrics: Current performance metrics snapshot.
        """
        # Update memory usage before acquiring lock to avoid deadlock
        self.update_memory_usage()

        with self._lock:
            # Return a copy to avoid external modification
            return PerformanceMetrics(
                memory_usage_mb=self.metrics.memory_usage_mb,
                cache_hit_rate=self.metrics.cache_hit_rate,
                ssh_connection_time_ms=self.metrics.ssh_connection_time_ms,
                terminal_output_lines=self.metrics.terminal_output_lines,
                function_execution_times=self.metrics.function_execution_times.copy(),
                timestamp=time.time(),
            )

    def get_recent_alerts(self, count: int = 10) -> list[PerformanceAlert]:
        """Get recent performance alerts.

        Args:
            count: Number of recent alerts to return.

        Returns:
            List[PerformanceAlert]: List of recent alerts.
        """
        with self._lock:
            return list(self.alerts)[-count:]

    def get_function_stats(self, function_name: str) -> dict[str, float]:
        """Get statistics for a specific function.

        Args:
            function_name: Name of the function.

        Returns:
            Dict[str, float]: Statistics including avg, min, max execution times.
        """
        with self._lock:
            times = list(self._function_times.get(function_name, []))

        if not times:
            return {}

        return {
            "avg_ms": sum(times) / len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "count": len(times),
        }

    def clear_metrics(self) -> None:
        """Clear all performance metrics and alerts."""
        with self._lock:
            self.metrics = PerformanceMetrics()
            self.alerts.clear()
            self._function_times.clear()

        # Force garbage collection
        gc.collect()
        self._logger.info("Performance metrics cleared")

    def set_threshold(self, metric_name: str, threshold: float) -> None:
        """Set performance alert threshold.

        Args:
            metric_name: Name of the metric.
            threshold: Alert threshold value.
        """
        self.thresholds[metric_name] = threshold
        self._logger.info(f"Performance threshold updated: {metric_name} = {threshold}")

    def generate_report(self) -> str:
        """Generate a comprehensive performance report.

        Returns:
            str: Formatted performance report.
        """
        metrics = self.get_metrics()
        recent_alerts = self.get_recent_alerts(5)

        report = f"""Performance Report - {time.strftime("%Y-%m-%d %H:%M:%S")}
{"=" * 60}

Memory Usage:
  Current: {metrics.memory_usage_mb:.1f} MB
  Threshold: {self.thresholds.get("memory_usage_mb", 500.0)} MB

Cache Performance:
  Hit Rate: {metrics.cache_hit_rate:.1f}%
  Threshold: {self.thresholds.get("cache_hit_rate", 50.0)}%

SSH Performance:
  Last Connection: {metrics.ssh_connection_time_ms:.2f} ms
  Threshold: {self.thresholds.get("ssh_connection_time_ms", 5000.0)} ms

Terminal Output:
  Lines: {metrics.terminal_output_lines}

Recent Alerts ({len(recent_alerts)}):
"""

        for alert in recent_alerts:
            report += f"  [{alert.severity.upper()}] {alert.message}\n"

        # Add function performance summary
        if metrics.function_execution_times:
            report += "\nFunction Performance Summary:\n"
            for func_name, _exec_time in metrics.function_execution_times.items():
                stats = self.get_function_stats(func_name)
                if stats:
                    report += (
                        f"  {func_name}: {stats['avg_ms']:.2f}ms avg ({stats['count']} calls)\n"
                    )

        report += f"\n{'=' * 60}\n"
        return report


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance.

    Returns:
        PerformanceMonitor: Global performance monitor.
    """
    return _performance_monitor


def track_performance(name: Optional[str] = None) -> Callable:
    """Decorator to track function performance using global monitor.

    Args:
        name: Optional name for the function. If None, uses function.__name__.

    Returns:
        Decorator function.
    """

    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__
        return _performance_monitor.track_function(func_name)(func)

    return decorator
