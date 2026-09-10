# Stage 8B8E — Binary Occurrence Multiple Answer

Patch ini memperluas parser metadata CSPro agar item berulang bernilai biner
(`0/1`) dapat dikenali sebagai helper multiple-answer walaupun label dictionary
tidak memuat frasa literal `Multiple Answer`.

Kasus sasaran adalah pola seperti `Q_61_1C` sampai `Q_61_6C` pada
`provntt_nov24`: setiap helper memiliki `Occurrences=6`, nilai `1=Ya` dan
`0=Tidak`, serta item induk yang mendefinisikan enam pilihan media sosial.

Patch tidak mengubah database, tidak membaca baris responden, dan tidak
memerlukan migration.

Setelah dipasang, bentuk ulang canonical metadata dengan command
`parse_survey_metadata`. Target untuk `provntt_nov24` adalah enam kelompok
multiple-answer.
