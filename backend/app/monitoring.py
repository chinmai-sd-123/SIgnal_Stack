"""
Monitoring and Metrics Module.

Provides observability through:
- Basic Prometheus-compatible metrics
- Structured JSON logging
- Metrics endpoint for scraping
"""

from typing import Dict, Any
from datetime import datetime
import time
import json
from functools import wraps


# In-memory metrics storage (for MVP - production would use Redis or proper metrics lib)
_metrics = {
    "counters": {
        "evaluations_total": 0,
        "snapshot_fetch_total": 0,
        "snapshot_fetch_errors": 0,
        "llm_calls_total": 0,
        "llm_failures_total": 0,
        "feedback_events_total": 0,
    },
    "histograms": {
        "evaluation_duration_seconds": [],
        "llm_latency_seconds": [],
    },
    "gauges": {
        "active_evaluations": 0,
    }
}

_start_time = datetime.utcnow()


def increment_counter(name: str, value: int = 1):
    """Increment a counter metric."""
    if name in _metrics["counters"]:
        _metrics["counters"][name] += value


def set_gauge(name: str, value: float):
    """Set a gauge metric."""
    _metrics["gauges"][name] = value


def record_histogram(name: str, value: float):
    """Record a value for a histogram metric."""
    if name in _metrics["histograms"]:
        # Keep last 1000 values for histogram
        _metrics["histograms"][name].append(value)
        if len(_metrics["histograms"][name]) > 1000:
            _metrics["histograms"][name] = _metrics["histograms"][name][-1000:]


def get_histogram_stats(name: str) -> Dict[str, float]:
    """Get statistical summary of a histogram."""
    values = _metrics["histograms"].get(name, [])
    if not values:
        return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
    
    sorted_values = sorted(values)
    count = len(sorted_values)
    
    def percentile(p):
        idx = int(count * p / 100)
        return sorted_values[min(idx, count - 1)]
    
    return {
        "count": count,
        "sum": sum(sorted_values),
        "avg": sum(sorted_values) / count,
        "min": sorted_values[0],
        "max": sorted_values[-1],
        "p50": percentile(50),
        "p95": percentile(95),
        "p99": percentile(99),
    }


def get_all_metrics() -> Dict[str, Any]:
    """Get all metrics in JSON format."""
    uptime = (datetime.utcnow() - _start_time).total_seconds()
    
    result = {
        "uptime_seconds": uptime,
        "counters": dict(_metrics["counters"]),
        "gauges": dict(_metrics["gauges"]),
        "histograms": {}
    }
    
    for name in _metrics["histograms"]:
        result["histograms"][name] = get_histogram_stats(name)
    
    return result


def get_prometheus_format() -> str:
    """Get metrics in Prometheus text format."""
    lines = []
    
    # Counters
    for name, value in _metrics["counters"].items():
        lines.append(f"# TYPE signalstack_{name} counter")
        lines.append(f"signalstack_{name} {value}")
    
    # Gauges
    for name, value in _metrics["gauges"].items():
        lines.append(f"# TYPE signalstack_{name} gauge")
        lines.append(f"signalstack_{name} {value}")
    
    # Histograms
    for name in _metrics["histograms"]:
        stats = get_histogram_stats(name)
        lines.append(f"# TYPE signalstack_{name} histogram")
        lines.append(f'signalstack_{name}_bucket{{le="0.1"}} {sum(1 for v in _metrics["histograms"][name] if v <= 0.1)}')
        lines.append(f'signalstack_{name}_bucket{{le="0.5"}} {sum(1 for v in _metrics["histograms"][name] if v <= 0.5)}')
        lines.append(f'signalstack_{name}_bucket{{le="1"}} {sum(1 for v in _metrics["histograms"][name] if v <= 1)}')
        lines.append(f'signalstack_{name}_bucket{{le="5"}} {sum(1 for v in _metrics["histograms"][name] if v <= 5)}')
        lines.append(f'signalstack_{name}_bucket{{le="+Inf"}} {stats["count"]}')
        lines.append(f'signalstack_{name}_sum {stats["sum"]}')
        lines.append(f'signalstack_{name}_count {stats["count"]}')
    
    return "\n".join(lines)


def timed(metric_name: str):
    """Decorator to time function execution and record to histogram."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                record_histogram(metric_name, duration)
        return wrapper
    return decorator


def log_metric_event(event_type: str, details: Dict[str, Any] = None):
    """Log a metric event as structured JSON."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "details": details or {}
    }
    # Print to stdout for log aggregation
    print(json.dumps(log_entry))


# Convenience functions for common operations
def track_evaluation_start():
    """Track start of an evaluation."""
    set_gauge("active_evaluations", _metrics["gauges"]["active_evaluations"] + 1)


def track_evaluation_complete(duration_seconds: float, success: bool = True):
    """Track completion of an evaluation."""
    set_gauge("active_evaluations", max(0, _metrics["gauges"]["active_evaluations"] - 1))
    increment_counter("evaluations_total")
    record_histogram("evaluation_duration_seconds", duration_seconds)
    if not success:
        log_metric_event("evaluation_failed", {"duration": duration_seconds})


def track_llm_call(latency_seconds: float, success: bool = True):
    """Track an LLM call."""
    increment_counter("llm_calls_total")
    record_histogram("llm_latency_seconds", latency_seconds)
    if not success:
        increment_counter("llm_failures_total")


def track_snapshot_fetch(success: bool = True):
    """Track a snapshot fetch operation."""
    increment_counter("snapshot_fetch_total")
    if not success:
        increment_counter("snapshot_fetch_errors")


def track_feedback():
    """Track a feedback event."""
    increment_counter("feedback_events_total")
