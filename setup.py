from setuptools import setup

APP = ['main.py']
DATA_FILES = ['Info.plist']
OPTIONS = {
    'argv_emulation': True,
    'plist': 'Info.plist',
    'packages': ['PySide6', 'paho-mqtt'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
