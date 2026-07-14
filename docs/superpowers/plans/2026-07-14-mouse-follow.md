# 鼠标跟随悬浮窗 实现计划

> **面向 AI 代理的工作者：** 使用 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** FloatingWindow 启动后始终跟随鼠标，永不自动隐藏；选区取消后内容置空。

**架构：** 在 FloatingWindow 中用 QTimer 轮询鼠标位置驱动窗口移动，移除自动隐藏逻辑。在 main.py 中扩展剪贴板轮询以检测选区取消。

**技术栈：** PySide6, Python 3.10+

---

### 任务 1：FloatingWindow — 移除自动隐藏 + 新增鼠标追踪 + 新增 clear_content

**文件：**
- 修改：`ui/floating_window.py`

- [ ] **步骤 1：修改 `__init__` — 移除 `_auto_hide_seconds` 和 `_hide_timer`，新增 `_mouse_track_timer`**

```python
def __init__(
    self, opacity: float = 0.92, parent=None
) -> None:
    super().__init__(parent)
    self._opacity = opacity
    self._dragging = False
    self._drag_pos = None

    self._mouse_track_timer = QTimer(self)
    self._mouse_track_timer.setInterval(50)
    self._mouse_track_timer.timeout.connect(self._position_near_cursor)

    self._setup_ui()
    self._setup_window_flags()
```

- [ ] **步骤 2：移除 `_reset_hide_timer`、`enterEvent`、`leaveEvent` 方法，新增 `clear_content` 和 `start_tracking`**

```python
def clear_content(self) -> None:
    self._source_text.clear()
    self._source_text.setVisible(False)
    self._direction_label.setText("")
    self._result_label.setText("翻译结果将在此处显示")
    self._error_label.clear()
    self._error_label.setVisible(False)

def start_tracking(self) -> None:
    self._position_near_cursor()
    self.show()
    self._mouse_track_timer.start()
```

- [ ] **步骤 3：`show_translation` 和 `show_error` 中移除 `_reset_hide_timer()` 调用**

`show_translation` 方法末尾，删除 `self._reset_hide_timer()`
`show_error` 方法末尾，删除 `self._reset_hide_timer()`

- [ ] **步骤 4：Commit**

```bash
git add ui/floating_window.py
git commit -m "feat: mouse tracking + remove auto-hide from FloatingWindow"
```

---

### 任务 2：main.py — 选区取消检测 + 窗口启动即显示

**文件：**
- 修改：`main.py`

- [ ] **步骤 1：修改 `__init__` — 不传 `auto_hide_seconds`，启动后立即追踪**

```python
self._floating_window = FloatingWindow(
    opacity=self._config.opacity,
)
self._floating_window.close_requested.connect(self._floating_window.hide)
self._floating_window.start_tracking()
```

- [ ] **步骤 2：修改 `_poll_clipboard` — 检测选区取消后调用 `clear_content`**

```python
def _poll_clipboard(self) -> None:
    if self._translating:
        return
    text = self._read_primary_selection()
    if not text:
        if self._last_clipboard:
            self._last_clipboard = ""
            self._floating_window.clear_content()
        return
    if text != self._last_clipboard:
        logger.debug("检测到选区变化: %s...", text[:80])
        self._last_clipboard = text
        self._translate(text)
```

- [ ] **步骤 3：`_open_settings` 中移除已不存在的 `_auto_hide_seconds` 引用**

删除这一行：
```python
self._floating_window._auto_hide_seconds = self._config.auto_hide_seconds
```

- [ ] **步骤 4：Commit**

```bash
git add main.py
git commit -m "feat: detect deselection to clear window, start tracking on init"
```

---

### 任务 3：验证运行

- [ ] **步骤 1：启动应用**

```bash
conda run -n spider python main.py
```

- [ ] **步骤 2：验证行为**

1. 窗口启动后立即显示在鼠标附近
2. 移动鼠标，窗口跟随
3. 划选文字，窗口显示翻译结果
4. 点击其他地方取消选区，窗口内容置空为占位提示
5. 窗口不自动消失
