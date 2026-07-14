# 鼠标跟随悬浮窗 — 设计规格

## 目标

FloatingWindow 启动后始终跟随鼠标移动，永不自动隐藏；划词时显示翻译结果，取消选区后窗口内容置空。

## 改动范围

### 1. `ui/floating_window.py`

| 项 | 操作 | 说明 |
|---|------|------|
| `_hide_timer` | 移除 | 不再需要自动隐藏定时器 |
| `_auto_hide_seconds` | 移除 | 不再需要自动隐藏秒数参数 |
| `_reset_hide_timer()` | 移除 | |
| `enterEvent`/`leaveEvent` | 移除 | 不再对进入/离开做定时器控制 |
| `_mouse_track_timer` | 新增 | QTimer，50ms 间隔，回调调用 `_position_near_cursor()` |
| `clear_content()` | 新增 | 清空原文、翻译、方向、错误标签，恢复占位文本 |
| `__init__` | 修改 | 构造后立即 `show()` + 启动 `_mouse_track_timer` |
| `show_translation()`/`show_error()` | 修改 | 移除 `_reset_hide_timer()` 调用 |

### 2. `main.py`

| 项 | 操作 | 说明 |
|---|------|------|
| `_poll_clipboard()` | 修改 | 本轮 xclip 返回空且上一轮有内容时 → `clear_content()` + 置空 `_last_clipboard` |

## 行为规格

- 程序启动 → 窗口立即显示在鼠标附近，持续跟随鼠标移动
- 用户划选文字 → xclip primary 变化 → 触发翻译 → 窗口显示结果
- 用户点击其他地方取消选区 → xclip primary 返回空 → 窗口内容置空，显示占位提示
- 窗口永不自动隐藏

## 不变约束

- 窗口定位算法 `_position_near_cursor()` 不变（+16 偏移 + 屏幕边界避让）
- 翻译流程 `_translate()` 不变
- 拖拽移动窗口功能不变
- 配置持久化不变（`auto_hide_seconds` 字段保留但不生效）
