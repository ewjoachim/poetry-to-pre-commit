from __future__ import annotations

import pathlib

import pytest


@pytest.fixture
def poetry_cwd():
    return pathlib.Path(__file__).parent
