from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_conferences import _location_from_json
from fetch_jobs import _key, _linkedin_url, _split_title, _unwrap_link


class ConferenceParsingTests(unittest.TestCase):
    def test_schema_location(self) -> None:
        location = {
            "address": {
                "addressLocality": "Toronto",
                "addressRegion": "ON",
                "addressCountry": "Canada",
            }
        }
        self.assertEqual(_location_from_json(location), "Toronto, ON, Canada")


class LinkedInJobParsingTests(unittest.TestCase):
    def test_accepts_only_linkedin_job_urls(self) -> None:
        self.assertTrue(_linkedin_url("https://www.linkedin.com/jobs/view/quantum-scientist-123456"))
        self.assertFalse(_linkedin_url("https://example.com/jobs/view/123456"))

    def test_job_id_is_stable_across_slug_changes(self) -> None:
        first = _key("https://www.linkedin.com/jobs/view/quantum-scientist-123456", "A")
        second = _key("https://linkedin.com/jobs/view/new-title-123456?trk=x", "B")
        self.assertEqual(first, second)

    def test_alert_redirect_is_unwrapped(self) -> None:
        wrapped = "https://www.google.com/url?url=https%3A%2F%2Fwww.linkedin.com%2Fjobs%2Fview%2F123456"
        self.assertEqual(_unwrap_link(wrapped), "https://www.linkedin.com/jobs/view/123456")

    def test_index_title_split(self) -> None:
        self.assertEqual(
            _split_title("Quantum Research Scientist - Example Labs | LinkedIn"),
            ("Quantum Research Scientist", "Example Labs"),
        )


if __name__ == "__main__":
    unittest.main()
