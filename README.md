# HLS Legal Stream Downloader & Merger

Perkakas Python untuk mengunduh berkas streaming HLS (`.m3u8`) domain publik/sampel legal secara paralel dan mengolahnya menjadi berkas `.mp4`.

## Fitur
- Support **PEP 723 Script Metadata** (Otomatis install dependensi dengan `uv`).
- Pemrosesan **Master Playlist** & seleksi kualitas otomatis.
- **Multithreading** pengunduhan segmen (`.ts`).
- Penggabungan via **FFmpeg** (dengan fallback binary concatenation jika FFmpeg tidak terpasang).

## Cara Menjalankan dengan `uv`

### 1. Jalankan Langsung Tanpa Install Manual
`uv` akan secara otomatis mengunduh dependensi (`requests`, `tqdm`) yang dibutuhkan:

```bash
uv run hls_downloader.py
```

### 2. Mengunduh Stream HLS Kustom (Public Domain / Sampel)
```bash
uv run hls_downloader.py --url "https://domain-publik/stream.m3u8" --output "video_saya.mp4" --threads 16
```

### 3. Opsi Parameter
- `--url` : URL berkas `.m3u8` (Default: Big Buck Bunny HLS Test Stream).
- `--output` : Nama berkas output (Default: `sample_video.mp4`).
- `--threads` : Jumlah koneksi thread bersamaan (Default: `8`).
