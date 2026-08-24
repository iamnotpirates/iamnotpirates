<p align="center">
  <img src="assets/logo.svg" alt="I Am Not Pirates Logo" width="160" height="160" />
</p>

# 🏴‍☠️ I Am Not Pirates — CLI Media Scraper & Downloader

![Version](https://img.shields.io/badge/version-v1.3.0-blue)
![Platform](https://img.shields.io/badge/platform-Windows%2064--bit-0078D6?logo=windows)

A high-performance, modern interactive Python CLI application to browse, search, and automatically download Movies and TV Series.  
*(Aplikasi CLI Python interaktif modern berkinerja tinggi untuk menjelajah, mencari, dan mendownload Film serta TV Series secara otomatis.)*

Powered by the ultra-fast multi-threaded **N_m3u8DL-RE** download engine, SQLite database management, **Jellyfin / Plex** standard media folder structure, automatic subtitle conversion, **Playwright Chromium Auto-Healing**, and a **Smart FFmpeg Auto-Healing System**.  
*(Ditenagai oleh mesin pengunduh **N_m3u8DL-RE** multi-threaded, manajemen database SQLite, struktur folder media standar **Jellyfin / Plex**, konversi subtitle otomatis, sistem **Playwright Chromium Auto-Healing**, dan sistem **FFmpeg Auto-Healing**.)*

---

## 💾 Download & Quick Start — Windows Executable (*Download & Mulai Cepat*)

> 📢 **For Non-IT Users (*Untuk Pengguna Awam*)**: No Python, Git, or developer tools required!  
> *(Tidak memerlukan instalasi Python, Git, atau tools developer sama sekali!)*

1. Go to the latest [GitHub Releases](https://github.com/iamnotpirates/iamnotpirates/releases) page.  
   *(Buka halaman [GitHub Releases](https://github.com/iamnotpirates/iamnotpirates/releases) terbaru.)*
2. Download **`IAmNotPirates.exe`** (Windows 64-bit standalone executable).  
   *(Unduh file **`IAmNotPirates.exe`** — executable standalone untuk Windows 64-bit.)*
3. Double-click **`IAmNotPirates.exe`** to start downloading movies and TV series!  
   *(Klik dua kali **`IAmNotPirates.exe`** untuk langsung menjelajah dan mendownload film/series!)*

> ℹ️ **Note (*Catatan*)**: Currently built and optimized specifically for **Windows 64-bit**. All required background tools (**N_m3u8DL-RE**, **FFmpeg**, and **Chromium**) are automatically downloaded and set up on first run.  
> *(Saat ini dibangun dan dioptimalkan khusus untuk **Windows 64-bit**. Seluruh pendukung background seperti **N_m3u8DL-RE**, **FFmpeg**, dan **Chromium** diunduh dan dipasang secara otomatis pada eksekusi pertama.)*

---

## ✨ Key Features (*Fitur Utama*)

- **🔍 Fast Media Search** (*Pencarian Media Cepat*):  
  Search for movies or TV series directly by title from the CLI via internal API integration.  
  *(Cari film atau TV Series langsung berdasarkan judul dari CLI via integrasi API internal.)*

- **⚡ High-Speed Downloader — N_m3u8DL-RE** (*Pengunduh Kecepatan Tinggi*):
  - Downloads HLS/DASH `.m3u8` streams with 16 parallel threads.  
    *(Mengunduh HLS/DASH `.m3u8` stream dengan 16 thread paralel.)*
  - Automatically fetches and manages official `N_m3u8DL-RE.exe` binary under `~/.iamnotpirates/bin/` on first run.  
    *(Mengunduh dan mengelola binary resmi `N_m3u8DL-RE.exe` secara otomatis di bawah `~/.iamnotpirates/bin/` saat pertama kali dijalankan.)*
  - **Auto-Heal & Windows File Lock Handling** (*Auto-Heal & Penanganan Lock File Windows*): Automatically detects and recovers `.MUX.mp4` leftover files with a 5x retry loop, and handles locked temporary `.ts` files gracefully during cleanup.  
    *(Mendeteksi dan memulihkan sisa file `.MUX.mp4` secara otomatis dengan perulangan retry 5x, dan mengabaikan kegagalan akibat file `.ts` sementara yang terkunci.)*
  - Clean cancellation handling via `Ctrl + C`.  
    *(Penanganan pembatalan bersih via `Ctrl + C`.)*

- **📺 Standard Folder Structure — Jellyfin / Plex** (*Struktur Folder Standar Jellyfin / Plex*):
  - Automatic organization for TV Series: `TV Series/<Show Title> (<Year>)/Season <0X>/<Show Title> - S<0X>E<0Y>.<ext>`.  
    *(Pengorganisasian otomatis TV Series: `TV Series/<Judul> (<Tahun>)/Season <0X>/<Judul> - S<0X>E<0Y>.<ext>`.)*
  - Fail-safe sequential multi-select episode navigation with a `⬅ Back` option at every step.  
    *(Navigasi multi-pilih episode aman dengan opsi `⬅ Kembali` di setiap langkah.)*

- **📝 Automatic Subtitle Conversion** (*Konversi Subtitle Otomatis*):
  - Downloads multi-language VTT/SRT subtitles (`.id.srt` & `.en.srt`).  
    *(Mengunduh subtitle VTT/SRT multi-bahasa `.id.srt` & `.en.srt`.)*
  - **Pre-Scraping Movie Subtitle Choice** (*Pemilihan Subtitle Movie Di Awal*): Allows choosing subtitles before movie video scraping starts to streamline the download flow.  
    *(Memungkinkan pemilihan subtitle sebelum scraping video film untuk merampingkan alur unduhan.)*
  - Automatically associated with media files matching Jellyfin/Plex conventions.  
    *(Otomatis diasosiasikan dengan file media sesuai konvensi Jellyfin/Plex.)*

- **🎭 Playwright Chromium Auto-Healing System** (*Sistem Playwright Chromium Auto-Healing*):
  - Automatically detects and installs Chromium binary for non-IT users if missing on target PC.  
    *(Secara otomatis mendeteksi dan memasang binary Chromium untuk pengguna non-IT jika belum ada di komputer.)*

- **🛡️ Smart FFmpeg Auto-Healing System** (*Sistem FFmpeg Auto-Healing Pintar*):
  - Auto-downloads official `ffmpeg.exe` & `ffprobe.exe` binaries to `~/.iamnotpirates/bin/`.  
    *(Auto-download binary resmi `ffmpeg.exe` & `ffprobe.exe` ke `~/.iamnotpirates/bin/`.)*
  - **Instant Local Check** (*Pengecekan File Lokal Instan*): Instantly verifies local files (Movies/TV Series) **before** executing any web scraper. Bypasses extraction entirely if the file is present and healthy, saving bandwidth and time.  
    *(Memverifikasi file lokal sebelum menjalankan scraper. Melewati ekstraksi sepenuhnya jika file ada dan sehat, menghemat bandwidth dan waktu.)*
  - **3-Level Health Check** (*Pengecekan Kesehatan 3-Level*):
    - **Corrupt Video (0-Byte)** (*Video Rusak / 0-Byte*): Automatically deletes corrupted files and re-downloads video + subtitles.  
      *(Otomatis menghapus file rusak dan mendownload ulang video + subtitle.)*
    - **Missing Subtitles** (*Video Sehat, Subtitle Kurang*): Downloads missing subtitles only without re-downloading video.  
      *(Hanya mendownload subtitle yang hilang tanpa mendownload ulang video.)*
    - **Healthy Media** (*Video & Subtitle Sehat*): Instantly skips download.  
      *(Langsung skip download.)*

- **🗃️ Persistent SQLite Database & Download Log** (*Database SQLite & Log Download*):
  - Stores app settings, target URLs, and download history in `~/.iamnotpirates/data/data.db`.  
    *(Menyimpan pengaturan aplikasi, target URL, dan riwayat download di `~/.iamnotpirates/data/data.db`.)*
  - **1-Click Retry All Failed** (*1-Click Retry Semua yang Gagal*): Easily retry all failed downloads.  
    *(Coba ulang semua download yang gagal dengan mudah.)*

- **🛠️ Custom Directory & Organization Settings** (*Pengaturan Direktori & Organisasi Kustom*):
  - Choose between `separate` mode (individual folders) or `combined` mode (single output folder).  
    *(Pilih antara mode `separate` — folder terpisah, atau mode `combined` — satu direktori.)*
  - Configure custom download directories directly from CLI settings menu.  
    *(Konfigurasi direktori download langsung dari menu pengaturan CLI.)*

---

## 📡 Telegram Backup (*Backup Telegram*)

Back up your downloaded media collection to your own Telegram account as an off-site cloud archive, and restore it anytime.  
(*Cadangkan koleksi media hasil download ke akun Telegram Anda sendiri sebagai arsip cloud off-site, dan pulihkan kapan saja.*)

- **Prerequisites (*Prasyarat*)**: Create an application at [my.telegram.org](https://my.telegram.org) to obtain your `api_id` & `api_hash`, then fill them in via the 📡 Telegram menu (one-time MTProto login with your phone number).  
  *(Buat aplikasi di [my.telegram.org](https://my.telegram.org) untuk mendapatkan `api_id` & `api_hash`, lalu isi melalui menu 📡 Telegram — login MTProto sekali dengan nomor telepon Anda.)*
- **Manual & Automatic Backup** (*Backup Manual & Otomatis*): Back up any movie/series on demand, or let the app back up newly completed downloads automatically after each successful download.  
  *(Backup film/series kapan saja secara manual, atau biarkan aplikasi mem-backup unduhan baru yang selesai secara otomatis setelah download berhasil.)*
- **Multi-Destination Forwarding** (*Forward Multi-Tujuan*): Send each backup to multiple destinations at once — e.g. **Saved Messages** and/or your own **Channel**.  
  *(Kirim setiap backup ke beberapa tujuan sekaligus — misalnya **Saved Messages** dan/atau **Channel** milik Anda sendiri.)*
- **Automatic >2GB Splitting** (*Split Otomatis >2GB*): Files larger than the Telegram 2GB limit are split automatically into parts and merged seamlessly back together during restore.  
  *(File yang melebihi batas 2GB Telegram dipecah otomatis menjadi beberapa bagian dan digabung kembali secara mulus saat restore.)*
- **Restore via Menu or Hybrid Search** (*Restore via Menu atau Pencarian Hybrid*): Restore from the 📡 Telegram menu, or find backed-up items directly in the search results table — IDLIX results and Telegram backups are combined into one list.  
  *(Pulihkan dari menu 📡 Telegram, atau temukan item backup langsung di tabel hasil pencarian — hasil IDLIX dan backup Telegram digabung dalam satu daftar.)*
- **Two-Level Deletion Guard** (*Pengaman Hapus Dua Tingkat*): Deleting a local file that has **not** been backed up yet triggers a double warning before proceeding, so you never lose unarchived media by accident.  
  *(Menghapus file lokal yang belum dibackup akan memicu peringatan ganda sebelum lanjut, sehingga media yang belum diarsipkan tidak hilang karena kelalaian.)*

---

## 🛠️ Developer Setup & Source Installation (*Instalasi Sumber & Developer*)

### Using `uv` (Recommended) (*Menggunakan `uv` — Direkomendasikan*)
For developers running from source code, this application is managed using **`uv`** (an ultra-fast Python package manager).  
*(Untuk pengembang yang menjalankan dari kode sumber, aplikasi ini dikelola menggunakan **`uv`** — package manager Python yang sangat cepat.)*

1. Clone this repository *(Clone repositori ini)*:
   ```bash
   git clone https://github.com/iamnotpirates/iamnotpirates.git
   cd iamnotpirates
   ```

2. Run application directly (dependencies installed automatically) *(Jalankan aplikasi secara langsung — dependensi otomatis diinstall)*:
   ```bash
   uv run python src/main.py
   ```

---

## 🚀 Usage Guide (*Panduan Penggunaan*)

### 1. Running Development Mode (*1. Menjalankan Mode Pengembangan*)
```bash
uv run python src/main.py
```

### 2. Interactive Main Menu (*2. Menu Utama Interaktif*)
Once launched, you will be presented with an interactive CLI menu:  
*(Setelah dijalankan, Anda akan disambut dengan menu CLI interaktif:)*

```text
==================================================
 🏴‍☠️ I AM NOT PIRATES — CLI Media Downloader
==================================================
 1. 🔍 Search Movie & TV Series / Cari Film & TV Series
 2. 🔥 Browse Featured Content / Lihat Content Populer
 3. 📋 Download Log & Retry / Log & Retry Download Gagal
 4. 🛠️  Settings / Pengaturan (Folder & Mode)
 5. 🌐 Switch Target URL / Pilih Active Target URL
 6. ➕ Add New Target URL / Tambah Target URL Baru
 7. ⚙️  Manage Target URLs / Kelola Daftar Target URL
 8. ❌ Exit / Keluar
```

- Select **`🔍 Search Movie & TV Series / Cari Film & TV Series`** and type any keyword (e.g. "Avatar" or "One Piece").  
  *(Pilih **`🔍 Search Movie & TV Series / Cari Film & TV Series`** dan ketik kata kunci apa saja misal "Avatar" atau "One Piece".)*
- Select your desired episodes or movie; extraction and downloading will process automatically!  
  *(Pilih episode atau film yang diinginkan; ekstraksi dan pengunduhan akan berjalan secara otomatis!)*

---

## 🧪 Unit Testing (*Pengujian Kode*)

This project is built using **Test-Driven Development (TDD)** with complete test coverage.  
*(Proyek ini dibangun menggunakan **Test-Driven Development (TDD)** dengan cakupan pengujian lengkap.)*

To run the full test suite (180 unit & integration tests):  
*(Untuk menjalankan seluruh test suite — 180 unit & integration tests:)*
```bash
uv run pytest -v
```

---

## 📦 Building Standalone Executable (`.exe`) (*Mengompilasi Binary Executable Standalone*)

Compile the application into a single standalone Windows executable binary (no Python installation required):  
*(Kompilasi aplikasi menjadi satu binary executable Windows standalone — tanpa butuh instalasi Python:)*

```bash
uv run python scripts/build_release.py
```

The output binary will be generated at `dist/IAmNotPirates.exe`.  
*(Binary output akan dibuat di `dist/IAmNotPirates.exe`.)*

---

## 📁 Project Directory Structure (*Struktur Direktori Proyek*)

```text
iamnotpirates/
├── src/
│   ├── main.py               # CLI entry point & interactive menu loop (CLI entry point & menu interaktif)
│   ├── scraper.py            # Playwright scraper & IDLIX API client (Scraper Playwright & klien IDLIX API)
│   ├── video_extractor.py    # HLS stream extractor & claim token handler (Ekstraktor stream HLS & claim token)
│   ├── series_extractor.py   # TV Series episode extractor & season parser (Ekstraktor episode TV Series)
│   ├── downloader.py         # Jellyfin path formatter & batch subtitle downloader (Formatter path Jellyfin & download sub)
│   ├── playwright_manager.py # Playwright Chromium auto-installer manager (Manager auto-install Chromium)
│   ├── n_m3u8dl_manager.py   # N_m3u8DL-RE subprocess wrapper & binary manager (Wrapper subprocess N_m3u8DL-RE)
│   ├── ffmpeg_manager.py     # FFmpeg binary manager & media health verifier (Manager FFmpeg & verifikasi media)
│   ├── db_manager.py         # SQLite database core manager (Manager inti database SQLite)
│   ├── config_manager.py     # App settings & target URLs manager (Manajer pengaturan & target URL)
│   ├── download_log.py       # Download history log & retry tracker (Log riwayat download & pelacak retry)
│   ├── telegram_manager.py   # Telegram MTProto backup, split/merge & restore manager (Manager backup, split/merge & restore Telegram)
│   └── ui.py                 # Rich console UI, tables & spinners (UI rich console, tabel & spinner)
├── tests/                    # 180 Pytest unit & integration test suite
├── scripts/                  # Release build automation scripts (Script otomatisasi build release)
│   └── build_release.py      # Automated PyInstaller executable builder
├── docs/                     # Architecture documentation, SDD specs & plans (Dokumentasi arsitektur, spec & plan)
├── IAmNotPirates.spec        # PyInstaller build specification (Spesifikasi build PyInstaller)
├── pyproject.toml            # Project dependencies & pytest configuration (Dependensi proyek & konfigurasi pytest)
└── README.md                 # Dual-language project documentation (Dokumentasi proyek dua bahasa)
```

---

## ⚠️ Known Limitations (*Keterbatasan*)

- **Foreign messages between split parts** (*Pesan asing di antara dua part split*): A foreign message sent between two parts of a split upload can break scan grouping; restore-time size verification acts as the safety net against corrupt merges.  
  *(Pesan asing yang dikirim di antara dua part split dapat memutus pengelompokan saat scan; verifikasi ukuran saat restore berfungsi sebagai jaring pengaman agar file rusak tidak tersimpan.)*
- **Duplicate rows per destination are intentional** (*Baris duplikat per tujuan bersifat disengaja*): Items backed up to multiple destinations appear once per destination so restore can fall back to the other copy if one fails.  
  *(Item yang dibackup ke beberapa tujuan muncul satu baris per tujuan sehingga restore bisa fallback ke salinan lain jika salah satu gagal.)*
- **Group topics are re-uploaded, not forwarded** (*Group dengan topik di-upload ulang*): Telegram forwarding cannot target a forum topic, so destinations like `group:<id>:<topic>` receive a fresh upload (extra bandwidth), while topic-less groups and channels are server-side forwards.  
  *(Forward Telegram tidak bisa menentukan topik forum, jadi tujuan `group:<id>:<topik>` dikirim ulang penuh — bandwitdh ekstra; group tanpa topik dan channel tetap forward di sisi server.)*

---

## ⚖️ License & Disclaimer (*Lisensi & Penafian*)

This application is created for educational purposes, scraping architecture research, and Proof of Concept (PoC) only. Users assume full responsibility for using this tool in compliance with applicable local laws and service terms.  
*(Aplikasi ini dibuat untuk tujuan pendidikan, penelitian arsitektur scraping, dan Proof of Concept (PoC) saja. Pengguna bertanggung jawab penuh atas penggunaan alat ini sesuai dengan hukum setempat dan ketentuan layanan yang berlaku.)*
