# FloatingTranslator v1.0.0

桌面划词翻译器 — 选中文本，悬浮窗弹出翻译。首个正式版本。

## 下载

| 平台 | 文件 | 大小 |
|------|------|------|
| Linux x86_64 | `FloatingTranslator-v1.0.0-linux-x86_64.tar.gz` | 98 MB |

> Windows 版本需在 Windows 环境自行构建，见下方说明。

## SHA256

```
e13269917ecb7eb77a1056ce632c579a706b7bb79c7006d74aa8d6ecb42ae29c  FloatingTranslator-v1.0.0-linux-x86_64.tar.gz
```

## 系统要求

- **Linux**: X11 环境，需安装 `xclip`（`sudo apt install xclip`），Wayland 下部分功能受限
- **Windows**: Python 3.10+，需安装 `pywin32`

## 功能

- **多引擎翻译**：免费 MyMemory / LLM API（兼容 OpenAI、DeepSeek 等）/ 本地模型（llama.cpp + GGUF）
- 语言自动检测，源语言=目标语言时自动反向
- 悬浮窗跟随光标、智能避让屏幕边界
- 可拖拽、可设置不透明度、自动隐藏
- 系统托盘驻留、右键切换引擎

## Linux 使用

```bash
tar -xzf FloatingTranslator-v1.0.0-linux-x86_64.tar.gz
cd FloatingTranslator
./FloatingTranslator
```

首次运行自动生成 `config.json`，也可通过系统托盘 → 设置修改。

## Windows 自行构建

```bash
# 1. 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 2. 打包
pyinstaller FloatingTranslator.spec

# 3. 产物在 dist/FloatingTranslator/
```

## 本地模型

```bash
# 安装 llama-cpp-python（无编译环境用预编译包）
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# 通过 ModelScope 下载模型
pip install modelscope
modelscope download --model Qwen/Qwen2.5-1.5B-Instruct-GGUF --include '*q4_k_m*' --local_dir ~/model
```

设置中选择"本地模型"，指定模型目录即可。
