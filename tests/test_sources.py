"""The corpus register must be complete: no source without a licence or a visibility flag."""

from datetime import date

import pytest

from docpilot.ingestion.sources import DOMAINS, SOURCES


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_every_source_is_fully_described(name):
    info = SOURCES[name]
    assert info.licence.strip() and info.licence_url.strip(), "licence and its link are required"
    assert info.visibility in ("public", "local_only")
    assert info.domain in DOMAINS
    assert info.version.strip() and info.url.strip() and info.topic.strip()
    date.fromisoformat(info.checked)  # raises if the check date is not YYYY-MM-DD


def test_every_domain_has_at_least_one_source():
    assert {info.domain for info in SOURCES.values()} == set(DOMAINS)
