# Spesifikasi Rancangan: Telegram Backup Platform

Tanggal: 2026-08-23
Status: Disetujui (hasil sesi brainstorming)

## 1. Konteks

File hasil unduhan dari IDLIX tidak dijamin tersedia selamanya di server mereka (link mati, konten dihapus). Pengguna ingin menyimpan salinan film/episode yang sudah diunduh ke Telegram agar aman permanen, menghapus file lokal yang sudah selesai ditonton untuk hemat ruang, dan menonton ulang kapan pun dengan memulihkan (restore) file dari Telegram.

Telegram dipilih karena berfungsi sebagai penyimpanan awan gratis. Karena ukuran film jauh melebihi batas 50MB Bot API, integrasi menggunakan **akun pribadi via MTProto (library Telethon)** — batas upload 2GB per file untuk akun gratis.

## 2. Tujuan

1. Mengunggah (backup) video + subtitle ke Telegram: manual maupun otomatis setelah unduhan sukses.
2. Memulihkan (restore) backup kembali ke folder lokal dengan struktur folder yang konsisten.
3. Pencarian hybrid: mencari judul sekaligus di IDLIX dan di backup Telegram.
4. Menghapus file lokal dengan pengaman: memberi peringatan tegas jika file ternyata belum dibackup.
5. Menangani file > 2GB dengan pemecahan (split) otomatis saat upload dan penggabungan (merge) otomatis saat restore.

## 3. Prinsip Arsitektur

**Telegram adalah sumber data langsung — tanpa tabel indeks lokal.**

- Tidak ada tabel SQLite baru untuk indeks backup. Semua pencarian, listing, dan penemuan message ID dilakukan dengan **fetch langsung ke pesan-pesan channel/Saved Messages**, membaca caption metadata terstruktur di tiap pesan.
- Konsekuensi yang disetujui pengguna: listing/pencarian butuh beberapa detik pada channel besar. UI wajib menampilkan spinner `📡 Mencari di Telegram...` selama proses agar jelas penyebab waktu tunggu.
- Tabel `downloads` yang lama **tidak diubah sama sekali** — tetap khusus log unduhan IDLIX.
- Tujuan backup dapat dikonfigurasi; skema unggah: **upload sekali ke tujuan utama, forward otomatis ke tujuan sekunder** (forwarding terjadi di server Telegram, tanpa bandwidth tambahan).

## 4. Komponen Baru

### A. `src/telegram_manager.py` — Mesin Telegram

Wrapper seluruh interaksi Telethon. Unit yang bisa diuji terpisah:

| Fungsi | Tanggung jawab |
|---|---|
| `ensure_telethon(console)` | Cek library `telethon` terinstall; tawarkan instalasi otomatis jika belum (pola `ensure_playwright`). |
| `login_flow(console)` | Jika session belum ada: minta `api_id`, `api_hash` (dengan panduan langkah my.telegram.org), nomor HP, kode OTP, password 2FA bila ada. Session disimpan di `~/.iamnotpirates/telegram/session`. |
| `get_client()` | Mengembalikan client Telethon yang siap pakai; resolve entity channel tujuan. |
| `split_file(path, part_size)` / `merge_files(parts, output)` | Murni binary; parts ≤ 1.9GB di folder temp `~/.iamnotpirates/tmp_split/`. |
| `build_caption(meta)` / `parse_caption(text)` | Serialisasi/deserialisasi metadata terstruktur (roundtrip). |
| `scan_backups(client)` | Fetch semua pesan di tujuan aktif, parse caption, kembalikan daftar item backup valid (caption rusak dilewati + warning). |
| `upload_backup(file_path, sub_paths, meta, progress_cb)` | Alur lengkap upload: split bila perlu → upload parts (caption di part pertama) → upload subtitle sebagai document → forward ke tujuan sekunder → hapus temp → kembalikan message IDs. |
| `restore_backup(item, progress_cb)` | Download semua part dari sumber yang dapat diakses → merge bila multi-part → verifikasi ukuran vs metadata → download subtitle → letakkan di folder sesuai aturan `get_download_dir`. |

### B. Perubahan `src/db_manager.py`

Hanya penambahan config keys (tabel `configs` yang sudah ada):

| Key | Isi |
|---|---|
| `tg_api_id` | API ID dari my.telegram.org |
| `tg_api_hash` | API Hash dari my.telegram.org |
| `tg_auto_backup` | `"0"` / `"1"` |
| `tg_destinations` | JSON array, misal `["saved", "channel"]`; elemen pertama = tujuan utama |
| `tg_channel_id` | Username atau ID channel privat |

### C. Perubahan `src/main.py` & `src/ui.py`

Menu utama mendapat entri baru `📡 Telegram Backup / Kelola Backup Telegram` (sebelum Exit) dengan handler `handle_telegram_menu(active_url, config)`:

```
📡 Telegram Backup
   ├─ 🔍 Cari & Restore dari Telegram  → input judul → spinner "Mencari di Telegram..."
   │                                      → tabel hasil → pilih → restore + progress bar
   ├─ 📚 Daftar Semua Backup           → scan live → tabel Rich
   ├─ 📤 Backup Manual                 → daftar film lokal (log + file masih ada)
   │                                      → penanda ✅ jika judul sudah ada di Telegram (anti-duplikat,
   │                                        tidak memblokir) → checkbox → upload (+forward) + progress bar
   ├─ 🗑️ Hapus File Lokal              → semua file lokal + kolom status backup
   │                                      → checkbox → konfirmasi bertingkat → hapus
   ├─ ⚙️ Pengaturan Telegram           → API keys, tujuan backup, auto-backup on/off, logout
   └─ ⬅ Kembali
```

Semua label mengikuti pola dual-language (`Label ID / Label EN`) dan tabel Rich seperti menu lain.

### D. Integrasi Fitur yang Sudah Ada

**Search hybrid (Menu 1):** setelah hasil IDLIX diperoleh, jalankan juga scan Telegram (spinner), filter caption cocok dengan query, gabungkan ke satu tabel dengan kolom baru "Sumber": `🌐 IDLIX` atau `📡 TELEGRAM`. Judul yang sama di dua sumber muncul dua baris. Memilih item TELEGRAM masuk alur restore; setelah selesai tawarkan membuka folder hasil.

**Auto-backup:** di akhir `process_download_item` ketika status success (movie maupun episode): jika `tg_auto_backup == "1"` dan sudah login → upload otomatis dengan progress bar. Kegagalan upload **tidak mengubah** suksesnya unduhan — hanya ditampilkan warning.

## 5. Format Metadata Caption

Caption part pertama menyimpan blok JSON (plus baris human-readable di atasnya) berisi minimal:

```json
{
  "app": "iamnotpirates",
  "v": 1,
  "kind": "video",
  "title": "Judul Film",
  "year": "2024",
  "media_type": "movie",
  "season": null,
  "episode": null,
  "file_size": 2147483648,
  "part_count": 2,
  "subtitles": ["Judul Film (2024).id.srt"]
}
```

Setiap dokumen subtitle juga diberi caption penanda agar bisa dibedakan dari part video:

```json
{
  "app": "iamnotpirates",
  "v": 1,
  "kind": "subtitle",
  "filename": "Judul Film (2024).id.srt",
  "parent_title": "Judul Film"
}
```

Aturan pengenalan pesan saat scan:
- `kind == "video"` → bagian dari backup video; part ke-N diketahui dari urutan pesan setelah part pertama.
- `kind == "subtitle"` → document subtitle milik `parent_title`.
- Tanpa caption / `"app"` bukan `"iamnotpirates"` → bukan milik aplikasi ini, diabaikan saat scan.

`parse_caption` hanya menerima JSON dengan `"app": "iamnotpirates"`. Restore merekonstruksi path dari `media_type`/`season`/`episode`/`title`/`year` lewat aturan `get_download_dir` — tidak bergantung path absolut mesin lama.

## 6. Penanganan Error

| Situasi | Perlakuan |
|---|---|
| Belum setup API / belum login | Semua aksi Telegram mengarahkan ke `login_flow()` dengan panduan. |
| Upload terputus di tengah | Pesan error jelas; part parsial di temp dibersihkan; user dapat mengulang. |
| File sumber hilang saat backup manual | Item di-skip dengan warning. |
| Hasil merge ≠ `file_size` metadata | Ditandai corrupt; parts temp TIDAK dihapus sampai user konfirmasi. |
| Tujuan utama tidak dapat diakses saat restore | Coba tujuan berikutnya yang tercatat di setting. |
| Caption rusak / bukan milik app | Dilewati dengan warning di listing. |

## 7. Alur Hapus File Lokal (Pengaman)

1. Listing = semua film/episode lokal (dari log `downloads` + verifikasi file masih ada), dicocokkan dengan hasil scan Telegram → kolom status: `✅ Aman di Telegram` / `⚠️ BELUM DIBACKUP`.
2. File **sudah aman**: konfirmasi biasa (`questionary.confirm`) lalu hapus file (+folder kosong yang tersisa).
3. File **belum dibackup**: peringatan merah *"File ini TIDAK ditemukan di Telegram. Jika dihapus, file hilang PERMANEN dan tidak bisa dipulihkan!"* — wajib konfirmasi dua kali termasuk mengetik kata konfirmasi secara eksplisit.

## 8. Rencana Pengujian (TDD)

1. **Unit murni (tanpa network):** `split_file`/`merge_files` roundtrip; `build_caption`/`parse_caption` roundtrip; matching judul search (normalisasi huruf besar-kecil).
2. **Mock Telethon client:** alur `upload_backup` (single-part, multi-part, forward), `restore_backup` (verifikasi ukuran, fallback tujuan), `scan_backups` (caption valid/rusak/bukan app).
3. **Handler menu:** test mocks ala `tests/test_main.py` — cari & restore, backup manual, hapus dengan kedua jalur konfirmasi (aman vs belum dibackup), pengaturan Telegram.
4. **Auto-backup:** sukses download + toggle aktif → upload terpanggil; gagal upload → status download tetap `success`.

Dependensi baru: `telethon` di `pyproject.toml`.
