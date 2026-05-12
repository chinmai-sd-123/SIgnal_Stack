from sqlalchemy import inspect, text


def _column_names(engine, table_name: str) -> set[str]:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def ensure_runtime_schema(engine) -> None:
    """
    Small production migration guard for columns added after the first prototype.

    This is intentionally narrow: it only handles backward-compatible columns
    needed by auth/tenant isolation and the nullable outcome template job link.
    """
    dialect = engine.dialect.name
    with engine.begin() as connection:
        recruiter_columns = _column_names(engine, "recruiters")
        if recruiter_columns and "role" not in recruiter_columns:
            if dialect == "sqlite":
                connection.execute(text("ALTER TABLE recruiters ADD COLUMN role VARCHAR DEFAULT 'recruiter'"))
            else:
                connection.execute(text("ALTER TABLE recruiters ADD COLUMN role VARCHAR NOT NULL DEFAULT 'recruiter'"))

        job_columns = _column_names(engine, "jobs")
        if job_columns and "recruiter_id" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN recruiter_id VARCHAR"))
            if dialect != "sqlite":
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_recruiter_id ON jobs (recruiter_id)"))

        outcome_columns = _column_names(engine, "outcomes")
        if outcome_columns and dialect == "postgresql":
            connection.execute(text("ALTER TABLE outcomes ALTER COLUMN job_id DROP NOT NULL"))
