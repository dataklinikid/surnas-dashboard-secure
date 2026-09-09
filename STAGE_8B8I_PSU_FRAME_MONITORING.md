# Stage 8B8I — PSU Frame dan Monitoring Operasional

## Tujuan

Stage ini memindahkan persiapan frame PSU dan pemetaan monitoring ke administrasi event Django. Database reporting CSWeb tetap hanya dibaca. Pilot pertama adalah `dapildiy_sep26` dengan frame 44 PSU dan total target 440.

## Kontrak data

- Satu baris sheet `PSU` adalah satu unit PSU.
- `RESPONDEN` adalah target PSU dan boleh berbeda pada setiap baris.
- Target event adalah `sum(RESPONDEN)`, bukan angka tetap per PSU.
- `NO KUES` adalah satu nomor atau rentang inklusif yang panjangnya harus sama dengan target PSU.
- Nomor kuesioner/responden adalah kunci utama linkage aktual ke PSU.
- Desa/kelurahan, kecamatan, dan kabupaten/kota adalah label serta audit lokasi; free text tidak digunakan sebagai kunci utama.
- Frame disimpan berversi dan ber-checksum. Unggahan baru selalu menjadi staging sebelum aktivasi eksplisit.
- Hanya satu versi frame yang aktif untuk satu event.
- Aktivasi frame menyinkronkan `SurveyDataSource.target_n` dari total frame.

## Header sheet PSU

Kolom wajib adalah `NO`, `DESA/KELURAHAN`, `KECAMATAN`, `KABUPATEN/KOTA`, `DAPIL DPRRI`, `PROVINSI`, `STATUS`, `RESPONDEN`, dan `NO KUES`. Sheet lain dan kolom metodologis tambahan tidak dipakai dalam perhitungan progres.

## Validasi impor

Impor ditolak bila file bukan XLSX, melebihi 5 MB, sheet/header wajib tidak tersedia, nomor PSU duplikat, target bukan bilangan bulat positif, lokasi wajib kosong, rentang kuesioner tidak valid, panjang rentang berbeda dari target, atau rentang antar-PSU tumpang tindih. Jeda nomor kuesioner dan lokasi berulang dilaporkan sebagai peringatan.

## Alur admin

1. Buka event lalu pilih **Frame PSU & monitoring**.
2. Unggah XLSX dengan version code baru.
3. Tinjau jumlah PSU, total target, rentang nomor, checksum, dan peringatan pada versi staging.
4. Aktifkan versi yang sudah benar.
5. Pilih kolom nomor kuesioner dari metadata aktif.
6. Pilih kolom enumerator, waktu, dan lokasi bila tersedia.
7. Simpan pemetaan dan jalankan validasi final event kembali.

## Perhitungan runtime

- Dataset dibaca melalui pipeline final yang sudah melakukan deduplikasi dan filter valid.
- Nomor kuesioner dikonversi ke bilangan bulat; nilai kosong, nonangka, dan pecahan masuk audit.
- Aktual PSU adalah jumlah nomor kuesioner unik yang berada pada rentang PSU tersebut.
- Progress PSU tidak dipotong pada 100%; excess tetap ditampilkan.
- Dashboard menampilkan target, aktual, sisa, progres per PSU dan kabupaten/kota, serta realisasi enumerator bila kolomnya dipetakan.
- Nomor di luar frame dan nomor duplikat selalu terlihat sebagai audit linkage.
- Halaman monitoring refresh otomatis sesuai interval event, default 60 detik.

## Keamanan dan audit

- Isi responden tidak disalin ke PostgreSQL control plane.
- PostgreSQL hanya menyimpan master frame, konfigurasi mapping, checksum, versi, waktu, dan pengguna pembuat/pengubah.
- XLSX sumber tidak disimpan; checksum dan baris canonical tersimpan untuk lineage.
- Mengubah frame aktif atau pemetaan mengubah configuration signature sehingga aktivasi event lama ditolak sampai validasi ulang.

## Rollout

```powershell
python manage.py migrate --settings=config.settings.local_live
python manage.py test --settings=config.settings.test
```

Setelah migrasi, seluruh langkah operasional dilakukan dari UI Django. Tidak diperlukan management command khusus untuk impor frame normal.
