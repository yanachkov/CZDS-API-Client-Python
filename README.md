# CZDS API Client - Python

Modern, optimized Python client for downloading zone files via ICANN's Centralized Zone Data Service (CZDS) REST API.

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## ✨ Features

### 🚀 Performance Optimizations
- **64KB chunk transfers** with configurable sizes for optimal network performance
- **HTTP session reuse** for efficient connection management
- **Exponential backoff** retry strategy with smart timeouts
- **Optimized file I/O** with reduced system calls and strategic flushing

### 📊 Enhanced Progress Display
- **Real-time progress** with percentage completion
- **Clean output** with HH:MM:SS timestamps (no milliseconds)
- **File size preview** before download starts
- **Visual separators** for better readability
- **Detailed summary** at completion with timing statistics

### 🛡️ Robust Error Handling
- **Automatic token refresh** on expiration
- **Connection retry** with exponential backoff
- **Partial download tracking** for recovery
- **Clear error messages** with actionable information

### 📁 Smart File Management
- **Auto-rename existing files** with timestamp (prevents overwrite)
- **Configurable download directory**
- **Selective TLD filtering** for targeted downloads

---

## 🍺 Beer Token 
**If this script helped you download terabytes of zone files without losing sanity, consider sending me a beer. My server runs better when I'm hydrated.** 
- PayPal: https://www.paypal.com/paypalme/IvailoYanachkov 
- Revolut: http://revolut.me/yanachkov
  
**Not required, but always appreciated. 🙂**

## 📬 Contact
 - Email: yanchkov@gmail.com 
 - LinkedIn: https://www.linkedin.com/in/yanachkov/

---

## 📦 Installation

**Requirements:**
- Python 3.13+ (tested with 3.13.2)
- `requests` library

```bash
pip install requests
```

---

## ⚙️ Configuration

### Quick Start

1. **Copy the sample configuration:**
   ```bash
   cp config.sample.ini config.ini
   ```

2. **Edit `config.ini` with your credentials:**
   ```ini
   [account]
   username = your_email@example.com
   password = your_password

   [download]
   tlds = com,net,org
   ```

3. **Run the script:**
   ```bash
   python download.py
   ```

### Configuration Options

| Section | Option | Description | Default |
|---------|--------|-------------|---------|
| **account** | `username` | Your CZDS account email | Required |
| **account** | `password` | Your CZDS account password | Required |
| **api** | `authentication_url` | ICANN auth API endpoint | `https://account-api.icann.org` |
| **api** | `czds_url` | CZDS API endpoint | `https://czds-api.icann.org` |
| **download** | `working_directory` | Where to save zone files | `.` (current directory) |
| **download** | `tlds` | Comma-separated TLD list | _(empty = all approved)_ |
| **download** | `progress_report_interval_mb` | Progress update frequency (MB) | `50` |
| **download** | `chunk_size_kb` | Network chunk size (KB) | `64` |
| **download** | `buffer_size_kb` | File buffer size (KB) | `64` |

> **Note:** Leave `tlds` empty or omit it to download all approved TLDs.

---

## 🎯 Usage Examples

### Download All Approved TLDs
```ini
[download]
tlds = 
```

### Download Specific TLDs
```ini
[download]
tlds = com,net,org,info
```

### Custom Performance Tuning
```ini
[download]
chunk_size_kb = 128        # For faster networks
buffer_size_kb = 128       # Match chunk size
progress_report_interval_mb = 100  # Less frequent updates
```

---

## 📺 Output Example

```
12:34:56: Access token received successfully
12:34:56: The number of zone files to be downloaded is 3
────────────────────────────────────────────────────────────
12:34:56: Download process started
12:34:56: Using chunk size 64 KB, buffer size 64 KB
────────────────────────────────────────────────────────────
14:12:50: [1/2] Starting download .COM
14:12:50: File size: 4182 MB
14:12:51: Downloading com.txt.gz
14:12:51: Downloading bytes from https://czds-download-api.icann.org/czds/downloads/com.zone
14:13:30: Downloaded 50 MB - 1.2%
14:13:39: Downloaded 100 MB - 2.4%
14:13:47: Downloaded 150 MB - 3.6%
...
14:26:32: Downloaded 3900 MB - 93.2%
14:26:40: Downloaded 3950 MB - 94.4%
14:26:49: Downloaded 4000 MB - 95.6%
14:26:57: Downloaded 4050 MB - 96.8%
14:27:06: Downloaded 4100 MB - 98.0%
14:27:16: Downloaded 4150 MB - 99.2%
14:27:21: COMPLETED - com.txt.gz - Total: 4182 MB
────────────────────────────────────────────────────────────
12:50:22: [2/3] Starting download .NET
...
────────────────────────────────────────────────────────────
DOWNLOAD SUMMARY
────────────────────────────────────────────────────────────
Start time: 12:34:56
End time: 13:45:30
Files downloaded: 3
Files failed: 0
Total time: 01:10:34
────────────────────────────────────────────────────────────
```

---

## 🔧 Performance Tuning

Optimize for your network and system:

| Environment | chunk_size_kb | buffer_size_kb | Notes |
|-------------|---------------|----------------|-------|
| **Fast/Stable Network** | 128-256 | 128-256 | Max throughput |
| **Standard Network** | 64 | 64 | Balanced (default) |
| **Slow/Unstable Network** | 32 | 32 | Better recovery |
| **SSD Storage** | 128+ | 128+ | Leverage fast I/O |
| **HDD Storage** | 64 | 64 | Reduce seeks |

---

## 📋 File Management

**Existing files are automatically renamed before new downloads:**

```
Example:
  Existing: com.txt.gz
  Renamed:  com.txt.gz-2025-12-06-12-45.txt.gz
  New:      com.txt.gz (fresh download)
```

This ensures:
- ✅ No data loss
- ✅ Historical versions preserved
- ✅ Clean download process

---

## 🏗️ Architecture

**Single-file design** with integrated components:
- Authentication handling
- HTTP client with session reuse
- Progress tracking and reporting
- Error handling and retry logic
- File management

**INI-based configuration** for:
- Human-readable format
- Comment support with `#`
- Easy editing and version control

---

## 📚 Documentation

- [CZDS API Specifications](https://github.com/icann/czds-api-client-java/blob/master/docs/ICANN_CZDS_api.pdf)
- [Java Reference Implementation](https://github.com/icann/czds-api-client-java)
- [CZDS Web Portal](https://czds.icann.org/)

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

---

## 📄 License
This project is a heavily modified fork of the original
"CZDS API Client in Python" by ICANN. All original notices are preserved.

See [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **CZDS Portal:** https://czds.icann.org/
- **API Documentation:** https://github.com/icann/czds-api-client-java/tree/master/docs
- **Java Client:** https://github.com/icann/czds-api-client-java
