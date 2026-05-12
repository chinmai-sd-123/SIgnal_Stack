import pytest

from app.config.config import config
from app.monitoring import _metrics, get_all_metrics, get_prometheus_format
from app.services.llm import OpenAILLMService


class _FakeResponse:
    output_text = '{"ok": true}'

    class usage:
        input_tokens = 1000
        output_tokens = 500
        total_tokens = 1500


class _FakeResponses:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return _FakeResponse()


class _FakeClient:
    def __init__(self):
        self.responses = _FakeResponses()


def _reset_llm_metrics():
    for key in list(_metrics["counters"]):
        if key.startswith("llm_"):
            _metrics["counters"][key] = 0
    _metrics["histograms"]["llm_latency_seconds"] = []
    _metrics["labeled_gauges"]["cost_per_candidate"] = {}
    _metrics["labeled_gauges"]["cost_per_job"] = {}


@pytest.mark.unit
def test_llm_call_tracks_tokens_cost_latency_and_context(monkeypatch):
    _reset_llm_metrics()
    monkeypatch.setattr(config, "LLM_INPUT_COST_PER_1M", 1.0)
    monkeypatch.setattr(config, "LLM_OUTPUT_COST_PER_1M", 2.0)
    monkeypatch.setattr("app.services.llm.cache.get_llm_response_by_prompt", lambda key: None)
    monkeypatch.setattr("app.services.llm.cache.set_llm_response", lambda *args, **kwargs: True)

    service = OpenAILLMService()
    service.api_key = "test-key"
    service.model = "test-model"
    service.client = _FakeClient()

    result = service._call_with_retry(
        "unique prompt for usage tracking",
        tracking_context={"candidate_id": "cand-1", "job_id": "job-1"},
    )

    assert result == '{"ok": true}'
    assert _metrics["counters"]["llm_calls_total"] == 1
    assert _metrics["counters"]["llm_cache_misses_total"] == 1
    assert _metrics["counters"]["llm_input_tokens_total"] == 1000
    assert _metrics["counters"]["llm_output_tokens_total"] == 500
    assert _metrics["counters"]["llm_estimated_cost_total"] == pytest.approx(0.002)
    assert _metrics["labeled_gauges"]["cost_per_candidate"]["cand-1"] == pytest.approx(0.002)
    assert _metrics["labeled_gauges"]["cost_per_job"]["job-1"] == pytest.approx(0.002)
    assert len(_metrics["histograms"]["llm_latency_seconds"]) == 1


@pytest.mark.unit
def test_llm_cache_hit_does_not_count_provider_call(monkeypatch):
    _reset_llm_metrics()
    monkeypatch.setattr("app.services.llm.cache.get_llm_response_by_prompt", lambda key: "cached response")

    service = OpenAILLMService()
    service.api_key = "test-key"
    service.model = "test-model"
    service.client = _FakeClient()

    result = service._call_with_retry("cached prompt")

    assert result == "cached response"
    assert service.client.responses.calls == 0
    assert _metrics["counters"]["llm_cache_hits_total"] == 1
    assert _metrics["counters"]["llm_calls_total"] == 0


@pytest.mark.unit
def test_default_gpt5_mini_cost_pricing_is_nonzero(monkeypatch):
    monkeypatch.setattr(config, "LLM_INPUT_COST_PER_1M", 0.25)
    monkeypatch.setattr(config, "LLM_OUTPUT_COST_PER_1M", 2.00)
    service = OpenAILLMService()
    service.model = "gpt-5-mini"

    assert service._estimate_cost(1_000_000, 1_000_000) == pytest.approx(2.25)


@pytest.mark.unit
def test_metrics_exports_cost_labels_in_json_and_prometheus():
    _reset_llm_metrics()
    _metrics["counters"]["llm_estimated_cost_total"] = 0.25
    _metrics["labeled_gauges"]["cost_per_candidate"] = {"cand-1": 0.10}
    _metrics["labeled_gauges"]["cost_per_job"] = {"job-1": 0.15}

    json_metrics = get_all_metrics()
    assert json_metrics["labeled_gauges"]["cost_per_candidate"]["cand-1"] == pytest.approx(0.10)
    assert json_metrics["labeled_gauges"]["cost_per_job"]["job-1"] == pytest.approx(0.15)

    prometheus = get_prometheus_format()
    assert 'signalstack_cost_per_candidate{candidate_id="cand-1"} 0.1' in prometheus
    assert 'signalstack_cost_per_job{job_id="job-1"} 0.15' in prometheus
