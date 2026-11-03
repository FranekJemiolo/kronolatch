"""
Unit tests for KronoLatch Anti-Phishing Vendor Verifier.
Validates canonical root domain normalization, whitelist audits, deceptive clone detection, and markup calculations.
"""

from kronolatch.models import VerificationStatus
from kronolatch.verifier import normalize_root_domain, verify_vendor_url


def test_root_domain_normalization():
    """Asserts subdomains, protocols, ports, and subpaths normalize to registrable root domains."""
    assert normalize_root_domain("https://ticketing.colosseo.it/book") == "colosseo.it"
    assert (
        normalize_root_domain("http://www.colosseum-rome-tickets.org/fast-track?ref=ad")
        == "colosseum-rome-tickets.org"
    )
    assert normalize_root_domain("https://ticket.louvre.fr/en/purchase") == "louvre.fr"
    assert normalize_root_domain("http://sub.portal.intercity.pl:8080/rozklad") == "intercity.pl"
    assert normalize_root_domain("https://booking.trainline.co.uk/search") == "trainline.co.uk"
    assert normalize_root_domain("trenitalia.com") == "trenitalia.com"


def test_verified_official_domain():
    """Asserts that official subdomains matching the ground truth pass as VERIFIED_OFFICIAL."""
    result = verify_vendor_url(
        candidate_url="https://ticketing.colosseo.it/purchase",
        venue_name="Colosseum",
        official_domain="colosseo.it",
        candidate_price=18.0,
        official_base_price=18.0,
    )
    assert result.status == VerificationStatus.VERIFIED_OFFICIAL
    assert result.is_blocked is False
    assert result.candidate_root_domain == "colosseo.it"


def test_trusted_aggregator_whitelist():
    """Asserts that reputable platforms on the whitelist pass as TRUSTED_AGGREGATOR."""
    result = verify_vendor_url(
        candidate_url="https://www.trainline.com/book/rome-to-florence",
        venue_name="Italian Rail",
        candidate_price=34.0,
        official_base_price=29.9,
    )
    assert result.status == VerificationStatus.TRUSTED_AGGREGATOR
    assert result.is_blocked is False


def test_high_risk_seo_clone_detection():
    """Asserts that deceptive keyword tokens + domain mismatch flag HIGH_RISK_CLONE."""
    result = verify_vendor_url(
        candidate_url="https://www.colosseum-rome-tickets.org/fast-track",
        venue_name="Parco Archeologico del Colosseo",
        official_domain="ticketing.colosseo.it",
        candidate_price=44.0,
        official_base_price=18.0,
    )
    assert result.status == VerificationStatus.HIGH_RISK_CLONE
    assert result.is_blocked is True
    assert result.markup_percent == 144.4
    assert any("mismatch" in r.lower() for r in result.reasons)
    assert any("deceptive" in r.lower() for r in result.reasons)


def test_excessive_markup_triggers_clone_warning():
    """Asserts that a markup > 15% flags HIGH_RISK_CLONE even without suspicious words."""
    result = verify_vendor_url(
        candidate_url="https://tours-travel-broker.com/booking",
        venue_name="Musée du Louvre",
        official_domain="louvre.fr",
        candidate_price=55.0,
        official_base_price=22.0,  # 150% markup
    )
    assert result.status == VerificationStatus.HIGH_RISK_CLONE
    assert result.is_blocked is True
    assert result.markup_percent == 150.0
