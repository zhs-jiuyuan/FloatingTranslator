import pytest

pytest_plugins = ["pytestqt"]


@pytest.fixture(autouse=True)
def _process_qt_events(qtbot):
    yield
    qtbot.wait(50)
