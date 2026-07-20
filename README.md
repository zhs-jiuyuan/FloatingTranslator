# FloatingTranslator

桌面划词翻译 — 选中文本，悬浮窗弹出翻译。

## 快速开始

```bash
pip install -r requirements.txt
python main.py
```

## 系统要求

- Python 3.10+
- **Linux**: X11 环境，需安装 `xclip`；Wayland 下部分功能受限
- **Windows**: 依赖 `pywin32`（自动安装）

## 使用

鼠标划选文本，翻译结果在光标旁自动弹出。右键系统托盘图标可切换引擎、打开设置。

## 翻译引擎

| 引擎 | 说明 |
|------|------|
| 免费在线 | MyMemory API，无需任何配置 |
| LLM API | 兼容 OpenAI 接口，支持 DeepSeek 等 |
| 本地模型 | llama.cpp + GGUF，完全离线 |

## 本地模型

需 GGUF 格式量化模型。以 Qwen2.5-1.5B 为例：

```bash
# 安装 llama-cpp-python（无编译环境用预编译包）
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# 通过 ModelScope 下载模型
pip install modelscope
modelscope download --model Qwen/Qwen2.5-1.5B-Instruct-GGUF --include '*q4_k_m*' --local_dir ~/model
```

设置中选择"本地模型"，指定模型目录即可。首次加载约 10 秒，之后常驻内存。

## 配置

首次运行自动生成 `config.json`，也可通过系统托盘 → 设置修改。API Key 等敏感信息保存在本地，不会同步到仓库。
