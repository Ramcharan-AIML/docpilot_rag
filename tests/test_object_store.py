"""Tests for storage/object_store.py against moto, a fake Amazon S3 that lives in memory.

The client is built with NO endpoint, exactly like on AWS (Phase 7), so passing here proves
the "empty endpoint = real S3" path; the laptop runs the same code against SeaweedFS.
"""

import pytest
from moto import mock_aws

from docpilot import config
from docpilot.storage.object_store import (
    download_prefix,
    ensure_bucket,
    get_s3_client,
    list_keys,
    presigned_get_url,
    upload_folder,
)

# S3 rule (moto enforces it too): 3-63 characters, lowercase letters, digits, dots, hyphens.
BUCKET = "test-bucket"


@pytest.fixture
def s3(monkeypatch):
    monkeypatch.setattr(config, "S3_ENDPOINT_URL", "")  # = real AWS S3 (moto intercepts it)
    monkeypatch.setattr(config, "S3_ACCESS_KEY", "")
    monkeypatch.setattr(config, "AWS_REGION", "eu-central-1")
    # Fake keys, so boto3 never looks for real ones on this machine.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        yield get_s3_client()


def test_ensure_bucket_creates_once_outside_us_east_1(s3):
    # Outside us-east-1, S3 requires the region in the request: forgetting it is a classic bug.
    assert ensure_bucket(s3, "docpilot-raw-docs") is True
    assert ensure_bucket(s3, "docpilot-raw-docs") is False


def test_folder_round_trip_keeps_paths_and_bytes(s3, tmp_path):
    source = tmp_path / "docs"
    (source / "fastapi").mkdir(parents=True)
    (source / "fastapi" / "body.md").write_bytes(b"# Body\n\xe2\x9c\x93 utf-8\n")
    (source / "top.md").write_text("top\n", encoding="utf-8")
    ensure_bucket(s3, BUCKET)

    assert upload_folder(s3, source, BUCKET, "docs/") == 2
    assert list_keys(s3, BUCKET) == ["docs/fastapi/body.md", "docs/top.md"]  # "/" even on Windows

    restored = tmp_path / "restored"
    assert download_prefix(s3, BUCKET, "docs/", restored) == 2
    assert (restored / "fastapi" / "body.md").read_bytes() == b"# Body\n\xe2\x9c\x93 utf-8\n"


def test_list_keys_follows_every_page(s3):
    # page_size=2 with 5 keys forces 3 requests: without the paginator only 2 would be seen.
    ensure_bucket(s3, BUCKET)
    for number in range(5):
        s3.put_object(Bucket=BUCKET, Key=f"k{number}", Body=b"x")
    assert list_keys(s3, BUCKET, page_size=2) == [f"k{number}" for number in range(5)]


def test_presigned_url_points_at_the_object(s3):
    ensure_bucket(s3, "snaps")
    url = presigned_get_url(s3, "snaps", "docpilot_v1_ft200/snap.snapshot", seconds=60)
    assert "docpilot_v1_ft200/snap.snapshot" in url and "Signature" in url
