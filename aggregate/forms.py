from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from aggregate.models import (
    LOWER_CODE_VALIDATOR,
    SQL_IDENTIFIER_VALIDATOR,
    EventModuleDefinition,
    EventType,
    Region,
    SurveyAccess,
    SurveyConnectionProfile,
    SurveyProgram,
    SurveyWeightSet,
)
from aggregate.weight_reuse import compatible_weight_sets
from aggregate.access_roles import ROLE_CHOICES


class EventIdentityForm(forms.Form):
    code = forms.CharField(
        label="Kode event",
        max_length=64,
        validators=[LOWER_CODE_VALIDATOR],
        help_text="Contoh: pilkada_surabaya27. Kode tidak dapat diubah setelah event dibuat.",
    )
    name = forms.CharField(label="Nama event", max_length=120)
    event_type = forms.ModelChoiceField(
        label="Jenis event",
        queryset=EventType.objects.none(),
    )
    period_start = forms.DateField(
        label="Tanggal mulai",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    period_end = forms.DateField(
        label="Tanggal selesai",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event_type"].queryset = EventType.objects.filter(active=True)

    def clean_code(self):
        code = self.cleaned_data["code"].strip().lower()
        if SurveyAccess.objects.filter(code=code).exists():
            raise ValidationError("Kode event sudah digunakan.")
        return code

    def clean(self):
        cleaned = super().clean()
        period_start = cleaned.get("period_start")
        period_end = cleaned.get("period_end")
        if period_start and period_end and period_end < period_start:
            self.add_error(
                "period_end",
                "Tanggal selesai tidak boleh lebih awal dari tanggal mulai.",
            )
        return cleaned


class SourceCatalogScanForm(forms.Form):
    connection_profile = forms.ModelChoiceField(
        label="Profil koneksi CSWeb",
        queryset=SurveyConnectionProfile.objects.none(),
        help_text="Catalog hanya menampilkan database reporting yang dapat dilihat akun read-only.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["connection_profile"].queryset = SurveyConnectionProfile.objects.filter(
            active=True
        ).order_by("name")


class EventReferencesForm(forms.Form):
    program_existing = forms.ModelChoiceField(
        label="Program yang sudah ada",
        queryset=SurveyProgram.objects.none(),
        required=False,
        empty_label="— Buat program baru —",
    )
    program_code = forms.CharField(
        label="Kode program baru",
        max_length=64,
        required=False,
        validators=[LOWER_CODE_VALIDATOR],
    )
    program_name = forms.CharField(label="Nama program baru", max_length=160, required=False)
    region_existing = forms.ModelChoiceField(
        label="Wilayah yang sudah ada",
        queryset=Region.objects.none(),
        required=False,
        empty_label="— Buat wilayah baru —",
    )
    region_code = forms.CharField(
        label="Kode wilayah baru",
        max_length=64,
        required=False,
        validators=[LOWER_CODE_VALIDATOR],
    )
    region_name = forms.CharField(label="Nama wilayah baru", max_length=160, required=False)
    region_level = forms.ChoiceField(
        label="Tingkat wilayah baru",
        choices=(("", "— Pilih tingkat —"), *Region.Level.choices),
        required=False,
    )
    region_parent = forms.ModelChoiceField(
        label="Induk wilayah baru",
        queryset=Region.objects.none(),
        required=False,
        empty_label="— Tidak ada/tingkat teratas —",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program_existing"].queryset = SurveyProgram.objects.filter(active=True)
        regions = Region.objects.filter(active=True).select_related("parent")
        self.fields["region_existing"].queryset = regions
        self.fields["region_parent"].queryset = regions

    def clean(self):
        cleaned = super().clean()
        program_existing = cleaned.get("program_existing")
        program_code = (cleaned.get("program_code") or "").strip().lower()
        program_name = (cleaned.get("program_name") or "").strip()
        if program_existing and (program_code or program_name):
            raise ValidationError("Pilih program yang sudah ada atau buat program baru, bukan keduanya.")
        if not program_existing:
            if not program_code or not program_name:
                raise ValidationError("Pilih program yang sudah ada atau isi kode dan nama program baru.")
            if SurveyProgram.objects.filter(code=program_code).exists():
                self.add_error("program_code", "Kode program sudah tersedia; pilih dari daftar.")

        region_existing = cleaned.get("region_existing")
        region_code = (cleaned.get("region_code") or "").strip().lower()
        region_name = (cleaned.get("region_name") or "").strip()
        region_level = cleaned.get("region_level")
        region_parent = cleaned.get("region_parent")
        if region_existing and (region_code or region_name or region_level or region_parent):
            raise ValidationError("Pilih wilayah yang sudah ada atau buat wilayah baru, bukan keduanya.")
        if not region_existing:
            if not region_code or not region_name or not region_level:
                raise ValidationError(
                    "Pilih wilayah yang sudah ada atau isi kode, nama, dan tingkat wilayah baru."
                )
            if Region.objects.filter(code=region_code).exists():
                self.add_error("region_code", "Kode wilayah sudah tersedia; pilih dari daftar.")

        cleaned["program_code"] = program_code
        cleaned["program_name"] = program_name
        cleaned["region_code"] = region_code
        cleaned["region_name"] = region_name
        return cleaned


class EventModulesForm(forms.Form):
    modules = forms.ModelMultipleChoiceField(
        label="Modul event",
        queryset=EventModuleDefinition.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text="Pilih hanya modul yang benar-benar diperlukan pada event ini.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["modules"].queryset = EventModuleDefinition.objects.filter(active=True)


class EventDataSourceForm(forms.Form):
    connection_profile = forms.ModelChoiceField(
        label="Profil koneksi",
        queryset=SurveyConnectionProfile.objects.none(),
        help_text="Profil menunjuk ke kredensial pada environment server; password tidak disimpan di event.",
    )
    database_name = forms.CharField(
        label="Nama database reporting",
        max_length=64,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    table_name = forms.CharField(
        label="Nama tabel responden",
        max_length=64,
        initial="h0",
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    identity_column = forms.CharField(
        label="Kolom identitas responden",
        max_length=64,
        initial="Q_AC",
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    latest_id_column = forms.CharField(
        label="Kolom ID versi terakhir",
        max_length=64,
        initial="H0_ID",
        required=False,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    valid_column = forms.CharField(
        label="Kolom filter kasus valid",
        max_length=64,
        required=False,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    valid_value = forms.CharField(
        label="Nilai kasus valid",
        max_length=120,
        required=False,
    )
    target_n = forms.IntegerField(label="Target jumlah kasus", min_value=1, required=False)

    def __init__(self, *args, locked_source=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["connection_profile"].queryset = SurveyConnectionProfile.objects.filter(
            active=True
        )
        if locked_source:
            for name in (
                "connection_profile",
                "database_name",
                "table_name",
                "identity_column",
                "latest_id_column",
            ):
                self.fields[name].disabled = True
                self.fields[name].help_text = (
                    "Nilai berasal dari CSWeb Source Catalog dan dikunci untuk mencegah salah tautan."
                )

    def clean(self):
        cleaned = super().clean()
        valid_column = (cleaned.get("valid_column") or "").strip()
        valid_value = (cleaned.get("valid_value") or "").strip()
        if bool(valid_column) != bool(valid_value):
            raise ValidationError("Kolom dan nilai filter kasus valid harus diisi bersama-sama.")
        for name in (
            "database_name",
            "table_name",
            "identity_column",
            "latest_id_column",
            "valid_column",
        ):
            if cleaned.get(name):
                cleaned[name] = cleaned[name].strip()
        cleaned["valid_value"] = valid_value
        return cleaned


class EventMetadataForm(forms.Form):
    version = forms.SlugField(
        label="Versi metadata",
        max_length=80,
        initial="metadata_v1",
        help_text="Dictionary dibaca langsung dari cspro_meta pada database reporting.",
    )

    def __init__(self, *args, survey=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey

    def clean_version(self):
        version = self.cleaned_data["version"].strip().lower()
        if self.survey and self.survey.metadata_versions.filter(version=version).exists():
            raise ValidationError("Versi metadata sudah digunakan pada event ini.")
        return version


class EventPSUFrameForm(forms.Form):
    version = forms.SlugField(
        label="Versi frame PSU",
        max_length=80,
        initial="psu_frame_v1",
        help_text="Gunakan versi baru untuk setiap revisi frame; versi aktif tidak ditimpa.",
    )
    frame_file = forms.FileField(
        label="File frame PSU (.xlsx)",
        help_text="Sistem membaca sheet PSU. Target event dihitung dari jumlah RESPONDEN per baris.",
    )

    def __init__(self, *args, survey=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey

    def clean_version(self):
        version = self.cleaned_data["version"].strip().lower()
        if self.survey and self.survey.psu_frames.filter(version=version).exists():
            raise ValidationError("Versi frame PSU sudah digunakan pada event ini.")
        return version

    def clean_frame_file(self):
        uploaded = self.cleaned_data["frame_file"]
        if not uploaded.name.lower().endswith(".xlsx"):
            raise ValidationError("File frame PSU harus berformat .xlsx.")
        if uploaded.size > 5 * 1024 * 1024:
            raise ValidationError("Ukuran file frame PSU maksimal 5 MB.")
        return uploaded


class EventMonitoringConfigForm(forms.Form):
    questionnaire_column = forms.ChoiceField(
        label="Nomor kuesioner/responden",
        help_text="Kunci utama yang dipetakan ke rentang NO KUES pada frame PSU.",
    )
    enumerator_column = forms.ChoiceField(label="Nama enumerator", required=False)
    submit_time_column = forms.ChoiceField(label="Waktu submit", required=False)
    start_hour_column = forms.ChoiceField(label="Jam mulai", required=False)
    start_minute_column = forms.ChoiceField(label="Menit mulai", required=False)
    village_column = forms.ChoiceField(label="Desa/kelurahan (audit)", required=False)
    district_column = forms.ChoiceField(label="Kecamatan (audit)", required=False)
    regency_column = forms.ChoiceField(label="Kabupaten/kota (audit)", required=False)
    refresh_seconds = forms.IntegerField(
        label="Interval refresh (detik)", min_value=30, max_value=3600, initial=60
    )

    def __init__(self, *args, variable_names=(), **kwargs):
        super().__init__(*args, **kwargs)
        choices = [("", "— Tidak digunakan —")]
        choices.extend((name, name) for name in sorted(set(variable_names)))
        for field_name in (
            "questionnaire_column", "enumerator_column", "submit_time_column",
            "start_hour_column", "start_minute_column", "village_column",
            "district_column", "regency_column",
        ):
            self.fields[field_name].choices = choices
        self.fields["questionnaire_column"].choices = choices[1:]

class WeightModuleDecisionForm(forms.Form):
    REUSE = "reuse"
    DISABLE = "disable"
    ACTION_CHOICES = (
        (REUSE, "Gunakan ulang weight set yang sudah terverifikasi"),
        (DISABLE, "Lanjutkan event tanpa analisis berbobot"),
    )

    action = forms.ChoiceField(
        label="Keputusan modul berbobot",
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect,
    )
    source_weight_set = forms.ModelChoiceField(
        label="Weight set sumber",
        queryset=SurveyWeightSet.objects.none(),
        required=False,
        empty_label="— Pilih weight set kompatibel —",
    )
    version = forms.SlugField(
        label="Versi pada event baru",
        max_length=80,
        required=False,
        initial="raking_v1",
    )

    def __init__(self, *args, survey=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey
        if survey is not None:
            self.fields["source_weight_set"].queryset = compatible_weight_sets(survey)

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        source = cleaned.get("source_weight_set")
        version = (cleaned.get("version") or "").strip().lower()
        if action == self.REUSE:
            if source is None:
                self.add_error("source_weight_set", "Pilih weight set sumber.")
            if not version:
                self.add_error("version", "Versi bobot wajib diisi.")
        elif action == self.DISABLE:
            if source is not None:
                self.add_error("source_weight_set", "Jangan pilih weight set saat menonaktifkan modul.")
        cleaned["version"] = version
        return cleaned


class EventMembershipForm(forms.Form):
    user = forms.ModelChoiceField(
        label="Pengguna aktif",
        queryset=get_user_model().objects.none(),
        empty_label="— Pilih pengguna —",
    )
    role = forms.ChoiceField(label="Peran pada event", choices=ROLE_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = get_user_model().objects.filter(
            is_active=True
        ).order_by("username")


class EventActivationForm(forms.Form):
    confirmation_code = forms.CharField(label="Ketik kode event untuk konfirmasi")
    confirm = forms.BooleanField(
        label="Saya memahami bahwa event akan tersedia bagi pengguna yang diberi akses."
    )

    def __init__(self, *args, survey=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey

    def clean_confirmation_code(self):
        value = self.cleaned_data["confirmation_code"].strip()
        if self.survey is None or value != self.survey.code:
            raise ValidationError("Kode konfirmasi tidak sama dengan kode event.")
        return value
