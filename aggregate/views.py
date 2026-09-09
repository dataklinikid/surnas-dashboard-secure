from io import StringIO

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from aggregate.forms import (
    EventActivationForm,
    EventDataSourceForm,
    EventIdentityForm,
    EventMetadataForm,
    EventMonitoringConfigForm,
    EventMembershipForm,
    EventModulesForm,
    EventPSUFrameForm,
    EventReferencesForm,
    SourceCatalogScanForm,
    WeightModuleDecisionForm,
)
from aggregate.models import (
    EventModuleDefinition,
    EventType,
    Region,
    SurveyAccess,
    SurveyConnectionProfile,
    SurveyDataSource,
    SurveyEventModule,
    SurveyMetadataVersion,
    SurveyMembership,
    SurveyMonitoringConfig,
    SurveyPSUFrame,
    SurveyProgram,
)
from aggregate.metadata_onboarding import (
    MetadataOnboardingError,
    inspect_metadata_source,
    prepare_metadata_candidate,
    reporting_column_names,
)
from aggregate.module_readiness import (
    event_module_readiness_rows,
    refresh_event_module_readiness,
)
from aggregate.services import visible_surveys_for
from aggregate.weight_reuse import WeightReuseError, reuse_weight_set
from aggregate.source_catalog import (
    SourceCatalogError,
    discover_reporting_databases,
    suggested_event_name,
    verified_link_candidate,
)
from aggregate.access_roles import ROLE_CAPABILITIES, role_for_capabilities
from aggregate.event_activation import (
    EventActivationError,
    activate_event,
    evaluate_activation_gate,
)
from aggregate.psu_frames import PSUFrameError, activate_psu_frame, stage_psu_frame


EVENT_ONBOARDING_SESSION_KEY = "event_onboarding_v2"
DEFAULT_MODULES_BY_EVENT_TYPE = {
    "opinion_survey": (
        "fieldwork_monitoring",
        "survey_analytics",
        "weighted_analysis",
    ),
    "quick_count": ("quick_count", "personnel_monitoring"),
    "field_operation": (
        "fieldwork_monitoring",
        "sampling_frame",
        "personnel_monitoring",
    ),
    "combined": (
        "fieldwork_monitoring",
        "survey_analytics",
        "weighted_analysis",
        "sampling_frame",
        "reporting",
        "quick_count",
        "personnel_monitoring",
    ),
}


@login_required
def home(request):
    surveys = visible_surveys_for(request.user)
    setup_events = []
    if request.user.is_staff:
        setup_events = list(
            SurveyAccess.objects.filter(
                active=False,
                status__in=(SurveyAccess.Status.DRAFT, SurveyAccess.Status.VALIDATION),
            )
            .select_related("event_type", "region")
            .prefetch_related("metadata_versions")
            .order_by("name")
        )
    return render(
        request,
        "aggregate/home.html",
        {"surveys": surveys, "setup_events": setup_events},
    )


@staff_member_required(login_url="login")
def source_catalog(request):
    catalog_rows = []
    selected_profile = None
    if request.method == "POST":
        form = SourceCatalogScanForm(request.POST)
        if form.is_valid():
            selected_profile = form.cleaned_data["connection_profile"]
            try:
                discovered = discover_reporting_databases(selected_profile)
            except SourceCatalogError as exc:
                form.add_error(None, str(exc))
            else:
                linked_sources = {}
                for source in SurveyDataSource.objects.filter(
                    connection_profile=selected_profile
                ).select_related("survey"):
                    key = (source.database_name.casefold(), source.table_name.casefold())
                    linked_sources.setdefault(key, []).append(source.survey)
                for row in discovered:
                    key = (
                        row["database_name"].casefold(),
                        row["table_name"].casefold(),
                    )
                    linked = linked_sources.get(key, []) if row["table_name"] else []
                    row["linked_events"] = linked
                    if linked:
                        row["catalog_status"] = "linked"
                        row["catalog_status_label"] = "Sudah tertaut"
                    elif not row["table_name"]:
                        row["catalog_status"] = "invalid"
                        row["catalog_status_label"] = "Tabel h0 tidak ditemukan"
                    elif not row.get("has_cspro_meta"):
                        row["catalog_status"] = "invalid"
                        row["catalog_status_label"] = "cspro_meta tidak ditemukan"
                    elif not row["has_identity"]:
                        row["catalog_status"] = "invalid"
                        row["catalog_status_label"] = "Q_AC tidak ditemukan"
                    else:
                        row["catalog_status"] = "available"
                        row["catalog_status_label"] = "Belum tertaut"
                    catalog_rows.append(row)
    else:
        form = SourceCatalogScanForm()
    return render(
        request,
        "aggregate/source_catalog.html",
        {
            "form": form,
            "catalog_rows": catalog_rows,
            "selected_profile": selected_profile,
        },
    )


@staff_member_required(login_url="login")
def source_catalog_link(request):
    if request.method != "POST":
        raise Http404
    profile = get_object_or_404(
        SurveyConnectionProfile,
        pk=request.POST.get("connection_profile"),
        active=True,
    )
    database_name = request.POST.get("database_name", "")
    try:
        candidate = verified_link_candidate(profile, database_name)
    except SourceCatalogError as exc:
        messages.error(request, str(exc))
        return redirect("aggregate:source_catalog")
    if SurveyDataSource.objects.filter(
        connection_profile=profile,
        database_name__iexact=candidate["database_name"],
        table_name__iexact=candidate["table_name"],
    ).exists():
        messages.error(request, "Sumber sudah tertaut pada event. Pindai ulang catalog.")
        return redirect("aggregate:source_catalog")

    state = {
        "identity": {
            "code": candidate["suggested_code"],
            "name": suggested_event_name(candidate["database_name"]),
            "period_start": "",
            "period_end": "",
        },
        "data_source": {
            "connection_profile": profile.pk,
            "database_name": candidate["database_name"],
            "table_name": candidate["table_name"],
            "identity_column": "Q_AC",
            "latest_id_column": "H0_ID" if candidate["has_latest_id"] else "",
            "valid_column": "",
            "valid_value": "",
            "target_n": None,
        },
        "catalog_source": {
            "connection_profile": profile.pk,
            "database_name": candidate["database_name"],
            "table_name": candidate["table_name"],
        },
    }
    request.session[EVENT_ONBOARDING_SESSION_KEY] = state
    messages.success(
        request,
        "Sumber catalog terverifikasi. Lengkapi identitas bisnis event.",
    )
    return redirect("aggregate:event_onboarding_identity")


def _serialize_identity(cleaned_data):
    return {
        "code": cleaned_data["code"],
        "name": cleaned_data["name"].strip(),
        "event_type": cleaned_data["event_type"].pk,
        "period_start": cleaned_data["period_start"].isoformat()
        if cleaned_data.get("period_start")
        else "",
        "period_end": cleaned_data["period_end"].isoformat()
        if cleaned_data.get("period_end")
        else "",
    }


def _serialize_references(cleaned_data):
    program = cleaned_data.get("program_existing")
    if program:
        program_state = {"mode": "existing", "id": program.pk}
    else:
        program_state = {
            "mode": "new",
            "code": cleaned_data["program_code"],
            "name": cleaned_data["program_name"],
        }

    region = cleaned_data.get("region_existing")
    if region:
        region_state = {"mode": "existing", "id": region.pk}
    else:
        parent = cleaned_data.get("region_parent")
        region_state = {
            "mode": "new",
            "code": cleaned_data["region_code"],
            "name": cleaned_data["region_name"],
            "level": cleaned_data["region_level"],
            "parent_id": parent.pk if parent else None,
        }
    return {"program": program_state, "region": region_state}


def _references_initial(state):
    references = state.get("references", {})
    program = references.get("program", {})
    region = references.get("region", {})
    initial = {}
    if program.get("mode") == "existing":
        initial["program_existing"] = program.get("id")
    else:
        initial["program_code"] = program.get("code", "")
        initial["program_name"] = program.get("name", "")
    if region.get("mode") == "existing":
        initial["region_existing"] = region.get("id")
    else:
        initial["region_code"] = region.get("code", "")
        initial["region_name"] = region.get("name", "")
        initial["region_level"] = region.get("level", "")
        initial["region_parent"] = region.get("parent_id")
    return initial


def _serialize_data_source(cleaned_data):
    return {
        "connection_profile": cleaned_data["connection_profile"].pk,
        "database_name": cleaned_data["database_name"],
        "table_name": cleaned_data["table_name"],
        "identity_column": cleaned_data["identity_column"],
        "latest_id_column": cleaned_data["latest_id_column"],
        "valid_column": cleaned_data["valid_column"],
        "valid_value": cleaned_data["valid_value"],
        "target_n": cleaned_data.get("target_n"),
    }


def _reference_preview(reference, model, label):
    if reference.get("mode") == "existing":
        return get_object_or_404(model, pk=reference.get("id"), active=True)
    code = reference.get("code", "")
    name = reference.get("name", "")
    if not code or not name or model.objects.filter(code=code).exists():
        raise Http404(f"{label} baru tidak lagi valid.")
    return reference


def _review_context(state):
    identity = state.get("identity")
    references = state.get("references")
    module_ids = state.get("modules")
    data_source = state.get("data_source")
    if not identity or not references or not module_ids or not data_source:
        raise Http404("Data onboarding belum lengkap.")

    event_type = get_object_or_404(EventType, pk=identity["event_type"], active=True)
    program = _reference_preview(references["program"], SurveyProgram, "Program")
    region = _reference_preview(references["region"], Region, "Wilayah")
    modules = list(
        EventModuleDefinition.objects.filter(pk__in=module_ids, active=True).order_by(
            "display_order", "name"
        )
    )
    if len(modules) != len(set(module_ids)):
        raise Http404("Katalog modul onboarding berubah.")
    connection_profile = get_object_or_404(
        SurveyConnectionProfile,
        pk=data_source["connection_profile"],
        active=True,
    )
    source_environment_prefix = connection_profile.environment_prefix
    if state.get("catalog_source"):
        source_environment_prefix = (
            connection_profile.discovery_environment_prefix
            or connection_profile.environment_prefix
        )
    return {
        "identity": identity,
        "references": references,
        "event_type": event_type,
        "program": program,
        "program_name": program.name if isinstance(program, SurveyProgram) else program["name"],
        "region": region,
        "region_name": region.name if isinstance(region, Region) else region["name"],
        "modules": modules,
        "data_source": data_source,
        "connection_profile": connection_profile,
        "source_environment_prefix": source_environment_prefix,
    }


def _require_state(request, *keys):
    state = request.session.get(EVENT_ONBOARDING_SESSION_KEY, {})
    if any(not state.get(key) for key in keys):
        messages.error(request, "Lengkapi tahapan onboarding secara berurutan.")
        return state, False
    return state, True


@staff_member_required(login_url="login")
def event_onboarding_identity(request):
    state = request.session.get(EVENT_ONBOARDING_SESSION_KEY, {})
    if request.method == "POST":
        form = EventIdentityForm(request.POST)
        if form.is_valid():
            identity = _serialize_identity(form.cleaned_data)
            previous_type = state.get("identity", {}).get("event_type")
            state["identity"] = identity
            if previous_type != identity["event_type"]:
                state.pop("modules", None)
            request.session[EVENT_ONBOARDING_SESSION_KEY] = state
            return redirect("aggregate:event_onboarding_references")
    else:
        form = EventIdentityForm(initial=state.get("identity", {}))
    return render(
        request,
        "aggregate/event_onboarding.html",
        {
            "step": "identity",
            "step_number": 1,
            "form": form,
            "catalog_source": state.get("catalog_source"),
        },
    )


@staff_member_required(login_url="login")
def event_onboarding_references(request):
    state, ready = _require_state(request, "identity")
    if not ready:
        return redirect("aggregate:event_onboarding_identity")
    if request.method == "POST":
        form = EventReferencesForm(request.POST)
        if form.is_valid():
            state["references"] = _serialize_references(form.cleaned_data)
            request.session[EVENT_ONBOARDING_SESSION_KEY] = state
            return redirect("aggregate:event_onboarding_modules")
    else:
        form = EventReferencesForm(initial=_references_initial(state))
    return render(
        request,
        "aggregate/event_onboarding.html",
        {"step": "references", "step_number": 2, "form": form},
    )


@staff_member_required(login_url="login")
def event_onboarding_modules(request):
    state, ready = _require_state(request, "identity", "references")
    if not ready:
        return redirect("aggregate:event_onboarding_identity")
    event_type = get_object_or_404(EventType, pk=state["identity"]["event_type"], active=True)
    if request.method == "POST":
        form = EventModulesForm(request.POST)
        if form.is_valid():
            state["modules"] = list(form.cleaned_data["modules"].values_list("pk", flat=True))
            request.session[EVENT_ONBOARDING_SESSION_KEY] = state
            return redirect("aggregate:event_onboarding_source")
    else:
        initial_ids = state.get("modules")
        if initial_ids is None:
            initial_ids = list(
                EventModuleDefinition.objects.filter(
                    active=True,
                    code__in=DEFAULT_MODULES_BY_EVENT_TYPE.get(event_type.code, ()),
                ).values_list("pk", flat=True)
            )
        form = EventModulesForm(initial={"modules": initial_ids})
    return render(
        request,
        "aggregate/event_onboarding.html",
        {"step": "modules", "step_number": 3, "form": form, "event_type": event_type},
    )


@staff_member_required(login_url="login")
def event_onboarding_source(request):
    state, ready = _require_state(request, "identity", "references", "modules")
    if not ready:
        return redirect("aggregate:event_onboarding_identity")
    locked_source = state.get("catalog_source")
    source_initial = state.get("data_source", {})
    if request.method == "POST":
        form = EventDataSourceForm(
            request.POST,
            initial=source_initial,
            locked_source=locked_source,
        )
        if form.is_valid():
            state["data_source"] = _serialize_data_source(form.cleaned_data)
            request.session[EVENT_ONBOARDING_SESSION_KEY] = state
            return redirect("aggregate:event_onboarding_review")
    else:
        form = EventDataSourceForm(
            initial=source_initial,
            locked_source=locked_source,
        )
    return render(
        request,
        "aggregate/event_onboarding.html",
        {
            "step": "source",
            "step_number": 4,
            "form": form,
            "catalog_source": locked_source,
        },
    )


def _create_reference(reference, model):
    if reference["mode"] == "existing":
        return model.objects.get(pk=reference["id"], active=True)
    values = {"code": reference["code"], "name": reference["name"], "active": True}
    if model is Region:
        values.update(level=reference["level"], parent_id=reference.get("parent_id"))
    return model.objects.create(**values)


@staff_member_required(login_url="login")
def event_onboarding_review(request):
    state = request.session.get(EVENT_ONBOARDING_SESSION_KEY, {})
    try:
        context = _review_context(state)
    except Http404:
        messages.error(request, "Data onboarding belum lengkap, bertabrakan, atau sudah berubah.")
        return redirect("aggregate:event_onboarding_identity")

    if request.method == "POST":
        identity = context["identity"]
        if SurveyAccess.objects.filter(code=identity["code"]).exists():
            messages.error(request, "Kode event sudah digunakan. Periksa kembali identitas event.")
            return redirect("aggregate:event_onboarding_identity")
        source_candidate = context["data_source"]
        if state.get("catalog_source") and SurveyDataSource.objects.filter(
            connection_profile_id=source_candidate["connection_profile"],
            database_name__iexact=source_candidate["database_name"],
            table_name__iexact=source_candidate["table_name"],
        ).exists():
            messages.error(
                request,
                "Sumber catalog sudah ditautkan oleh event lain. Pindai ulang catalog.",
            )
            return redirect("aggregate:source_catalog")
        try:
            with transaction.atomic():
                program = _create_reference(context["references"]["program"], SurveyProgram)
                region = _create_reference(context["references"]["region"], Region)
                survey = SurveyAccess.objects.create(
                    code=identity["code"],
                    name=identity["name"],
                    event_type=context["event_type"],
                    program=program,
                    region=region,
                    period_start=identity["period_start"] or None,
                    period_end=identity["period_end"] or None,
                    status=SurveyAccess.Status.DRAFT,
                    validation_state=SurveyAccess.ValidationState.NOT_RUN,
                    active=False,
                )
                SurveyEventModule.objects.bulk_create(
                    [
                        SurveyEventModule(
                            survey=survey,
                            module=module,
                            enabled=True,
                            readiness=SurveyEventModule.Readiness.PENDING,
                        )
                        for module in context["modules"]
                    ]
                )
                source = context["data_source"]
                profile = context["connection_profile"]
                SurveyDataSource.objects.create(
                    survey=survey,
                    connection_profile=profile,
                    engine=profile.engine,
                    connection_alias=profile.code,
                    environment_prefix=context["source_environment_prefix"],
                    database_name=source["database_name"],
                    table_name=source["table_name"],
                    identity_column=source["identity_column"],
                    latest_id_column=source["latest_id_column"],
                    valid_column=source["valid_column"],
                    valid_value=source["valid_value"],
                    target_n=source["target_n"],
                    active=True,
                )
        except (IntegrityError, SurveyProgram.DoesNotExist, Region.DoesNotExist):
            messages.error(request, "Referensi berubah saat disimpan. Tinjau ulang program dan wilayah.")
            return redirect("aggregate:event_onboarding_references")

        request.session.pop(EVENT_ONBOARDING_SESSION_KEY, None)
        messages.success(request, "Draft event dan kontrak data source berhasil dibuat.")
        return redirect("aggregate:event_onboarding_done", survey_code=survey.code)

    context.update({"step": "review", "step_number": 5})
    return render(request, "aggregate/event_onboarding.html", context)


@staff_member_required(login_url="login")
def event_onboarding_done(request, survey_code):
    survey = get_object_or_404(
        SurveyAccess.objects.select_related(
            "event_type", "program", "region", "data_source__connection_profile"
        ),
        code=survey_code,
    )
    return render(
        request,
        "aggregate/event_onboarding.html",
        {"step": "done", "step_number": 6, "survey": survey},
    )


@staff_member_required(login_url="login")
def event_metadata_setup(request, survey_code):
    survey = get_object_or_404(
        SurveyAccess.objects.select_related(
            "event_type", "program", "region", "data_source__connection_profile"
        ),
        code=survey_code,
        active=False,
        status__in=(SurveyAccess.Status.DRAFT, SurveyAccess.Status.VALIDATION),
    )
    active_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
    if len(active_rows) > 1:
        messages.error(request, "Event memiliki lebih dari satu metadata aktif dan harus diperbaiki.")
        return redirect("aggregate:home")
    if active_rows:
        metadata = active_rows[0]
        return render(
            request,
            "aggregate/event_metadata_setup.html",
            {"survey": survey, "metadata": metadata, "report": metadata.onboarding_report},
        )

    report = None
    if request.method == "POST":
        form = EventMetadataForm(request.POST, request.FILES, survey=survey)
        if form.is_valid():
            try:
                candidate = prepare_metadata_candidate(
                    survey=survey,
                    source_mode="database",
                )
                report = candidate["onboarding_report"]
                if report is None:
                    report = inspect_metadata_source(
                        survey=survey,
                        payload=candidate["payload"],
                    )
            except MetadataOnboardingError as exc:
                form.add_error(None, str(exc))
            else:
                if report["errors"]:
                    form.add_error(
                        None,
                        "Pemeriksaan sumber data gagal; metadata belum disimpan.",
                    )
                else:
                    try:
                        with transaction.atomic():
                            locked = SurveyAccess.objects.select_for_update().get(pk=survey.pk)
                            if locked.active or locked.metadata_versions.filter(is_active=True).exists():
                                raise IntegrityError("Event berubah saat metadata disimpan.")
                            SurveyMetadataVersion.objects.create(
                                survey=locked,
                                version=form.cleaned_data["version"],
                                metadata_schema_version=candidate["metadata_schema_version"],
                                questionnaire_key=candidate["questionnaire_key"],
                                source_database=candidate["source_database"],
                                payload=candidate["payload"],
                                sha256=candidate["sha256"],
                                source_name=candidate["source_name"],
                                onboarding_report=report,
                                is_active=True,
                                created_by=request.user,
                            )
                            locked.status = SurveyAccess.Status.VALIDATION
                            locked.validation_state = SurveyAccess.ValidationState.NOT_RUN
                            locked.validated_at = None
                            locked.validation_fingerprint = ""
                            locked.validation_report = {}
                            locked.dashboard_config = candidate["dashboard_config"]
                            locked.save(
                                update_fields=(
                                    "status",
                                    "validation_state",
                                    "validated_at",
                                    "validation_fingerprint",
                                    "validation_report",
                                    "dashboard_config",
                                )
                            )
                    except IntegrityError:
                        form.add_error(None, "Event berubah saat metadata disimpan; muat ulang halaman.")
                    else:
                        messages.success(
                            request,
                            "Metadata tersimpan dan pemeriksaan koneksi read-only lulus.",
                        )
                        return redirect("aggregate:event_metadata_setup", survey_code=survey.code)
    else:
        form = EventMetadataForm(
            survey=survey,
            initial={"version": "metadata_v1"},
        )
    return render(
        request,
        "aggregate/event_metadata_setup.html",
        {"survey": survey, "form": form, "report": report},
    )


@staff_member_required(login_url="login")
def event_psu_frame_setup(request, survey_code):
    survey = get_object_or_404(
        SurveyAccess.objects.select_related("data_source").prefetch_related(
            "metadata_versions", "psu_frames__psus", "event_modules__module"
        ),
        code=survey_code,
    )
    metadata_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
    variable_names = []
    column_source_error = ""
    if len(metadata_rows) == 1:
        try:
            variable_names = list(reporting_column_names(survey))
        except MetadataOnboardingError as exc:
            column_source_error = str(exc)
            variables = metadata_rows[0].payload.get("variables", {})
            if isinstance(variables, dict):
                variable_names = list(variables)
    try:
        current_config = survey.monitoring_config
    except SurveyMonitoringConfig.DoesNotExist:
        current_config = None

    frame_form = EventPSUFrameForm(survey=survey, prefix="frame")
    config_initial = {
        field: getattr(current_config, field)
        for field in (
            "questionnaire_column", "enumerator_column", "submit_time_column",
            "start_hour_column", "start_minute_column", "village_column",
            "district_column", "regency_column", "refresh_seconds",
        )
    } if current_config else {"refresh_seconds": 60}
    config_form = EventMonitoringConfigForm(
        variable_names=variable_names,
        initial=config_initial,
        prefix="monitoring",
    )

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "stage_frame":
            frame_form = EventPSUFrameForm(
                request.POST, request.FILES, survey=survey, prefix="frame"
            )
            if frame_form.is_valid():
                try:
                    frame = stage_psu_frame(
                        survey=survey,
                        version=frame_form.cleaned_data["version"],
                        uploaded_file=frame_form.cleaned_data["frame_file"],
                        user=request.user,
                    )
                except PSUFrameError as exc:
                    frame_form.add_error(None, str(exc))
                else:
                    messages.success(
                        request,
                        f"Frame {frame.version} lolos pemeriksaan dan disimpan sebagai staging.",
                    )
                    return redirect("aggregate:event_psu_frame_setup", survey_code=survey.code)
        elif action == "activate_frame":
            try:
                frame = activate_psu_frame(
                    survey=survey,
                    frame_id=request.POST.get("frame_id"),
                )
            except (PSUFrameError, SurveyPSUFrame.DoesNotExist, ValueError, TypeError) as exc:
                messages.error(request, str(exc) or "Frame PSU tidak ditemukan.")
            else:
                refresh_event_module_readiness(survey)
                messages.success(
                    request,
                    f"Frame {frame.version} diaktifkan. Target event kini {frame.target_total}.",
                )
            return redirect("aggregate:event_psu_frame_setup", survey_code=survey.code)
        elif action == "save_monitoring":
            config_form = EventMonitoringConfigForm(
                request.POST, variable_names=variable_names, prefix="monitoring"
            )
            if config_form.is_valid():
                if not survey.psu_frames.filter(is_active=True).exists():
                    config_form.add_error(
                        None,
                        "Aktifkan satu versi frame PSU sebelum menyimpan pemetaan monitoring.",
                    )
                else:
                    values = {
                        key: value
                        for key, value in config_form.cleaned_data.items()
                        if key != "refresh_seconds"
                    }
                    values["refresh_seconds"] = config_form.cleaned_data["refresh_seconds"]
                    values["updated_by"] = request.user
                    SurveyMonitoringConfig.objects.update_or_create(
                        survey=survey,
                        defaults=values,
                    )
                    refresh_event_module_readiness(survey)
                    messages.success(request, "Pemetaan monitoring berhasil disimpan.")
                    return redirect("aggregate:event_psu_frame_setup", survey_code=survey.code)

    frames = survey.psu_frames.prefetch_related("psus").all()
    active_frame = next((frame for frame in frames if frame.is_active), None)
    preview_rows = list(active_frame.psus.all()[:100]) if active_frame else []
    return render(
        request,
        "aggregate/event_psu_frame_setup.html",
        {
            "survey": survey,
            "frame_form": frame_form,
            "config_form": config_form,
            "frames": frames,
            "active_frame": active_frame,
            "preview_rows": preview_rows,
            "metadata_ready": len(metadata_rows) == 1,
            "column_source_error": column_source_error,
        },
    )


@staff_member_required(login_url="login")
def event_final_validation(request, survey_code):
    survey = get_object_or_404(
        SurveyAccess.objects.select_related(
            "event_type", "program", "region", "data_source__connection_profile"
        ).prefetch_related("event_modules__module", "weight_sets"),
        code=survey_code,
        active=False,
        status=SurveyAccess.Status.VALIDATION,
    )
    metadata_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
    if len(metadata_rows) != 1:
        messages.error(request, "Event harus memiliki tepat satu metadata aktif.")
        return redirect("aggregate:event_metadata_setup", survey_code=survey.code)

    command_output = ""
    if request.method == "POST":
        output = StringIO()
        try:
            call_command(
                "validate_survey_event",
                survey=survey.code,
                apply=True,
                stdout=output,
            )
        except CommandError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Validasi final event lulus dan laporannya tersimpan.")
        command_output = output.getvalue()
        survey.refresh_from_db()
        refresh_event_module_readiness(survey)
        survey.refresh_from_db()

    weighted_assignment = survey.event_modules.filter(
        module__code="weighted_analysis",
        enabled=True,
    ).first()
    activation_ready = not survey.event_modules.filter(enabled=True).exclude(
        readiness=SurveyEventModule.Readiness.READY
    ).exists()
    return render(
        request,
        "aggregate/event_final_validation.html",
        {
            "survey": survey,
            "metadata": metadata_rows[0],
            "report": survey.validation_report,
            "module_rows": event_module_readiness_rows(survey),
            "command_output": command_output,
            "weighted_assignment": weighted_assignment,
            "activation_ready": activation_ready,
        },
    )


@staff_member_required(login_url="login")
def event_weighting_setup(request, survey_code):
    survey = get_object_or_404(
        SurveyAccess.objects.select_related("data_source").prefetch_related(
            "event_modules__module", "weight_sets__parent_weight_set__survey"
        ),
        code=survey_code,
        active=False,
        status=SurveyAccess.Status.VALIDATION,
        validation_state=SurveyAccess.ValidationState.PASSED,
    )
    assignment = get_object_or_404(
        SurveyEventModule.objects.select_related("module"),
        survey=survey,
        module__code="weighted_analysis",
        enabled=True,
    )

    if request.method == "POST":
        form = WeightModuleDecisionForm(request.POST, survey=survey)
        if form.is_valid():
            if form.cleaned_data["action"] == WeightModuleDecisionForm.REUSE:
                try:
                    reuse_weight_set(
                        survey=survey,
                        source_weight_set=form.cleaned_data["source_weight_set"],
                        version=form.cleaned_data["version"],
                        user=request.user,
                    )
                except WeightReuseError as exc:
                    form.add_error(None, str(exc))
                else:
                    messages.success(
                        request,
                        "Weight set berhasil digunakan ulang dan lineage sumber tersimpan.",
                    )
                    return redirect("aggregate:event_weighting_setup", survey_code=survey.code)
            else:
                with transaction.atomic():
                    locked_survey = SurveyAccess.objects.select_for_update().get(pk=survey.pk)
                    locked_assignment = SurveyEventModule.objects.select_for_update().get(
                        pk=assignment.pk
                    )
                    locked_assignment.enabled = False
                    locked_assignment.readiness = SurveyEventModule.Readiness.PENDING
                    locked_assignment.save(update_fields=("enabled", "readiness", "updated_at"))
                    locked_survey.validation_state = SurveyAccess.ValidationState.NOT_RUN
                    locked_survey.validated_at = None
                    locked_survey.validation_fingerprint = ""
                    locked_survey.validation_report = {}
                    locked_survey.save(
                        update_fields=(
                            "validation_state",
                            "validated_at",
                            "validation_fingerprint",
                            "validation_report",
                        )
                    )
                messages.warning(
                    request,
                    "Modul berbobot dinonaktifkan. Jalankan validasi final kembali sebelum aktivasi.",
                )
                return redirect("aggregate:event_final_validation", survey_code=survey.code)
    else:
        form = WeightModuleDecisionForm(
            survey=survey,
            initial={"action": WeightModuleDecisionForm.REUSE, "version": "raking_v1"},
        )

    active_weights = list(survey.weight_sets.filter(is_active=True)[:2])
    return render(
        request,
        "aggregate/event_weighting_setup.html",
        {
            "survey": survey,
            "assignment": assignment,
            "form": form,
            "active_weight": active_weights[0] if len(active_weights) == 1 else None,
            "compatible_count": form.fields["source_weight_set"].queryset.count(),
        },
    )


@staff_member_required(login_url="login")
def event_activation_review(request, survey_code):
    survey = get_object_or_404(
        SurveyAccess.objects.select_related(
            "event_type", "program", "region", "data_source"
        ).prefetch_related(
            "event_modules__module",
            "metadata_versions",
            "memberships__user",
            "weight_sets__parent_weight_set__survey",
        ),
        code=survey_code,
        active=False,
        status=SurveyAccess.Status.VALIDATION,
        validation_state=SurveyAccess.ValidationState.PASSED,
    )
    membership_form = EventMembershipForm(prefix="membership")
    activation_form = EventActivationForm(prefix="activation", survey=survey)

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "save_membership":
            membership_form = EventMembershipForm(request.POST, prefix="membership")
            if membership_form.is_valid():
                capabilities = ROLE_CAPABILITIES[membership_form.cleaned_data["role"]]
                membership, created = SurveyMembership.objects.update_or_create(
                    survey=survey,
                    user=membership_form.cleaned_data["user"],
                    defaults=capabilities,
                )
                messages.success(
                    request,
                    "Akses pengguna berhasil dibuat."
                    if created
                    else "Akses pengguna berhasil diperbarui.",
                )
                return redirect("aggregate:event_activation_review", survey_code=survey.code)
        elif action == "remove_membership":
            membership = get_object_or_404(
                SurveyMembership,
                pk=request.POST.get("membership_id"),
                survey=survey,
            )
            username = membership.user.username
            membership.delete()
            messages.warning(request, f"Akses {username} dihapus dari event.")
            return redirect("aggregate:event_activation_review", survey_code=survey.code)
        elif action == "activate":
            activation_form = EventActivationForm(
                request.POST,
                prefix="activation",
                survey=survey,
            )
            if activation_form.is_valid():
                try:
                    activate_event(survey=survey)
                except EventActivationError as exc:
                    activation_form.add_error(None, str(exc))
                else:
                    messages.success(
                        request,
                        f"Event {survey.code} berhasil diaktifkan dan tersedia sesuai membership.",
                    )
                    return redirect("aggregate:home")
        else:
            raise Http404

    survey.refresh_from_db()
    gate = evaluate_activation_gate(survey)
    memberships = [
        {"row": row, "role": role_for_capabilities(row)}
        for row in survey.memberships.select_related("user").order_by("user__username")
    ]
    metadata = survey.metadata_versions.get(is_active=True)
    active_weight = survey.weight_sets.filter(is_active=True).first()
    return render(
        request,
        "aggregate/event_activation_review.html",
        {
            "survey": survey,
            "metadata": metadata,
            "active_weight": active_weight,
            "module_rows": event_module_readiness_rows(survey),
            "memberships": memberships,
            "membership_form": membership_form,
            "activation_form": activation_form,
            "gate": gate,
        },
    )


@staff_member_required(login_url="login")
def event_onboarding_cancel(request):
    if request.method != "POST":
        raise Http404
    request.session.pop(EVENT_ONBOARDING_SESSION_KEY, None)
    messages.success(request, "Onboarding dibatalkan; tidak ada event yang dibuat.")
    return redirect("aggregate:home")


def healthz(request):
    return render(request, "aggregate/healthz.txt", {"status": "ok"}, content_type="text/plain")
