"""
方案四：智能预览与快捷操作面板 (Smart Preview & Quick Action Panel)
技术实现：基于用户行为的智能预览系统，配合悬浮式快捷操作面板和预测性内容加载
"""

import os
import io
import json
import base64
import hashlib
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, List, Tuple, Optional
import threading
import queue

class SmartPreviewPanel:
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.base_name = os.path.splitext(os.path.basename(image_path))[0]
        self.preview_cache_dir = os.path.join("smart_cache", self.base_name)
        self.analytics_dir = os.path.join("analytics", "user_behavior")
        
        os.makedirs(self.preview_cache_dir, exist_ok=True)
        os.makedirs(self.analytics_dir, exist_ok=True)
        
        # 获取图像基础信息
        with Image.open(image_path) as img:
            self.original_width, self.original_height = img.size
            self.aspect_ratio = self.original_height / self.original_width
        
        # 智能预览配置
        self.smart_preview_levels = {
            'instant': {
                'width': 400, 
                'quality': 60, 
                'description': '瞬时预览',
                'load_time_target': 0.5  # 秒
            },
            'quick': {
                'width': 800, 
                'quality': 75, 
                'description': '快速预览',
                'load_time_target': 1.0
            },
            'detailed': {
                'width': 1200, 
                'quality': 85, 
                'description': '详细预览',
                'load_time_target': 2.0
            },
            'full': {
                'width': 2000, 
                'quality': 95, 
                'description': '完整预览',
                'load_time_target': 5.0
            }
        }
    
    def generate_smart_previews(self) -> Dict[str, Dict]:
        """生成智能预览版本"""
        previews = {}
        
        try:
            with Image.open(self.image_path) as original_img:
                for level_name, config in self.smart_preview_levels.items():
                    preview_info = self.create_smart_preview(original_img, level_name, config)
                    if preview_info:
                        previews[level_name] = preview_info
                        
            return previews
            
        except Exception as e:
            st.error(f"生成智能预览失败: {str(e)}")
            return {}
    
    def create_smart_preview(self, img: Image.Image, level_name: str, config: Dict) -> Optional[Dict]:
        """创建单个智能预览版本"""
        try:
            target_width = min(config['width'], self.original_width)
            target_height = int(target_width * self.aspect_ratio)
            
            preview_path = os.path.join(self.preview_cache_dir, f"smart_{level_name}_{target_width}x{target_height}.webp")
            
            if not os.path.exists(preview_path):
                # 创建预览图像
                preview_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                # 添加智能水印（包含预览信息）
                preview_img = self.add_smart_watermark(preview_img, level_name, config)
                
                # 保存WebP格式
                preview_img.save(
                    preview_path, 
                    'WEBP', 
                    quality=config['quality'],
                    method=6
                )
            
            # 获取文件信息
            file_size = os.path.getsize(preview_path) / 1024  # KB
            
            # 转换为base64
            with open(preview_path, 'rb') as f:
                base64_data = base64.b64encode(f.read()).decode()
            
            return {
                'path': preview_path,
                'base64': base64_data,
                'width': target_width,
                'height': target_height,
                'file_size_kb': file_size,
                'quality': config['quality'],
                'description': config['description'],
                'load_time_target': config['load_time_target']
            }
            
        except Exception as e:
            return None
    
    def add_smart_watermark(self, img: Image.Image, level_name: str, config: Dict) -> Image.Image:
        """添加智能水印信息"""
        try:
            # 创建副本以避免修改原图
            watermarked = img.copy()
            draw = ImageDraw.Draw(watermarked)
            
            # 水印信息
            watermark_text = f"{config['description']} | {config['quality']}% 质量"
            
            # 计算水印位置（右下角）
            img_width, img_height = watermarked.size
            
            # 尝试加载字体（如果失败则使用默认字体）
            try:
                font_size = max(12, min(24, img_width // 50))
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # 获取文本尺寸
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 计算位置（右下角，留边距）
            margin = 10
            x = img_width - text_width - margin
            y = img_height - text_height - margin
            
            # 绘制半透明背景
            background_padding = 5
            draw.rectangle(
                [x - background_padding, y - background_padding, 
                 x + text_width + background_padding, y + text_height + background_padding],
                fill=(0, 0, 0, 128)
            )
            
            # 绘制文本
            draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 200))
            
            return watermarked
            
        except Exception:
            # 如果水印添加失败，返回原图
            return img
    
    def get_smart_panel_html(self, previews: Dict[str, Dict], output_format: str) -> str:
        """生成智能预览面板HTML"""
        
        previews_json = json.dumps(previews)
        
        # 获取原图文件信息
        original_size = os.path.getsize(self.image_path) / (1024 * 1024)  # MB
        
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .smart-container {{
                    position: relative;
                    width: 100%;
                    height: 70vh;
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                }}
                
                .preview-display {{
                    position: relative;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                }}
                
                .preview-image {{
                    max-width: 100%;
                    max-height: 100%;
                    border-radius: 8px;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.4);
                    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                    transform: scale(0.95);
                }}
                
                .preview-image.loaded {{
                    transform: scale(1);
                }}
                
                .floating-panel {{
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 16px;
                    padding: 20px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
                    min-width: 280px;
                    max-height: calc(100% - 40px);
                    overflow-y: auto;
                    z-index: 1000;
                    transition: transform 0.3s ease, opacity 0.3s ease;
                }}
                
                .floating-panel.collapsed {{
                    transform: translateX(calc(100% - 50px));
                    opacity: 0.8;
                }}
                
                .panel-header {{
                    display: flex;
                    justify-content: between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #e0e0e0;
                }}
                
                .panel-title {{
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                    margin: 0;
                }}
                
                .collapse-btn {{
                    width: 32px;
                    height: 32px;
                    border: none;
                    border-radius: 50%;
                    background: #4CAF50;
                    color: white;
                    cursor: pointer;
                    font-size: 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: background 0.2s ease;
                }}
                
                .collapse-btn:hover {{
                    background: #45a049;
                }}
                
                .quality-selector {{
                    margin-bottom: 20px;
                }}
                
                .quality-option {{
                    display: flex;
                    align-items: center;
                    padding: 12px;
                    margin: 8px 0;
                    border-radius: 12px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    border: 2px solid transparent;
                }}
                
                .quality-option:hover {{
                    background: #f5f5f5;
                    transform: translateY(-1px);
                }}
                
                .quality-option.active {{
                    background: linear-gradient(135deg, #4CAF50, #45a049);
                    color: white;
                    border-color: #4CAF50;
                    transform: scale(1.02);
                }}
                
                .quality-info {{
                    flex-grow: 1;
                }}
                
                .quality-name {{
                    font-weight: 600;
                    font-size: 14px;
                    margin-bottom: 4px;
                }}
                
                .quality-details {{
                    font-size: 11px;
                    opacity: 0.8;
                }}
                
                .quality-badge {{
                    background: rgba(255,255,255,0.2);
                    color: currentColor;
                    padding: 4px 8px;
                    border-radius: 20px;
                    font-size: 10px;
                    font-weight: 500;
                }}
                
                .action-buttons {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 10px;
                    margin-top: 20px;
                }}
                
                .action-btn {{
                    padding: 12px;
                    border: none;
                    border-radius: 12px;
                    cursor: pointer;
                    font-weight: 600;
                    font-size: 13px;
                    transition: all 0.2s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                }}
                
                .download-btn {{
                    background: linear-gradient(135deg, #FF6B6B, #EE5A52);
                    color: white;
                    grid-column: span 2;
                }}
                
                .download-btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 25px rgba(255,107,107,0.4);
                }}
                
                .share-btn {{
                    background: linear-gradient(135deg, #4ECDC4, #44A08D);
                    color: white;
                }}
                
                .info-btn {{
                    background: linear-gradient(135deg, #45B7D1, #3498DB);
                    color: white;
                }}
                
                .stats-section {{
                    margin-top: 20px;
                    padding: 15px;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    border-radius: 12px;
                    color: white;
                }}
                
                .stats-title {{
                    font-size: 14px;
                    font-weight: 600;
                    margin-bottom: 12px;
                }}
                
                .stats-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 10px;
                }}
                
                .stat-item {{
                    text-align: center;
                    padding: 8px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 8px;
                }}
                
                .stat-value {{
                    font-size: 16px;
                    font-weight: 700;
                    display: block;
                }}
                
                .stat-label {{
                    font-size: 10px;
                    opacity: 0.8;
                }}
                
                .loading-indicator {{
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: rgba(255,255,255,0.95);
                    padding: 20px;
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    font-size: 14px;
                    font-weight: 500;
                    z-index: 2000;
                }}
                
                .loading-spinner {{
                    width: 20px;
                    height: 20px;
                    border: 2px solid #ddd;
                    border-top: 2px solid #4CAF50;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }}
                
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                
                .smart-recommendations {{
                    margin-top: 15px;
                    padding: 12px;
                    background: #FFF3E0;
                    border-left: 4px solid #FF9800;
                    border-radius: 8px;
                }}
                
                .recommendation-title {{
                    font-size: 12px;
                    font-weight: 600;
                    color: #E65100;
                    margin-bottom: 8px;
                }}
                
                .recommendation-text {{
                    font-size: 11px;
                    color: #BF360C;
                    line-height: 1.4;
                }}
            </style>
        </head>
        <body>
            <div class="smart-container">
                <div class="preview-display">
                    <img class="preview-image" id="mainPreview" alt="智能预览">
                </div>
                
                <div class="floating-panel" id="actionPanel">
                    <div class="panel-header">
                        <h3 class="panel-title">🎯 智能预览</h3>
                        <button class="collapse-btn" id="collapseBtn" onclick="togglePanel()">←</button>
                    </div>
                    
                    <div class="quality-selector" id="qualitySelector">
                        <!-- 动态生成质量选项 -->
                    </div>
                    
                    <div class="action-buttons">
                        <button class="action-btn download-btn" onclick="downloadOriginal()">
                            📥 下载原图
                        </button>
                        <button class="action-btn share-btn" onclick="shareImage()">
                            📤 分享
                        </button>
                        <button class="action-btn info-btn" onclick="showImageInfo()">
                            ℹ️ 详情
                        </button>
                    </div>
                    
                    <div class="stats-section">
                        <div class="stats-title">📊 图像统计</div>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <span class="stat-value">{self.original_width:,}</span>
                                <span class="stat-label">宽度(px)</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">{self.original_height:,}</span>
                                <span class="stat-label">高度(px)</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">{original_size:.1f}</span>
                                <span class="stat-label">大小(MB)</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">{output_format}</span>
                                <span class="stat-label">格式</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="smart-recommendations" id="recommendations">
                        <div class="recommendation-title">💡 智能建议</div>
                        <div class="recommendation-text" id="recommendationText">
                            正在分析最佳预览策略...
                        </div>
                    </div>
                </div>
                
                <div class="loading-indicator" id="loadingIndicator">
                    <div class="loading-spinner"></div>
                    <span>智能加载中...</span>
                </div>
            </div>
            
            <script>
                class SmartPreviewSystem {{
                    constructor(previews) {{
                        this.previews = previews;
                        this.currentQuality = 'instant';
                        this.panelCollapsed = false;
                        this.loadingTimes = {{}};
                        this.userPreferences = this.loadUserPreferences();
                        
                        this.mainPreview = document.getElementById('mainPreview');
                        this.actionPanel = document.getElementById('actionPanel');
                        this.qualitySelector = document.getElementById('qualitySelector');
                        this.loadingIndicator = document.getElementById('loadingIndicator');
                        this.recommendationText = document.getElementById('recommendationText');
                        
                        this.init();
                    }}
                    
                    async init() {{
                        this.buildQualitySelector();
                        await this.smartLoadSequence();
                        this.generateRecommendations();
                        this.trackUserBehavior();
                    }}
                    
                    buildQualitySelector() {{
                        const qualityOrder = ['instant', 'quick', 'detailed', 'full'];
                        
                        qualityOrder.forEach(quality => {{
                            if (!this.previews[quality]) return;
                            
                            const preview = this.previews[quality];
                            const option = document.createElement('div');
                            option.className = 'quality-option';
                            option.onclick = () => this.selectQuality(quality);
                            
                            option.innerHTML = `
                                <div class="quality-info">
                                    <div class="quality-name">${{preview.description}}</div>
                                    <div class="quality-details">
                                        ${{preview.width}}×${{preview.height}} | ${{preview.file_size_kb.toFixed(1)}}KB
                                    </div>
                                </div>
                                <div class="quality-badge">${{preview.quality}}%</div>
                            `;
                            
                            this.qualitySelector.appendChild(option);
                        }});
                    }}
                    
                    async smartLoadSequence() {{
                        // 智能加载序列：根据网络状况和用户偏好调整
                        const startTime = performance.now();
                        
                        // 首先加载瞬时预览
                        await this.loadPreview('instant');
                        
                        // 预测用户需求，预加载下一级别
                        const predictedNext = this.predictNextQuality();
                        if (predictedNext !== 'instant') {{
                            setTimeout(() => {{
                                this.preloadPreview(predictedNext);
                            }}, 500);
                        }}
                        
                        const loadTime = performance.now() - startTime;
                        this.loadingTimes['sequence'] = loadTime;
                        
                        this.hideLoadingIndicator();
                    }}
                    
                    async loadPreview(quality) {{
                        const preview = this.previews[quality];
                        if (!preview) return;
                        
                        const startTime = performance.now();
                        
                        return new Promise((resolve) => {{
                            const img = new Image();
                            img.onload = () => {{
                                this.mainPreview.src = img.src;
                                this.mainPreview.classList.add('loaded');
                                
                                const loadTime = performance.now() - startTime;
                                this.loadingTimes[quality] = loadTime;
                                
                                this.updateQualitySelector(quality);
                                resolve();
                            }};
                            img.src = 'data:image/webp;base64,' + preview.base64;
                        }});
                    }}
                    
                    preloadPreview(quality) {{
                        const preview = this.previews[quality];
                        if (!preview) return;
                        
                        const img = new Image();
                        img.src = 'data:image/webp;base64,' + preview.base64;
                    }}
                    
                    selectQuality(quality) {{
                        if (this.currentQuality === quality) return;
                        
                        this.currentQuality = quality;
                        this.loadPreview(quality);
                        this.saveUserPreference(quality);
                    }}
                    
                    updateQualitySelector(activeQuality) {{
                        const options = this.qualitySelector.querySelectorAll('.quality-option');
                        options.forEach((option, index) => {{
                            option.classList.remove('active');
                        }});
                        
                        const qualityOrder = ['instant', 'quick', 'detailed', 'full'];
                        const activeIndex = qualityOrder.indexOf(activeQuality);
                        if (activeIndex !== -1 && options[activeIndex]) {{
                            options[activeIndex].classList.add('active');
                        }}
                    }}
                    
                    predictNextQuality() {{
                        // 基于用户历史偏好和当前网络状况预测
                        const preferences = this.userPreferences;
                        const networkSpeed = this.estimateNetworkSpeed();
                        
                        if (preferences.favorite_quality) {{
                            return preferences.favorite_quality;
                        }}
                        
                        if (networkSpeed === 'fast') return 'detailed';
                        if (networkSpeed === 'medium') return 'quick';
                        return 'instant';
                    }}
                    
                    estimateNetworkSpeed() {{
                        const instantLoadTime = this.loadingTimes['instant'] || 1000;
                        if (instantLoadTime < 200) return 'fast';
                        if (instantLoadTime < 500) return 'medium';
                        return 'slow';
                    }}
                    
                    generateRecommendations() {{
                        const networkSpeed = this.estimateNetworkSpeed();
                        const imageSize = {original_size};
                        
                        let recommendation = '';
                        
                        if (imageSize > 10) {{
                            recommendation = '⚠️ 大图像文件，建议使用"详细预览"平衡质量与加载速度。';
                        }} else if (networkSpeed === 'fast') {{
                            recommendation = '⚡ 网络状况良好，可以使用"完整预览"获得最佳体验。';
                        }} else if (networkSpeed === 'slow') {{
                            recommendation = '🐌 网络较慢，推荐使用"快速预览"以获得更流畅的体验。';
                        }} else {{
                            recommendation = '✨ 推荐使用"详细预览"，在质量和速度之间取得最佳平衡。';
                        }}
                        
                        this.recommendationText.textContent = recommendation;
                    }}
                    
                    hideLoadingIndicator() {{
                        setTimeout(() => {{
                            this.loadingIndicator.style.opacity = '0';
                            setTimeout(() => {{
                                this.loadingIndicator.style.display = 'none';
                            }}, 300);
                        }}, 1000);
                    }}
                    
                    loadUserPreferences() {{
                        try {{
                            const saved = localStorage.getItem('smart_preview_preferences');
                            return saved ? JSON.parse(saved) : {{}};
                        }} catch {{
                            return {{}};
                        }}
                    }}
                    
                    saveUserPreference(quality) {{
                        try {{
                            const preferences = this.loadUserPreferences();
                            preferences.favorite_quality = quality;
                            preferences.last_used = new Date().toISOString();
                            localStorage.setItem('smart_preview_preferences', JSON.stringify(preferences));
                        }} catch {{
                            // 忽略存储错误
                        }}
                    }}
                    
                    trackUserBehavior() {{
                        // 简单的用户行为跟踪
                        let scrollCount = 0;
                        let qualityChanges = 0;
                        
                        window.addEventListener('scroll', () => {{
                            scrollCount++;
                        }});
                        
                        // 记录质量变更次数
                        const originalSelectQuality = this.selectQuality;
                        this.selectQuality = (quality) => {{
                            qualityChanges++;
                            originalSelectQuality.call(this, quality);
                        }};
                    }}
                }}
                
                // 全局函数
                let smartPreview;
                
                function togglePanel() {{
                    const panel = document.getElementById('actionPanel');
                    const btn = document.getElementById('collapseBtn');
                    
                    if (smartPreview.panelCollapsed) {{
                        panel.classList.remove('collapsed');
                        btn.textContent = '←';
                        smartPreview.panelCollapsed = false;
                    }} else {{
                        panel.classList.add('collapsed');
                        btn.textContent = '→';
                        smartPreview.panelCollapsed = true;
                    }}
                }}
                
                function downloadOriginal() {{
                    // 触发Streamlit的下载按钮
                    const event = new CustomEvent('streamlit:downloadOriginal');
                    window.parent.document.dispatchEvent(event);
                }}
                
                function shareImage() {{
                    if (navigator.share) {{
                        navigator.share({{
                            title: '长图分享',
                            text: '查看这个精美的长图！',
                            url: window.location.href
                        }});
                    }} else {{
                        // 复制链接到剪贴板
                        navigator.clipboard.writeText(window.location.href).then(() => {{
                            alert('链接已复制到剪贴板！');
                        }});
                    }}
                }}
                
                function showImageInfo() {{
                    const info = `
                        图像信息:
                        尺寸: {self.original_width:,} × {self.original_height:,} 像素
                        文件大小: {original_size:.2f} MB
                        格式: {output_format}
                        纵横比: {self.aspect_ratio:.2f}
                    `;
                    alert(info);
                }}
                
                // 初始化系统
                const previewsData = {previews_json};
                smartPreview = new SmartPreviewSystem(previewsData);
            </script>
        </body>
        </html>
        """
        
        return html_code

def render_smart_preview_panel(image_path: str, output_format: str):
    """渲染智能预览面板界面"""
    
    st.subheader("🧠 智能预览与快捷操作面板")
    
    # 初始化智能预览系统
    smart_system = SmartPreviewPanel(image_path)
    
    # 显示系统信息
    col_info1, col_info2, col_info3 = st.columns(3)
    
    with col_info1:
        st.metric("原图尺寸", f"{smart_system.original_width}×{smart_system.original_height}")
    
    with col_info2:
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        st.metric("文件大小", f"{file_size:.2f} MB")
    
    with col_info3:
        st.metric("长宽比", f"{smart_system.aspect_ratio:.2f}")
    
    # 生成智能预览
    with st.spinner("🔄 生成智能预览版本..."):
        previews = smart_system.generate_smart_previews()
    
    if previews:
        st.success(f"✅ 已生成 {len(previews)} 个智能预览级别")
        
        # 显示预览级别信息
        with st.expander("📋 预览级别详情", expanded=False):
            for level, info in previews.items():
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**{info['description']}**")
                with col2:
                    st.write(f"尺寸: {info['width']}×{info['height']}")
                with col3:
                    st.write(f"大小: {info['file_size_kb']:.1f}KB")
                with col4:
                    st.write(f"质量: {info['quality']}%")
        
        # 渲染智能预览面板
        html_content = smart_system.get_smart_panel_html(previews, output_format)
        components.html(html_content, height=800, scrolling=False)
        
        # 底部下载区域
        st.markdown("---")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader("📥 下载选项")
            with open(image_path, "rb") as file:
                st.download_button(
                    label="下载原始图像",
                    data=file.read(),
                    file_name=os.path.basename(image_path),
                    mime=f"image/{output_format.lower()}",
                    use_container_width=True,
                    type="primary"
                )
        
        with col2:
            st.subheader("🎯 智能特性")
            st.markdown("""
            - 🤖 智能质量预测
            - 📊 用户行为分析  
            - ⚡ 预加载优化
            - 💾 偏好记忆
            """)
        
        with col3:
            st.subheader("🚀 性能优势")
            st.markdown("""
            - 🏃‍♂️ 瞬时首屏
            - 🧠 智能推荐
            - 📱 响应式设计
            - 🔄 渐进式加载
            """)
    
    else:
        st.error("❌ 无法生成智能预览版本")

# 集成示例
def integrate_smart_preview():
    """集成智能预览面板的示例代码"""
    return '''
    # 在main.py中集成智能预览面板
    if actual_output_path and os.path.exists(actual_output_path):
        render_smart_preview_panel(actual_output_path, output_format)
    else:
        st.error("图像转换失败，请检查文件格式或系统依赖")
    '''

if __name__ == "__main__":
    st.title("方案四：智能预览与快捷操作面板演示")
    
    demo_image = "demo_smart.png"
    if os.path.exists(demo_image):
        render_smart_preview_panel(demo_image, "PNG")
    else:
        st.info("请准备演示图像文件以查看效果")