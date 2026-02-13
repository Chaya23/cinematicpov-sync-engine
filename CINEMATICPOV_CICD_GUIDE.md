# 🎬 CinematicPOV Sync Engine v6.0 - CI/CD Setup Guide

## 📱 Mobile-First Automation Stack with Audio Processing & Performance Monitoring

---

## 🚀 Quick Start

This CI/CD pipeline is specifically designed for your **multimodal cinematic POV sync engine** with:
- ✅ **Audio Processing Tests** - Validates FFmpeg, yt-dlp, and transcription pipeline
- ✅ **Performance Monitoring** - Tracks memory, CPU, and processing speed
- ✅ **Mobile-First Deployment** - Optimized for mobile devices
- ✅ **Security Scanning** - Automated dependency and code security checks

---

## 📦 Repository Structure

```
cinematicpov-sync-engine/
├── .github/
│   └── workflows/
│       └── cinematicpov-cicd.yml    # Main CI/CD pipeline
├── scripts/
│   ├── validate_api_keys.py         # API key validation
│   ├── monitor_performance.py       # Performance monitoring
│   └── optimize_mobile.py           # Mobile optimization
├── tests/
│   ├── test_audio_processing.py     # Audio pipeline tests
│   ├── test_performance.py          # Performance benchmarks
│   └── test_api_mocks.py            # API mock tests
├── static/
│   ├── manifest.json                # PWA manifest
│   └── mobile.css                   # Mobile styles
├── .streamlit/
│   └── config.toml                  # Streamlit mobile config
├── requirements.txt                 # Python dependencies
├── Dockerfile.mobile                # Mobile-optimized container
└── app.py                           # Your Streamlit app
```

---

## 🔧 Setup Instructions

### Step 1: Clone and Prepare Repository

```bash
# Create your repository
git init cinematicpov-sync-engine
cd cinematicpov-sync-engine

# Copy all CI/CD files to your repo
# (Files are already organized in the structure above)
```

### Step 2: Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret Name | Description | Required |
|------------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key (starts with sk-) | ✅ Yes |
| `GOOGLE_API_KEY` | Your Google Gemini API key | ✅ Yes |
| `DOCKER_USERNAME` | Docker Hub username | ⚪ Optional |
| `DOCKER_PASSWORD` | Docker Hub password/token | ⚪ Optional |

### Step 3: Install Dependencies Locally

```bash
# Install system dependencies (macOS)
brew install ffmpeg

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y ffmpeg libsndfile1 portaudio19-dev

# Install Python dependencies
pip install -r requirements.txt
```

### Step 4: Test Locally

```bash
# Run audio processing tests
pytest tests/test_audio_processing.py -v

# Run performance benchmarks
pytest tests/test_performance.py --benchmark-only

# Validate API keys
python scripts/validate_api_keys.py

# Run the app
streamlit run app.py
```

### Step 5: Push to GitHub

```bash
git add .
git commit -m "Add CinematicPOV CI/CD pipeline"
git push origin main
```

The pipeline will automatically trigger! 🎉

---

## 🔄 CI/CD Pipeline Workflow

### On Every Push/Pull Request:

1. **Security Scan** (2-3 min)
   - Checks dependencies for vulnerabilities
   - Scans code for security issues
   - Generates security reports

2. **Audio Processing Tests** (5-10 min)
   - Validates FFmpeg installation
   - Tests audio download with yt-dlp
   - Mocks Whisper API calls
   - Tests Gemini speaker identification
   - Validates chunk processing for 23-min episodes

3. **Performance Tests** (3-5 min)
   - Benchmarks download speed
   - Tests transcription performance
   - Monitors memory usage
   - Tests concurrent processing

4. **API Validation** (1-2 min)
   - Validates API key formats
   - Tests API connectivity (mocked)

### On Push to Main Branch:

5. **Mobile Build** (5-7 min)
   - Optimizes for mobile devices
   - Tests mobile responsiveness
   - Builds Docker image
   - Pushes to Docker Hub (if configured)

6. **PWA Deployment** (1-2 min)
   - Deploys to Streamlit Cloud
   - Applies mobile-first configuration

7. **Post-Deployment Monitoring** (1 min)
   - Health checks
   - Performance baseline
   - Generates deployment summary

**Total Pipeline Time: ~15-30 minutes**

---

## 📱 Mobile Optimization Features

### PWA Support
- Install as app on mobile devices
- Offline-capable manifest
- Touch-optimized UI (44px minimum button size)
- Responsive layout for all screen sizes

### Performance
- Lazy loading for large files
- Progress indicators for long operations
- Memory-efficient chunk processing
- Optimized for slow connections

### UX Improvements
- Large touch targets
- Mobile-friendly file upload
- Progress bars for 23-minute episodes
- Real-time processing updates

---

## 🧪 Testing Your Audio Pipeline

### Test Audio Download
```python
# tests/test_audio_processing.py includes:
- FFmpeg installation check
- yt-dlp download mock
- Audio format conversion
- Error handling for invalid URLs
```

### Test Transcription
```python
# Whisper API tests:
- Verbatim accuracy (95%+ required)
- Chunk processing for long files
- Timeout handling (60s max)
```

### Test Speaker Mapping
```python
# Gemini API tests:
- Speaker identification
- Character name mapping
- Cast list integration
```

---

## 📊 Performance Monitoring

### Metrics Tracked
- **CPU Usage** - Should stay under 80%
- **Memory Usage** - Should stay under 1GB
- **Processing Speed** - Benchmarked per operation
- **Network I/O** - Upload/download tracking

### Access Performance Reports
```bash
# Run locally
python scripts/monitor_performance.py

# View in GitHub Actions
# Go to Actions tab → Select workflow run → Check artifacts
```

---

## 🌐 Deployment Options

### Option A: Streamlit Cloud (Recommended)
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repository
3. Select branch: `main`
4. Add secrets: `OPENAI_API_KEY`, `GOOGLE_API_KEY`
5. Deploy! 🚀

### Option B: Docker Container
```bash
# Build mobile-optimized image
docker build -f Dockerfile.mobile -t cinematicpov:latest .

# Run locally
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=your_key \
  -e GOOGLE_API_KEY=your_key \
  cinematicpov:latest

# Deploy to cloud provider
docker push your-username/cinematicpov:latest
```

### Option C: Mobile App Wrapper
Use tools like **Capacitor** or **Cordova** to wrap the Streamlit app as a native mobile app.

---

## 🔍 Pipeline Status & Badges

Add this to your README.md:

```markdown
![CI/CD Status](https://github.com/YOUR_USERNAME/cinematicpov-sync-engine/workflows/CinematicPOV%20Sync%20Engine%20CI/CD/badge.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![Mobile](https://img.shields.io/badge/mobile-optimized-blue)
```

---

## 🎯 Key Features of This Pipeline

### ✅ Audio Processing Validation
- Tests FFmpeg installation
- Validates audio extraction
- Mocks API calls to avoid costs during CI
- Tests 23-minute episode chunk processing

### ✅ Performance Benchmarking
- Measures download speed
- Tracks transcription time
- Monitors memory usage
- Tests concurrent requests

### ✅ Mobile-First Design
- Responsive layouts
- Touch-optimized controls
- PWA manifest for app-like experience
- Optimized for slow connections

### ✅ Security & Quality
- Dependency vulnerability scanning
- Code security analysis
- API key validation
- Automated testing

---

## 🆘 Troubleshooting

### Pipeline Fails on Audio Tests
**Issue:** FFmpeg not found  
**Solution:** Ensure `sudo apt-get install ffmpeg` is in the workflow

### API Key Validation Fails
**Issue:** Keys not configured  
**Solution:** Add secrets in GitHub Settings → Secrets

### Performance Tests Timeout
**Issue:** Tests take too long  
**Solution:** Increase timeout in pytest.ini or use `@pytest.mark.timeout(120)`

### Mobile Build Fails
**Issue:** Docker build errors  
**Solution:** Check Dockerfile.mobile for missing dependencies

---

## 💡 Best Practices

1. **Use Mocks for CI** - Don't call real APIs in tests (costs money)
2. **Test Locally First** - Run `pytest` before pushing
3. **Monitor Performance** - Check benchmark reports regularly
4. **Keep Secrets Safe** - Never commit API keys
5. **Mobile Test** - Use Chrome DevTools mobile emulator

---

## 📚 Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Streamlit Docs](https://docs.streamlit.io)
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [Google Gemini API](https://ai.google.dev/docs)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)

---

## 🎬 Next Steps

1. ✅ Copy all files to your repository
2. ✅ Configure GitHub secrets
3. ✅ Push to GitHub (pipeline auto-runs)
4. ✅ Deploy to Streamlit Cloud
5. ✅ Test on mobile device
6. ✅ Start processing your Wizards episodes!

---

**Happy building! 🎉**

Your CinematicPOV Sync Engine is now production-ready with:
- Automated testing
- Mobile optimization
- Performance monitoring
- Secure deployment

Questions? Check the pipeline logs in GitHub Actions or review test outputs.
