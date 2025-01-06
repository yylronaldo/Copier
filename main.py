import sys
import time
import uuid
import json
import io
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QLabel, QSystemTrayIcon, QMenu, QPushButton,
                              QHBoxLayout, QListWidget, QListWidgetItem, QSplitter,
                              QScrollArea, QTextEdit, QStackedWidget, QLineEdit,
                              QMessageBox)
from PySide6.QtCore import (Qt, QTimer, QBuffer, QByteArray, QSize, QRectF,
                           QMetaObject, Q_ARG, QSettings)
from PySide6.QtGui import (QIcon, QImage, QPixmap, QPainter, QFont, QPen, QBrush, 
                          QColor, QFontMetrics, QKeySequence, QShortcut)
import base64
import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
import pyperclip
import hashlib
from settings_dialog import SettingsDialog
from config import load_config, save_config
from data_processor import DataProcessor
import platform
import ssl
import os

class ClipboardItem:
    def __init__(self, content_type: str, content, timestamp: int):
        self.content_type = content_type  # "text" or "image"
        self.content = content
        self.timestamp = timestamp
        self.click_count = 0  # 记录点击次数
        self.last_click_time = 0  # 记录最后一次点击时间

    def increment_click_count(self):
        """增加点击次数并更新最后点击时间"""
        self.click_count += 1
        self.last_click_time = int(time.time() * 1000)

    def get_display_text(self) -> str:
        """获取显示文本，包括点击次数"""
        # 对于文本内容，限制长度为30个字符
        if self.content_type == "text":
            base_text = self.content[:30] + "..." if len(self.content) > 30 else self.content
        else:
            base_text = "[图片]"
            
        if self.click_count > 0:
            return base_text + " " + f"(+{self.click_count})"  # 不使用HTML标签
        return base_text

    def get_time_text(self) -> str:
        """获取时间显示文本"""
        display_time = self.last_click_time if self.last_click_time > 0 else self.timestamp
        return time.strftime("%H:%M:%S", time.localtime(display_time / 1000))

class MainWindow(QMainWindow):
    VERSION = "2.1.0"
    
    def __init__(self):
        super().__init__()
        print("初始化主窗口...")
        
        # 添加操作系统判断
        self.is_windows = platform.system().lower() == 'windows'
        self.is_macos = platform.system().lower() == 'darwin'
        print(f"操作系统: {'macOS' if self.is_macos else 'Windows' if self.is_windows else 'Other'}")
        
        # 初始化pasteboard为None
        self.pasteboard = None
        
        # 初始化数据处理器
        print("初始化数据处理器...")
        self.data_processor = DataProcessor()
        
        # 初始化剪贴板
        self.clipboard = QApplication.clipboard()
        
        # 初始化UI
        self.setup_ui()
        
        # 初始化剪贴板监控状态
        self.clipboard_monitoring_enabled = True  # 默认启用
        self.is_receiving_content = False
        self.last_processed_hash = None
        self.last_processed_time = 0
        self.is_processing = False
        
        # 设置快捷键
        self.setup_shortcuts()
        
        # 连接剪贴板信号
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        
        # 初始化MQTT客户端
        self.client_id = f"copier_{platform.node()}_{uuid.uuid4().hex[:8]}"
        self.mqtt_client = None
        self.mqtt_connected = False
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self.setup_mqtt)
        self.reconnect_timer.setInterval(5000)  # 5秒后重试
        
        # 设置MQTT连接
        self.setup_mqtt()
        
        # 显示窗口
        self.show()

    def enable_clipboard_monitoring(self):
        """启用剪贴板监听"""
        print("启用剪贴板监听...")
        self.clipboard_monitoring_enabled = True
        print("剪贴板监听已启用")

    def check_clipboard(self):
        """检查剪贴板变化"""
        if not self.clipboard_monitoring_enabled or self.is_receiving_content:
            return
            
        try:
            mime = self.clipboard.mimeData()
            current_hash = None
            
            if mime.hasText():
                text = mime.text()
                if text:
                    current_hash = hashlib.md5(text.encode()).hexdigest()
            elif mime.hasImage():
                image = mime.imageData()
                if image and not image.isNull():
                    # 转换为固定格式和大小的图片以确保一致性
                    scaled_image = image.scaled(800, 800, Qt.AspectRatioMode.KeepAspectRatio, 
                                             Qt.TransformationMode.SmoothTransformation)
                    buffer = QByteArray()
                    buffer_device = QBuffer(buffer)
                    buffer_device.open(QBuffer.OpenModeFlag.WriteOnly)
                    scaled_image.save(buffer_device, "PNG")
                    buffer_device.close()
                    current_hash = hashlib.md5(buffer.data()).hexdigest()
                    buffer = None  # 清理缓冲区
            
            # 如果内容有变化，处理新内容
            if current_hash and current_hash != self.last_processed_hash:
                print(f"检测到剪贴板内容变化，新哈希值: {current_hash}")
                self.last_processed_hash = current_hash
                
                if mime.hasText():
                    text = mime.text()
                    if text:
                        print(f"从剪贴板获取到文本，长度：{len(text)}")
                        self.process_text(text)
                elif mime.hasImage():
                    image = mime.imageData()
                    if image and not image.isNull():
                        print("从剪贴板获取到图片")
                        self.process_image(image)
                        
        except Exception as e:
            print(f"检查剪贴板时出错: {e}")
            import traceback
            traceback.print_exc()
            
        # 强制进行垃圾回收
        import gc
        gc.collect()
            
    def update_preview(self, content_type: str, content):
        """更新预览区域"""
        try:
            if content_type == "text":
                QMetaObject.invokeMethod(self.text_preview, "setPlainText",
                                       Qt.ConnectionType.QueuedConnection,
                                       Q_ARG(str, content))
                self.preview_stack.setCurrentIndex(1)  # 切换到文本预览
            else:  # image
                if isinstance(content, QImage):
                    pixmap = QPixmap.fromImage(content)
                else:
                    pixmap = content
                
                # 计算缩放后的尺寸，保持宽高比
                preview_size = self.image_preview.size()
                scaled_pixmap = pixmap.scaled(preview_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # 创建一个新的QPixmap作为背景
                final_pixmap = QPixmap(preview_size)
                final_pixmap.fill(Qt.transparent)
                
                # 创建QPainter在新的QPixmap上绘制
                painter = QPainter(final_pixmap)
                
                # 在中心绘制图片
                x = (preview_size.width() - scaled_pixmap.width()) // 2
                y = (preview_size.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
                
                # 获取当前项的时间文本
                current_item = self.history_list.currentItem()
                if current_item and hasattr(current_item, 'clipboard_item'):
                    time_text = current_item.clipboard_item.get_time_text()
                    
                    # 设置字体和颜色
                    font = painter.font()
                    font.setPointSize(10)
                    painter.setFont(font)
                    
                    # 计算文本大小
                    font_metrics = painter.fontMetrics()
                    text_width = font_metrics.horizontalAdvance(time_text)
                    text_height = font_metrics.height()
                    
                    # 在右下角绘制半透明背景
                    padding = 5
                    bg_rect = QRectF(
                        preview_size.width() - text_width - padding * 2,
                        preview_size.height() - text_height - padding * 2,
                        text_width + padding * 2,
                        text_height + padding * 2
                    )
                    painter.setBrush(QColor(0, 0, 0, 128))
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(bg_rect, 3, 3)
                    
                    # 绘制时间文本
                    painter.setPen(Qt.white)
                    painter.drawText(
                        preview_size.width() - text_width - padding,
                        preview_size.height() - padding - font_metrics.descent(),
                        time_text
                    )
                
                painter.end()
                
                # 设置最终的图片
                QMetaObject.invokeMethod(self.image_preview, "setPixmap",
                                       Qt.ConnectionType.QueuedConnection,
                                       Q_ARG(QPixmap, final_pixmap))
                self.preview_stack.setCurrentIndex(0)  # 切换到图片预览
                
        except Exception as e:
            print(f"更新预览时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def on_history_item_clicked(self, item):
        """处理历史记录项的单击事件"""
        if not hasattr(item, 'clipboard_item'):
            return
        
        # 更新预览
        clipboard_item = item.clipboard_item
        self.update_preview(clipboard_item.content_type, clipboard_item.content)

    def on_history_item_double_clicked(self, item):
        """处理历史记录项的双击事件"""
        if not hasattr(item, 'clipboard_item'):
            return
            
        # 暂时禁用剪贴板监听
        self.clipboard_monitoring_enabled = False
        
        try:
            clipboard_item = item.clipboard_item
            clipboard_item.increment_click_count()
            
            # 更新列表项显示文本和样式
            self.update_list_item(item)
            
            # 复制内容到剪贴板
            if clipboard_item.content_type == "text":
                self.clipboard.setText(clipboard_item.content)
            else:  # image
                self.clipboard.setImage(clipboard_item.content)
                
            # 刷新预览以更新时间戳
            self.update_preview(clipboard_item.content_type, clipboard_item.content)
            
            # 更新最后的内容哈希，防止重复添加
            _, compressed = self.data_processor.process_clipboard_data(
                clipboard_item.content_type, 
                clipboard_item.content
            )
            self.last_processed_hash = self.calculate_content_hash(
                clipboard_item.content_type, 
                compressed
            )
        finally:
            # 确保剪贴板监听最终被重新启用
            QTimer.singleShot(100, self.enable_clipboard_monitoring)

    def update_list_item(self, item):
        """更新列表项的显示"""
        if not hasattr(item, 'clipboard_item'):
            return
            
        clipboard_item = item.clipboard_item
        
        # 设置文本
        item.setText(clipboard_item.get_display_text())
        
        # 如果有点击次数，设置文本颜色为绿色，否则恢复默认颜色
        if clipboard_item.click_count > 0:
            item.setForeground(QColor("#4CAF50"))
        else:
            item.setForeground(QColor("#ffffff"))
        
        # 如果是图片，设置缩略图
        if clipboard_item.content_type == "image":
            thumb = clipboard_item.content.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item.setIcon(QIcon(QPixmap.fromImage(thumb)))

    def process_text(self, text):
        """处理文本内容"""
        try:
            # 更新预览
            self.update_preview("text", text)
            
            # 如果启用了MQTT，发送文本
            if self.mqtt_client and self.mqtt_client.is_connected():
                # 准备要发送的数据
                data = {
                    "type": "text",
                    "content": text,
                    "timestamp": int(time.time())
                }
                
                # 发送数据
                self.mqtt_client.publish(f"copier/{self.client_id}/content", 
                                      json.dumps(data))
                print("文本已发送")
            else:
                print("MQTT客户端未连接，无法发送文本")
                
            # 添加到历史记录
            self.add_to_history("text", text, int(time.time() * 1000))
            
        except Exception as e:
            print(f"处理文本时出错: {e}")
            import traceback
            traceback.print_exc()

    def process_image(self, image):
        """处理图片内容"""
        try:
            if image.isNull():
                print("图片内容为空")
                return
                
            # 转换为固定格式和大小的图片以确保一致性
            scaled_image = image.scaled(800, 800, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
            
            # 将图片转换为base64
            buffer = QByteArray()
            buffer_device = QBuffer(buffer)
            buffer_device.open(QBuffer.OpenModeFlag.WriteOnly)
            scaled_image.save(buffer_device, "PNG")
            buffer_device.close()
            
            # 更新预览
            self.update_preview("image", scaled_image)
            
            # 如果启用了MQTT，发送图片
            if self.mqtt_client and self.mqtt_client.is_connected():
                # 准备要发送的数据
                data = {
                    "type": "image",
                    "content": base64.b64encode(buffer.data()).decode(),
                    "timestamp": int(time.time())
                }
                
                # 发送数据
                self.mqtt_client.publish(f"copier/{self.client_id}/content", 
                                      json.dumps(data))
                print("图片已发送")
            else:
                print("MQTT客户端未连接，无法发送图片")
                
            # 清理资源
            buffer = None
            
            # 添加到历史记录
            self.add_to_history("image", scaled_image, int(time.time() * 1000))
            
        except Exception as e:
            print(f"处理图片时出错: {e}")
            import traceback
            traceback.print_exc()

    def on_mqtt_message(self, client, userdata, message):
        """MQTT v5 消息回调"""
        try:
            if not self.mqtt_connected:
                print("收到消息但MQTT未连接")
                return
            
            print(f"收到消息 - 主题: {message.topic}, QoS: {message.qos}")
            
            # 处理状态消息
            if message.topic.endswith('/status'):
                try:
                    status_data = json.loads(message.payload)
                    client_id = status_data.get('client_id')
                    status = status_data.get('status')
                    print(f"客户端状态更新 - ID: {client_id}, 状态: {status}")
                except:
                    pass
                return
                
            if not message.topic.endswith('/content'):
                print(f"未知的消息主题: {message.topic}")
                return
                
            try:
                # 获取消息属性
                content_type = message.properties.ContentType
                if not content_type:
                    print("消息缺少内容类型")
                    return
                    
                content_type = content_type.replace('application/x-copier-', '')
                if content_type not in ['text', 'image']:
                    print(f"不支持的内容类型: {content_type}")
                    return
                    
                # 处理消息内容
                self.process_received_data(content_type, message.payload)
                
                # 发送确认
                if message.properties.CorrelationData:
                    response_topic = f"{message.topic}/ack"
                    response_properties = mqtt.Properties(PacketTypes.PUBLISH)
                    response_properties.CorrelationData = message.properties.CorrelationData
                    self.mqtt_client.publish(
                        response_topic,
                        "ok",
                        qos=1,
                        properties=response_properties
                    )
                
            except Exception as e:
                print(f"处理消息内容时出错: {str(e)}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"MQTT消息回调出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def process_received_data(self, content_type: str, content: bytes):
        """处理接收到的数据"""
        try:
            if content_type == "text":
                self.process_received_text(content)
            elif content_type == "image":
                self.process_received_image(content)
        except Exception as e:
            print(f"处理数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def process_received_image(self, content):
        """处理接收到的图片内容"""
        try:
            # 标记正在接收内容
            self.is_receiving_content = True
            
            # 计算内容哈希，避免重复处理
            content_hash = self.calculate_content_hash("image", content)
            if content_hash in self.received_hashes or content_hash in self.sent_hashes:
                print(f"忽略重复的图片内容，哈希值: {content_hash}")
                return
                
            print(f"接收新的图片内容，哈希值: {content_hash}")
            
            # 还原内容
            image_content = self.data_processor.restore_clipboard_data("image", content)
            if not image_content:
                print("还原图片内容失败")
                return
                
            print(f"还原后的图片大小: {image_content.size()}")
            
            # 计算还原后图片的哈希值
            buffer = QByteArray()
            buffer_device = QBuffer(buffer)
            buffer_device.open(QBuffer.OpenModeFlag.WriteOnly)
            image_content.save(buffer_device, "PNG", 100)  # 使用最高质量保存
            buffer_device.close()
            restored_hash = self.calculate_content_hash("image", buffer.data())
            
            self.received_hashes.add(content_hash)
            self.received_hashes.add(restored_hash)
            self.sent_hashes.add(content_hash)
            self.sent_hashes.add(restored_hash)
            
            # 更新预览和历史
            self.update_preview("image", image_content)
            self.add_to_history("image", image_content, int(time.time() * 1000))
            
            # 更新剪贴板
            print("更新剪贴板图片内容")
            self.clipboard.setImage(image_content)
            
        except Exception as e:
            print(f"处理图片内容时出错: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 确保标志被重置
            self.is_receiving_content = False
            
    def process_received_text(self, content):
        """处理接收到的文本内容"""
        try:
            # 标记正在接收内容
            self.is_receiving_content = True
            
            # 计算内容哈希，避免重复处理
            content_hash = self.calculate_content_hash("text", content)
            if content_hash in self.received_hashes or content_hash in self.sent_hashes:
                print(f"忽略重复的文本内容，哈希值: {content_hash}")
                return
                
            print(f"接收新的文本内容，哈希值: {content_hash}")
            
            # 还原内容
            text_content = self.data_processor.restore_clipboard_data("text", content)
            if not text_content:
                print("还原文本内容失败")
                return
                
            print(f"还原后的文本长度: {len(text_content)}")
            
            # 计算还原后文本的哈希值
            restored_hash = self.calculate_content_hash("text", text_content.encode('utf-8'))
            
            self.received_hashes.add(content_hash)
            self.received_hashes.add(restored_hash)
            self.sent_hashes.add(content_hash)
            self.sent_hashes.add(restored_hash)
            
            # 更新预览和历史
            self.update_preview("text", text_content)
            self.add_to_history("text", text_content, int(time.time() * 1000))
            
            # 更新剪贴板
            print("更新剪贴板文本内容")
            self.clipboard.setText(text_content)
            
        except Exception as e:
            print(f"处理文本内容时出错: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 确保标志被重置
            self.is_receiving_content = False
            
    def on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        self.mqtt_connected = False
        print(f"MQTT断开连接，返回码: {rc}")
        if rc != 0:
            print("意外断开连接，启动重连定时器")
            QMetaObject.invokeMethod(self.reconnect_timer, "start", Qt.QueuedConnection)
            
    def on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        """MQTT消息发布回调"""
        try:
            status = "成功" if reason_code is None or not reason_code.is_failure else f"失败({reason_code.getName()})"
            print(f"消息已发布，消息ID: {mid}, 状态: {status}")
        except Exception as e:
            print(f"处理发布回调时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def calculate_content_hash(self, content_type: str, content) -> str:
        """计算内容的哈希值"""
        try:
            if content_type == "image" and isinstance(content, QImage):
                # 将 QImage 转换为字节数组
                buffer = QByteArray()
                buffer_device = QBuffer(buffer)
                buffer_device.open(QBuffer.OpenModeFlag.WriteOnly)
                content.save(buffer_device, "PNG")
                buffer_device.close()
                content_bytes = buffer.data()
            elif content_type == "image" and isinstance(content, bytes):
                content_bytes = content
            else:
                content_bytes = content if isinstance(content, bytes) else str(content).encode('utf-8')
                
            return hashlib.sha256(content_bytes).hexdigest()
        except Exception as e:
            print(f"计算哈希值时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return str(time.time())  # 如果计算失败，返回时间戳作为备用

    def send_clipboard_content(self, content_type: str, compressed_content: bytes):
        """发送剪贴板内容到MQTT服务器"""
        if not self.mqtt_client or not self.mqtt_connected:
            print("MQTT未连接，无法发送消息")
            return
            
        try:
            config = load_config()
            topic_prefix = config.get('mqtt', {}).get('topic_prefix', 'copier/clipboard')
            
            # 创建消息属性
            properties = mqtt.Properties(PacketTypes.PUBLISH)
            properties.MessageExpiryInterval = 3600  # 消息1小时后过期
            properties.ContentType = f"application/x-copier-{content_type}"
            properties.PayloadFormatIndicator = 1  # 表示是应用程序定义的数据
            
            # 计算消息ID
            message_id = str(uuid.uuid4())
            properties.CorrelationData = message_id.encode()
            
            # 发布消息，使用QoS 2确保只传递一次
            info = self.mqtt_client.publish(
                f"{topic_prefix}/content",
                compressed_content,
                qos=2,  # 使用QoS 2
                retain=False,
                properties=properties
            )
            
            # 等待消息发送完成
            info.wait_for_publish()
            
            print(f"消息已发送 - ID: {message_id}, mid: {info.mid}")
            
        except Exception as e:
            print(f"发送消息时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # 创建一个图标
        icon = QIcon.fromTheme("edit-copy")  # 使用系统图标
        if icon.isNull():
            # 如果系统图标不可用，创建一个空白图标
            icon = QIcon()
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Copier - 剪贴板同步工具")
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 添加显示/隐藏动作
        toggle_action = tray_menu.addAction("显示/隐藏")
        toggle_action.triggered.connect(self.toggle_window)
        
        tray_menu.addSeparator()
        
        # 添加退出动作
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self.cleanup_and_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # 添加托盘图标双击事件
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def toggle_window(self):
        """切换窗口显示/隐藏状态"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()  # 激活窗口
            self.raise_()  # 将窗口置于最前

    def on_tray_icon_activated(self, reason):
        """处理托盘图标的激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()

    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == SettingsDialog.Accepted:
            self.setup_mqtt()  # 重新连接MQTT服务器

    def cleanup_and_quit(self):
        """清理并退出程序"""
        print("开始清理资源...")
        try:
            # 停止所有定时器
            if hasattr(self, 'clipboard_timer'):
                self.clipboard_timer.stop()
            if hasattr(self, 'reconnect_timer'):
                self.reconnect_timer.stop()
            
            # 断开MQTT连接
            if hasattr(self, 'mqtt_client') and self.mqtt_client:
                try:
                    print("断开MQTT连接...")
                    if self.mqtt_client.is_connected():
                        self.publish_status("offline")
                        self.mqtt_client.disconnect()
                    self.mqtt_client.loop_stop()
                except Exception as e:
                    print(f"断开MQTT连接时出错: {str(e)}")
            
            # 保存窗口状态
            try:
                print("保存窗口状态...")
                settings = QSettings('Copier', 'Copier')
                settings.setValue('geometry', self.saveGeometry())
                settings.setValue('windowState', self.saveState())
            except Exception as e:
                print(f"保存窗口状态时出错: {str(e)}")
            
            # 清理系统托盘
            if hasattr(self, 'tray_icon'):
                print("清理系统托盘...")
                self.tray_icon.hide()
                self.tray_icon.deleteLater()
            
            print("清理完成，准备退出...")
            # 使用 singleShot 确保在主线程中退出
            QTimer.singleShot(0, lambda: (
                QApplication.instance().quit()
            ))
        except Exception as e:
            print(f"清理资源时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            # 如果清理失败，强制退出
            QApplication.instance().quit()

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            # 如果托盘图标可见，则隐藏窗口而不是退出
            event.ignore()
            self.hide()
            return
            
        # 如果没有托盘图标，则执行正常的退出流程
        self.cleanup_and_quit()
        event.accept()
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+F 聚焦搜索框
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.focus_search)
        
        # Ctrl+L 清空搜索框
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self.clear_search)
        
        # Ctrl+R 刷新列表
        refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_shortcut.activated.connect(self.refresh_history)
        
        # Esc 隐藏窗口
        hide_shortcut = QShortcut(QKeySequence("Esc"), self)
        hide_shortcut.activated.connect(self.hide)
        
        # Ctrl+Q 退出程序
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.cleanup_and_quit)

    def focus_search(self):
        """聚焦搜索框"""
        self.search_box.setFocus()
        self.search_box.selectAll()

    def clear_search(self):
        """清空搜索框"""
        self.search_box.clear()

    def refresh_history(self):
        """刷新历史记录列表"""
        current_text = self.search_box.text()
        self.filter_history(current_text)

    def filter_history(self, text):
        """根据搜索文本过滤历史记录"""
        text = text.lower()
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            if not hasattr(item, 'clipboard_item'):
                continue
                
            clipboard_item = item.clipboard_item
            if clipboard_item.content_type == "text":
                content = clipboard_item.content.lower()
                item.setHidden(text not in content)
            else:  # image
                item.setHidden(bool(text) and text != "图片")

    def add_to_history(self, content_type: str, content, timestamp: int):
        """添加内容到历史记录"""
        # 创建新的历史记录项
        clipboard_item = ClipboardItem(content_type, content, timestamp)
        list_item = QListWidgetItem()
        list_item.clipboard_item = clipboard_item
        
        # 设置文本和样式
        self.update_list_item(list_item)
        
        # 将新项添加到列表开头
        self.history_list.insertItem(0, list_item)
        
        # 如果超过最大历史记录数，删除最后一项
        while self.history_list.count() > 50:
            self.history_list.takeItem(self.history_list.count() - 1)

    def setup_mqtt(self):
        """设置MQTT客户端"""
        try:
            if self.mqtt_client:
                try:
                    self.mqtt_client.disconnect()
                except:
                    pass
                    
            # 加载配置
            config = load_config()
            mqtt_config = config.get('mqtt', {})
            
            # 创建新的客户端实例
            client_id = f"copier_{platform.node()}_{uuid.uuid4().hex[:8]}"
            self.mqtt_client = mqtt.Client(
                client_id=client_id,
                protocol=mqtt.MQTTv5,
                transport="tcp",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
            
            # 设置回调
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_disconnect = self.on_disconnect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_publish = self.on_publish
            
            # 设置客户端选项
            self.mqtt_client.enable_logger()
            
            try:
                # 设置连接属性
                connect_properties = mqtt.Properties(mqtt.PacketTypes.CONNECT)
                connect_properties.SessionExpiryInterval = 0  # 会话在断开连接时立即过期
                
                # 设置遗嘱消息
                will_properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
                will_properties.MessageExpiryInterval = 3600  # 1小时后过期
                will_properties.ContentType = "application/json"
                
                will_payload = json.dumps({
                    "client_id": client_id,
                    "status": "offline",
                    "timestamp": int(time.time())
                }).encode()
                
                self.mqtt_client.will_set(
                    topic=f"{mqtt_config.get('topic_prefix', 'copier/clipboard')}/status",
                    payload=will_payload,
                    qos=1,
                    retain=True,
                    properties=will_properties
                )
                
                # 设置TLS（如果配置了）
                if mqtt_config.get('use_tls', False):
                    # 设置TLS上下文
                    context = ssl.create_default_context()
                    
                    # 如果提供了CA证书，加载它
                    ca_certs = mqtt_config.get('ca_certs')
                    if ca_certs and os.path.exists(ca_certs):
                        context.load_verify_locations(ca_certs)
                    
                    # 如果提供了客户端证书和密钥，加载它们
                    certfile = mqtt_config.get('certfile')
                    keyfile = mqtt_config.get('keyfile')
                    if certfile and keyfile and os.path.exists(certfile) and os.path.exists(keyfile):
                        context.load_cert_chain(certfile, keyfile)
                    
                    self.mqtt_client.tls_set_context(context)
                    
                    # 如果不验证服务器证书
                    if not mqtt_config.get('verify_cert', True):
                        self.mqtt_client.tls_insecure_set(True)
                
                # 设置用户名和密码（如果配置了）
                username = mqtt_config.get('username')
                password = mqtt_config.get('password')
                if username:
                    self.mqtt_client.username_pw_set(username, password)
                
                # 连接到服务器
                host = mqtt_config.get('host', 'localhost')
                port = mqtt_config.get('port', 1883)
                keepalive = mqtt_config.get('keepalive', 60)
                
                print(f"正在连接到MQTT服务器 {host}:{port}")
                self.mqtt_client.connect(
                    host=host,
                    port=port,
                    keepalive=keepalive,
                    properties=connect_properties
                )
                
                # 启动网络循环
                self.mqtt_client.loop_start()
                
            except Exception as e:
                print(f"连接MQTT服务器时出错: {str(e)}")
                import traceback
                traceback.print_exc()
                self.reconnect_timer.start()
                
        except Exception as e:
            print(f"设置MQTT时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """MQTT v5 连接回调"""
        try:
            if reason_code.is_failure:
                print(f"MQTT连接失败，原因: {reason_code.getName()}")
                self.mqtt_connected = False
                self.status_label.setText(f"连接失败: {reason_code.getName()}")
                QMetaObject.invokeMethod(self.reconnect_timer, "start", Qt.QueuedConnection)
                return
                
            print(f"MQTT连接成功，返回码: {reason_code.value}")
            self.mqtt_connected = True
            self.status_label.setText("已连接")
            QMetaObject.invokeMethod(self.reconnect_timer, "stop", Qt.QueuedConnection)
            
            # 订阅主题
            config = load_config()
            topic_prefix = config.get('mqtt', {}).get('topic_prefix', 'copier/clipboard')
            topics = [
                (f"{topic_prefix}/+/content", 2),  # QoS 2，接收所有客户端的内容
                (f"{topic_prefix}/+/status", 1)    # QoS 1，接收所有客户端的状态
            ]
            
            # 订阅主题
            for topic, qos in topics:
                print(f"订阅主题: {topic}, QoS: {qos}")
                subscribe_properties = mqtt.Properties(mqtt.PacketTypes.SUBSCRIBE)
                subscribe_properties.SubscriptionIdentifier = 1
                self.mqtt_client.subscribe(topic, qos=qos, properties=subscribe_properties)
                
            # 发布上线状态
            status_payload = json.dumps({
                "client_id": self.client_id,
                "status": "online",
                "timestamp": int(time.time())
            }).encode()
            
            status_properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
            status_properties.MessageExpiryInterval = 3600  # 1小时后过期
            status_properties.ContentType = "application/json"
            
            self.mqtt_client.publish(
                topic=f"{topic_prefix}/status",
                payload=status_payload,
                qos=1,
                retain=True,
                properties=status_properties
            )
            
        except Exception as e:
            print(f"处理连接回调时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            self.mqtt_connected = False
            self.status_label.setText(f"连接错误: {str(e)}")
            QMetaObject.invokeMethod(self.reconnect_timer, "start", Qt.QueuedConnection)
            
    def publish_status(self, status):
        """发布客户端状态到MQTT服务器"""
        if not self.mqtt_client or not self.mqtt_connected:
            print(f"MQTT未连接，无法发布状态: {status}")
            return
            
        try:
            config = load_config()
            topic_prefix = config.get('mqtt', {}).get('topic_prefix', 'copier/clipboard')
            topic = f"{topic_prefix}/status"
            
            payload = {
                "client_id": self.client_id,
                "status": status,
                "timestamp": int(time.time() * 1000)
            }
            
            print(f"正在发布状态: {status}")
            result = self.mqtt_client.publish(topic, json.dumps(payload), qos=1, retain=True)
            print(f"状态发布结果: {result}")
            
        except Exception as e:
            print(f"发布状态时出错: {str(e)}")

    def setup_ui(self):
        self.setWindowTitle(f"Copier v{self.VERSION}")
        self.setMinimumSize(800, 600)
        
        # 设置应用程序样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                color: #ffffff;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #454545;
            }
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3b3b3b;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QSplitter::handle {
                background-color: #555555;
            }
        """)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧面板（历史列表）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 历史列表标题和搜索框
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        history_label = QLabel("剪贴板历史")
        history_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            padding: 5px;
            color: #ffffff;
        """)
        header_layout.addWidget(history_label)
        
        # 添加搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索历史记录...")
        self.search_box.textChanged.connect(self.filter_history)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #666666;
            }
        """)
        header_layout.addWidget(self.search_box)
        left_layout.addWidget(header_widget)
        
        # 历史列表
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.on_history_item_clicked)
        self.history_list.itemDoubleClicked.connect(self.on_history_item_double_clicked)
        left_layout.addWidget(self.history_list)
        
        # 创建右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 状态和设置面板
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        # 状态标签
        self.status_label = QLabel("未连接到MQTT服务器")
        self.status_label.setStyleSheet("color: #ffffff;")
        top_layout.addWidget(self.status_label)
        
        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setFixedWidth(100)
        top_layout.addWidget(settings_btn)
        
        right_layout.addWidget(top_panel)
        
        # 预览区域标题
        preview_label = QLabel("当前内容预览")
        preview_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            padding: 5px;
            color: #ffffff;
        """)
        right_layout.addWidget(preview_label)
        
        # 创建堆叠窗口部件用于切换不同类型的预览
        self.preview_stack = QStackedWidget()
        
        # 创建图片预览标签
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumSize(400, 300)
        self.image_preview.setStyleSheet("""
            background-color: #1e1e1e;
            border: 1px solid #555555;
            color: #888888;
            border-radius: 4px;
        """)
        
        # 创建文本预览编辑框
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setMinimumSize(400, 300)
        self.text_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #555555;
                color: #ffffff;
                font-family: "Menlo", monospace;
                font-size: 13px;
                padding: 10px;
                border-radius: 4px;
            }
            QTextEdit:focus {
                border: 1px solid #666666;
            }
        """)
        self.text_preview.setPlaceholderText("暂无预览内容")
        
        # 将两种预览部件添加到堆叠窗口
        self.preview_stack.addWidget(self.image_preview)  # index 0
        self.preview_stack.addWidget(self.text_preview)   # index 1
        
        right_layout.addWidget(self.preview_stack)
        
        # 添加分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)  # 左侧面板
        splitter.setStretchFactor(1, 2)  # 右侧面板
        
        main_layout.addWidget(splitter)
        
        # 初始化系统托盘
        self.setup_tray()

    def on_clipboard_change(self):
        """剪贴板内容变化回调"""
        if not self.clipboard_monitoring_enabled or self.is_receiving_content or self.is_processing:
            return
            
        try:
            self.is_processing = True
            current_time = time.time()
            
            # 检查处理间隔
            if current_time - self.last_processed_time < 2:  # 至少2秒间隔
                print("处理间隔太短，跳过")
                return
                
            mime = self.clipboard.mimeData()
            current_hash = None
            
            if mime.hasImage():
                image = mime.imageData()
                if image and not image.isNull():
                    # 转换为固定格式和大小的图片以确保一致性
                    scaled_image = image.scaled(800, 800, Qt.AspectRatioMode.KeepAspectRatio, 
                                             Qt.TransformationMode.SmoothTransformation)
                    buffer = QByteArray()
                    buffer_device = QBuffer(buffer)
                    buffer_device.open(QBuffer.OpenModeFlag.WriteOnly)
                    scaled_image.save(buffer_device, "PNG")
                    buffer_device.close()
                    current_hash = hashlib.md5(buffer.data()).hexdigest()
                    buffer = None  # 清理缓冲区
            
            if mime.hasText():
                text = mime.text()
                if text:
                    current_hash = hashlib.md5(text.encode()).hexdigest()
            elif mime.hasUrls():
                for url in mime.urls():
                    file_path = url.toLocalFile()
                    if file_path and any(file_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']):
                        try:
                            image = QImage(file_path)
                            if not image.isNull():
                                # 转换为固定格式和大小的图片以确保一致性
                                scaled_image = image.scaled(800, 800, Qt.AspectRatioMode.KeepAspectRatio, 
                                                         Qt.TransformationMode.SmoothTransformation)
                                buffer = QByteArray()
                                buffer_device = QBuffer(buffer)
                                buffer_device.open(QBuffer.OpenModeFlag.WriteOnly)
                                scaled_image.save(buffer_device, "PNG")
                                buffer_device.close()
                                current_hash = hashlib.md5(buffer.data()).hexdigest()
                                buffer = None  # 清理缓冲区
                        except Exception as e:
                            print(f"处理图片文件时出错: {str(e)}")
            
            # 如果内容有变化，处理新内容
            if current_hash and current_hash != self.last_processed_hash:
                print(f"检测到剪贴板内容变化，新哈希值: {current_hash}")
                self.last_processed_hash = current_hash
                
                if mime.hasImage():
                    image = mime.imageData()
                    if image and not image.isNull():
                        print("从剪贴板获取到新图片")
                        self.last_processed_time = current_time
                        self.process_image(image)
                elif mime.hasText():
                    text = mime.text()
                    if text:
                        print(f"从剪贴板获取到文本，长度：{len(text)}")
                        self.last_processed_time = current_time
                        self.process_text(text)
                elif mime.hasUrls():
                    for url in mime.urls():
                        file_path = url.toLocalFile()
                        if file_path and any(file_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']):
                            try:
                                image = QImage(file_path)
                                if not image.isNull():
                                    print(f"从文件加载图片: {file_path}")
                                    self.last_processed_time = current_time
                                    self.process_image(image)
                            except Exception as e:
                                print(f"处理图片文件时出错: {str(e)}")
            
        except Exception as e:
            print(f"处理剪贴板变化时出错: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            self.is_processing = False
            
        # 强制进行垃圾回收
        import gc
        gc.collect()
        
    def on_polling_timer(self):
        """轮询定时器回调"""
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
