import platform
import zstandard
from PIL import Image
import io
import base64
from PySide6.QtGui import QImage
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
import time

class DataProcessor:
    def __init__(self):
        self.compressor = zstandard.ZstdCompressor(level=3)  # 压缩级别1-22，数字越大压缩率越高但速度越慢
        self.decompressor = zstandard.ZstdDecompressor()
        self.is_windows = platform.system().lower() == 'windows'
        
    def compress_data(self, data: bytes) -> bytes:
        """压缩二进制数据"""
        return self.compressor.compress(data)
        
    def decompress_data(self, compressed_data: bytes) -> bytes:
        """解压缩二进制数据"""
        return self.decompressor.decompress(compressed_data)
    
    def optimize_image(self, qimage: QImage) -> bytes:
        """优化并压缩图片"""
        # 将QImage转换为bytes
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)  # 修复：使用正确的枚举值
        qimage.save(buffer, "PNG")
        buffer.close()
        
        # 使用PIL进行图片优化
        img_data = byte_array.data()
        pil_image = Image.open(io.BytesIO(img_data))
        
        # 转换为RGB模式（如果是RGBA，移除透明通道）
        if pil_image.mode == 'RGBA':
            background = Image.new('RGB', pil_image.size, (255, 255, 255))
            background.paste(pil_image, mask=pil_image.split()[3])
            pil_image = background
        
        # 根据操作系统调整优化参数
        if self.is_windows:
            max_size = 1600  # Windows下使用较小的最大尺寸
            quality = 70     # 降低图片质量以提高性能
        else:
            max_size = 1920  # macOS下保持原有设置
            quality = 80
        
        # 优化图片大小
        if max(pil_image.size) > max_size:
            ratio = max_size / max(pil_image.size)
            new_size = tuple(int(dim * ratio) for dim in pil_image.size)
            pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
        
        # 保存为WebP格式
        output = io.BytesIO()
        pil_image.save(output, format='WebP', quality=quality, optimize=True)
        return output.getvalue()
    
    def restore_image(self, image_data: bytes) -> QImage:
        """从优化的图片数据恢复QImage"""
        pil_image = Image.open(io.BytesIO(image_data))
        
        # 将PIL Image转换回QImage
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        qimage = QImage()
        qimage.loadFromData(buffer.getvalue())
        return qimage

    def process_clipboard_data(self, content_type: str, content: str | QImage) -> tuple[str, bytes]:
        """处理剪贴板数据，返回(类型, 压缩后的二进制数据)"""
        if content_type == "text":
            text_bytes = content.encode('utf-8')
            compressed = self.compress_data(text_bytes)
            return "text", compressed
        else:  # image
            optimized = self.optimize_image(content)
            compressed = self.compress_data(optimized)
            return "image", compressed
    
    def restore_clipboard_data(self, content_type: str, compressed_data: bytes) -> str | QImage:
        """还原剪贴板数据"""
        decompressed = self.decompress_data(compressed_data)
        if content_type == "text":
            return decompressed.decode('utf-8')
        else:  # image
            return self.restore_image(decompressed)
