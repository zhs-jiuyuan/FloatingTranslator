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

## 配置文件

首次运行时自动生成 `config.json`，也可通过设置界面修改。
