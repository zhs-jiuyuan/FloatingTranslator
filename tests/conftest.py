import pytest
from PySide6.QtCore import QCoreApplication

pytest_plugins = ["pytestqt"]


@pytest.fixture(autouse=True)
def _process_qt_events(qtbot):
    yield
    QCoreApplication.processEvents()
    qtbot.wait(50)
