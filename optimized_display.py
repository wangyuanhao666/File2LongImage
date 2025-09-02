"""
优化的长图显示方案 - 解决预览过高和下载按钮位置问题
"""
import streamlit as st
from PIL import Image
import os
import base64
from io import BytesIO

def create_optimized_display(actual_output_path, output_format, dpi, quality):
    """
    创建优化的显示布局
    
    特点：
    1. 固定的操作栏在顶部
    2. 智能的预览高度控制
    3. 多种预览模式
    4. 性能优化的图片加载
    """
    
    if not actual_output_path or not os.path.exists(actual_output_path):
        st.error("文件不存在")
        return
    
    # 获取文件信息
    file_size = os.path.getsize(actual_output_path) / (1024 * 1024)  # MB
    img = Image.open(actual_output_path)
    
    # 生成快速预览缩略图（Base64编码）
    def create_thumbnail_base64(img, max_size=150):
        """创建Base64编码的缩略图用于快速预览"""
        ratio = max_size / max(img.width, img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        thumb = img.resize(new_size, Image.Resampling.LANCZOS)
        
        buffered = BytesIO()
        thumb.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    
    # 1. 成功提示和关键信息（固定在顶部）
    success_container = st.container()
    with success_container:
        # 成功消息
        st.success("✅ 转换完成！图片已生成")
        
        # 创建三列布局：缩略图 | 文件信息 | 操作按钮
        col_thumb, col_info, col_actions = st.columns([1, 2, 2])
        
        with col_thumb:
            # 显示小缩略图
            thumb_base64 = create_thumbnail_base64(img)
            st.markdown(
                f'<img src="{thumb_base64}" style="width:100%; max-width:150px; border-radius:10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">',
                unsafe_allow_html=True
            )
        
        with col_info:
            st.markdown("**📊 文件信息**")
            st.caption(f"• 尺寸: {img.width:,} × {img.height:,} px")
            st.caption(f"• 大小: {file_size:.1f} MB")
            st.caption(f"• 格式: {output_format}")
            st.caption(f"• DPI: {dpi}")
        
        with col_actions:
            # 主要下载按钮
            with open(actual_output_path, "rb") as file:
                file_data = file.read()
                st.download_button(
                    label="⬇️ 下载完整图片",
                    data=file_data,
                    file_name=os.path.basename(actual_output_path),
                    mime=f"image/{output_format.lower()}",
                    use_container_width=True,
                    type="primary",
                    key=f"download_main_{hash(actual_output_path)}"
                )
            
            # 次要操作按钮
            col_action1, col_action2 = st.columns(2)
            with col_action1:
                if st.button("🔄 新转换", use_container_width=True):
                    # 清理session state
                    if 'processed_files' in st.session_state:
                        st.session_state.processed_files.clear()
                    st.rerun()
            
            with col_action2:
                if st.button("📋 复制路径", use_container_width=True):
                    st.code(actual_output_path, language=None)
    
    # 分隔线
    st.markdown("---")
    
    # 2. 预览控制区域
    preview_container = st.container()
    with preview_container:
        st.markdown("### 🖼️ 图片预览")
        
        # 预览选项
        preview_col1, preview_col2, preview_col3 = st.columns(3)
        
        with preview_col1:
            preview_mode = st.selectbox(
                "预览模式",
                ["智能适应", "固定高度", "缩略图", "分段查看"],
                help="选择不同的预览方式"
            )
        
        with preview_col2:
            if preview_mode == "固定高度":
                max_height = st.slider("最大高度", 300, 1000, 600, 50)
            elif preview_mode == "分段查看":
                segment = st.selectbox("选择段落", 
                    [f"第 {i+1} 段" for i in range(min(5, img.height // 1000 + 1))])
                segment_idx = int(segment.split()[1]) - 1
            else:
                max_height = 600
                segment_idx = 0
        
        with preview_col3:
            show_ruler = st.checkbox("显示标尺", False)
            enhance_quality = st.checkbox("高质量预览", False)
        
        # 3. 图片预览区域
        preview_area = st.container()
        with preview_area:
            # 根据预览模式处理图片
            if preview_mode == "智能适应":
                # 自动计算最佳显示尺寸
                screen_width = 1200  # 假设的屏幕宽度
                if img.width > screen_width:
                    scale = screen_width / img.width
                    new_width = screen_width
                    new_height = int(img.height * scale)
                else:
                    new_width = img.width
                    new_height = img.height
                
                # 限制最大高度
                if new_height > 800:
                    scale = 800 / new_height
                    new_height = 800
                    new_width = int(new_width * scale)
                
                display_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
            elif preview_mode == "固定高度":
                # 固定高度，宽度按比例
                scale = max_height / img.height
                new_width = int(img.width * scale)
                display_img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)
                
            elif preview_mode == "缩略图":
                # 生成小缩略图
                thumb_size = 400
                scale = thumb_size / max(img.width, img.height)
                new_width = int(img.width * scale)
                new_height = int(img.height * scale)
                display_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
            elif preview_mode == "分段查看":
                # 分段显示（每段1000px高）
                segment_height = 1000
                start_y = segment_idx * segment_height
                end_y = min(start_y + segment_height, img.height)
                
                # 裁剪图片段
                segment_img = img.crop((0, start_y, img.width, end_y))
                
                # 缩放到合适的显示尺寸
                if segment_img.width > 1200:
                    scale = 1200 / segment_img.width
                    new_width = 1200
                    new_height = int(segment_img.height * scale)
                    display_img = segment_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    display_img = segment_img
            
            # 如果选择高质量预览，使用更好的重采样
            if enhance_quality and hasattr(display_img, 'resize'):
                # 确保使用最高质量的重采样算法
                pass  # 已经使用LANCZOS
            
            # 创建可滚动的容器显示图片
            if preview_mode != "缩略图":
                # 使用自定义HTML创建可滚动容器
                st.markdown(
                    f"""
                    <style>
                    .preview-container {{
                        max-height: {max_height if preview_mode == "固定高度" else 800}px;
                        overflow-y: auto;
                        border: 2px solid #f0f2f6;
                        border-radius: 10px;
                        padding: 10px;
                        background: white;
                        position: relative;
                    }}
                    .ruler {{
                        position: absolute;
                        left: 0;
                        top: 0;
                        width: 30px;
                        height: 100%;
                        background: linear-gradient(to bottom,
                            #f0f2f6 0px, #f0f2f6 1px,
                            transparent 1px, transparent 100px);
                        background-size: 100% 100px;
                        border-right: 1px solid #ddd;
                    }}
                    </style>
                    <div class="preview-container">
                        {"<div class='ruler'></div>" if show_ruler else ""}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            # 显示处理后的图片
            caption = f"预览模式: {preview_mode}"
            if preview_mode == "分段查看":
                caption += f" - 第 {segment_idx + 1}/{img.height // 1000 + 1} 段"
            caption += f" | 显示尺寸: {display_img.width}×{display_img.height}px"
            
            st.image(display_img, caption=caption, use_container_width=True)
    
    # 4. 快速操作工具栏（浮动在底部）
    st.markdown("---")
    
    quick_actions = st.container()
    with quick_actions:
        st.markdown("### ⚡ 快速工具")
        
        tool_col1, tool_col2, tool_col3, tool_col4 = st.columns(4)
        
        with tool_col1:
            if st.button("💾 另存为 PNG", use_container_width=True):
                if output_format != "PNG":
                    # 转换为PNG
                    png_path = actual_output_path.replace(f".{output_format.lower()}", ".png")
                    img.save(png_path, "PNG", optimize=True)
                    st.success(f"已保存为: {png_path}")
        
        with tool_col2:
            if st.button("🎨 另存为 JPG", use_container_width=True):
                if output_format != "JPG":
                    # 转换为JPG
                    jpg_path = actual_output_path.replace(f".{output_format.lower()}", ".jpg")
                    img.convert("RGB").save(jpg_path, "JPEG", quality=85)
                    st.success(f"已保存为: {jpg_path}")
        
        with tool_col3:
            if st.button("📏 查看原始尺寸", use_container_width=True):
                st.info(f"原始尺寸: {img.width:,} × {img.height:,} 像素\n"
                       f"宽高比: {img.width/img.height:.2f}")
        
        with tool_col4:
            if st.button("🗑️ 清理缓存", use_container_width=True):
                if 'processed_files' in st.session_state:
                    st.session_state.processed_files.clear()
                st.success("缓存已清理")
    
    # 5. 高级选项（折叠）
    with st.expander("🔧 高级选项"):
        adv_col1, adv_col2 = st.columns(2)
        
        with adv_col1:
            st.markdown("**导出选项**")
            export_scale = st.slider("导出缩放比例", 10, 100, 100, 10)
            if st.button("导出缩放版本"):
                scale = export_scale / 100
                scaled_img = img.resize(
                    (int(img.width * scale), int(img.height * scale)),
                    Image.Resampling.LANCZOS
                )
                scaled_path = actual_output_path.replace(
                    f".{output_format.lower()}", 
                    f"_scaled_{export_scale}.{output_format.lower()}"
                )
                scaled_img.save(scaled_path)
                st.success(f"已导出: {scaled_path}")
        
        with adv_col2:
            st.markdown("**分享选项**")
            if st.button("生成分享链接"):
                # 这里可以集成云存储服务
                st.info("分享功能正在开发中...")
            
            if st.button("生成二维码"):
                # 可以生成包含下载链接的二维码
                st.info("二维码功能正在开发中...")

def integrate_optimized_display(actual_output_path, output_format, dpi, quality):
    """
    集成优化显示到主应用
    替换 main.py 中第183-241行的显示逻辑
    """
    try:
        create_optimized_display(actual_output_path, output_format, dpi, quality)
    except Exception as e:
        st.error(f"显示错误: {str(e)}")
        # 降级处理 - 显示基本的下载按钮
        if actual_output_path and os.path.exists(actual_output_path):
            with open(actual_output_path, "rb") as file:
                st.download_button(
                    label="下载生成的图像",
                    data=file.read(),
                    file_name=os.path.basename(actual_output_path),
                    mime=f"image/{output_format.lower()}"
                )