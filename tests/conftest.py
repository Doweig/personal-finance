"""Shared test fixtures."""

import duckdb
import pytest

from ingestion.db import create_schema


@pytest.fixture
def conn():
    """In-memory DuckDB connection with schema created."""
    c = duckdb.connect(":memory:")
    create_schema(c)
    yield c
    c.close()
