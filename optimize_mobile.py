#!/usr/bin/env python3
"""
Mobile Optimization Script for CinematicPOV Sync Engine
Optimizes Streamlit app for mobile devices
"""

import os
import json
from pathlib import Path

def create_mobile_config():
    """Create Streamlit config optimized for mobile"""
    
    config_content = """
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#262730"
textColor = "#FAFAFA"
font = "sans serif"

[server]
headless = true
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 200

[browser]
gatherUsageStats = false

[client]
showErrorDetails = false
toolbarMode = "minimal"
"""
    
    # Create .streamlit directory if it doesn't exist
    streamlit_dir = Path('.streamlit')
    streamlit_dir.mkdir(exist_ok=True)
    
    # Write config
    config_path = streamlit_dir / 'config.toml'
    with open(config_path, 'w') as f:
        f.write(config_content.strip())
    
    print(f"✅ Created mobile config: {config_path}")


def create_pwa_manifest():
    """Create Progressive Web App manifest"""
    
    manifest = {
        "name": "CinematicPOV Sync Engine",
        "short_name": "CinematicPOV",
        "description": "AI-powered media transcription and POV narrative engine",
        "start_url": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#0E1117",
        "theme_color": "#FF4B4B",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    
    # Create static directory
    static_dir = Path('static')
    static_dir.mkdir(exist_ok=True)
    
    # Write manifest
    manifest_path = static_dir / 'manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Created PWA manifest: {manifest_path}")


def create_mobile_css():
    """Create mobile-optimized CSS"""
    
    css_content = """
/* Mobile-First Responsive Design */
@media (max-width: 768px) {
    .main .block-container {
        padding: 1rem;
        max-width: 100%;
    }
    
    /* Touch-friendly buttons */
    .stButton button {
        min-height: 44px;
        font-size: 16px;
        padding: 12px 24px;
    }
    
    /* Improved text inputs */
    .stTextInput input {
        min-height: 44px;
        font-size: 16px;
    }
    
    /* Progress bars */
    .stProgress > div {
        height: 8px;
    }
    
    /* File uploader */
    .stFileUploader {
        font-size: 14px;
    }
}

/* Optimize for very small screens */
@media (max-width: 480px) {
    .main .block-container {
        padding: 0.5rem;
    }
    
    h1 {
        font-size: 1.5rem;
    }
    
    h2 {
        font-size: 1.25rem;
    }
}

/* Loading states */
.stSpinner {
    text-align: center;
}

/* Error messages */
.stAlert {
    border-radius: 8px;
    margin: 1rem 0;
}

/* Performance optimization - reduce animations on mobile */
@media (prefers-reduced-motion: reduce) {
    * {
        animation: none !important;
        transition: none !important;
    }
}
"""
    
    # Create static directory
    static_dir = Path('static')
    static_dir.mkdir(exist_ok=True)
    
    # Write CSS
    css_path = static_dir / 'mobile.css'
    with open(css_path, 'w') as f:
        f.write(css_content.strip())
    
    print(f"✅ Created mobile CSS: {css_path}")


def optimize_images():
    """Create placeholder for image optimization"""
    
    static_dir = Path('static')
    static_dir.mkdir(exist_ok=True)
    
    readme = """
# Static Assets

Place your optimized images here:
- icon-192.png (192x192 PWA icon)
- icon-512.png (512x512 PWA icon)
- favicon.ico (32x32 favicon)

Optimization tips:
- Use WebP format for better compression
- Keep image sizes small (<100KB each)
- Use responsive images for different screen sizes
"""
    
    readme_path = static_dir / 'README.md'
    with open(readme_path, 'w') as f:
        f.write(readme.strip())
    
    print(f"✅ Created static assets guide: {readme_path}")


def main():
    """Run all mobile optimizations"""
    print("🎬 CinematicPOV Sync Engine - Mobile Optimization")
    print("=" * 60)
    
    create_mobile_config()
    create_pwa_manifest()
    create_mobile_css()
    optimize_images()
    
    print("=" * 60)
    print("✅ Mobile optimization complete!")
    print("\n📱 Next steps:")
    print("   1. Add your app icons to static/ directory")
    print("   2. Test on mobile devices or emulators")
    print("   3. Deploy to Streamlit Cloud")
    print("=" * 60)


if __name__ == '__main__':
    main()
