"""
方案一：分层预览系统 (Multi-Level Preview System)
技术实现：渐进式图像预览系统，基于多分辨率金字塔和WebP格式优化
"""

import os
import io
import base64
from PIL import Image, ImageOps
import streamlit as st
from typing import Dict, Tuple, List
import threading
import time

class MultiLevelPreview:
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.base_name = os.path.splitext(os.path.basename(image_path))[0]
        self.cache_dir = os.path.join("cache", self.base_name)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 预定义的分辨率级别
        self.levels = {
            'thumbnail': 300,      # 缩略图：最大宽度300px
            'preview': 800,        # 预览图：最大宽度800px  
            'medium': 1500,        # 中等图：最大宽度1500px
            'high': 2500          # 高清图：最大宽度2500px
        }
        
    def generate_preview_levels(self) -> Dict[str, str]:
        """生成多级预览图并返回路径"""
        try:
            with Image.open(self.image_path) as original_img:
                original_width, original_height = original_img.size
                aspect_ratio = original_height / original_width
                
                preview_paths = {}
                
                for level_name, max_width in self.levels.items():
                    # 只有当原图宽度大于目标宽度时才缩放
                    if original_width <= max_width:
                        preview_paths[level_name] = self.image_path
                        continue
                        
                    # 计算新尺寸
                    new_width = min(max_width, original_width)
                    new_height = int(new_width * aspect_ratio)
                    
                    # 生成预览图路径
                    webp_path = os.path.join(self.cache_dir, f"{level_name}_{new_width}x{new_height}.webp")
                    
                    if not os.path.exists(webp_path):
                        # 创建并保存WebP格式的预览图
                        resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        
                        # WebP参数优化
                        webp_quality = 85 if level_name in ['high', 'medium'] else 75
                        resized_img.save(webp_path, 'WEBP', quality=webp_quality, method=6)
                    
                    preview_paths[level_name] = webp_path
                    
                return preview_paths
                
        except Exception as e:
            st.error(f"生成预览图失败: {str(e)}")
            return {}
    
    def get_base64_thumbnail(self, max_size: int = 200) -> str:
        """生成Base64编码的超小缩略图，用于即时显示"""
        try:
            with Image.open(self.image_path) as img:
                # 创建极小的缩略图
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                buffer = io.BytesIO()
                img.save(buffer, format='WEBP', quality=60)
                buffer.seek(0)
                
                return base64.b64encode(buffer.getvalue()).decode()
        except Exception as e:
            return ""

def render_multi_level_preview(image_path: str, output_format: str):
    """渲染分层预览界面"""
    preview_system = MultiLevelPreview(image_path)
    
    # 创建三栏布局
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader("图像预览")
        
        # 立即显示Base64缩略图
        base64_thumb = preview_system.get_base64_thumbnail()
        if base64_thumb:
            st.markdown(
                f'<img src="data:image/webp;base64,{base64_thumb}" '
                f'style="width:100%;max-width:300px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">',
                unsafe_allow_html=True
            )
            
        # 异步生成高质量预览图
        if st.button("加载高清预览", key="load_hq_preview"):
            with st.spinner("生成高质量预览图..."):
                preview_paths = preview_system.generate_preview_levels()
                
                if preview_paths:
                    # 选择最佳预览级别
                    best_preview = preview_paths.get('preview', preview_paths.get('thumbnail'))
                    if best_preview:
                        st.image(best_preview, caption="高质量预览", use_container_width=True)
    
    with col2:
        st.subheader("下载选项")
        
        # 获取文件信息
        file_size = os.path.getsize(image_path) / (1024 * 1024)  # MB
        with Image.open(image_path) as img:
            width, height = img.size
            
        # 文件信息显示
        st.info(f"""
        **文件信息**
        - 尺寸: {width} × {height} px
        - 大小: {file_size:.2f} MB
        - 格式: {output_format}
        """)
        
        # 主下载按钮 - 置顶显示
        with open(image_path, "rb") as file:
            st.download_button(
                label="⬇️ 下载原图",
                data=file.read(),
                file_name=os.path.basename(image_path),
                mime=f"image/{output_format.lower()}",
                use_container_width=True,
                type="primary"
            )
    
    with col3:
        st.subheader("预览选项")
        
        # 预览级别选择器
        preview_level = st.selectbox(
            "选择预览质量",
            options=["thumbnail", "preview", "medium", "high"],
            format_func=lambda x: {
                "thumbnail": "缩略图 (快速)",
                "preview": "预览图 (推荐)", 
                "medium": "中等质量",
                "high": "高质量"
            }[x],
            index=1
        )
        
        if st.button("切换预览", key="switch_preview"):
            preview_paths = preview_system.generate_preview_levels()
            selected_preview = preview_paths.get(preview_level)
            
            if selected_preview and os.path.exists(selected_preview):
                st.image(selected_preview, caption=f"{preview_level} 预览", use_container_width=True)

# 集成到主应用的示例代码
def integrate_multi_level_preview():
    """集成分层预览系统到主应用"""
    
    # 在main.py的显示结果部分替换现有代码
    code_example = '''
    # 替换原来的图像显示代码 (第173-227行)
    if actual_output_path and os.path.exists(actual_output_path):
        render_multi_level_preview(actual_output_path, output_format)
    else:
        st.error("图像转换失败，请检查文件格式或系统依赖")
    '''
    
    return code_example

if __name__ == "__main__":
    # 示例用法
    st.title("方案一：分层预览系统演示")
    
    # 模拟图像路径
    test_image_path = "test_long_image.png"
    if os.path.exists(test_image_path):
        render_multi_level_preview(test_image_path, "PNG")
    else:
        st.info("请先生成一个测试长图以查看效果")