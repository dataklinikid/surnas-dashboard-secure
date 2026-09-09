# Stage 8B8G — Compact-code Multiple Answer

Patch ini menambahkan dukungan multiple-answer yang disimpan pada satu kolom
induk sebagai gabungan kode satu karakter, misalnya `156` untuk pilihan 1, 5,
dan 6. Mode lama berbasis helper biner tetap dipertahankan.

Tampilan menghasilkan dua ukuran: persentase responden dan persentase dari
seluruh pilihan. Command revisi membuat versi metadata baru, mempertahankan
versi lama sebagai riwayat, memperbarui signature, dan tidak menulis ke
database reporting.
