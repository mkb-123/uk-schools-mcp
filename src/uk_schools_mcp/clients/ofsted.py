"""Client for Ofsted inspection data.

Provides URL generation for Ofsted reports and rating code formatting.
Full inspection data (grades, dates, judgement areas) requires downloading
the Ofsted Management Information files from GOV.UK -- see NEXT_STEPS.md.

Data source: https://www.gov.uk/government/statistical-data-sets/monthly-management-information-ofsteds-school-inspections-outcomes
"""

# Ofsted publishes management information as downloadable files
# The state-funded schools dataset is the most comprehensive
OFSTED_MI_URL = (
    "https://www.gov.uk/government/statistical-data-sets/"
    "monthly-management-information-ofsteds-school-inspections-outcomes"
)


class OfstedClient:
    """Ofsted report URL generation and rating formatting.

    Note: The GIAS bulk CSV includes OfstedLastInsp date. For full
    inspection grades and history, the Ofsted MI files need to be
    downloaded and parsed (see NEXT_STEPS.md for implementation plan).
    """

    @staticmethod
    def ofsted_report_url(urn: int) -> str:
        """Generate the Ofsted report URL for a school."""
        return f"https://reports.ofsted.gov.uk/provider/17/{urn}"

    @staticmethod
    def format_rating(rating_code: str | None) -> str:
        """Convert Ofsted rating code to human-readable string."""
        ratings = {
            "1": "Outstanding",
            "2": "Good",
            "3": "Requires Improvement",
            "4": "Inadequate",
            "8": "Does not apply",
            "9": "No judgement",
        }
        if rating_code is None:
            return "Not yet inspected"
        return ratings.get(str(rating_code).strip(), f"Unknown ({rating_code})")
