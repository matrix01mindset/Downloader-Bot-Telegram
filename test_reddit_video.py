import requests
import os
import tempfile
import time

video_url = 'https://v.redd.it/92567y9qsmif1/DASH_480.mp4?source=fallback'
print('Testing video download...')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.reddit.com/',
    'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
    'Accept-Language': 'en-US,en;q=0.5',
    'Range': 'bytes=0-'
}

try:
    r = requests.get(video_url, headers=headers, stream=True, timeout=10)
    print(f'Status: {r.status_code}')
    print(f'Content-Type: {r.headers.get("content-type")}')
    print(f'Content-Length: {r.headers.get("content-length")}')
    
    if r.status_code in [200, 206]:  # Accept both OK and Partial Content
        print(f'✅ Video accessible (Status: {r.status_code})')
        
        # Test download
        temp_dir = tempfile.mkdtemp()
        filename = f"reddit_test_{int(time.time())}.mp4"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(file_path)
        print(f'✅ Video downloaded: {file_path} ({file_size} bytes)')
        
        # Cleanup
        os.remove(file_path)
        os.rmdir(temp_dir)
        print('✅ Test completed successfully')
    else:
        print('❌ Video not accessible')
        print(f'Response: {r.text[:200]}')
        
except Exception as e:
    print(f'❌ Error: {e}')