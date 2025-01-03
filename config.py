import json
import os

# 获取用户主目录
HOME_DIR = os.path.expanduser('~')
# 在用户主目录下创建 .copier 目录
CONFIG_DIR = os.path.join(HOME_DIR, '.copier')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

DEFAULT_CONFIG = {
    "mqtt": {
        "host": "localhost",
        "port": 1883,
        "username": "",
        "password": "",
        "topic_prefix": "copier/clipboard"
    }
}

def load_config():
    # 确保配置目录存在
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR)
        except Exception as e:
            print(f"无法创建配置目录: {e}")
            return DEFAULT_CONFIG

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"无法读取配置文件: {e}")
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    # 确保配置目录存在
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR)
        except Exception as e:
            print(f"无法创建配置目录: {e}")
            return

    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"无法保存配置文件: {e}")
