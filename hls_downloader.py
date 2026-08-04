# /// script
# dependencies = [
#     "requests>=2.31.0",
#     "tqdm>=4.66.0",
# ]
# ///

import os
import sys
import time
import shutil
import argparse
import subprocess
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    requests = None

# Public domain HLS test streams for demonstration
DEFAULT_TEST_STREAM = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"

class HLSDownloader:
    def __init__(self, m3u8_url: str, output_path: str = "output.mp4", max_workers: int = 8):
        self.m3u8_url = m3u8_url
        self.output_path = output_path
        self.max_workers = max_workers
        self.temp_dir = "temp_segments"

    def fetch_text(self, url: str) -> str:
        """Fetch URL content as string using requests or urllib."""
        if requests:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.text
        else:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read().decode('utf-8')

    def fetch_bytes(self, url: str) -> bytes:
        """Fetch binary content from URL."""
        if requests:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            return resp.content
        else:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                return response.read()

    def parse_m3u8(self, url: str):
        """Parse m3u8 playlist. If master playlist, pick highest resolution stream."""
        content = self.fetch_text(url)
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        if not lines or not lines[0].startswith("#EXTM3U"):
            raise ValueError("URL ini bukan berkas m3u8 HLS yang valid.")

        # Check if master playlist
        is_master = any("#EXT-X-STREAM-INF" in line for line in lines)
        if is_master:
            print("Detected Master Playlist. Selecting highest quality variant...")
            variant_url = None
            max_bandwidth = -1

            for i, line in enumerate(lines):
                if "#EXT-X-STREAM-INF" in line:
                    # extract bandwidth
                    bandwidth = 0
                    if "BANDWIDTH=" in line:
                        try:
                            bandwidth = int(line.split("BANDWIDTH=")[1].split(",")[0])
                        except ValueError:
                            pass
                    
                    next_line = lines[i + 1] if i + 1 < len(lines) else ""
                    if next_line and not next_line.startswith("#"):
                        if bandwidth > max_bandwidth:
                            max_bandwidth = bandwidth
                            variant_url = urljoin(url, next_line)
            
            if variant_url:
                print(f"Selected variant stream: {variant_url} (Bandwidth: {max_bandwidth})")
                return self.parse_m3u8(variant_url)
            else:
                raise ValueError("Tidak dapat menemukan stream varian pada master playlist.")

        # Media playlist (segment list)
        segment_urls = []
        for line in lines:
            if line.startswith("#"):
                continue
            segment_urls.append(urljoin(url, line))

        return segment_urls

    def download_segment(self, index: int, seg_url: str):
        """Download a single segment."""
        filename = os.path.join(self.temp_dir, f"segment_{index:05d}.ts")
        for attempt in range(3):
            try:
                data = self.fetch_bytes(seg_url)
                with open(filename, "wb") as f:
                    f.write(data)
                return index, True
            except Exception as e:
                if attempt == 2:
                    print(f"\nFailed segment {index}: {e}")
                    return index, False
                time.sleep(1)

    def merge_segments_ffmpeg(self, total_segments: int) -> bool:
        """Merge segments using FFmpeg if installed."""
        concat_file = os.path.join(self.temp_dir, "file_list.txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            for i in range(total_segments):
                seg_name = f"segment_{i:05d}.ts"
                f.write(f"file '{seg_name}'\n")

        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file, "-c", "copy", self.output_path
        ]
        
        try:
            subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def merge_segments_fallback(self, total_segments: int):
        """Direct binary concatenation fallback if FFmpeg is not available."""
        with open(self.output_path, "wb") as outfile:
            for i in range(total_segments):
                seg_path = os.path.join(self.temp_dir, f"segment_{i:05d}.ts")
                if os.path.exists(seg_path):
                    with open(seg_path, "rb") as infile:
                        shutil.copyfileobj(infile, outfile)

    def run(self):
        print(f"=== HLS Stream Downloader ===")
        print(f"Target URL : {self.m3u8_url}")
        print(f"Output File: {self.output_path}\n")

        # Create temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir, exist_ok=True)

        try:
            print("1. Parsing m3u8 playlist...")
            segment_urls = self.parse_m3u8(self.m3u8_url)
            total = len(segment_urls)
            print(f"-> Total segmen ditemukan: {total}\n")

            print(f"2. Mengunduh segmen dengan {self.max_workers} thread...")
            completed = 0
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self.download_segment, i, url): i for i, url in enumerate(segment_urls)}
                
                for future in as_completed(futures):
                    idx, success = future.result()
                    completed += 1
                    percent = (completed / total) * 100
                    elapsed = time.time() - start_time
                    speed = completed / elapsed if elapsed > 0 else 0
                    
                    sys.stdout.write(f"\rProgresi: [{completed}/{total}] {percent:.1f}% ({speed:.1f} segmen/detik)")
                    sys.stdout.flush()

            print("\n\n3. Menggabungkan segmen video...")
            ffmpeg_success = self.merge_segments_ffmpeg(total)
            
            if ffmpeg_success:
                print(f"-> Penggabungan selesai menggunakan FFmpeg! Berkas disimpan di '{self.output_path}'.")
            else:
                print("-> FFmpeg tidak terdeteksi. Menggunakan fallback penggabungkan berkas binary...")
                self.merge_segments_fallback(total)
                print(f"-> Selesai! Berkas disimpan di '{self.output_path}'.")

        finally:
            # Cleanup temp directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            print("4. Berkas sementara telah dibersihkan.")

def main():
    parser = argparse.ArgumentParser(description="HLS (.m3u8) Legal Stream Downloader & Merger")
    parser.add_argument("--url", type=str, default=DEFAULT_TEST_STREAM, help="URL berkas .m3u8 HLS")
    parser.add_argument("--output", type=str, default="sample_video.mp4", help="Nama berkas output (misal: output.mp4)")
    parser.add_argument("--threads", type=int, default=8, help="Jumlah worker thread pengunduhan")

    args = parser.parse_args()

    downloader = HLSDownloader(m3u8_url=args.url, output_path=args.output, max_workers=args.threads)
    downloader.run()

if __name__ == "__main__":
    main()
