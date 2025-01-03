from PIL import Image, ImageDraw

def create_clipboard_sync_icon():
    # 创建一个透明背景的图像
    size = 256
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # 定义颜色
    primary_color = (0, 120, 212)  # 微软蓝
    secondary_color = (0, 153, 204)  # 浅蓝色
    
    # 绘制圆形背景
    padding = 20
    draw.ellipse([padding, padding, size-padding, size-padding], 
                 fill=primary_color)
    
    # 绘制剪贴板轮廓
    cb_width = size * 0.6
    cb_height = cb_width * 1.2
    cb_x = (size - cb_width) / 2
    cb_y = (size - cb_height) / 2
    
    # 剪贴板主体（白色）
    draw.rectangle([cb_x, cb_y + cb_width*0.1, 
                   cb_x + cb_width, cb_y + cb_height], 
                   fill='white')
    
    # 剪贴板顶部夹子
    clip_width = cb_width * 0.4
    clip_height = cb_width * 0.1
    clip_x = (size - clip_width) / 2
    draw.rectangle([clip_x, cb_y,
                   clip_x + clip_width, cb_y + clip_height],
                   fill='white')
    
    # 绘制同步箭头
    arrow_color = secondary_color
    arrow_width = cb_width * 0.4
    arrow_height = cb_height * 0.15
    center_y = size / 2
    
    # 左箭头
    left_points = [
        (cb_x + cb_width*0.3, center_y),  # 箭头尖端
        (cb_x + cb_width*0.5, center_y - arrow_height),  # 上边
        (cb_x + cb_width*0.5, center_y + arrow_height),  # 下边
    ]
    draw.polygon(left_points, fill=arrow_color)
    
    # 右箭头
    right_points = [
        (cb_x + cb_width*0.7, center_y),  # 箭头尖端
        (cb_x + cb_width*0.5, center_y - arrow_height),  # 上边
        (cb_x + cb_width*0.5, center_y + arrow_height),  # 下边
    ]
    draw.polygon(right_points, fill=arrow_color)
    
    # 保存为不同尺寸的图标
    sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
    icons = []
    for size in sizes:
        icons.append(image.resize(size, Image.Resampling.LANCZOS))
    
    # 保存为 PNG
    image.save('icon.png', 'PNG')
    
    # 保存为 ICO（Windows）
    icons[0].save('icon.ico', format='ICO', sizes=sizes)
    
    print("图标已创建：icon.png 和 icon.ico")

if __name__ == '__main__':
    create_clipboard_sync_icon()
