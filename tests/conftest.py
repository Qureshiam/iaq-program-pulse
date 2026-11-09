import pytest

from pulse import data


@pytest.fixture(scope="session")
def programs():
    return {p.id: p for p in data.load_programs()}


@pytest.fixture(scope="session")
def updates():
    return data.load_updates()


@pytest.fixture(scope="session")
def analyses():
    return data.load_demo_analyses()
