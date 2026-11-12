import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def dbConnection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(tmp_path / "nba.db")
    yield connection
    connection.close()
