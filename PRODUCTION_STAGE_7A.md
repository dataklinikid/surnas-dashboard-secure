# Tahap 7A — Production Readiness di Lokal

Tahap ini belum menghubungkan atau mengubah VPS. Tujuannya memastikan source code sudah memiliki
konfigurasi production yang konsisten sebelum dimasukkan ke Git privat.

## Perubahan

1. Database internal production menggunakan PostgreSQL, bukan SQLite.
2. Gunicorn menjadi application server.
3. systemd mengelola proses Gunicorn.
4. Nginx menjadi reverse proxy dan pelayan static files.
5. `.env.example` memisahkan database internal Django dari database reporting CSWeb.

## Pengujian lokal Windows

Aktifkan virtual environment dari direktori project:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements\production.txt
python manage.py test --settings=config.settings.test
python manage.py check --settings=config.settings.test
python -c "import gunicorn, psycopg; print('gunicorn=', gunicorn.__version__); print('psycopg=', psycopg.__version__)"
```

Jangan menjalankan `config.settings.production` di Windows pada tahap ini karena PostgreSQL production
belum dibuat. Konfigurasi production akan diuji setelah PostgreSQL staging tersedia pada Tahap 7C.

## Batas kelulusan

- seluruh test berstatus `OK`;
- system check tidak menemukan masalah;
- Gunicorn dan Psycopg dapat diimpor;
- fungsi lokal `local_live` tetap berjalan dan membaca data reporting melalui SSH tunnel;
- tidak ada `.env`, SQLite, CSV bobot, `.sav`, dump, atau credential di source release.

Setelah seluruh batas ini terpenuhi, lanjut ke `PRODUCTION_STAGE_7B.md`: pemeriksaan source,
inisialisasi Git privat, dan pembuatan release pertama.
