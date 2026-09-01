from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from funding_common import extract_money, funding_event_from_item, grant_disposition
from fetch_opportunities import _grants_gov_date
from fetch_stock_prices import _awarded_grant_lines


class GrantDispositionTests(unittest.TestCase):
    def test_open_call_is_actionable(self) -> None:
        self.assertEqual(
            grant_disposition("Call for proposals: quantum technologies. Applications are open."),
            "actionable",
        )

    def test_award_announcement_is_not_an_opportunity(self) -> None:
        self.assertEqual(
            grant_disposition("Harvard awarded $37M NSF grant for fault-tolerant quantum computing"),
            "awarded",
        )

    def test_generic_grant_story_is_unknown(self) -> None:
        self.assertEqual(grant_disposition("The future of quantum technology grants"), "unknown")

    def test_application_language_wins_if_both_are_present(self) -> None:
        text = "After last year's awards, applications open for the 2027 quantum grant"
        self.assertEqual(grant_disposition(text), "actionable")

    def test_grants_gov_deadline_normalization(self) -> None:
        self.assertEqual(_grants_gov_date("10/15/2026"), "2026-10-15")


class MoneyExtractionTests(unittest.TestCase):
    def test_extracts_and_labels_currencies(self) -> None:
        self.assertEqual(
            extract_money("US$1.5 million and €2M"),
            [
                {"currency": "USD", "amount": 1_500_000, "display": "US$1.5 million"},
                {"currency": "EUR", "amount": 2_000_000, "display": "€2M"},
            ],
        )

    def test_event_prefers_headline_amount(self) -> None:
        item = {
            "id": "x",
            "title": "Lab receives $4M quantum grant",
            "summary": "The $4M award belongs to a broader $40M program.",
        }
        self.assertEqual(funding_event_from_item(item)["amounts"][0]["amount"], 4_000_000)

    def test_extracts_comma_grouped_amount(self) -> None:
        self.assertEqual(extract_money("Awarded $750,000")[0]["amount"], 750_000)

    def test_industry_totals_stay_separate_by_currency(self) -> None:
        events = [
            {"amounts": [{"currency": "USD", "amount": 3_000_000}]},
            {"amounts": [{"currency": "EUR", "amount": 2_000_000}]},
        ]
        report = "\n".join(_awarded_grant_lines(events))
        self.assertIn("€2.0M", report)
        self.assertIn("$3.0M", report)


if __name__ == "__main__":
    unittest.main()
