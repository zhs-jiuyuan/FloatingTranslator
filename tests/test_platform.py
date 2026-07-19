"""平台抽象层测试"""
import sys
from unittest.mock import patch, MagicMock

import pytest
from PySide6.QtCore import QTimer

from utils.platform import read_selection, get_cursor_pos, create_monitor, SelectionMonitor


class TestReadSelection:
    @patch("utils.platform.sys.platform", "linux")
    @patch("subprocess.run")
    def test_linux_reads_primary_selection(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="选中的文本")
        result = read_selection()
        assert result == "选中的文本"
        call_args = mock_run.call_args[0][0]
        assert "-selection" in call_args
        assert "primary" in call_args

    @patch("utils.platform.sys.platform", "linux")
    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_linux_missing_xclip_returns_empty(self, mock_run):
        result = read_selection()
        assert result == ""

    @patch("utils.platform.sys.platform", "linux")
    @patch("subprocess.run")
    def test_linux_nonzero_return_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = read_selection()
        assert result == ""


class TestGetCursorPos:
    def test_returns_ints(self, qtbot):
        x, y = get_cursor_pos()
        assert isinstance(x, int)
        assert isinstance(y, int)


class TestCreateMonitor:
    @patch("utils.platform.sys.platform", "linux")
    def test_linux_returns_selection_monitor(self, qtbot):
        monitor = create_monitor()
        assert isinstance(monitor, SelectionMonitor)
        monitor.stop()

    def test_monitor_has_expected_interface(self, qtbot):
        monitor = create_monitor()
        assert hasattr(monitor, "text_selected")
        assert hasattr(monitor, "start")
        assert hasattr(monitor, "stop")
        monitor.stop()
