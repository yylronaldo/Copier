# Copier - 跨设备剪贴板同步工具

Copier 是一个基于 MQTT 的跨设备剪贴板同步工具，支持文本和图片的实时同步。

## 功能特点

- 实时同步：快速同步多台设备间的剪贴板内容
- 多格式支持：支持文本和图片格式
- 历史记录：保存剪贴板历史，方便查看和恢复
- 智能预览：直观显示剪贴板内容
- 系统托盘：最小化到系统托盘，不影响日常使用
- 自动重连：网络断开时自动重连
- 图片优化：自动压缩图片，节省带宽

## 系统要求

- Windows 10/11
- 网络连接
- MQTT 服务器（可以使用公共服务器或自建服务器）

## 快速开始

1. 下载最新的 [Copier.exe](https://github.com/your-username/copier/releases)
2. 运行程序，首次运行时会自动创建配置文件
3. 点击设置按钮，配置 MQTT 服务器信息：
   - 服务器地址
   - 端口
   - 用户名和密码（如果需要）
   - 主题前缀（用于区分不同的同步组）
4. 完成配置后，程序会自动连接到 MQTT 服务器
5. 复制任何内容，它们会自动同步到其他设备

## 使用说明

### 基本操作
- 复制内容：正常使用系统复制功能（Ctrl+C）
- 查看历史：主窗口显示最近的剪贴板内容
- 恢复内容：点击历史记录中的项目
- 暂停同步：点击暂停按钮
- 最小化：点击最小化按钮或关闭窗口（程序会继续在后台运行）
- 退出程序：右键系统托盘图标，选择"退出"

### 设置选项
- MQTT 服务器配置
- 历史记录数量限制
- 图片压缩质量
- 自动启动选项

## 开发说明

### 环境配置
```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 构建可执行文件
```bash
# 安装 PyInstaller
pip install pyinstaller

# 构建
python -m PyInstaller copier.spec
```

### 主要依赖
- PySide6：GUI 框架
- Paho-MQTT：MQTT 客户端
- Pillow：图片处理

## 更新日志

### v1.0.0 (2025-01-03)
- 优化性能和资源占用
- 改进窗口关闭逻辑
- 更新 MQTT 客户端到 v5
- 添加自定义应用图标
- 修复多个稳定性问题

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
