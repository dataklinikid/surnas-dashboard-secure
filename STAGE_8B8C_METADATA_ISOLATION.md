# Stage 8B8C — Isolasi Metadata per Event

## Kontrak arsitektur

- Satu connection profile dan database reporting hanya dapat ditautkan ke satu event.
- Satu event memiliki satu kuesioner dan tepat satu metadata aktif.
- Identitas kuesioner aktif tidak dapat digunakan oleh event lain.
- Metadata event lain tidak dapat dipilih, diwarisi, atau disalin.
- Versi metadata lama tetap dapat disimpan sebagai riwayat tidak aktif milik event yang sama.

## Perubahan alur

Halaman metadata hanya menerima unggahan canonical JSON yang dibuat khusus dari kuesioner event. Opsi template event telah dihapus. Command `clone_survey_event_config` hanya membuat kerangka draft, sumber data, dan pilihan modul; metadata, konfigurasi dashboard, serta konfigurasi modul tidak disalin.

Metadata yang diunggah wajib memuat sedikitnya:

```json
{
  "survey": {
    "code": "kode_event",
    "dictionary_name": "IDENTITAS_KUESIONER_UNIK",
    "source_table": "h0",
    "aggregate_only": true
  },
  "variables": {},
  "build_report": {
    "contains_respondent_rows": false
  }
}
```

`survey.code` harus sama dengan kode draft event. `survey.dictionary_name` menjadi identitas kuesioner dan harus berbeda dari event lain. Metadata juga diikat ke nama database reporting saat disimpan dan diperiksa kembali pada validasi final.

## Pemasangan

```powershell
Expand-Archive `
  -Path "$HOME\Downloads\stage8b8c_event_metadata_isolation_patch_v1.zip" `
  -DestinationPath . `
  -Force

python manage.py migrate --settings=config.settings.local_live
python manage.py test --settings=config.settings.test
python manage.py check --settings=config.settings.local_live
```

Target migration:

```text
Applying aggregate.0013_event_metadata_isolation... OK
```

Migration juga merapikan salinan konfigurasi legacy secara aman. Metadata aktif tertua atau metadata milik event canonical dipertahankan. Event yang pernah dibuat melalui lineage `clone:<event>:<versi>` maupun `template:<event>:<versi>` otomatis dikenali sebagai salinan walaupun sebelumnya sempat diaktifkan; metadata salinannya dinonaktifkan dan event dikembalikan ke Draft tanpa menghapus data metadata. Tautan database gandanya juga dinonaktifkan. Jika dua event aktif menggunakan identitas yang sama tetapi keduanya bukan salinan yang dapat dikenali, migration tetap berhenti dan meminta pemeriksaan manual.

Target test:

```text
Ran 131 tests
OK
```

Setelah itu buka kembali halaman metadata draft. Antarmuka hanya menampilkan field unggah metadata event dan versi metadata; pilihan template event tidak lagi tersedia.
