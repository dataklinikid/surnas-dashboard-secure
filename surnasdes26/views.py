from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .services.dataset import DatasetUnavailable, get_dataset
from .services.metadata import (
    allowed_variables,
    grouped_variable_choices,
    multiple_answer_choices,
    multiple_answer_groups,
    value_labels,
    variable_choices,
    variable_label,
)
from .services.tabulation import (
    InvalidTabulation,
    crosstab_table,
    frequency_table,
    multiple_answer_table,
)
from .services.registry import SurveyRegistryError, get_survey
from aggregate.services import capabilities_for
from aggregate.weighting import ActiveWeightUnavailable, resolve_weighting


def _error_response(request, message: str, status: int):
    if request.path.endswith(".json"):
        return JsonResponse({"error": message}, status=status)
    return render(request, "surnasdes26/error.html", {"message": message}, status=status)


def _survey_or_404(survey_code: str) -> dict:
    try:
        return get_survey(survey_code)
    except SurveyRegistryError as exc:
        raise Http404("Survei tidak ditemukan.") from exc


@login_required
def monitoring(request, survey_code):
    survey = _survey_or_404(survey_code)
    capabilities = capabilities_for(request.user, survey["code"])
    if not capabilities.can_monitor:
        raise PermissionDenied
    try:
        df = get_dataset(survey_code=survey["code"])
    except DatasetUnavailable as exc:
        return _error_response(request, str(exc), 503)

    n = len(df)
    target = int(survey["dataset"].get("target_n", 0))
    progress = round((n / target) * 100, 1) if target else 0
    province_rows = []
    group_variable = survey.get("dashboard", {}).get("monitoring_group_variable", "")
    if group_variable and group_variable in df.columns:
        province_rows = frequency_table(
            df,
            group_variable,
            value_labels(group_variable, survey["code"]),
        )["rows"]
    return render(
        request,
        "surnasdes26/monitoring.html",
        {
            "survey": survey,
            "capabilities": capabilities,
            "n": n,
            "target": target,
            "progress": progress,
            "province_rows": province_rows,
            "monitoring_group_label": survey.get("dashboard", {}).get("monitoring_group_label", "Distribusi"),
        },
    )


@login_required
def analysis(request, survey_code):
    survey = _survey_or_404(survey_code)
    capabilities = capabilities_for(request.user, survey["code"])
    if not capabilities.can_analyse:
        raise PermissionDenied
    try:
        df = get_dataset(survey_code=survey["code"])
        df, weight_variable, weighting = resolve_weighting(
            df,
            survey["code"],
            request.GET.get("weighting", "unweighted"),
        )
        choices = variable_choices(df.columns, survey["code"])
        selected = request.GET.get("variable", choices[0][0] if choices else "")
        if selected not in dict(choices):
            selected = choices[0][0] if choices else ""
        result = (
            frequency_table(
                df,
                selected,
                value_labels(selected, survey["code"]),
                weight_variable,
            )
            if selected
            else None
        )
    except (DatasetUnavailable, InvalidTabulation, ActiveWeightUnavailable, ValueError) as exc:
        return _error_response(request, str(exc), 503 if isinstance(exc, DatasetUnavailable) else 400)

    return render(
        request,
        "surnasdes26/analysis.html",
        {
            "choices": choices,
            "survey": survey,
            "capabilities": capabilities,
            "choice_groups": grouped_variable_choices(df.columns, survey["code"]),
            "selected": selected,
            "selected_label": variable_label(selected, survey["code"]) if selected else "",
            "result": result,
            "weighting": weighting,
        },
    )


@login_required
def crosstab(request, survey_code):
    survey = _survey_or_404(survey_code)
    capabilities = capabilities_for(request.user, survey["code"])
    if not capabilities.can_analyse:
        raise PermissionDenied
    try:
        df = get_dataset(survey_code=survey["code"])
        df, weight_variable, weighting = resolve_weighting(
            df,
            survey["code"],
            request.GET.get("weighting", "unweighted"),
        )
        choices = variable_choices(df.columns, survey["code"])
        choice_names = dict(choices)
        row_variable = request.GET.get("row", choices[0][0] if choices else "")
        column_variable = request.GET.get("column", choices[1][0] if len(choices) > 1 else row_variable)
        output_type = request.GET.get("output_type", "row_percentage")
        if row_variable not in choice_names or column_variable not in choice_names:
            raise InvalidTabulation("Variabel crosstab tidak terdaftar.")
        result = crosstab_table(
            df,
            row_variable,
            column_variable,
            value_labels(row_variable, survey["code"]),
            value_labels(column_variable, survey["code"]),
            output_type,
            weight_variable,
        )
    except (DatasetUnavailable, InvalidTabulation, ActiveWeightUnavailable, ValueError) as exc:
        return _error_response(request, str(exc), 503 if isinstance(exc, DatasetUnavailable) else 400)

    return render(
        request,
        "surnasdes26/crosstab.html",
        {
            "choices": choices,
            "survey": survey,
            "capabilities": capabilities,
            "choice_groups": grouped_variable_choices(df.columns, survey["code"]),
            "row_variable": row_variable,
            "column_variable": column_variable,
            "output_type": output_type,
            "row_label": variable_label(row_variable, survey["code"]),
            "column_label": variable_label(column_variable, survey["code"]),
            "result": result,
            "weighting": weighting,
        },
    )


@require_GET
@login_required
def frequency_api(request, survey_code):
    survey = _survey_or_404(survey_code)
    capabilities = capabilities_for(request.user, survey["code"])
    if not capabilities.can_analyse:
        raise PermissionDenied
    variable = request.GET.get("variable", "")
    if variable not in allowed_variables(survey["code"]):
        return JsonResponse({"error": "Variabel tidak diizinkan."}, status=400)
    try:
        df = get_dataset(survey_code=survey["code"])
        df, weight_variable, weighting = resolve_weighting(
            df,
            survey["code"],
            request.GET.get("weighting", "unweighted"),
        )
        return JsonResponse(
            {
                "variable": variable,
                "label": variable_label(variable, survey["code"]),
                **frequency_table(
                    df,
                    variable,
                    value_labels(variable, survey["code"]),
                    weight_variable,
                ),
                "weighting": {
                    key: value
                    for key, value in weighting.items()
                    if key != "weight_set"
                },
            }
        )
    except DatasetUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except InvalidTabulation as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except ActiveWeightUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@login_required
def multiple_answer(request, survey_code):
    survey = _survey_or_404(survey_code)
    capabilities = capabilities_for(request.user, survey["code"])
    if not capabilities.can_analyse:
        raise PermissionDenied
    try:
        df = get_dataset(survey_code=survey["code"])
        df, weight_variable, weighting = resolve_weighting(
            df,
            survey["code"],
            request.GET.get("weighting", "unweighted"),
        )
        groups = multiple_answer_groups(survey["code"])
        choices = multiple_answer_choices(survey["code"])
        selected = request.GET.get("group", choices[0][0] if choices else "")
        if selected not in groups:
            selected = choices[0][0] if choices else ""
        result = (
            multiple_answer_table(df, selected, groups[selected], weight_variable)
            if selected
            else None
        )
    except (DatasetUnavailable, InvalidTabulation, ActiveWeightUnavailable, ValueError) as exc:
        return _error_response(
            request,
            str(exc),
            503 if isinstance(exc, DatasetUnavailable) else 400,
        )

    return render(
        request,
        "surnasdes26/multiple_answer.html",
        {
            "survey": survey,
            "capabilities": capabilities,
            "choices": choices,
            "selected": selected,
            "result": result,
            "weighting": weighting,
        },
    )
