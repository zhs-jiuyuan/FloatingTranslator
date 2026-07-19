import pytest

import six  # noqa: F401
if not hasattr(six._SixMetaPathImporter, "_path"):
    six._SixMetaPathImporter._path = None

pytest_plugins = ["pytestqt"]


@pytest.fixture(autouse=True)
def _process_qt_events(qtbot):
    yield
    qtbot.wait(50)
