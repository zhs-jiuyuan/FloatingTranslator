# FloatingTranslator

桌面划词翻译器 — 选中文本 → 悬浮翻译窗

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动
python main.py
```

## 使用方式

1. 用鼠标选中任意文本
2. 翻译结果在鼠标位置自动弹出

## 系统要求

- Python 3.10+
- **Linux**: 需要 X11 环境（依赖 `xclip` 读取选区，Wayland 下部分功能受限）

## 功能

- 多引擎支持：免费 MyMemory / LLM API / 本地模型
- 语言自动检测与反向翻译
- 悬浮窗自动隐藏、智能避让屏幕边界
- 系统托盘最小化

## 本地模型（llama.cpp + GGUF）

> 临时记录，README 待程序完成后重写。

本地翻译引擎基于 `llama-cpp-python` 加载 GGUF 格式模型。

**1. 安装 llama-cpp-python**

PyPI 只提供源码包，直接 `pip install llama-cpp-python` 需要本机有 gcc/cmake 编译工具，
没有编译环境的机器请使用官方预编译包：

```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

**2. 下载 GGUF 模型（通过 ModelScope，国内直连）**

```bash
pip install modelscope
modelscope download --model Qwen/Qwen2.5-1.5B-Instruct-GGUF --include '*q4_k_m*' --local_dir ~/model
```

注意必须下载 **GGUF 后缀仓库**的量化文件，safetensors 格式无法加载。
模型大小参考：1.5B-q4_k_m 约 1.1GB（运行需 2GB 以上可用内存）。

**3. 配置**

设置界面选择"本地模型 (llama.cpp)"，"模型目录"填 GGUF 所在目录（默认 `~/model`），
在"选择模型"下拉框中选取要用的模型文件。
首次翻译会加载模型（约 10 秒），之后常驻内存无需重复加载。

## 配置文件

首次运行时自动生成 `config.json`，也可通过设置界面修改。
