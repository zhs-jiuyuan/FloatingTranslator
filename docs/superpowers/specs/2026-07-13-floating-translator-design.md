# FloatingTranslator 设计规格

> 桌面划词翻译器 — 极简暗色悬浮窗，多引擎可插拔架构

**目标：** 构建一个 Windows 桌面划词翻译应用，用户选中文本后按 Ctrl+Q，在鼠标位置弹出半透明悬浮翻译窗。

**架构：** QThread + 信号槽驱动的多引擎翻译框架。main.py 作为依赖注入中心，连接热键管理器、翻译引擎、悬浮窗和系统托盘。平台相关代码（热键）通过运行时检测隔离。

**技术栈：** Python 3.10+, PySide6, dataclasses, logging, QThread

---

## 一、项目结构

```
FloatingTranslator/
├── main.py                     # 应用入口
├── config.py                   # 配置数据模型 + JSON 读写
├── config.json                 # 运行时配置文件（gitignore）
├── engine/
│   ├── __init__.py
│   ├── base.py                 # 抽象基类 TranslationEngine
│   ├── free_online.py          # 免费引擎（MyMemory，无需 API Key）
│   ├── llm_api.py              # 大模型 API 引擎（OpenAI/DeepSeek 兼容）
│   └── local_model.py          # 本地模型引擎（Ollama / llama-cpp-python）
├── ui/
│   ├── __init__.py
│   ├── floating_window.py      # 悬浮翻译窗（无边框、置顶、半透明、自动隐藏）
│   ├── tray_icon.py            # 系统托盘图标与右键菜单
│   └── settings_dialog.py      # 设置对话框
├── utils/
│   ├── __init__.py
│   ├── hotkey.py               # 全局热键（Win→keyboard, Linux→pynput）
│   ├── text_selector.py        # 获取选中文本（Ctrl+C，剪贴板还原）
│   └── language_detector.py    # 语言检测（字符集 + langdetect）
├── resources/
│   └── style.qss               # 全局 QSS 暗色样式表
├── logs/                       # 日志目录（gitignore）
│   └── app.log
├── requirements.txt
├── README.md
└── develop.md
```

## 二、组件设计

### 2.1 main.py — 应用入口

职责：创建 QApplication，实例化所有组件，连接信号槽，启动事件循环。

```
main() 流程:
1. 初始化 QApplication
2. 加载 Config（config.json）
3. 创建 TranslationEngine 实例（按配置选择引擎）
4. 创建 FloatingWindow（注入 engine）
5. 创建 TrayIcon（注入 config, engine 列表, floating_window）
6. 创建 HotkeyManager，绑定回调到翻译流程
7. 显示托盘图标
8. app.exec()
```

翻译触发流程（`on_translate_triggered`）:
1. TextSelector 获取选中文本
2. LanguageDetector 检测源语言 + 自动反向
3. 在工作线程中调用 engine.translate()
4. engine.result_ready 信号 → FloatingWindow.show_translation()
5. engine.error_occurred 信号 → FloatingWindow.show_error()

### 2.2 config.py — 配置模型

```python
@dataclass
class AppConfig:
    target_lang: str = "zh"           # 默认目标语言
    source_lang: str = "auto"         # 源语言（auto=自动检测）
    engine_type: str = "free_online"  # free_online | llm_api | local_model
    hotkey: str = "ctrl+q"           # 全局快捷键
    opacity: float = 0.92            # 窗口不透明度
    auto_hide_seconds: int = 5       # 自动隐藏延时
    # LLM API 配置
    llm_api_key: str = ""
    llm_api_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-3.5-turbo"
    llm_system_prompt: str = "你是一个专业的翻译助手，请准确、简洁地翻译用户输入的内容。"
    # 本地模型配置
    local_model_type: str = "ollama"  # ollama | llama_cpp
    local_model_path: str = ""        # ollama 模型名 或 gguf 文件路径
```

序列化：`ConfigManager.load(path) -> AppConfig` / `ConfigManager.save(config, path)`

### 2.3 engine/ — 翻译引擎

**base.py — TranslationEngine (QObject)**

```python
class TranslationEngine(QObject):
    result_ready = Signal(str)       # 翻译成功
    error_occurred = Signal(str)     # 翻译失败

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> None:
        """在工作线程中调用，完成后发射信号"""
```

各引擎在 translate() 中创建 QThread，在线程的 run() 中执行网络请求/本地推理，通过信号返回结果。严禁阻塞主线程。

**free_online.py — MyMemory 引擎**
- 调用 `https://api.mymemory.translated.net/get`（免费，无需 API Key）
- 解析 JSON 返回 `responseData.translatedText`

**llm_api.py — 大模型 API 引擎**
- 使用 `openai` 库，兼容 OpenAI / DeepSeek / 其他兼容 API
- 支持自定义 system prompt 实现翻译风格控制
- 配置 base_url 切换不同服务商

**local_model.py — 本地模型引擎**
- ollama 模式：调用 `ollama` Python 库
- llama_cpp 模式：使用 `llama-cpp-python` 加载 GGUF 模型
- 同样支持 system prompt 角色设定

### 2.4 ui/ — 用户界面

**floating_window.py — 悬浮翻译窗**

- `Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool`
- 背景色 `rgba(20, 20, 20, 0.92)`，圆角 10px
- 窗口大小自适应内容，最大宽度 400px
- 标题栏：原文 / 译文标签 + 关闭按钮
- 内容区：原文（灰色） + 译文（绿色高亮）
- 鼠标进入窗口时取消自动隐藏计时器
- 鼠标离开窗口时启动 5 秒倒计时，到时自动隐藏
- 窗口位置跟随鼠标，智能避让屏幕边缘

**tray_icon.py — 系统托盘**

- 右键菜单：切换引擎（子菜单）| 设置 | 分隔线 | 退出
- 左键双击：显示/隐藏悬浮窗（手动触发一次翻译）
- 最小化到托盘（不退出）

**settings_dialog.py — 设置对话框**

- 模态对话框，QTabWidget 或分组布局
- 通用设置：目标语言下拉框、快捷键、不透明度滑块、自动隐藏秒数
- 引擎选择：单选按钮切换引擎类型
- LLM API 设置：API Key（密码输入框）、API URL、模型名、系统提示词（多行文本框）
- 本地模型设置：模型类型（ollama/llama_cpp 下拉）、模型路径/名称
- 保存时调用 ConfigManager.save()，关闭时应用新配置

### 2.5 utils/ — 工具模块

**hotkey.py — 全局热键**

```python
class HotkeyManager(QObject):
    triggered = Signal()

    def __init__(self, hotkey: str):
        if sys.platform == "win32":
            import keyboard
            keyboard.add_hotkey(hotkey, lambda: self.triggered.emit())
        else:
            from pynput import keyboard as pynput_keyboard
            # 使用 pynput 的 GlobalHotKeys 监听组合键
```

**text_selector.py — 选中文本获取**

```python
class TextSelector:
    @staticmethod
    def get_selected_text() -> str:
        # 1. 保存当前剪贴板内容
        # 2. 模拟 Ctrl+C（pyautogui.hotkey('ctrl', 'c')）
        # 3. 延时 0.1s 等待剪贴板更新
        # 4. 读取 pyperclip.paste()
        # 5. 还原剪贴板原内容
        # 6. 返回选中文本
```

Windows 注意：云剪贴板可能引入额外延时，已通过 0.1s 延时和异常捕获处理。

**language_detector.py — 语言检测**

```python
class LanguageDetector:
    @staticmethod
    def detect(text: str) -> str:
        # 快速路径：字符集判断
        #   - 含 CJK 字符 → "zh"
        #   - 纯 ASCII → "en"
        #   - 含日文假名 → "ja"
        #   - 含韩文 → "ko"
        # 不确定时回退到 langdetect 库
```

语言反向逻辑：若 `detect(text) == target_lang`，自动交换源语言和目标语言。

### 2.6 resources/style.qss — 全局样式

极简暗色主题：
- 背景色 `#141414`，文字色 `#e0e0e0`
- 圆角输入框、按钮
- 选中高亮 `#5af`（蓝色调）
- 滚动条暗色风格
- 对话框、菜单统一配色

## 三、线程安全规则

1. 翻译引擎的 `translate()` 在 QThread 中执行，**严禁直接操作 UI**
2. UI 与引擎之间仅通过信号通信：`result_ready(str)`, `error_occurred(str)`
3. FloatingWindow 连接引擎信号，在主线程更新界面
4. 工作线程中捕获所有异常，转为 `error_occurred` 信号

## 四、平台差异处理

| 特性 | Windows | Linux |
|------|---------|-------|
| 全局热键 | `keyboard` 库 | `pynput` 库 |
| 剪贴板 | `pyperclip` + `pyautogui` | 同左（pyautogui 不支持 Wayland 部分功能） |
| 窗口置顶 | `Qt.WindowStaysOnTopHint` | 同左 |
| 系统托盘 | QSystemTrayIcon | 同左 |
| 管理员权限 | keyboard 需要 | pynput 不需要 root |

## 五、配置持久化

- 默认配置硬编码在 `AppConfig` 的默认值中
- 首次运行时生成 `config.json`
- 设置对话框保存时写回 JSON
- 启动时读取，JSON 解析失败则使用默认配置

## 六、日志

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
```

## 七、依赖项

```
PySide6>=6.5.0
keyboard>=0.13.5
pynput>=1.7.6
pyperclip>=1.8.2
pyautogui>=0.9.54
langdetect>=1.0.9
openai>=1.0.0
ollama>=0.1.0
requests>=2.28.0
```

## 八、启动验证清单

- [ ] `python main.py` 能启动，显示系统托盘图标
- [ ] Ctrl+Q（或热键）触发翻译，悬浮窗弹出在鼠标位置
- [ ] 免费引擎返回占位/真实翻译结果
- [ ] 设置对话框可打开、修改、保存
- [ ] 托盘右键菜单可切换引擎、打开设置、退出
- [ ] 5 秒无操作后悬浮窗自动隐藏
- [ ] 鼠标移入悬浮窗时取消自动隐藏
- [ ] 所有异常被捕获，不崩溃
