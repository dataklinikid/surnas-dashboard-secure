# Cetak Biru Platform Event Survei

## Keputusan arsitektur

Platform tetap menggunakan **modular monolith Django**. `SurveyAccess` dipertahankan sebagai identitas event karena sudah menjadi penghubung membership, metadata, sumber data, bobot, validasi, dan runtime. Nama teknis ini dapat diperbaiki pada antarmuka menjadi **Event** tanpa mengganti tabel secara berisiko.

Git hanya digunakan ketika source code, migration, adapter sumber data, atau jenis komponen analisis berubah. Penambahan event normal nantinya dilakukan melalui Event Onboarding Wizard dan disimpan di PostgreSQL.

## Lapisan domain

| Lapisan | Tanggung jawab | Contoh |
|---|---|---|
| Control plane | Identitas, status, modul, akses, dan versi konfigurasi event | Event, wilayah, program, membership |
| Integration | Koneksi read-only ke sistem sumber | CSWeb/MariaDB, tabel `h0` |
| Metadata | Definisi pertanyaan dan pemetaan makna variabel | Q_12 menjadi `candidate_choice` |
| Master data | Data referensi berversi | PSU, DPT, TPS, enumerator, relawan |
| Analytics | Perhitungan generik dan standar | Frekuensi, crosstab, weighting |
| Operations | Monitoring pelaksanaan | Progress per waktu, lokasi, enumerator |
| Reporting | Template, snapshot, dan dokumen | Laporan standar dan custom event |

## Entitas fondasi Tahap 8B0

| Entitas | Fungsi |
|---|---|
| `EventType` | Menentukan pola utama event: survei opini, quick count, operasi lapangan, atau gabungan |
| `EventModuleDefinition` | Katalog kemampuan platform yang tersedia |
| `SurveyEventModule` | Memilih modul yang berlaku pada satu event dan mencatat kesiapan konfigurasinya |
| `SurveyAccess` | Tetap menjadi identitas event dan pusat relasi yang sudah berjalan |
| `SurveyConnectionProfile` | Whitelist koneksi yang boleh dipilih wizard; hanya menyimpan alias dan environment prefix, bukan kredensial |

Migration 0008 mengisi katalog standar. Event yang sudah ada diperlakukan sebagai survei opini serta memperoleh modul monitoring lapangan, analisis survei, dan analisis berbobot. Hal ini hanya mencatat kemampuan yang sudah ada; tidak mengubah rumus, akses, status, atau weight set aktif.

## Urutan MVP Event Onboarding Wizard

1. Identitas event: nama, kode, jenis, program, wilayah, dan periode.
2. Pemilihan modul: hanya fitur yang dibutuhkan event.
3. Sumber data: memilih connection profile yang sudah disetujui dan database/tabel sumber.
4. Metadata: mengunggah metadata canonical yang dihasilkan khusus dari kuesioner event tersebut.
5. Semantic variable mapping: menghubungkan variabel aktual ke peran analisis standar.
6. Master data: mengunggah dataset yang diwajibkan oleh modul terpilih.
7. Validasi: menampilkan pemeriksaan dan penghambat secara terpusat.
8. Aktivasi dan akses: mengaktifkan event serta menetapkan pengguna.

## Implementasi sampai Stage 8B2

Wizard telah menangani enam langkah awal: identitas, referensi program/wilayah, modul, kontrak sumber data, review, dan pembuatan draft. Program dan wilayah baru hanya dibuat pada konfirmasi akhir dalam transaksi yang sama dengan event. Profil koneksi menyimpan `environment_prefix`; host, port, username, dan password tetap dibaca dari environment server.

Wizard belum menguji koneksi atau membaca isi database pada Stage 8B2. Pemeriksaan tersebut baru aman dilakukan bersama metadata pada tahap selanjutnya, karena validasi memerlukan identity column, latest ID, dan daftar variabel yang seharusnya tersedia.

### Stage 8B3

Event Draft hanya dapat menerima unggahan metadata canonical JSON maksimal 5 MB yang dibuat dari kuesioner event tersebut. Metadata event lain tidak dapat dipilih, diwarisi, atau disalin. Kontraknya adalah satu connection profile/database report untuk satu event, satu identitas kuesioner aktif untuk satu event, dan tepat satu metadata aktif per event. Riwayat versi metadata tetap dapat disimpan sebagai versi tidak aktif milik event yang sama.

Pemeriksaan awal sumber data hanya menjalankan dua query read-only: `SELECT COUNT(*)` dan `SELECT ... LIMIT 0`. Sistem membandingkan identity column, latest ID, filter valid, variabel kategorik, dan helper multiple-answer dengan kolom aktual. Jika ada kolom wajib yang hilang, metadata tidak disimpan. Jika lulus, metadata beserta onboarding report disimpan dan status event bergerak dari Draft ke Validasi, tetapi event tetap tidak aktif.

### Stage 8B4

Validasi final dapat dijalankan oleh staff melalui antarmuka dengan tetap menggunakan mesin validasi management command yang sama. Proses membaca dataset reporting, menghapus key kosong, memilih rekaman terakhir per identity/latest ID, menerapkan filter valid, memeriksa metadata, menghitung kasus final, dan membentuk dataset fingerprint.

Module readiness diperlakukan sebagai derived state dan tidak masuk configuration signature. Monitoring lapangan dan analisis survei menjadi siap setelah dataset lulus. Analisis berbobot baru siap jika terdapat tepat satu weight set aktif dengan coverage 100% dan fingerprint yang sama. Modul lain tetap pending sampai master data atau konfigurasi khususnya tersedia. Activation gate menolak event selama masih ada modul terpilih yang belum siap.

### Stage 8B5

Keputusan analisis berbobot menjadi langkah eksplisit setelah validasi final. Weight set event lain hanya dapat digunakan ulang jika sumber masih aktif dan seluruh kontrak berikut cocok: fingerprint dataset, identity column, jumlah kasus final, jumlah detail bobot, serta coverage tepat 100%. Sistem menyalin detail bobot ke event target dan menyimpan `parent_weight_set` sebagai lineage; weight set sumber tidak dipindahkan atau dinonaktifkan.

Jika analisis berbobot tidak diperlukan, admin dapat menonaktifkan modul tersebut. Perubahan ini mengosongkan hasil validasi karena susunan modul merupakan bagian dari configuration signature. Validasi final wajib dijalankan kembali sebelum activation gate dapat lulus. Kedua pilihan tidak mengaktifkan event secara otomatis.

### Stage 8B6

Aktivasi dan akses digabungkan dalam satu review final, tetapi tetap menjadi dua tindakan terpisah. Admin lebih dahulu menetapkan membership event dengan peran Monitor, Analyst, atau Admin event. Peran Admin event hanya berarti monitoring, analisis, dan export pada event tersebut; peran ini tidak memberikan status Django staff, superuser, atau akses server.

Activation gate digunakan bersama oleh antarmuka dan management command. Gate memeriksa status validation, validation state, checksum metadata, configuration signature, kesiapan seluruh modul aktif, laporan validasi tanpa error, serta minimal satu membership dengan hak operasional. Aktivasi memerlukan pengetikan ulang kode event dan transaksi dengan row lock. Jika konfigurasi berubah di antara review dan submit, aktivasi ditolak. Setelah berhasil, event menjadi sumber runtime PostgreSQL dan hanya terlihat oleh pengguna sesuai membership.

### Stage 8B6A — kontrak monitoring dinamis

Modul monitoring lapangan memerlukan `dashboard_config.monitoring_group_variable` yang tersedia pada metadata aktif. Lulusnya validasi dataset saja tidak lagi cukup untuk menyatakan modul monitoring siap. Konfigurasi dapat berasal dari object `dashboard` pada metadata event; `Q_F` digunakan sebagai default hanya jika kolom tersebut memang terdaftar pada metadata. Konfigurasi dashboard event lain tidak disalin.

Event aktif yang terlanjur tidak memiliki konfigurasi monitoring diperbaiki melalui command tervalidasi `configure_event_monitoring`. Command memeriksa keberadaan variabel pada metadata, mempertahankan status aktif, memperbarui configuration signature, dan menyimpan signature sebelumnya sebagai riwayat. Database reporting tetap read-only dan tidak diubah.

### Stage 8B7A — CSWeb Source Catalog

Onboarding dimulai dari sumber yang benar-benar tersedia, bukan dari pengetikan nama database. Staff memilih connection profile lalu menjalankan discovery read-only. Catalog memakai `SHOW DATABASES` dan `information_schema` untuk menampilkan database yang cocok dengan pola `dbcs..._report` atau `csdb..._report`, keberadaan tabel `h0`, estimasi baris, jumlah kolom, serta ketersediaan `Q_AC` dan `H0_ID`.

Catalog menyinkronkan hasil discovery dengan `SurveyDataSource` berdasarkan connection profile, database, dan tabel. Event aktif maupun draft yang sudah berjalan hanya diberi status "sudah tertaut" dan tidak diubah. Database tanpa `h0` atau tanpa `Q_AC` ditandai tidak valid. Database reporting yang memenuhi kontrak tetapi belum memiliki event ditandai siap ditautkan. Discovery tidak menyimpan kredensial, tidak membaca baris responden, dan tidak menulis ke CSWeb.

### Stage 8B7B — tautkan catalog ke wizard

Database yang valid dan belum tertaut memiliki tindakan "Tautkan sebagai event". Saat tindakan dijalankan, server melakukan discovery ulang agar keputusan tidak bergantung pada data form atau hasil scan lama. Wizard memperoleh saran kode dan nama dari pola database, sedangkan connection profile, database, tabel, identity column, dan latest ID disimpan pada session serta dikunci pada form sumber. Admin tetap menentukan identitas bisnis, jenis event, program, wilayah, periode, modul, filter valid, dan target kasus.

Sebelum draft disimpan, sistem kembali memeriksa apakah kombinasi connection profile, database, dan tabel telah digunakan. Alur manual tetap tersedia untuk sumber khusus, tetapi alur catalog menjadi jalur utama. Event dan data source lama tidak dimodifikasi.

### Stage 8B7C — pemisahan kredensial discovery dan runtime

Satu `SurveyConnectionProfile` merepresentasikan satu server/sistem sumber, sehingga event lama dan hasil catalog tetap berada pada namespace tautan yang sama. Profile dapat memiliki `environment_prefix` runtime lama serta `discovery_environment_prefix` untuk akun read-only lintas database report. Scan catalog memakai prefix discovery; event lama mempertahankan prefix yang telah disalin pada `SurveyDataSource`; event baru dari catalog memakai prefix discovery sebagai runtime read-only. Dengan demikian, penambahan akun catalog tidak mengubah kredensial event aktif dan tidak membuat database lama tampak sebagai sumber baru hanya karena profile berbeda.

## Batas MVP pertama

MVP pertama hanya mencakup event **survei opini** dengan sumber CSWeb/MariaDB, monitoring, analisis, dan weighting. Quick count, report builder, sampling frame, serta monitoring personel tetap masuk desain, tetapi implementasinya dilakukan setelah alur onboarding survei opini berhasil dari awal sampai aktif.

## Aturan desain yang tidak boleh dilanggar

- Kredensial tidak disimpan pada model event atau Git.
- Event aktif tidak diedit langsung; perubahan berikutnya harus menjadi revisi yang divalidasi ulang.
- Nomor pertanyaan tidak boleh di-hard-code pada laporan standar; gunakan semantic variable mapping.
- Master data harus berversi, memiliki checksum, dan dapat ditelusuri ke event.
- Quick count tidak digabung ke tabel responden survei dan tidak menggunakan survey weight.
- Report run harus menyimpan snapshot versi dataset, metadata, bobot, master data, template, filter, waktu, dan pembuat.
