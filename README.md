# 🏴‍☠️ I Am Not Pirates — CLI Media Scraper & Downloader

Aplikasi CLI Python interaktif modern berkinerja tinggi untuk menjelajah, mencari, dan mengunduh Film serta TV Series secara otomatis. Dilengkapi dengan mesin unduh multi-thread super cepat **N_m3u8DL-RE**, manajemen basis data SQLite, penataan folder standar **Jellyfin / Plex**, konversi subtitle otomatis, serta sistem pemulihan file rusak (**Smart FFmpeg Auto-Healing**).

---

## ✨ Fitur Utama

- **🔍 Pencarian Media Cepat (Search)**: Cari film atau serial TV berdasarkan judul secara langsung dari CLI melalui integrasi API internal.
- **⚡ Mesin Downloader Berkecepatan Tinggi (N_m3u8DL-RE)**:
  - Mengunduh stream HLS/DASH `.m3u8` dengan 16 thread paralel.
  - Binary `N_m3u8DL-RE.exe` terunduh dan terkelola secara otomatis di `~/.iamnotpirates/bin/` pada eksekusi pertama.
  - Dukungan pembatalan aman via `Ctrl + C`.
- **📺 Struktur Folder Standar Jellyfin / Media Server**:
  - Penataan otomatis untuk TV Series: `TV Series/<Show Title> (<Year>)/Season <0X>/<Show Title> - S<0X>E<0Y>.<ext>`.
  - Multi-select episode sekuensial interaktif dengan opsi navigasi kembali `⬅ Kembali`.
- **📝 Konversi Subtitle Otomatis**:
  - Mendownload subtitle VTT/SRT multi-bahasa (`.id.srt` & `.en.srt`).
  - Otomatis terhubung dengan file media sesuai penamaan Jellyfin/Plex.
- **🛡️ Smart FFmpeg Auto-Healing System**:
  - Auto-download `ffmpeg.exe` & `ffprobe.exe` resmi di `~/.iamnotpirates/bin/`.
  - **3-Level Health Check**:
    - **Corrupt / 0-Byte Video**: Menghapus file rusak dan mengunduh ulang video + subtitle.
    - **Video Sehat, Subtitle Kurang**: **Hanya mengunduh subtitlenya saja** tanpa perlu mengunduh ulang video yang sudah ada.
    - **Video & Subtitle Sehat**: Melompati proses unduh secara instan.
- **🗃️ Basis Data SQLite & Log Histori Persisten**:
  - Menyimpan konfigurasi dan log pengunduhan di `~/.iamnotpirates/data/data.db`.
  - Fitur **Retry All Failed**: Ulangi semua pengunduhan yang gagal hanya dengan 1 klik.
- **🛠️ Pengaturan Folder Custom**:
  - Pilih mode penyimpanan `separate` (Folder Movies & Series terpisah) atau `combined` (Satu folder gabungan).
  - Tentukan lokasi direktori penyimpanan kustom dari dalam menu CLI.

---

## 🛠️ Prasyarat & Instalasi

### Menggunakan `uv` (Direkomendasikan)
Aplikasi ini dikelola menggunakan **`uv`** (Python package manager ultra-cepat).

1. Clone repositori ini:
   ```bash
   git clone https://github.com/username/iamnotpirates.git
   cd iamnotpirates
   ```

2. Jalankan aplikasi langsung (dependensi terinstal otomatis):
   ```bash
   uv run python src/main.py
   ```

---

## 🚀 Cara Penggunaan

### 1. Menjalankan Mode Development
```bash
uv run python src/main.py
```

### 2. Menu Utama Interaktif
Setelah aplikasi berjalan, kamu akan disajikan menu CLI interaktif:

```text
==================================================
 🏴‍☠️ I AM NOT PIRATES — CLI Media Downloader
==================================================
 1. 🔍 Cari Film / TV Series
 2. 🔥 Lihat Featured Content
 3. 🔄 Retry Semua yang Gagal
 4. 🛠️ Pengaturan (Folder & Mode)
 5. 🌐 Kelola URL Target IDLIX
 6. ❌ Keluar
```

- Pilih **`🔍 Cari Film / TV Series`** untuk mengetik judul media (misal *"Avatar"* atau *"One Piece"*).
- Pilih episode/movie yang diinginkan, proses ekstraksi dan pengunduhan akan berjalan otomatis di background!

---

## 🧪 Menguji Kode (Unit Tests)

Proyek ini dibangun menggunakan **Test-Driven Development (TDD)** dengan cakupan pengujian penuh.

Untuk menjalankan seluruh rangkaian pengujian (80+ unit tests):
```bash
uv run pytest
```

---

## 📦 Membangun Executable Standalone (`.exe`)

Aplikasi dapat dikompilasi menjadi satu file biner executable Windows tanpa memerlukan Python terinstal:

```bash
uv run pyinstaller IAmNotPirates.spec --clean
```

Hasil biner executable akan tersedia di folder `dist/IAmNotPirates.exe`.

---

## 📁 Struktur Direktori Proyek

```text
iamnotpirates/
├── src/
│   ├── main.py               # Entry point CLI & alur menu interaktif
│   ├── scraper.py            # Engine scraper Playwright & IDLIX JSON API
│   ├── video_extractor.py    # Extractor streaming HLS & claim token
│   ├── series_extractor.py   # Extractor episode TV Series & season parser
│   ├── downloader.py         # Formatter path Jellyfin & batch subtitle downloader
│   ├── n_m3u8dl_manager.py   # Subprocess wrapper & binary manager N_m3u8DL-RE
│   ├── ffmpeg_manager.py     # Binary manager FFmpeg & media verifier
│   ├── db_manager.py         # Pengelola SQLite database & konfigurasi
│   └── ui.py                 # Helper tampilan Rich Console & banner
├── tests/                    # 80+ Suite Unit Tests (Pytest)
├── docs/                     # Dokumentasi arsitektur, SDD spec & plan
├── IAmNotPirates.spec        # Konfigurasi PyInstaller build
├── pyproject.toml            # Konfigurasi dependensi uv & pytest
└── README.md                 # Dokumentasi proyek
```

---

## ⚖️ Lisensi & Penolakan Tanggung Jawab (Disclaimer)

Aplikasi ini dibuat hanya untuk tujuan edukasi, riset arsitektur scraping, dan pembuktian konsep (*Proof of Concept*). Pengguna bertanggung jawab penuh atas penggunaan perkakas ini sesuai dengan hukum dan ketentuan layanan yang berlaku di wilayah masing-masing.
