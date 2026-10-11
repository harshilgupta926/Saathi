"""Source-backed scheme catalogue.

Records are informational, not a government eligibility decision. Re-check the
official portal and current state/season notices before applying.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SchemeRecord:
    scheme_id: str
    name: str
    summary: str
    eligibility_notes: tuple[str, ...]
    required_documents: tuple[str, ...]
    application_url: str
    source_url: str
    source_checked_on: str
    review_note: str


SCHEME_CATALOG: tuple[SchemeRecord, ...] = (
    SchemeRecord(
        scheme_id="pm-kisan",
        name="PM-KISAN Samman Nidhi",
        summary=(
            "Central-sector income support scheme. The official portal describes "
            "support of ₹6,000 per year in three instalments for eligible "
            "landholding farmer families, subject to scheme exclusions."
        ),
        eligibility_notes=(
            "Landholding farmer-family eligibility is determined by the relevant "
            "State/UT using official land records and scheme guidelines.",
            "Institutional landholders and specified higher-economic-status "
            "categories are excluded; check the official exclusions and current "
            "beneficiary status before relying on eligibility.",
            "eKYC is mandatory for registered beneficiaries according to the portal.",
        ),
        required_documents=(
            "Landholding/land-record details as required by the State/UT",
            "Aadhaar or an officially accepted alternative where applicable",
            "Bank account details required by the official registration process",
        ),
        application_url="https://pmkisan.gov.in/RegistrationFormupdated.aspx",
        source_url="https://www.pmkisan.gov.in/",
        source_checked_on="2026-10-11",
        review_note=(
            "Indicative checklist only. Required fields and eligibility are subject "
            "to the live government portal and State/UT verification."
        ),
    ),
    SchemeRecord(
        scheme_id="pmfby",
        name="Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        summary=(
            "Government crop-insurance programme. Availability, notified crops, "
            "insurance units, deadlines and application routes can vary by state "
            "and season; check the current official notification."
        ),
        eligibility_notes=(
            "Do not infer eligibility from farmer status alone. Verify the current "
            "state, season, notified crop/area and applicable insurable-interest "
            "requirements on the official portal or state notification.",
            "The official portal notes that some states use their own enrollment "
            "portal, so the national portal may not accept every application.",
        ),
        required_documents=(
            "Identity and farmer details requested by the current official portal",
            "Land/tenancy or other insurable-interest evidence as required by the "
            "current state notification",
            "Bank account details and crop/season details requested by the portal",
        ),
        application_url="https://pmfby.gov.in/farmerApplicationForm",
        source_url="https://pmfby.gov.in/home",
        source_checked_on="2026-10-11",
        review_note=(
            "Season- and state-dependent. Confirm the live notification and deadline; "
            "this catalogue does not determine or guarantee eligibility."
        ),
    ),
)


def list_schemes() -> tuple[SchemeRecord, ...]:
    """Return the reviewed catalogue in stable order."""
    return SCHEME_CATALOG


def get_scheme(scheme_id: str) -> SchemeRecord | None:
    """Find a scheme by its stable identifier."""
    normalized = scheme_id.strip().casefold()
    return next((item for item in SCHEME_CATALOG if item.scheme_id == normalized), None)
