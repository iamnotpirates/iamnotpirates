# Spesifikasi Rancangan: Instant Local Checks Sebelum Web Scraping

## 1. Konteks
Saat ini, proses unduhan film (single movie) atau episode serial TV (TV Series) selalu melakukan scraping (koneksi HTTP) ke IDLIX terlebih dahulu untuk mengambil URL stream (`m3u8`) dan subtitle, baru kemudian melakukan pemeriksaan apakah file tersebut sudah ada secara lokal. Hal ini membuang waktu dan bandwidth ketika pengguna mengunduh item yang sebenarnya sudah selesai dan sehat di penyimpanan lokal.

## 2. Tujuan
Mengoptimalkan kinerja dengan memindahkan pengecekan lokal (`is_already_downloaded` & `verify_media_file`) ke awal proses sebelum request scraping web dilakukan. Jika file lokal ada dan sehat, proses scraping dilewati sepenuhnya.

## 3. Detail Implementasi

### A. Alur Modul Movies (`src/main.py`)
1. Dapatkan folder tujuan (`target_dir`) dan subtitle preference.
2. Tentukan `expected_path` berdasarkan judul dan tahun rilis.
3. Jalankan `is_already_downloaded(expected_path)`.
4. Jika file ditemukan, panggil `verify_media_file(expected_path, required_sub_mode)`.
5. Jika status video `"HEALTHY"` dan subtitle lengkap:
   - Cetak log status `skipped`.
   - Simpan entri log unduhan ke database SQLite.
   - Hentikan eksekusi fungsi (`return`) **tanpa** memanggil `extract_video_sources()`.

### B. Alur Modul TV Series (`src/main.py`)
1. Pengguna memilih episode, save directory, dan preferensi subtitle.
2. Untuk setiap episode dalam loop:
   - Tentukan `expected_path` episode.
   - Panggil `is_already_downloaded(expected_path)` & `verify_media_file()`.
   - Jika sehat dan lengkap, log status `skipped` dan langsung `continue` ke episode berikutnya **tanpa** memanggil `extract_episode_sources()`.

## 4. Rencana Pengujian (Test Cases)
1. `test_process_download_item_movie_instant_skip`: Memastikan unduhan film tunggal langsung dilewati tanpa memanggil scraper jika file lokal sudah lengkap.
2. `test_process_download_item_series_instant_skip`: Memastikan unduhan episode serial TV langsung dilewati per episode tanpa memanggil scraper episode jika file lokal sudah lengkap.
