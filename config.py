import sys
import os

# 输出目录
OUTPUT_DIR = "output"

# 临时文件目录（用于存储上传的文件）
INTERMEDIATE_DIR = ".intermediate"

# Poppler 路径
if sys.platform.startswith('win'):
    POPPLER_PATH = os.path.join("poppler", "poppler-24.07.0", "Library", "bin")
    # 默认poppler路径是当前目录
elif sys.platform == 'darwin':  # macOS
    # macOS 上通过 Homebrew 安装的 poppler 通常在这个路径
    POPPLER_PATH = "/opt/homebrew/bin"
else:
    POPPLER_PATH = "/usr/bin"  # Linux 默认路径

# LibreOffice 路径
if sys.platform.startswith('win'):
    LIBREOFFICE_PATH = os.path.join('.', 'libreoffice', 'App', 'libreoffice', 'program', 'soffice.exe')
    # 默认libreoffice路径是当前目录
elif sys.platform == 'darwin':  # macOS
    # macOS 上 LibreOffice 通常安装在 Applications 文件夹
    if os.path.exists('/Applications/LibreOffice.app/Contents/MacOS/soffice'):
        LIBREOFFICE_PATH = '/Applications/LibreOffice.app/Contents/MacOS/soffice'
    else:
        # 如果未安装，设置为 None 或提示用户安装
        LIBREOFFICE_PATH = None
else:
    LIBREOFFICE_PATH = "/usr/bin/libreoffice"  # Linux 默认路径