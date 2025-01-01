from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QFormLayout, QSpinBox)
from PySide6.QtCore import Qt
import json
from config import load_config, save_config

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MQTT设置")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 创建表单布局
        form_layout = QFormLayout()

        # MQTT服务器设置
        self.host_input = QLineEdit()
        form_layout.addRow("服务器地址:", self.host_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(1883)
        form_layout.addRow("端口:", self.port_input)

        self.username_input = QLineEdit()
        form_layout.addRow("用户名:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密码:", self.password_input)

        self.topic_prefix_input = QLineEdit()
        form_layout.addRow("主题前缀:", self.topic_prefix_input)

        layout.addLayout(form_layout)

        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)

        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_button)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def load_settings(self):
        config = load_config()
        mqtt_config = config.get('mqtt', {})
        
        self.host_input.setText(mqtt_config.get('host', 'localhost'))
        self.port_input.setValue(mqtt_config.get('port', 1883))
        self.username_input.setText(mqtt_config.get('username', ''))
        self.password_input.setText(mqtt_config.get('password', ''))
        self.topic_prefix_input.setText(mqtt_config.get('topic_prefix', 'copier/clipboard'))

    def save_settings(self):
        config = {
            'mqtt': {
                'host': self.host_input.text(),
                'port': self.port_input.value(),
                'username': self.username_input.text(),
                'password': self.password_input.text(),
                'topic_prefix': self.topic_prefix_input.text()
            }
        }
        
        try:
            save_config(config)
            self.status_label.setStyleSheet("color: green;")
            self.status_label.setText("设置已保存")
            self.accept()
        except Exception as e:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText(f"保存失败: {str(e)}")

    def test_connection(self):
        import paho.mqtt.client as mqtt
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.status_label.setStyleSheet("color: green;")
                self.status_label.setText("连接测试成功！")
            else:
                self.status_label.setStyleSheet("color: red;")
                self.status_label.setText(f"连接失败，错误码：{rc}")
            client.disconnect()

        try:
            client = mqtt.Client()
            if self.username_input.text():
                client.username_pw_set(self.username_input.text(), 
                                     self.password_input.text())
            
            client.on_connect = on_connect
            client.connect(self.host_input.text(), self.port_input.value(), 5)
            client.loop_start()
            
            self.status_label.setText("正在测试连接...")
            
        except Exception as e:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText(f"连接错误: {str(e)}")
