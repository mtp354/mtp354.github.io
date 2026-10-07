from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_conferences import _is_conference_candidate, _location_from_json
from fetch_jobs import _key, _linkedin_url, _split_title, _unwrap_link
from render_opportunity_tables import _merge, render
from fetch_opportunities import _is_open_program_item


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

    def test_discovery_requires_an_event_and_rejects_financial_results(self) -> None:
        self.assertTrue(_is_conference_candidate("Quantum Computing Conference", ""))
        self.assertFalse(_is_conference_candidate("ECTC call for papers", ""))
        self.assertFalse(
            _is_conference_candidate(
                "AmpliTech Group To Report Second Quarter 2026 Results",
                "Upcoming conference",
            )
        )


class OpportunityRenderingTests(unittest.TestCase):
    def test_news_stories_are_not_open_programs(self) -> None:
        self.assertFalse(
            _is_open_program_item(
                {
                    "title": "QUTE Summer School Welcomes A Record 80 Quantum Learners",
                    "summary": "",
                }
            )
        )
        self.assertTrue(
            _is_open_program_item(
                {"title": "Applications are now open for Quantum Summer School", "summary": ""}
            )
        )

    def test_empty_jobs_section_is_hidden(self) -> None:
        self.assertNotIn("Jobs (0 listings)", render({}, []))

    def test_careers_search_placeholders_are_omitted(self) -> None:
        merged = _merge(
            {
                "internships": [
                    {
                        "name": "Quantum Roles",
                        "link": "https://www.nvidia.com/en-us/about-nvidia/careers/",
                        "notes": "Search NVIDIA careers for quantum roles",
                    },
                    {"name": "Real listing", "link": "https://example.com/jobs/123"},
                ]
            },
            [],
        )
        self.assertEqual([entry["name"] for entry in merged["internships"]], ["Real listing"])


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
