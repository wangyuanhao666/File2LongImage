"""
方案二：虚拟滚动长图查看器 (Virtual Scrolling Long Image Viewer)
技术实现：基于Canvas的虚拟滚动渲染系统，仅渲染可视区域的图像块
"""

import os
import io
import base64
import json
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components
from typing import List, Tuple, Dict
import math

class VirtualScrollViewer:
    def __init__(self, image_path: str, tile_height: int = 1000):
        self.image_path = image_path
        self.tile_height = tile_height
        self.tiles_dir = os.path.join("tiles", os.path.splitext(os.path.basename(image_path))[0])
        os.makedirs(self.tiles_dir, exist_ok=True)
        
        # 获取图像基本信息
        with Image.open(image_path) as img:
            self.image_width, self.image_height = img.size
            self.total_tiles = math.ceil(self.image_height / tile_height)
    
    def generate_tiles(self) -> List[Dict]:
        """生成图像分块并返回分块信息"""
        tiles_info = []
        
        try:
            with Image.open(self.image_path) as img:
                for i in range(self.total_tiles):
                    tile_filename = f"tile_{i:04d}.webp"
                    tile_path = os.path.join(self.tiles_dir, tile_filename)
                    
                    # 计算分块区域
                    top = i * self.tile_height
                    bottom = min(top + self.tile_height, self.image_height)
                    
                    tile_info = {
                        'index': i,
                        'filename': tile_filename,
                        'path': tile_path,
                        'top': top,
                        'bottom': bottom,
                        'height': bottom - top,
                        'width': self.image_width
                    }
                    
                    # 如果分块不存在，则创建
                    if not os.path.exists(tile_path):
                        tile_img = img.crop((0, top, self.image_width, bottom))
                        tile_img.save(tile_path, 'WEBP', quality=90, method=6)
                    
                    # 转换为base64用于web显示
                    with open(tile_path, 'rb') as f:
                        tile_data = f.read()
                        tile_info['base64'] = base64.b64encode(tile_data).decode()
                    
                    tiles_info.append(tile_info)
                    
            return tiles_info
            
        except Exception as e:
            st.error(f"生成图像分块失败: {str(e)}")
            return []
    
    def get_viewer_html(self, tiles_info: List[Dict]) -> str:
        """生成虚拟滚动查看器的HTML代码"""
        
        tiles_json = json.dumps(tiles_info)
        
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .virtual-scroll-container {{
                    width: 100%;
                    height: 600px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    overflow-y: auto;
                    overflow-x: auto;
                    position: relative;
                    background: #f9f9f9;
                }}
                
                .virtual-content {{
                    position: relative;
                    width: {self.image_width}px;
                    height: {self.image_height}px;
                }}
                
                .tile-canvas {{
                    position: absolute;
                    left: 0;
                    display: block;
                    max-width: 100%;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                
                .loading-placeholder {{
                    position: absolute;
                    left: 0;
                    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                    background-size: 200% 100%;
                    animation: loading 2s infinite;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #666;
                    font-size: 14px;
                }}
                
                @keyframes loading {{
                    0% {{ background-position: 200% 0; }}
                    100% {{ background-position: -200% 0; }}
                }}
                
                .scroll-indicator {{
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    background: rgba(0,0,0,0.7);
                    color: white;
                    padding: 8px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    z-index: 1000;
                }}
                
                .zoom-controls {{
                    position: absolute;
                    bottom: 10px;
                    right: 10px;
                    display: flex;
                    gap: 5px;
                    z-index: 1000;
                }}
                
                .zoom-btn {{
                    width: 40px;
                    height: 40px;
                    border: none;
                    border-radius: 50%;
                    background: rgba(0,0,0,0.7);
                    color: white;
                    cursor: pointer;
                    font-size: 18px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                
                .zoom-btn:hover {{
                    background: rgba(0,0,0,0.9);
                }}
            </style>
        </head>
        <body>
            <div class="virtual-scroll-container" id="scrollContainer">
                <div class="scroll-indicator" id="scrollIndicator">0%</div>
                <div class="zoom-controls">
                    <button class="zoom-btn" onclick="zoomOut()">-</button>
                    <button class="zoom-btn" onclick="zoomIn()">+</button>
                    <button class="zoom-btn" onclick="resetZoom()">⌂</button>
                </div>
                <div class="virtual-content" id="virtualContent">
                    <!-- 动态生成的图块将插入这里 -->
                </div>
            </div>
            
            <script>
                class VirtualScrollViewer {{
                    constructor(tilesData) {{
                        this.tiles = tilesData;
                        this.container = document.getElementById('scrollContainer');
                        this.content = document.getElementById('virtualContent');
                        this.indicator = document.getElementById('scrollIndicator');
                        
                        this.viewportHeight = 600;
                        this.bufferSize = 2; // 预加载前后2个tile
                        this.loadedTiles = new Map();
                        this.currentScale = 1.0;
                        this.minScale = 0.1;
                        this.maxScale = 2.0;
                        
                        this.init();
                    }}
                    
                    init() {{
                        this.container.addEventListener('scroll', () => this.handleScroll());
                        this.container.addEventListener('wheel', (e) => this.handleWheel(e));
                        this.updateVisibleTiles();
                    }}
                    
                    handleScroll() {{
                        this.updateVisibleTiles();
                        this.updateScrollIndicator();
                    }}
                    
                    handleWheel(event) {{
                        if (event.ctrlKey || event.metaKey) {{
                            event.preventDefault();
                            const delta = event.deltaY > 0 ? -0.1 : 0.1;
                            this.zoom(delta);
                        }}
                    }}
                    
                    updateVisibleTiles() {{
                        const scrollTop = this.container.scrollTop;
                        const scrollBottom = scrollTop + this.viewportHeight;
                        
                        // 计算可见的tile范围
                        const startIndex = Math.max(0, 
                            Math.floor(scrollTop / {self.tile_height}) - this.bufferSize);
                        const endIndex = Math.min(this.tiles.length - 1,
                            Math.ceil(scrollBottom / {self.tile_height}) + this.bufferSize);
                        
                        // 移除不在视窗范围的tiles
                        for (let [index, element] of this.loadedTiles) {{
                            if (index < startIndex || index > endIndex) {{
                                element.remove();
                                this.loadedTiles.delete(index);
                            }}
                        }}
                        
                        // 加载新的tiles
                        for (let i = startIndex; i <= endIndex; i++) {{
                            if (!this.loadedTiles.has(i)) {{
                                this.loadTile(i);
                            }}
                        }}
                    }}
                    
                    loadTile(index) {{
                        const tile = this.tiles[index];
                        if (!tile) return;
                        
                        // 创建加载占位符
                        const placeholder = document.createElement('div');
                        placeholder.className = 'loading-placeholder';
                        placeholder.style.top = tile.top + 'px';
                        placeholder.style.width = tile.width + 'px';
                        placeholder.style.height = tile.height + 'px';
                        placeholder.textContent = `加载中... (${{index + 1}}/${{this.tiles.length}})`;
                        
                        this.content.appendChild(placeholder);
                        this.loadedTiles.set(index, placeholder);
                        
                        // 创建图像元素
                        const img = new Image();
                        img.onload = () => {{
                            placeholder.remove();
                            
                            const canvas = document.createElement('canvas');
                            canvas.className = 'tile-canvas';
                            canvas.style.top = tile.top + 'px';
                            canvas.width = tile.width;
                            canvas.height = tile.height;
                            
                            const ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0);
                            
                            this.content.appendChild(canvas);
                            this.loadedTiles.set(index, canvas);
                        }};
                        
                        img.onerror = () => {{
                            placeholder.textContent = `加载失败 (${{index + 1}}/${{this.tiles.length}})`;
                            placeholder.style.background = '#ffebee';
                            placeholder.style.color = '#c62828';
                        }};
                        
                        img.src = 'data:image/webp;base64,' + tile.base64;
                    }}
                    
                    updateScrollIndicator() {{
                        const scrollPercent = Math.round(
                            (this.container.scrollTop / 
                            (this.container.scrollHeight - this.container.clientHeight)) * 100
                        );
                        this.indicator.textContent = `${{scrollPercent}}%`;
                    }}
                    
                    zoom(delta) {{
                        const newScale = Math.max(this.minScale, 
                            Math.min(this.maxScale, this.currentScale + delta));
                        
                        if (newScale !== this.currentScale) {{
                            this.currentScale = newScale;
                            this.content.style.transform = `scale(${{newScale}})`;
                            this.content.style.transformOrigin = 'top left';
                        }}
                    }}
                }}
                
                // 全局缩放函数
                let viewer;
                
                function zoomIn() {{
                    if (viewer) viewer.zoom(0.2);
                }}
                
                function zoomOut() {{
                    if (viewer) viewer.zoom(-0.2);
                }}
                
                function resetZoom() {{
                    if (viewer) {{
                        viewer.currentScale = 1.0;
                        viewer.content.style.transform = 'scale(1)';
                    }}
                }}
                
                // 初始化查看器
                const tilesData = {tiles_json};
                viewer = new VirtualScrollViewer(tilesData);
            </script>
        </body>
        </html>
        """
        
        return html_code

def render_virtual_scroll_viewer(image_path: str, output_format: str):
    """渲染虚拟滚动查看器界面"""
    
    # 创建两栏布局
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("虚拟滚动长图查看器")
        
        # 初始化查看器
        viewer = VirtualScrollViewer(image_path, tile_height=1000)
        
        # 显示加载进度
        with st.spinner("正在生成图像分块..."):
            tiles_info = viewer.generate_tiles()
        
        if tiles_info:
            st.success(f"已生成 {len(tiles_info)} 个图像分块")
            
            # 渲染虚拟滚动查看器
            html_content = viewer.get_viewer_html(tiles_info)
            components.html(html_content, height=650, scrolling=False)
            
        else:
            st.error("无法生成图像分块")
    
    with col2:
        st.subheader("下载与信息")
        
        # 文件信息
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        with Image.open(image_path) as img:
            width, height = img.size
        
        st.info(f"""
        **图像信息**
        - 尺寸: {width:,} × {height:,} px
        - 大小: {file_size:.2f} MB
        - 分块数量: {viewer.total_tiles}
        - 每块高度: {viewer.tile_height}px
        """)
        
        # 下载按钮
        with open(image_path, "rb") as file:
            st.download_button(
                label="📥 下载完整图像",
                data=file.read(),
                file_name=os.path.basename(image_path),
                mime=f"image/{output_format.lower()}",
                use_container_width=True,
                type="primary"
            )
        
        # 查看器控制说明
        st.markdown("""
        **控制说明:**
        - 🖱️ 滚动查看图像
        - 🔍 Ctrl+滚轮缩放
        - ➕➖ 点击缩放按钮
        - 🏠 点击重置缩放
        """)
        
        # 性能指标
        st.markdown("""
        **性能优势:**
        - ✅ 内存使用优化
        - ✅ 流畅滚动体验  
        - ✅ 快速加载预览
        - ✅ 支持大图浏览
        """)

# 集成示例
def integrate_virtual_scroll():
    """集成虚拟滚动查看器的示例代码"""
    return '''
    # 在main.py中替换显示结果的代码
    if actual_output_path and os.path.exists(actual_output_path):
        render_virtual_scroll_viewer(actual_output_path, output_format)
    else:
        st.error("图像转换失败，请检查文件格式或系统依赖")
    '''

if __name__ == "__main__":
    st.title("方案二：虚拟滚动长图查看器演示")
    
    # 演示代码
    demo_image = "demo_long_image.png"
    if os.path.exists(demo_image):
        render_virtual_scroll_viewer(demo_image, "PNG")
    else:
        st.info("请先生成演示长图查看效果")