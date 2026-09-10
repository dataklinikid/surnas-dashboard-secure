# Stage 8B8D — Ekspor Sumber Metadata Event Dinamis

Command `export_event_metadata_source` membaca `SurveyDataSource` milik event dinamis, lalu mengekspor dictionary terbaru dari `cspro_meta` dan schema tabel `h0`. Command menjalankan tiga query read-only dan tidak mengekspor baris responden.

```powershell
python manage.py export_event_metadata_source `
  --survey provntt_nov24 `
  --settings=config.settings.local_live
```

Keluaran default:

```text
local_artifacts/provntt_nov24_metadata_source/
  cspro_dictionary.txt
  h0_schema.json
  manifest.json
```

Bangun canonical metadata:

```powershell
python manage.py parse_survey_metadata `
  --source ".\local_artifacts\provntt_nov24_metadata_source" `
  --code provntt_nov24 `
  --name "Survei Provinsi NTT November 2024" `
  --output ".\local_artifacts\provntt_nov24_canonical_metadata.json" `
  --settings=config.settings.local_live
```

File canonical perlu diperiksa sebelum diunggah melalui halaman metadata event. Khususnya periksa `survey.code`, `survey.dictionary_name`, `survey.source_table`, jumlah variabel kategorik, kelompok multiple-answer, daftar kolom yang tidak ditemukan, dan `contains_respondent_rows=false`.
