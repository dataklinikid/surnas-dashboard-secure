from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from aggregate.models import SurveyAccess, SurveyDataSource, SurveyPSUFrame
from aggregate.psu_frames import (
    PSUFrameCandidate,
    PSUFrameError,
    activate_psu_frame,
    stage_psu_frame,
)


def candidate(version_seed="a"):
    rows = (
        {
            "psu_number": 1,
            "village": "A",
            "district": "D1",
            "regency": "R1",
            "dpr_ri_constituency": "DAPIL 1",
            "province": "P",
            "urban_rural": "KOTA",
            "target_n": 8,
            "questionnaire_start": 1,
            "questionnaire_end": 8,
            "normalized_location_key": "A|D1|R1",
        },
        {
            "psu_number": 2,
            "village": "B",
            "district": "D2",
            "regency": "R2",
            "dpr_ri_constituency": "DAPIL 1",
            "province": "P",
            "urban_rural": "DESA",
            "target_n": 15,
            "questionnaire_start": 9,
            "questionnaire_end": 23,
            "normalized_location_key": "B|D2|R2",
        },
    )
    return PSUFrameCandidate(
        source_name="frame.xlsx",
        file_sha256=version_seed * 64,
        rows=rows,
        report={
            "sheet": "PSU", "header_row": 5, "row_count": 2,
            "target_total": 23, "questionnaire_start": 1,
            "questionnaire_end": 23, "warnings": [], "errors": [],
        },
    )


class PSUFrameLifecycleTests(TestCase):
    def setUp(self):
        self.survey = SurveyAccess.objects.create(code="pilot_frame", name="Pilot", active=False)
        SurveyDataSource.objects.create(
            survey=self.survey,
            connection_alias="pilot_frame",
            environment_prefix="PILOT_FRAME_DB",
            database_name="pilot_frame_report",
            table_name="h0",
            identity_column="Q_AC",
        )

    @patch("aggregate.psu_frames.inspect_psu_frame")
    def test_staging_and_activation_derive_target_from_rows(self, inspect):
        inspect.return_value = candidate()
        frame = stage_psu_frame(
            survey=self.survey, version="frame_v1", uploaded_file=object()
        )
        self.assertFalse(frame.is_active)
        self.assertEqual(frame.row_count, 2)
        self.assertEqual(frame.target_total, 23)
        self.assertEqual(list(frame.psus.values_list("target_n", flat=True)), [8, 15])

        activate_psu_frame(survey=self.survey, frame_id=frame.pk)
        frame.refresh_from_db()
        self.survey.data_source.refresh_from_db()
        self.assertTrue(frame.is_active)
        self.assertEqual(self.survey.data_source.target_n, 23)

    @patch("aggregate.psu_frames.inspect_psu_frame")
    def test_duplicate_version_and_file_are_rejected(self, inspect):
        inspect.return_value = candidate()
        stage_psu_frame(survey=self.survey, version="frame_v1", uploaded_file=object())
        with self.assertRaises(PSUFrameError):
            stage_psu_frame(survey=self.survey, version="frame_v1", uploaded_file=object())
        with self.assertRaises(PSUFrameError):
            stage_psu_frame(survey=self.survey, version="frame_v2", uploaded_file=object())

    def test_staff_can_open_event_frame_configuration(self):
        user = get_user_model().objects.create_user("staff_psu", password="secret", is_staff=True)
        self.client.force_login(user)
        response = self.client.get(
            reverse("aggregate:event_psu_frame_setup", args=(self.survey.code,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tidak mengasumsikan setiap PSU berisi 10 responden")

    def test_non_staff_cannot_open_event_frame_configuration(self):
        user = get_user_model().objects.create_user("member_psu", password="secret")
        self.client.force_login(user)
        response = self.client.get(
            reverse("aggregate:event_psu_frame_setup", args=(self.survey.code,))
        )
        self.assertEqual(response.status_code, 302)
