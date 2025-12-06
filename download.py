"""
CZDS Zone File Downloader - Optimized Python Client
====================================================
Downloads zone files from ICANN's Centralized Zone Data Service (CZDS) API.

Features:
- High-performance downloads with configurable chunk/buffer sizes
- Automatic token refresh and retry logic with exponential backoff
- Progress tracking with percentage completion
- Automatic file renaming to preserve existing downloads
- Clean, readable output with timestamps

Author: Modified and optimized version
License: See LICENSE file
"""

import sys
import os
import datetime
import re
import time
import json
import requests
import configparser
from requests.exceptions import ChunkedEncodingError, ConnectionError
from urllib3.exceptions import ProtocolError

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def now_str():
    """Return current time in HH:MM:SS format for clean logging."""
    return datetime.datetime.now().strftime('%H:%M:%S')

def authenticate(username, password, authen_base_url):
    """
    Authenticate with CZDS API and obtain access token.
    
    Args:
        username: CZDS account email
        password: CZDS account password
        authen_base_url: Authentication API base URL
        
    Returns:
        str: Access token for subsequent API calls
        
    Raises:
        SystemExit: On authentication failure
    """
    authen_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    credential = {'username': username, 'password': password}
    authen_url = authen_base_url + '/api/authenticate'
    
    response = requests.post(authen_url, data=json.dumps(credential), headers=authen_headers)
    status_code = response.status_code
    
    if status_code == 200:
        access_token = response.json()['accessToken']
        print(f'{now_str()}: Access token received successfully')
        return access_token
    elif status_code == 404:
        sys.stderr.write(f"Invalid url {authen_url}\n")
        exit(1)
    elif status_code == 401:
        sys.stderr.write("Invalid username/password. Please reset your password via web\n")
        exit(1)
    elif status_code == 500:
        sys.stderr.write("Internal server error. Please try again later\n")
        exit(1)
    else:
        sys.stderr.write(f"Failed to authenticate user {username} with error code {status_code}\n")
        exit(1)

# Global HTTP session for connection reuse (improves performance)
_session = requests.Session()

def get_bearer_headers(access_token):
    """
    Build HTTP headers with Bearer token authentication.
    
    Args:
        access_token: OAuth access token from authentication
        
    Returns:
        dict: Headers dictionary ready for requests
    """
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

def do_get(url, access_token):
    """
    Execute HTTP GET request with authentication.
    
    Args:
        url: Target URL
        access_token: OAuth access token
        
    Returns:
        Response: Streaming response object (timeout: 5 minutes)
    """
    bearer_headers = get_bearer_headers(access_token)
    response = _session.get(url, params=None, headers=bearer_headers, stream=True, timeout=300)
    return response

def do_head(url, access_token):
    """
    Execute HTTP HEAD request for metadata (filename, size).
    
    Args:
        url: Target URL
        access_token: OAuth access token
        
    Returns:
        Response: Response object (timeout: 1 minute)
    """
    bearer_headers = get_bearer_headers(access_token)
    response = _session.head(url, headers=bearer_headers, timeout=60)
    return response

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

# Load configuration from config.ini or environment variable
try:
    config = configparser.ConfigParser()
    if 'CZDS_CONFIG' in os.environ:
        # Support config from environment variable for Docker/automation
        config.read_string(os.environ['CZDS_CONFIG'])
    else:
        config.read('config.ini')
except Exception as e:
    sys.stderr.write(f"Error loading config.ini file: {e}\n")
    exit(1)

# Extract configuration values
username = config.get('account', 'username')
password = config.get('account', 'password')
authen_base_url = config.get('api', 'authentication_url')
czds_base_url = config.get('api', 'czds_url')

# Parse TLD list (comma-separated)
tlds_str = config.get('download', 'tlds', fallback='')
tlds = [t.strip() for t in tlds_str.split(',') if t.strip()] if tlds_str else []

# Download settings
working_directory = config.get('download', 'working_directory', fallback='.')
progress_interval_mb = config.getint('download', 'progress_report_interval_mb', fallback=50)
chunk_size_kb = config.getint('download', 'chunk_size_kb', fallback=64)
buffer_size_kb = config.getint('download', 'buffer_size_kb', fallback=64)

# Convert KB to bytes for internal use
chunk_size = chunk_size_kb * 1024
buffer_size = buffer_size_kb * 1024

# Validate required configuration parameters
if not username:
    sys.stderr.write("'account.username' parameter not found in the config.ini file\n")
    exit(1)

if not password:
    sys.stderr.write("'account.password' parameter not found in the config.ini file\n")
    exit(1)

if not authen_base_url:
    sys.stderr.write("'api.authentication_url' parameter not found in the config.ini file\n")
    exit(1)

if not czds_base_url:
    sys.stderr.write("'api.czds_url' parameter not found in the config.ini file\n")
    exit(1)

def refresh_token(username, password, authen_base_url):
    """Helper function to refresh access token."""
    return authenticate(username, password, authen_base_url)

# ============================================================================
# INITIAL AUTHENTICATION
# ============================================================================

print(f"Authenticate user {username}")
access_token = refresh_token(username, password, authen_base_url)

# Maximum retry attempts for failed operations
MAX_RETRIES = 3

# ============================================================================
# ZONE LINKS RETRIEVAL
# ============================================================================

def get_zone_links(czds_base_url, access_token, username, password, authen_base_url):
    """
    Retrieve list of available zone file download URLs from CZDS API.
    
    Args:
        czds_base_url: CZDS API base URL
        access_token: Current access token
        username, password, authen_base_url: For token refresh if needed
        
    Returns:
        tuple: (list of download URLs, updated access_token)
    """
    links_url = f"{czds_base_url}/czds/downloads/links"
    retries = 0
    
    while retries < MAX_RETRIES:
        links_response = do_get(links_url, access_token)
        status_code = links_response.status_code
        
        if status_code == 200:
            zone_links = links_response.json()
            count = len(tlds) if tlds else len(zone_links)
            print(f"{now_str()}: The number of zone files to be downloaded is {count}")
            print("─" * 60)
            return zone_links, access_token
        elif status_code == 401:
            print(f"The access_token has been expired. Re-authenticate user {username}")
            access_token = refresh_token(username, password, authen_base_url)
            retries += 1
        else:
            sys.stderr.write(f"Failed to get zone links from {links_url} with error code {status_code}\n")
            return None, access_token
    
    sys.stderr.write(f"Failed to get zone links after {MAX_RETRIES} retries\n")
    return None, access_token

zone_links, access_token = get_zone_links(czds_base_url, access_token, username, password, authen_base_url)
if not zone_links:
    exit(1)

# ============================================================================
# FILE DOWNLOAD FUNCTIONS
# ============================================================================

def parse_content_disposition(header_value):
    """
    Extract filename from Content-Disposition HTTP header.
    
    Args:
        header_value: Raw Content-Disposition header string
        
    Returns:
        str: Extracted filename or None if not found
    """
    if not header_value:
        return None
    
    match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', header_value, re.IGNORECASE)
    if match:
        filename = match.group(1).strip('\'"')
        return filename
    return None

def download_one_zone(url, output_directory, access_token, username, password, authen_base_url, progress_interval_mb, chunk_size, buffer_size):
    """
    Download a single zone file with progress tracking and error recovery.
    
    Features:
    - Automatic file renaming if exists (preserves old versions)
    - Progress reporting with percentage completion
    - Exponential backoff retry on connection errors
    - Token refresh on 401 errors
    
    Args:
        url: Zone file download URL
        output_directory: Where to save the file
        access_token: Current OAuth token
        username, password, authen_base_url: For authentication refresh
        progress_interval_mb: How often to report progress (in MB)
        chunk_size: Network transfer chunk size (bytes)
        buffer_size: File write buffer size (bytes)
        
    Returns:
        bool: True if download succeeded, False otherwise
    """
    content_disposition = None
    filename = None
    file_size = None
    
    def fetch_metadata():
        """
        Fetch file metadata (filename, size) via HEAD request.
        Handles token expiration and retries with refreshed token.
        """
        nonlocal content_disposition, filename, file_size, access_token
        try:
            head_response = do_head(url, access_token)
            if head_response.status_code == 200:
                content_disposition = head_response.headers.get('content-disposition', '')
                filename = parse_content_disposition(content_disposition)
                content_length = head_response.headers.get('content-length')
                if content_length:
                    file_size = int(content_length)
            elif head_response.status_code == 401:
                print(f"{now_str()}: The access_token has been expired. Re-authenticate user {username}")
                access_token = refresh_token(username, password, authen_base_url)
                return False
        except:
            pass
        return True
    
    fetch_metadata()
    
    # Generate fallback filename from URL if Content-Disposition header missing
    if not filename:
        url_part = url.rsplit('/', 1)[-1]
        tld = url_part.rsplit('.', 2)[0] if '.' in url_part else url_part
        filename = f"{tld}.txt.gz"
    
    path = os.path.join(output_directory, filename)
    
    # Rename existing file with timestamp to preserve old version
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        file_datetime = datetime.datetime.fromtimestamp(mtime)
        date_suffix = file_datetime.strftime('%Y-%m-%d-%H-%M')
        renamed_filename = f"{filename}-{date_suffix}.txt.gz"
        renamed_path = os.path.join(output_directory, renamed_filename)
        os.rename(path, renamed_path)
        print(f"{now_str()}: Existing file renamed to {renamed_filename}")
    
    # Display file size if available
    if file_size:
        total_mb = file_size // (1024 * 1024)
        print(f"{now_str()}: File size: {total_mb} MB")
    
    # Download loop with retry logic
    for retry in range(MAX_RETRIES):
        try:
            download_zone_response = do_get(url, access_token)
            status_code = download_zone_response.status_code
            
            if status_code == 200:
                downloaded_size = 0
                last_reported = 0
                report_interval = progress_interval_mb * 1024 * 1024
                
                if not file_size:
                    content_length = download_zone_response.headers.get('content-length')
                    if content_length:
                        file_size = int(content_length)
                
                print(f"{now_str()}: Downloading {filename}")
                print(f"{now_str()}: Downloading bytes from {url}")
                
                # Stream download with progress tracking
                try:
                    with open(path, 'wb', buffering=buffer_size) as f:
                        for chunk in download_zone_response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                # Report progress at configured intervals
                                if downloaded_size - last_reported >= report_interval:
                                    mb_downloaded = downloaded_size // (1024 * 1024)
                                    if file_size:
                                        percentage = (downloaded_size / file_size) * 100
                                        print(f"{now_str()}: Downloaded {mb_downloaded} MB - {percentage:.1f}%")
                                    else:
                                        print(f"{now_str()}: Downloaded {mb_downloaded} MB")
                                    last_reported = downloaded_size
                                    f.flush()  # Flush buffer on progress report
                        
                        # Final flush and sync to disk
                        f.flush()
                        os.fsync(f.fileno())
                    
                    final_size = os.path.getsize(path)
                    final_mb = final_size // (1024 * 1024)
                    print(f"{now_str()}: COMPLETED - {filename} - Total: {final_mb} MB")
                    print("─" * 60)
                    return True
                except (ChunkedEncodingError, ProtocolError, ConnectionError) as e:
                    raise
                except OSError as e:
                    sys.stderr.write(f"Failed to write file {path}: {e}\n")
                    return False
                    
            elif status_code == 401:
                print(f"{now_str()}: The access_token has been expired. Re-authenticate user {username}")
                access_token = refresh_token(username, password, authen_base_url)
                if not fetch_metadata():
                    continue
                continue
            elif status_code == 404:
                print(f"{now_str()}: No zone file found for {url}")
                return False
            else:
                print(f"{now_str()}: Server returned status {status_code}. Retrying...")
                if retry < MAX_RETRIES - 1:
                    wait_time = min(5 * (2 ** retry), 30)
                    time.sleep(wait_time)
                continue
                
        except (ChunkedEncodingError, ProtocolError, ConnectionError) as e:
            # Handle network interruptions with exponential backoff
            print(f"{now_str()}: CONNECTION BROKEN (attempt {retry + 1}/{MAX_RETRIES})")
            
            if os.path.exists(path):
                current_size = os.path.getsize(path)
                print(f"{now_str()}: Partial download saved: {current_size // (1024 * 1024)} MB")
            
            if retry < MAX_RETRIES - 1:
                # Exponential backoff: 5s, 10s, 20s, 30s (capped at 30s)
                wait_time = min(5 * (2 ** retry), 30)
                print(f"{now_str()}: Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"{now_str()}: Max retries reached for {filename}. Partial file may remain.")
                return False
        except Exception as e:
            print(f"{now_str()}: Error downloading {url}: {e}")
            if retry < MAX_RETRIES - 1:
                wait_time = min(5 * (2 ** retry), 30)
                time.sleep(wait_time)
            else:
                return False
    
    return False

def download_zone_files(urls, working_directory, access_token, username, password, authen_base_url, tlds, progress_interval_mb, chunk_size, buffer_size):
    """
    Download all zone files, optionally filtered by TLD list.
    
    Args:
        urls: List of zone file download URLs
        working_directory: Output directory
        access_token: OAuth token
        username, password, authen_base_url: For authentication
        tlds: List of TLDs to filter (empty = download all)
        progress_interval_mb: Progress report frequency
        chunk_size, buffer_size: Performance tuning parameters
        
    Returns:
        tuple: (successful_downloads, failed_downloads)
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(working_directory):
        os.makedirs(working_directory)
    
    # Filter URLs by TLD list if specified
    if tlds:
        suffix_set = {f"{tld}.zone" for tld in tlds}
        urls_to_download = [link for link in urls if any(link.endswith(suffix) for suffix in suffix_set)]
    else:
        urls_to_download = urls
    
    # Track statistics
    successful_downloads = 0
    failed_downloads = 0
    
    # Download each zone file
    for i, link in enumerate(urls_to_download):
        url_part = link.rsplit('/', 1)[-1]
        tld_ext = url_part.rsplit('.', 2)[0].upper() if '.' in url_part else url_part.upper()
        print(f"{now_str()}: [{i + 1}/{len(urls_to_download)}] Starting download .{tld_ext}")
        
        if download_one_zone(link, working_directory, access_token, username, password, authen_base_url, progress_interval_mb, chunk_size, buffer_size):
            successful_downloads += 1
        else:
            failed_downloads += 1
    
    return successful_downloads, failed_downloads

# ============================================================================
# MAIN EXECUTION
# ============================================================================

# Record start time for statistics
start_time = datetime.datetime.now()
print(f"{now_str()}: Download process started")
print(f"{now_str()}: Using chunk size {chunk_size_kb} KB, buffer size {buffer_size_kb} KB")
print("─" * 60)

# Execute download process
successful_downloads, failed_downloads = download_zone_files(
    zone_links, 
    working_directory, 
    access_token, 
    username, 
    password, 
    authen_base_url, 
    tlds, 
    progress_interval_mb, 
    chunk_size, 
    buffer_size
)

# Calculate elapsed time
end_time = datetime.datetime.now()
total_time = end_time - start_time

hours = total_time.seconds // 3600
minutes = (total_time.seconds % 3600) // 60
seconds = total_time.seconds % 60

# Display final summary
print("DOWNLOAD SUMMARY")

print(f"Start time: {start_time.strftime('%H:%M:%S')}")
print(f"End time: {end_time.strftime('%H:%M:%S')}")
print(f"Files downloaded: {successful_downloads}")
print(f"Files failed: {failed_downloads}")
print(f"Total time: {hours:02d}:{minutes:02d}:{seconds:02d}")
