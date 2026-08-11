# 🏴‍☠️ I Am Not Pirates — CLI Media Scraper & Downloader

![Version](https://img.shields.io/badge/version-v1.1.0-blue)

Aplikasi CLI Python interaktif modern berkinerja tinggi untuk menjelajah, mencari, dan mendownload Film serta TV Series secara otomatis.  
*A high-performance, modern interactive Python CLI application to browse, search, and automatically download Movies and TV Series.*

Ditenagai oleh mesin pengunduh **N_m3u8DL-RE** multi-threaded, manajemen database SQLite, struktur folder media standar **Jellyfin / Plex**, konversi subtitle otomatis, sistem **Playwright Chromium Auto-Healing**, dan sistem **FFmpeg Auto-Healing**.  
*Powered by the ultra-fast multi-threaded **N_m3u8DL-RE** download engine, SQLite database management, **Jellyfin / Plex** standard media folder structure, automatic subtitle conversion, **Playwright Chromium Auto-Healing**, and a **Smart FFmpeg Auto-Healing System**.*

---

## ✨ Fitur Utama / Key Features

- **🔍 Pencarian Media Cepat / Fast Media Search**: Cari film atau TV Series langsung berdasarkan judul dari CLI via integrasi API internal / *Search for movies or TV series directly by title from the CLI via internal API integration.*
- **⚡ Pengunduh Kecepatan Tinggi / High-Speed Downloader (N_m3u8DL-RE)**:
  - Mengunduh HLS/DASH `.m3u8` stream dengan 16 thread paralel / *Downloads HLS/DASH `.m3u8` streams with 16 parallel threads.*
  - Mengunduh dan mengelola binary resmi `N_m3u8DL-RE.exe` secara otomatis di bawah `~/.iamnotpirates/bin/` saat pertama kali dijalankan / *Automatically fetches and manages official `N_m3u8DL-RE.exe` binary under `~/.iamnotpirates/bin/` on first run.*
  - Penanganan pembatalan bersih via `Ctrl + C` / *Clean cancellation handling via `Ctrl + C`.*
- **📺 Struktur Folder Standar Jellyfin / Plex / Standard Folder Structure**:
  - Pengorganisasian otomatis TV Series: `TV Series/<Judul> (<Tahun>)/Season <0X>/<Judul> - S<0X>E<0Y>.<ext>` / *Automatic organization for TV Series: `TV Series/<Title> (<Year>)/Season <0X>/<Title> - S<0X>E<0Y>.<ext>`.*
  - Navigasi multi-pilih episode aman dengan opsi `⬅ Kembali` di setiap langkah / *Fail-safe sequential multi-select episode navigation with a `⬅ Back` option.*
- **📝 Konversi Subtitle Otomatis / Automatic Subtitle Conversion**:
  - Mengunduh subtitle VTT/SRT multi-bahasa (`.id.srt` & `.en.srt`) / *Downloads multi-language VTT/SRT subtitles (`.id.srt` & `.en.srt`).*
  - Otomatis diasosiasikan dengan file media sesuai konvensi Jellyfin/Plex / *Automatically associated with media files matching Jellyfin/Plex conventions.*
- **🎭 Sistem Playwright Chromium Auto-Healing / Playwright Chromium Auto-Healing System**:
  - Secara otomatis mendeteksi dan memasang binary Chromium untuk pengguna non-IT jika belum ada di komputer / *Automatically detects and installs Chromium binary for non-IT users if missing on target PC.*
- **🛡️ Sistem FFmpeg Auto-Healing Pintar / Smart FFmpeg Auto-Healing System**:
  - Auto-download binary resmi `ffmpeg.exe` & `ffprobe.exe` ke `~/.iamnotpirates/bin/` / *Auto-downloads official `ffmpeg.exe` & `ffprobe.exe` binaries to `~/.iamnotpirates/bin/`.*
  - **Pengecekan Kesehatan 3-Level / 3-Level Health Check**:
    - **Video Rusak (0-Byte) / Corrupt Video**: Otomatis menghapus file rusak dan mendownload ulang video + subtitle / *Automatically deletes corrupted files and re-downloads video + subtitles.*
    - **Video Sehat, Subtitle Kurang / Missing Subtitles**: Hanya mendownload subtitle yang hilang / *Downloads missing subtitles only.*
    - **Video & Subtitle Sehat / Healthy Media**: Langsung skip download / *Instantly skips download.*
- **🗃️ Database SQLite & Log Download / Persistent SQLite Database & Download Log**:
  - Menyimpan pengaturan aplikasi, target URL, dan riwayat download di `~/.iamnotpirates/data/data.db` / *Stores app settings, target URLs, and download history in `~/.iamnotpirates/data/data.db`.*
  - **1-Click Retry Semua yang Gagal / 1-Click Retry All Failed**: Coba ulang semua download yang gagal dengan mudah / *Easily retry all failed downloads.*
- **🛠️ Pengaturan Direktori & Organisasi Kustom / Custom Directory & Organization Settings**:
  - Pilih antara mode `separate` (folder terpisah) atau mode `combined` (satu direktori) / *Choose between `separate` mode or `combined` mode.*
  - Konfigurasi direktori download langsung dari menu pengaturan CLI / *Configure custom download directories directly from CLI settings.*

---

## 🛠️ Prasyarat & Instalasi / Prerequisites & Installation

### Menggunakan `uv` (Direkomendasikan) / Using `uv` (Recommended)
Aplikasi ini dikelola menggunakan **`uv`** (package manager Python yang sangat cepat) / *This application is managed using **`uv`** (an ultra-fast Python package manager).*

1. Clone repositori ini / Clone this repository:
   ```bash
   git clone https://github.com/iamnotpirates/iamnotpirates.git
   cd iamnotpirates
   ```

2. Jalankan aplikasi secara langsung (dependensi otomatis diinstall) / Run application directly (dependencies installed automatically):
   ```bash
   uv run python src/main.py
   ```

---

## 🚀 Panduan Penggunaan / Usage Guide

### 1. Menjalankan Mode Pengembangan / Running Development Mode
```bash
uv run python src/main.py
```

### 2. Menu Utama Interaktif / Interactive Main Menu
Setelah dijalankan, Anda akan disambut dengan menu CLI interaktif / *Once launched, you will be presented with an interactive CLI menu:*

```text
==================================================
 🏴‍☠️ I AM NOT PIRATES — CLI Media Downloader
==================================================
 1. 🔍 Cari Film / TV Series
 2. 🔥 Lihat Featured Content
 3. 📋 Lihat & Retry Download Gagal
 4. 🛠️  Pengaturan (Folder & Mode)
 5. 🌐 Pilih / Ganti Active Target URL
 6. ➕ Tambah URL Target Baru
 7. ⚙️  Manage List URL (Edit/Delete)
 8. ❌ Exit Program
```

- Pilih **`🔍 Cari Film / TV Series`** dan ketik kata kunci apa saja (misal *"Avatar"* atau *"One Piece"*) / *Select **`🔍 Search Movie / TV Series`** and type any keyword (e.g. "Avatar" or "One Piece").*
- Pilih episode atau film yang diinginkan; ekstraksi dan pengunduhan akan berjalan secara otomatis / *Select your desired episodes or movie; extraction and downloading will process automatically!*

---

## 🧪 Pengujian Kode / Unit Testing

Proyek ini dibangun menggunakan **Test-Driven Development (TDD)** dengan cakupan pengujian lengkap / *This project is built using **Test-Driven Development (TDD)** with complete test coverage.*

Untuk menjalankan seluruh test suite (100+ unit & integration tests) / *To run the full test suite (100+ unit & integration tests):*
```bash
uv run pytest -v
```

---

## 📦 Mengompilasi Binary Executable Standalone (`.exe`) / Building Standalone Executable

Kompilasi aplikasi menjadi satu binary executable Windows standalone (tanpa butuh instalasi Python) / *Compile the application into a single standalone Windows executable binary (no Python installation required):*

```bash
uv run python scripts/build_release.py
```

Binary output akan dibuat di `dist/IAmNotPirates.exe` / *The output binary will be generated at `dist/IAmNotPirates.exe`.*

---

## 📁 Struktur Direktori Proyek / Project Directory Structure

```text
iamnotpirates/
├── src/
│   ├── main.py               # CLI entry point & menu interaktif / CLI entry point & interactive menu loop
│   ├── scraper.py            # Scraper Playwright & klien IDLIX API / Playwright scraper & IDLIX JSON API client
│   ├── video_extractor.py    # Ekstraktor stream HLS & claim token / HLS stream extractor & claim token handler
│   ├── series_extractor.py   # Ekstraktor episode TV Series / TV Series episode extractor & season parser
│   ├── downloader.py         # Formatter path Jellyfin & download sub / Jellyfin path formatter & batch subtitle downloader
│   ├── playwright_manager.py # Manager auto-install Chromium / Playwright Chromium auto-installer manager
│   ├── n_m3u8dl_manager.py   # Wrapper subprocess N_m3u8DL-RE / N_m3u8DL-RE subprocess wrapper & binary manager
│   ├── ffmpeg_manager.py     # Manager FFmpeg & verifikasi media / FFmpeg binary manager & media health verifier
│   ├── db_manager.py         # SQLite database & manajer konfigurasi / SQLite database & configuration manager
│   └── ui.py                 # Helper UI rich console & banner / Rich console UI & banner helpers
├── tests/                    # 100+ Pytest unit & integration test suite
├── scripts/                  # Script otomatisasi build release / Release build automation scripts
│   └── build_release.py      # Automated PyInstaller executable builder
├── docs/                     # Dokumentasi arsitektur, spec & plan / Architecture documentation, SDD specs & plans
├── IAmNotPirates.spec        # Spesifikasi build PyInstaller / PyInstaller build specification
├── pyproject.toml            # Dependensi proyek & konfigurasi pytest / Project dependencies & pytest configuration
└── README.md                 # Dokumentasi proyek dua bahasa / Dual-language project documentation
```

---

## ⚖️ Lisensi & Penafian / License & Disclaimer

Aplikasi ini dibuat untuk tujuan pendidikan, penelitian arsitektur scraping, dan Proof of Concept (PoC) saja. Pengguna bertanggung jawab penuh atas penggunaan alat ini sesuai dengan hukum setempat dan ketentuan layanan yang berlaku / *This application is created for educational purposes, scraping architecture research, and Proof of Concept (PoC) only. Users assume full responsibility for using this tool in compliance with applicable local laws and service terms.*
