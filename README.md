# Dashboard Analitik Survei - Surnas Februari 2026

Project ini merupakan rekonstruksi aman dari pola dashboard CSPro/CSWeb sebelumnya. Isinya hanya dua aplikasi:

- `aggregate`: autentikasi, landing page, Group, dan Permission;
- `surnasdes26`: monitoring, frekuensi, crosstab, API terproteksi, dan koneksi read-only ke database reporting CSWeb.

Project menggunakan Django 5.2 LTS, Pandas 3, Python minimal 3.11, konfigurasi terpisah untuk development/production, dan tidak menyimpan kredensial atau data responden.

Panduan persiapan deployment disusun bertahap dalam `PRODUCTION_STAGE_7A.md` dan
`PRODUCTION_STAGE_7B.md`.

## Asumsi

1. CSWeb menjalankan `csweb:process-cases` menuju database `dbcs76_surnasfeb26_report`.
2. Tabel utama hasil parsing adalah `h0` dengan 418 kolom yang telah dicocokkan dengan dictionary CSPro 7.7.
3. `Q_AC` adalah identitas kuesioner; `h0-id` menentukan urutan record ketika ada duplikasi.
4. `Q_V` adalah nama pewawancara dan tidak digunakan sebagai status validasi.
5. `metadata.json` berasal dari dictionary Februari 2026; `demo.csv` tetap data sintetis untuk test.

## Menjalankan mode demo

Linux/macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements/development.txt
python manage.py migrate --settings=config.settings.development
python manage.py bootstrap_survey_roles --settings=config.settings.development
python manage.py createsuperuser --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements\development.txt
python manage.py migrate --settings=config.settings.development
python manage.py bootstrap_survey_roles --settings=config.settings.development
python manage.py createsuperuser --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

Masuk ke `/admin/`, buka pengguna, lalu tambahkan salah satu Group:

- `surnasdes26_monitor`;
- `surnasdes26_analyst`;
- `surnasdes26_admin`.

## Menjalankan lokal dengan database VPS melalui SSH tunnel

Mode `local_live` mempertahankan database internal Django di SQLite lokal, tetapi membaca database
reporting MariaDB 10.4 melalui connector read-only pada tunnel `127.0.0.1:3307`. Sumber legacy tidak
didaftarkan sebagai backend ORM Django karena Django 5.2 hanya mendukung MariaDB 10.5 atau lebih baru.

1. Salin `.env.local.example` menjadi `.env.local` dan isi credential akun database read-only.
2. Buka tunnel: `ssh -N -L 127.0.0.1:3307:127.0.0.1:3306 USER_VPS@IP_VPS`.
3. Periksa koneksi: `python manage.py check_survey_db --settings=config.settings.local_live`.
4. Jalankan: `python manage.py runserver --settings=config.settings.local_live`.

File `.env.local` diabaikan Git dan tidak boleh dibagikan atau dimasukkan ke ZIP.

## Pengujian

```bash
python manage.py test --settings=config.settings.test
```

Test mencakup autentikasi, permission, router, deduplikasi dataset, frequency, crosstab, dan penolakan variabel API yang tidak diizinkan.

## Konfigurasi production baru

Pasang dependency sistem Ubuntu terlebih dahulu:

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential pkg-config default-libmysqlclient-dev postgresql nginx
```

1. Ikuti pengujian lokal dalam `PRODUCTION_STAGE_7A.md`.
2. Salin `.env.example` menjadi `.env` pada VPS.
2. Isi `.env` hanya di server; jangan commit file tersebut.
3. Buat akun database khusus dashboard dengan hak `SELECT` saja dan batasi asal koneksi ke IP/private network VPS Django.
4. Gunakan TLS MariaDB atau private VPN/network.
5. Gunakan template Gunicorn, systemd, dan Nginx dalam direktori `deploy/`.

Contoh prinsip hak akses:

```sql
GRANT SELECT ON dbcs76_surnasfeb26_report.*
TO 'dashboard_readonly'@'<IP_VPS_DJANGO>' IDENTIFIED BY '<PASSWORD_RANDOM>';
```

Deployment berbasis release Git akan disiapkan pada Tahap 7B–7C. Script Apache lama tidak menjadi
jalur deployment production baru.

## Schema Februari 2026

Schema dan dictionary aktual diekspor melalui `export_legacy_metadata`. Metadata analisis hanya berisi
variabel kategorikal berlabel; item identitas, nomor telepon, nama, alamat, dan teks bebas tidak masuk
allowlist dashboard.

## Aturan dataset

Semua menu memakai `get_dataset()` yang sama:

1. nama kolom diubah menjadi uppercase;
2. baris tanpa `Q_AC` dikeluarkan;
3. data diurutkan berdasarkan `Q_AC` dan `H0_ID`;
4. record terakhir untuk setiap `Q_AC` dipertahankan;
5. filter validasi hanya diterapkan jika `SURNAS_VALID_COLUMN` dan `SURNAS_VALID_VALUE` diisi;
6. hasil disimpan dalam cache singkat.

Jika aturan validasi lapangan berbeda, ubah hanya `services/dataset.py` dan tambahkan test baru.

## Catatan keamanan

- Database reporting tidak pernah dimigrasikan oleh Django.
- Model menolak `save`, `delete`, `update`, dan bulk write melalui ORM.
- Akun database `SELECT`-only tetap menjadi pengamanan utama.
- Seluruh view survei memakai login dan permission.
- API hanya menerima variabel allowlist dari `metadata.json`.
- Template tidak menggunakan `safe` atau menyisipkan HTML hasil data melalui `innerHTML`.
- `DEBUG=False`, secure cookies, HTTPS redirect, HSTS, dan host validation aktif di production.
- Jangan menyimpan `.sav`, `.env`, dump database, private key, atau data responden dalam repository.
