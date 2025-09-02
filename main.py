import os
import pdf2image
import streamlit as st
from PIL import Image
import time
import subprocess
import sys
import hashlib
from config import OUTPUT_DIR, POPPLER_PATH, LIBREOFFICE_PATH, INTERMEDIATE_DIR

# 增加 PIL 的最大图像像素限制，防止 DecompressionBombWarning
Image.MAX_IMAGE_PIXELS = 500000000  # 5亿像素

st.set_page_config(page_title="文件转长图工具", page_icon="🖼️")

def get_file_hash(file_content):
    """计算文件内容的哈希值，用于识别文件是否已处理"""
    return hashlib.md5(file_content).hexdigest()

def merge_images(images, output_path, output_format="PNG", quality=85):
    """合并图像并返回实际保存的文件路径"""
    st.write("开始合并图像...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    start_time = time.time()

    widths, heights = zip(*(i.size for i in images))
    total_height = sum(heights)
    max_width = max(widths)

    merged_image = Image.new('RGB', (max_width, total_height))
    y_offset = 0

    total_images = len(images)
    for idx, img in enumerate(images):
        merged_image.paste(img, (0, y_offset))
        y_offset += img.height

        # 更新进度
        progress = (idx + 1) / total_images
        progress_bar.progress(progress)
        elapsed_time = time.time() - start_time
        estimated_total_time = elapsed_time / progress
        remaining_time = estimated_total_time - elapsed_time
        status_text.text(f"正在合并图像：{idx + 1}/{total_images}，预计剩余时间：{int(remaining_time)}秒")

    # 保存并压缩图像
    if output_format == "JPG":
        merged_image = merged_image.convert("RGB")  # 确保是 RGB 模式
        try:
            merged_image.save(output_path, format="JPEG", quality=quality)
        except (OSError, IOError) as e:
            if "encoder error" in str(e).lower():
                # 如果 JPEG 保存失败，尝试使用不同的参数或降级保存
                st.warning("JPEG 编码出现问题，尝试其他保存方式...")
                try:
                    # 尝试使用较低的质量设置和不同的子采样
                    merged_image.save(output_path, format="JPEG", quality=min(quality, 85), 
                                    optimize=False, progressive=False, subsampling=2)
                except:
                    # 如果仍然失败，改为保存为 PNG
                    st.warning("JPEG 保存失败，改为保存为 PNG 格式")
                    output_path = output_path.replace('.jpg', '.png')
                    merged_image.save(output_path, format="PNG", optimize=True)
            else:
                raise
    else:
        merged_image.save(output_path, format="PNG", optimize=True)
        
    status_text.text("图像合并并压缩完成！")
    progress_bar.progress(1.0)
    return output_path  # 返回实际保存的文件路径

def convert_to_image(file_path, output_dir, dpi, output_format="PNG", quality=85):
    """转换文件为图像并返回实际保存的文件路径"""
    st.write("开始转换文件...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    start_time = time.time()

    images = []
    base_name = os.path.splitext(os.path.basename(file_path))[0]

    if file_path.lower().endswith('.pdf'):
        images = pdf2image.convert_from_path(file_path, poppler_path=POPPLER_PATH, dpi=dpi)
        progress_bar.progress(0.3)
    elif file_path.lower().endswith((".doc", ".docx", ".ppt", ".pptx", ".csv", ".xls", ".xlsx", ".odt", ".rtf", ".txt", ".psd", ".cdr", ".wps", ".svg")):
        if LIBREOFFICE_PATH is None:
            raise ValueError("LibreOffice 未安装。请安装 LibreOffice 以支持非 PDF 文件的转换。\n"
                           "macOS 安装方法：\n"
                           "1. 从 https://www.libreoffice.org/download/download/ 下载\n"
                           "2. 或使用 Homebrew: brew install --cask libreoffice")
        
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        if sys.platform.startswith('win'):
            conversion_cmd = f'"{LIBREOFFICE_PATH}" --headless --convert-to pdf "{file_path}" --outdir "{output_dir}"'
        else:
            conversion_cmd = f'{LIBREOFFICE_PATH} --headless --convert-to pdf "{file_path}" --outdir "{output_dir}"'
        
        subprocess.run(conversion_cmd, shell=True, capture_output=True)

        if not os.path.exists(pdf_path):
            raise ValueError("文件转换为 PDF 失败")
        else:
            status_text.text(f"文件转换为 PDF 成功，正在转换为图像: {pdf_path}")
            progress_bar.progress(0.6)

        images = pdf2image.convert_from_path(pdf_path, poppler_path=POPPLER_PATH, dpi=dpi)
        progress_bar.progress(0.9)
    else:
        raise ValueError("不支持的文件格式")

    if images:
        merged_output_path = os.path.join(output_dir, f"{base_name}.{output_format.lower()}")
        actual_output_path = merge_images(images, merged_output_path, output_format, quality)
        progress_bar.progress(1.0)
        status_text.text("文件转换完成！")
        return actual_output_path  # 返回实际保存的文件路径
    return None

# 初始化 session state
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = {}
if 'last_file_hash' not in st.session_state:
    st.session_state.last_file_hash = None
if 'last_output_path' not in st.session_state:
    st.session_state.last_output_path = None

st.title("文件转长图工具")

dpi = st.slider("设置图片 PPI", min_value=72, max_value=600, value=300)
output_format = st.selectbox("选择输出格式", ["JPG", "PNG"])
quality = st.slider("设置 JPG 质量", min_value=1, max_value=100, value=85) if output_format == "JPG" else None

uploaded_file = st.file_uploader("上传文件", type=["pdf", "doc", "docx", "ppt", "pptx", "csv", "xls", "xlsx", "odt", "rtf", "txt", "psd", "cdr", "wps", "svg"])

if uploaded_file is not None:
    # 创建必要的目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
    
    # 获取文件内容和哈希
    file_content = uploaded_file.getbuffer()
    file_hash = get_file_hash(file_content)
    
    # 构建转换参数的唯一标识
    conversion_key = f"{file_hash}_{dpi}_{output_format}_{quality}"
    
    # 检查是否已经处理过相同的文件和参数
    if conversion_key in st.session_state.processed_files:
        # 使用缓存的结果
        actual_output_path = st.session_state.processed_files[conversion_key]
        st.success("使用缓存的转换结果")
    else:
        # 保存上传的文件到临时目录
        temp_file_path = os.path.join(INTERMEDIATE_DIR, uploaded_file.name)
        with open(temp_file_path, "wb") as f:
            f.write(file_content)
        
        try:
            # 执行转换
            actual_output_path = convert_to_image(temp_file_path, OUTPUT_DIR, dpi, output_format, quality)
            
            # 缓存结果
            if actual_output_path:
                st.session_state.processed_files[conversion_key] = actual_output_path
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    # 显示结果
    if actual_output_path and os.path.exists(actual_output_path):
        # 对于大图像，创建一个缩略图用于显示
        try:
            # 获取文件大小
            file_size = os.path.getsize(actual_output_path) / (1024 * 1024)  # MB
            
            if file_size > 10:  # 如果文件大于 10MB
                # 创建一个用于显示的缩略图
                display_image = Image.open(actual_output_path)
                
                # 计算缩放比例，限制最大宽度为 2000 像素
                max_width = 2000
                if display_image.width > max_width:
                    ratio = max_width / display_image.width
                    new_width = max_width
                    new_height = int(display_image.height * ratio)
                    display_image = display_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                st.image(display_image, caption=f'转换后的长图 (原始大小: {file_size:.2f}MB)', use_container_width=True)
                
                # 提供下载链接
                with open(actual_output_path, "rb") as file:
                    btn = st.download_button(
                        label="下载原始大小图像",
                        data=file.read(),
                        file_name=os.path.basename(actual_output_path),
                        mime=f"image/{output_format.lower()}",
                        key=f"download_{conversion_key}"  # 使用唯一的 key 避免重新运行
                    )
            else:
                # 小文件直接显示
                st.image(actual_output_path, caption='转换后的长图', use_container_width=True)
                
                # 提供下载按钮
                with open(actual_output_path, "rb") as file:
                    btn = st.download_button(
                        label="下载图像",
                        data=file.read(),
                        file_name=os.path.basename(actual_output_path),
                        mime=f"image/{output_format.lower()}",
                        key=f"download_{conversion_key}"  # 使用唯一的 key 避免重新运行
                    )
        except Exception as e:
            st.warning(f"图像显示出现问题: {str(e)}")
            st.info(f"图像已成功保存到: {actual_output_path}")
            
            # 提供下载按钮作为备用方案
            with open(actual_output_path, "rb") as file:
                btn = st.download_button(
                    label="下载生成的图像",
                    data=file.read(),
                    file_name=os.path.basename(actual_output_path),
                    mime=f"image/{output_format.lower()}",
                    key=f"download_fallback_{conversion_key}"  # 使用唯一的 key
                )
    else:
        st.error("图像转换失败，请检查文件格式或系统依赖")

st.markdown(
    """
    ---
    ### 使用说明
    1. 选择要转换的文件（支持 PDF、Word、Excel、PPT 等格式）
    2. 设置图片的 DPI（PPI），DPI 越高，图片越清晰，但文件越大
    3. 选择输出格式（JPG 或 PNG）
    4. 如果选择 JPG，可以设置质量（1-100）
    5. 点击"Browse files"上传文件，等待转换完成
    6. 转换完成后，可以预览并下载生成的长图
    
    ### 注意事项
    - 大文件转换可能需要较长时间，请耐心等待
    - 如需转换非 PDF 文件，请确保已安装 LibreOffice
    - 转换结果会缓存，相同文件和参数不会重复转换
    """
)