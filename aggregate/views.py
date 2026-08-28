from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from aggregate.services import visible_surveys_for


@login_required
def home(request):
    surveys = visible_surveys_for(request.user)
    return render(request, "aggregate/home.html", {"surveys": surveys})


def healthz(request):
    return render(request, "aggregate/healthz.txt", {"status": "ok"}, content_type="text/plain")
