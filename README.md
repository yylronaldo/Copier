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
- 跨平台支持：支持 Windows 和 macOS

## 系统要求

- Windows 10/11 或 macOS 10.15+
- Python 3.8+
- 网络连接
- MQTT 服务器（可以使用公共服务器或自建服务器）

## 依赖要求

- PySide6 >= 6.5.0
- paho-mqtt >= 2.0.0（使用 MQTT v5 协议）
- pyperclip >= 1.8.2
- protobuf >= 4.21.0
- Pillow >= 9.0.0
- zstandard >= 0.21.0

## 快速开始

1. 克隆仓库：
   ```bash
   git clone https://github.com/yylronaldo/Copier.git
   cd Copier
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 运行程序：
   ```bash
   python main.py
   ```

4. 首次运行时会自动创建配置文件

5. 点击设置按钮，配置 MQTT 服务器信息：
   - 服务器地址
   - 端口
   - 用户名和密码（如果需要）
   - 主题前缀（用于区分不同的同步组）

6. 完成配置后，程序会自动连接到 MQTT 服务器

## 使用说明

### 基本操作
- 复制内容：正常使用系统复制功能（Ctrl+C 或 Command+C）
- 查看历史：主窗口显示最近的剪贴板内容
- 搜索历史：使用搜索框筛选历史记录
- 恢复内容：点击历史记录中的项目
- 最小化：点击最小化按钮或关闭窗口（程序会继续在后台运行）
- 退出程序：右键系统托盘图标，选择"退出"

### 设置选项
- MQTT 服务器配置
- 历史记录数量限制（默认 50 条）
- 自动重连设置

### 系统特定功能
- Windows：
  - 更长的 MQTT 保活时间（120秒）
  - 更长的重连间隔（10秒）
  - 优化的图片压缩参数
- macOS：
  - 标准的 MQTT 保活时间（60秒）
  - 标准的重连间隔（5秒）
  - 标准的图片压缩参数

## 开发说明

### 环境配置
1. 确保安装了 Python 3.8 或更高版本
2. 安装所有依赖：`pip install -r requirements.txt`
3. 如果在 macOS 上遇到证书问题，需要安装 Python 的证书：
   ```bash
   /Applications/Python\ 3.x/Install\ Certificates.command
   ```

### 构建说明
使用 PyInstaller 构建可执行文件：
```bash
pyinstaller copier.spec
```

### Windows 开发说明

#### 构建 Windows 应用程序

1. 生成图标：
```bash
python create_icon.py
```

2. 安装 PyInstaller：
```bash
pip install pyinstaller
```

3. 使用专用的 Windows spec 文件构建应用程序：
```bash
python -m PyInstaller copier.windows.spec
```

构建完成后，可执行文件会在 `dist` 目录中生成。双击 `Copier.exe` 即可运行程序。

### macOS 开发说明

#### 解决 pip 证书问题

如果在使用 pip 时遇到证书问题，可以通过以下步骤解决：

1. 创建 pip 配置目录：
```bash
mkdir -p ~/Library/Application\ Support/pip
```

2. 创建 pip.conf 文件并添加以下内容：
```ini
[global]
trusted-host = pypi.org
               files.pythonhosted.org
               pypi.python.org
```

3. 将配置文件复制到正确位置：
```bash
cp pip.conf ~/Library/Application\ Support/pip/
```

#### 构建 macOS 应用

1. 安装 py2app：
```bash
pip install py2app
```

2. 构建应用程序：
```bash
python setup.py py2app
```

构建完成后，应用程序会在 `dist` 目录中生成。首次运行时会请求辅助功能权限，授权后即可在后台监控剪贴板变化。

## 更新日志

### v2.1.0 (2025-01-04)
- 升级到 MQTT v5 协议
- 改进 Windows 和 macOS 的兼容性
- 优化网络连接的稳定性
- 改进错误处理和日志记录
- 修复线程安全问题
- 优化剪贴板监听逻辑
- 添加自定义应用图标

## 许可证

MIT License
