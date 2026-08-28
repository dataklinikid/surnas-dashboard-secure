# Tahap 7B — Git Privat dan Release Pertama

Tahap 7B dibagi menjadi dua bagian. Tahap 7B1 menyiapkan repository lokal dan memeriksa kebersihan
source. Tahap 7B2 menghubungkan repository lokal ke repository privat. VPS belum digunakan.

## Inisialisasi Git lokal

```powershell
git --version
git init -b main
git status --short
python deploy\scripts\check_release_hygiene.py
git add .
git diff --cached --check
git status --short
```

Target pemeriksaan:

```text
RELEASE HYGIENE: OK
```

Script menolak credential, private key, database, dump, `.sav`, ZIP, dan CSV selain data demo
sintetis. `.gitignore` tetap menjadi pengamanan pertama; script menjadi pemeriksaan kedua.

Sebelum commit, pastikan daftar tidak memuat `.env`, `.env.local`, `dashboard.sqlite3`, `.sav`,
CSV bobot, ZIP, private key, atau dump database.

Commit awal baru dibuat setelah daftar file diperiksa:

```powershell
git commit -m "Prepare secure dashboard production baseline"
git status
```

Target akhir:

```text
nothing to commit, working tree clean
```

Jangan membuat repository public. Pemilihan layanan dan pembuatan remote privat dilakukan pada
Tahap 7B2 setelah Tahap 7B1 dinyatakan lulus.
