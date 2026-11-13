from __future__ import annotations

import os
import smtplib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from requests.exceptions import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import personal_send_email as email


class AnalyticsTests(unittest.TestCase):
    def test_numeric_property_id(self) -> None:
        self.assertEqual(email._ga4_property_id(" properties/123456 "), "123456")
        for invalid in ("G-979B8LMLWV", "../123", "１２３"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                email._ga4_property_id(invalid)

    def test_days_are_validated(self) -> None:
        for raw in ("0", "91", "many", ""):
            with self.subTest(raw=raw), patch.dict(os.environ, {"GA4_ANALYTICS_DAYS": raw}):
                with self.assertRaises(ValueError):
                    email._analytics_days()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(email._analytics_days(), 7)

    def test_credentials_must_be_an_object(self) -> None:
        session, error = email._ga4_session("[]")
        self.assertIsNone(session)
        self.assertIn("JSON object", error)

    def test_missing_configuration_is_visible(self) -> None:
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(StringIO()) as output:
            section = email._build_analytics_section()
        self.assertIn("Not configured", section)
        self.assertIn("::warning", output.getvalue())

    @patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON": "{}"}, clear=True)
    def test_report_metrics_dates_and_top_pages(self) -> None:
        session = MagicMock()
        totals = {"rows": [{"metricValues": [{"value": value} for value in ("1234", "20", "45", "15", "65")]}]}
        pages = {"rows": [{"dimensionValues": [{"value": "/quantum-radar/"}], "metricValues": [{"value": "12"}]}]}
        with patch.object(email, "_ga4_session", return_value=(session, "")):
            with patch.object(email, "_run_ga4_report", side_effect=[totals, pages]) as report:
                section = email._build_analytics_section()
        self.assertIn("Active users: 1,234", section)
        self.assertIn("Avg. session duration: 1m 05s", section)
        self.assertIn("/quantum-radar/: 12 views", section)
        self.assertEqual(report.call_args_list[0].args[2]["dateRanges"], [{"startDate": "7daysAgo", "endDate": "yesterday"}])
        self.assertEqual(report.call_args_list[1].args[2]["limit"], 5)
        session.close.assert_called_once()

    @patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON": "{}"}, clear=True)
    def test_api_error_is_not_reported_as_zero_traffic(self) -> None:
        session = MagicMock()
        with patch.object(email, "_ga4_session", return_value=(session, "")):
            with patch.object(email, "_run_ga4_report", side_effect=HTTPError("forbidden")):
                with redirect_stdout(StringIO()) as output:
                    section = email._build_analytics_section()
        self.assertIn("Could not fetch", section)
        self.assertNotIn("Active users: 0", section)
        self.assertIn("Viewer", section)
        self.assertIn("::warning", output.getvalue())
        session.close.assert_called_once()

    def test_report_uses_authenticated_api_and_timeout(self) -> None:
        session = MagicMock()
        session.post.return_value.json.return_value = {"rows": []}
        body = {"metrics": [{"name": "activeUsers"}]}
        self.assertEqual(email._run_ga4_report(session, "123", body), {"rows": []})
        session.post.assert_called_once_with(
            "https://analyticsdata.googleapis.com/v1beta/properties/123:runReport",
            json=body,
            timeout=30,
        )
        session.post.return_value.raise_for_status.assert_called_once()

    def test_analytics_only_persists_report_without_smtp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analytics.txt"
            with patch.object(email, "ANALYTICS_REPORT", path), patch.dict(os.environ, {}, clear=True):
                with patch.object(sys, "argv", ["personal_send_email.py", "--analytics-only"]):
                    with redirect_stdout(StringIO()):
                        self.assertEqual(email.main(), 0)
            self.assertIn("Not configured", path.read_text())


class SMTPTests(unittest.TestCase):
    @patch.object(email.time, "sleep")
    @patch.object(email.smtplib, "SMTP")
    def test_retries_login_disconnect_before_sending(self, factory: MagicMock, sleep: MagicMock) -> None:
        first, second = MagicMock(), MagicMock()
        first.login.side_effect = smtplib.SMTPServerDisconnected("disconnected")
        factory.side_effect = [first, second]
        with redirect_stdout(StringIO()):
            result = email._connect_smtp("smtp.example.com", 587, "user", "password")
        self.assertIs(result, second)
        first.close.assert_called_once()
        second.starttls.assert_called_once()
        second.login.assert_called_once_with("user", "password")
        first.send_message.assert_not_called()
        sleep.assert_called_once_with(2)

    @patch.object(email.smtplib, "SMTP_SSL")
    @patch.object(email.smtplib, "SMTP")
    def test_port_465_uses_implicit_tls(self, plain: MagicMock, secure: MagicMock) -> None:
        result = email._connect_smtp("smtp.example.com", 465, "user", "password")
        self.assertIs(result, secure.return_value)
        plain.assert_not_called()
        secure.return_value.starttls.assert_not_called()

    @patch.object(email.time, "sleep")
    @patch.object(email.smtplib, "SMTP")
    def test_authentication_errors_are_not_retried(self, factory: MagicMock, sleep: MagicMock) -> None:
        factory.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"invalid")
        with self.assertRaises(smtplib.SMTPAuthenticationError):
            email._connect_smtp("smtp.example.com", 587, "user", "password")
        self.assertEqual(factory.call_count, 1)
        factory.return_value.close.assert_called_once()
        sleep.assert_not_called()

    @patch.object(email.time, "sleep")
    @patch.object(email.smtplib, "SMTP", side_effect=smtplib.SMTPServerDisconnected("disconnected"))
    def test_connection_retries_are_bounded(self, factory: MagicMock, sleep: MagicMock) -> None:
        with redirect_stdout(StringIO()), self.assertRaises(smtplib.SMTPServerDisconnected):
            email._connect_smtp("smtp.example.com", 587, "user", "password")
        self.assertEqual(factory.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_default_and_invalid_ports(self) -> None:
        with patch.dict(os.environ, {"SMTP_PORT": ""}):
            self.assertEqual(email._smtp_port(), 587)
        for raw in ("bad", "0", "65536"):
            with self.subTest(raw=raw), patch.dict(os.environ, {"SMTP_PORT": raw}):
                with self.assertRaises(SystemExit):
                    email._smtp_port()

    def test_send_failure_is_not_retried_and_uses_saved_analytics(self) -> None:
        env = {name: "value" for name in (
            "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD",
            "PERSONAL_REPORT_TO_EMAIL", "PERSONAL_REPORT_FROM_EMAIL",
        )}
        smtp = MagicMock()
        smtp.__enter__.return_value.send_message.side_effect = smtplib.SMTPServerDisconnected("ambiguous delivery")
        report = MagicMock()
        report.read_text.return_value = "Website Analytics\nActive users: 42"
        with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", ["personal_send_email.py"]):
            with patch.object(email, "ANALYTICS_REPORT", report), patch.object(email, "_load_digest", return_value={}):
                with patch.object(email, "_connect_smtp", return_value=smtp) as connect:
                    with self.assertRaises(smtplib.SMTPServerDisconnected):
                        email.main()
        connect.assert_called_once()
        message = smtp.__enter__.return_value.send_message.call_args.args[0]
        self.assertIn("Active users: 42", message.get_body(preferencelist=("plain",)).get_content())


if __name__ == "__main__":
    unittest.main()
