import os
import pdf2image
import streamlit as st
from PIL import Image
import time
import subprocess
import sys
from config import OUTPUT_DIR, POPPLER_PATH, LIBREOFFICE_PATH

# 增加 PIL 的最大图像像素限制，防止 DecompressionBombWarning
Image.MAX_IMAGE_PIXELS = 500000000  # 5亿像素

st.set_page_config(page_title="文件转长图工具", page_icon="🖼️")

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
        except OSError as e:
            if "Wrong JPEG library version" in str(e) or "encoder error" in str(e):
                # 如果 JPEG 保存失败，尝试使用不同的参数或降级保存
                st.warning("JPEG 编码出现问题，尝试其他保存方式...")
                try:
                    # 尝试使用较低的质量设置
                    merged_image.save(output_path, format="JPEG", quality=min(quality, 85), optimize=False, progressive=False)
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
        subprocess.run(conversion_cmd, shell=True)

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

st.title("文件转长图工具")



dpi = st.slider("设置图片 PPI", min_value=72, max_value=600, value=300)
output_format = st.selectbox("选择输出格式", ["JPG", "PNG"])
quality = st.slider("设置 JPG 质量", min_value=1, max_value=100, value=85) if output_format == "JPG" else None

uploaded_file = st.file_uploader("上传文件", type=["pdf", "doc", "docx", "ppt", "pptx", "csv", "xls", "xlsx", "odt", "rtf", "txt", "psd", "cdr", "wps", "svg"])



if uploaded_file is not None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.getbuffer())
    # 获取实际保存的文件路径
    actual_output_path = convert_to_image(uploaded_file.name, OUTPUT_DIR, dpi, output_format, quality)
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
                
                st.image(display_image, caption=f'转换后的长图 (原始大小: {file_size:.2f}MB)', use_column_width=True)
                
                # 提供下载链接
                with open(actual_output_path, "rb") as file:
                    st.download_button(
                        label="下载原始大小图像",
                        data=file.read(),
                        file_name=os.path.basename(actual_output_path),
                        mime=f"image/{output_format.lower()}"
                    )
            else:
                # 小文件直接显示
                st.image(actual_output_path, caption='转换后的长图', use_column_width=True)
        except Exception as e:
            st.warning(f"图像显示出现问题: {str(e)}")
            st.info(f"图像已成功保存到: {actual_output_path}")
            
            # 提供下载按钮作为备用方案
            with open(actual_output_path, "rb") as file:
                st.download_button(
                    label="下载生成的图像",
                    data=file.read(),
                    file_name=os.path.basename(actual_output_path),
                    mime=f"image/{output_format.lower()}"
                )
    else:
        st.error("图像转换失败，请检查文件格式或系统依赖")


st.markdown(
    """
    <div style="text-align: center;">
        <a href="https://github.com/yr2b/File2LongImage/" target="_blank">
            <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub Logo" style="width:50px;height:50px;">
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
