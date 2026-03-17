"""Performance monitoring module for BanditCLI.

Tracks memory usage, function execution times, cache performance, and SSH
connection metrics. Provides configurable alerting for performance issues.
"""

import gc
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


@dataclass
class PerformanceMetrics:
    """Snapshot of current performance metrics."""

    memory_usage_mb: float = 0.0
    cache_hit_rate: float = 0.0
    ssh_connection_time_ms: float = 0.0
    terminal_output_lines: int = 0
    function_execution_times: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceAlert:
    """A performance threshold violation."""

    metric_name: str
    current_value: float
    threshold: float
    severity: str  # "warning" or "critical"
    message: str
    timestamp: float = field(default_factory=time.time)


class PerformanceMonitor:
    """Centralized performance monitoring for BanditCLI.

    Tracks memory usage, cache performance, SSH connection times, and
    function execution times. Provides configurable threshold alerting.

    Attributes:
        enabled (bool): Whether monitoring is active.
        thresholds (Dict): Numeric thresholds that trigger alerts.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.metrics = PerformanceMetrics()
        self.alerts: deque[PerformanceAlert] = deque(maxlen=100)
        self.thresholds: dict[str, float] = {
            "memory_usage_mb": 500.0,
            "cache_hit_rate": 50.0,
            "ssh_connection_time_ms": 5000.0,
            "function_execution_time_ms": 1000.0,
        }
        self._lock = threading.Lock()
        self._function_times: dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self._logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up a performance logger that doesn't pollute the TUI."""
        logger = logging.getLogger("bandit_performance")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        return logger

    def track_function(self, name: str) -> Callable:
        """Decorator factory to track a function's execution time.

        Args:
            name: Label used in metrics and alerts.

        Returns:
            Decorator that wraps the function with timing logic.
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if not self.enabled:
                    return func(*args, **kwargs)
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    self._record_function_time(name, elapsed_ms)

            return wrapper

        return decorator

    def _record_function_time(self, name: str, execution_time_ms: float) -> None:
        with self._lock:
            self._function_times[name].append(execution_time_ms)
            self.metrics.function_execution_times[name] = execution_time_ms

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
        """Sample and record current process memory usage."""
        if not self.enabled or not _PSUTIL_AVAILABLE:
            return

        try:
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024

            with self._lock:
                self.metrics.memory_usage_mb = memory_mb

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
        """Record cache hit/miss ratio.

        Args:
            hits: Number of cache hits.
            misses: Number of cache misses.
        """
        if not self.enabled:
            return

        total = hits + misses
        if total == 0:
            return

        hit_rate = (hits / total) * 100

        with self._lock:
            self.metrics.cache_hit_rate = hit_rate

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
        """Record SSH connection time.

        Args:
            connection_time_ms: Time taken to connect in milliseconds.
        """
        if not self.enabled:
            return

        with self._lock:
            self.metrics.ssh_connection_time_ms = connection_time_ms

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
        """Record terminal output line count.

        Args:
            lines_count: Number of lines currently in terminal output.
        """
        if not self.enabled:
            return

        with self._lock:
            self.metrics.terminal_output_lines = lines_count

    def _add_alert(self, alert: PerformanceAlert) -> None:
        self.alerts.append(alert)
        log_level = logging.WARNING if alert.severity == "warning" else logging.ERROR
        self._logger.log(log_level, f"PERFORMANCE ALERT: {alert.message}")

    def get_metrics(self) -> PerformanceMetrics:
        """Return a snapshot of current performance metrics."""
        self.update_memory_usage()
        with self._lock:
            return PerformanceMetrics(
                memory_usage_mb=self.metrics.memory_usage_mb,
                cache_hit_rate=self.metrics.cache_hit_rate,
                ssh_connection_time_ms=self.metrics.ssh_connection_time_ms,
                terminal_output_lines=self.metrics.terminal_output_lines,
                function_execution_times=self.metrics.function_execution_times.copy(),
                timestamp=time.time(),
            )

    def get_recent_alerts(self, count: int = 10) -> list[PerformanceAlert]:
        """Get the most recent performance alerts.

        Args:
            count: Maximum number of alerts to return.

        Returns:
            List of recent PerformanceAlert instances.
        """
        with self._lock:
            return list(self.alerts)[-count:]

    def get_function_stats(self, function_name: str) -> dict[str, float]:
        """Get timing statistics for a tracked function.

        Args:
            function_name: Name of the function.

        Returns:
            Dict with avg_ms, min_ms, max_ms, and count. Empty if no data.
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
        """Clear all metrics, alerts, and function timing data."""
        with self._lock:
            self.metrics = PerformanceMetrics()
            self.alerts.clear()
            self._function_times.clear()

        gc.collect()
        self._logger.info("Performance metrics cleared")

    def set_threshold(self, metric_name: str, threshold: float) -> None:
        """Update a performance alert threshold.

        Args:
            metric_name: The metric to update.
            threshold: New threshold value.
        """
        self.thresholds[metric_name] = threshold


# Module-level singleton
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Return the global PerformanceMonitor instance."""
    return _performance_monitor


def track_performance(name: Optional[str] = None) -> Callable:
    """Module-level decorator to track function performance.

    Args:
        name: Optional label. Defaults to the decorated function's name.

    Returns:
        Decorator function.
    """

    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__
        return _performance_monitor.track_function(func_name)(func)

    return decorator
