"""
Shared pytest fixtures for Phase 1 DB tests.

Uses SQLite in-memory so tests run without a real PostgreSQL instance.
SQLAlchemy's JSON type maps to TEXT in SQLite — read/write behaviour is
identical to PostgreSQL for our use cases (dict serialization).
"""

import sys
import os

# Ensure backend/ is on the path (for db.models)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Ensure src/ is on the path (for golden_feature_calculator)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from db.models import Base


@pytest.fixture
def engine():
    """
    Fresh SQLite in-memory engine with all tables created.

    StaticPool: forces all connections to share the same underlying SQLite
    connection so tables created by create_all() are visible to every
    subsequent call (including calls from FastAPI's request-handler threads).

    check_same_thread=False: SQLite's default single-thread guard would reject
    connections re-used across FastAPI's threadpool — disable it since we own
    the engine and control its lifecycle within a single test.
    """
    e = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    yield e
    e.dispose()
