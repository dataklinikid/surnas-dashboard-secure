import copy
import re
from collections import Counter
from collections.abc import Mapping


DEFAULT_SECTION = "Variabel lainnya"

SECTION_RULES = (
    (
        "Kontrol mutu wawancara",
        (
            "enumerator", "surveyor", "pewawancara", "supervisor", "spotcheck",
            "quality control", "kontrol mutu", "gps", "latitude", "longitude",
            "durasi", "waktu mulai", "waktu selesai", "status wawancara",
            "kunjungan", "device", "audio",
        ),
    ),
    (
        "Demografi dan karakteristik responden",
        (
            "jenis kelamin", "gender", "umur", "usia", "pendidikan", "pekerjaan",
            "pendapatan", "pengeluaran", "agama", "suku", "etnis", "perkawinan",
            "desa", "kelurahan", "kecamatan", "kabupaten", "provinsi", "domisili",
            "perkotaan", "perdesaan", "rural", "urban",
        ),
    ),
    (
        "Program dan kebijakan pemerintah",
        (
            "program pemerintah", "kebijakan", "bantuan sosial", "bansos", "subsidi",
            "bpjs", "kartu indonesia", "penerima bantuan", "program makan", "pangan",
        ),
    ),
    (
        "Kondisi nasional dan kinerja pemerintah",
        (
            "kinerja pemerintah", "kinerja presiden", "kepuasan", "puas", "kondisi ekonomi",
            "kondisi nasional", "arah negara", "masalah utama", "kepercayaan pemerintah",
            "kabinet", "kementerian",
        ),
    ),
    (
        "Politik dan elektoral",
        (
            "pilihan politik", "pilihan partai", "pilihan presiden", "partai", "kandidat",
            "calon", "pemilu", "pilkada", "elektabilitas", "dukungan", "mencoblos",
            "politik", "kampanye", "ideologi",
        ),
    ),
    (
        "Sosial, media, dan perilaku publik",
        (
            "media sosial", "televisi", "radio", "internet", "whatsapp", "facebook",
            "tiktok", "instagram", "youtube", "media", "organisasi", "perilaku",
            "sumber informasi", "kegiatan sosial", "isu sosial",
        ),
    ),
)


def _searchable_text(variable: str, specification: Mapping) -> str:
    label = str(specification.get("label", ""))
    normalized_name = re.sub(r"[_\-]+", " ", variable)
    return f"{normalized_name} {label}".casefold()


def semantic_section(variable: str, specification: Mapping) -> str:
    text = _searchable_text(variable, specification)
    for section, keywords in SECTION_RULES:
        if any(keyword in text for keyword in keywords):
            return section
    return DEFAULT_SECTION


def section_counts(metadata: Mapping) -> Counter:
    variables = metadata.get("variables", {})
    return Counter(
        str(specification.get("section") or DEFAULT_SECTION).strip() or DEFAULT_SECTION
        for specification in variables.values()
        if isinstance(specification, Mapping)
    )


def sections_are_informative(metadata: Mapping) -> bool:
    counts = section_counts(metadata)
    total = sum(counts.values())
    if total == 0 or len(counts) < 2:
        return False
    return max(counts.values()) / total < 0.9


def classify_metadata_sections(
    target_metadata: Mapping,
    reference_metadata: Mapping | None = None,
    *,
    preserve_current: bool = False,
) -> dict:
    classified = copy.deepcopy(target_metadata)
    variables = classified.get("variables", {})
    if not isinstance(variables, dict) or not variables:
        raise ValueError("Metadata target tidak memiliki variables yang valid.")

    reference_variables = {}
    if reference_metadata is not None:
        candidate = reference_metadata.get("variables", {})
        if not isinstance(candidate, Mapping):
            raise ValueError("Metadata referensi tidak memiliki variables yang valid.")
        reference_variables = candidate

    preserve_existing = preserve_current or sections_are_informative(target_metadata)
    sources = Counter()
    changed = 0
    for variable, specification in variables.items():
        old_section = str(specification.get("section") or DEFAULT_SECTION).strip()
        reference_specification = reference_variables.get(variable)
        if isinstance(reference_specification, Mapping) and reference_specification.get("section"):
            new_section = str(reference_specification["section"]).strip()
            source = "reference"
        elif preserve_existing and old_section:
            new_section = old_section
            source = "existing"
        else:
            new_section = semantic_section(variable, specification)
            source = "semantic"
        specification["section"] = new_section or DEFAULT_SECTION
        sources[source] += 1
        if specification["section"] != old_section:
            changed += 1

    return {
        "metadata": classified,
        "variable_count": len(variables),
        "changed_count": changed,
        "source_counts": dict(sources),
        "section_counts": dict(section_counts(classified)),
    }
