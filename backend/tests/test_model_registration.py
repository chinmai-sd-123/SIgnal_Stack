import app.models as models


def test_job_candidate_table_is_registered_for_startup_create_all():
    assert "job_candidates" in models.Base.metadata.tables
