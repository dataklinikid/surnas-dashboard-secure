# Stage 8B8F — Optional Monitoring Target

Patch ini memperbaiki halaman monitoring event dinamis ketika `target_n` belum
ditetapkan. Nilai `None`, kosong, nol, atau tidak valid tidak lagi dikonversi
langsung dengan `int()`.

Untuk event tanpa target, jumlah kuesioner unik tetap ditampilkan, sedangkan
Target menjadi `Belum ditetapkan` dan Progres menjadi `—`. Event yang memiliki
target tetap menghitung persentase seperti sebelumnya.

Patch tidak memerlukan migration dan tidak mengubah data event.
