"""Tests for bib_checker.cache."""

from __future__ import annotations

from pathlib import Path

from bib_checker.cache import CheckCache
from bib_checker.models import CheckResult, FieldMismatch


def _result(key: str, status: str = "ok") -> CheckResult:
    return CheckResult(key=key, status=status)


# ---------------------------------------------------------------------------
# Cache miss / hit
# ---------------------------------------------------------------------------


def test_cache_miss_on_empty_cache(tmp_path):
    cache = CheckCache(tmp_path / "cache.json")
    assert cache.get("Spolyar:2007qv", {"year": "2008"}) is None


def test_cache_hit_after_put_and_save(tmp_path):
    path = tmp_path / "cache.json"
    fields = {"year": "2008", "doi": "10.1/x"}

    cache = CheckCache(path)
    cache.put("Spolyar:2007qv", fields, _result("Spolyar:2007qv", "ok"))
    cache.save()

    cache2 = CheckCache(path)
    hit = cache2.get("Spolyar:2007qv", fields)
    assert hit is not None
    assert hit.key == "Spolyar:2007qv"
    assert hit.status == "ok"


def test_cache_hit_preserves_mismatches(tmp_path):
    path = tmp_path / "cache.json"
    fields = {"year": "2009"}
    result = CheckResult(
        key="Spolyar:2007qv",
        status="mismatch",
        mismatches=[FieldMismatch("year", "2009", "2008")],
    )
    cache = CheckCache(path)
    cache.put("Spolyar:2007qv", fields, result)
    cache.save()

    hit = CheckCache(path).get("Spolyar:2007qv", fields)
    assert hit is not None
    assert hit.status == "mismatch"
    assert len(hit.mismatches) == 1
    assert hit.mismatches[0].field_name == "year"


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------


def test_cache_stale_when_fields_change(tmp_path):
    path = tmp_path / "cache.json"
    cache = CheckCache(path)
    cache.put("Spolyar:2007qv", {"year": "2008"}, _result("Spolyar:2007qv"))
    cache.save()

    hit = CheckCache(path).get("Spolyar:2007qv", {"year": "2009"})
    assert hit is None


def test_cache_stale_when_doi_added(tmp_path):
    path = tmp_path / "cache.json"
    cache = CheckCache(path)
    cache.put("Key:2000ab", {"year": "2000"}, _result("Key:2000ab"))
    cache.save()

    hit = CheckCache(path).get("Key:2000ab", {"year": "2000", "doi": "10.1/x"})
    assert hit is None


# ---------------------------------------------------------------------------
# Persistence and error handling
# ---------------------------------------------------------------------------


def test_cache_save_not_dirty_skips_write(tmp_path):
    path = tmp_path / "cache.json"
    CheckCache(path).save()
    assert not path.exists()


def test_cache_corrupt_file_handled_gracefully(tmp_path):
    path = tmp_path / "cache.json"
    path.write_text("not valid json {{ garbage")
    cache = CheckCache(path)  # should not raise
    assert cache.get("any_key", {}) is None


def test_cache_wrong_version_discarded(tmp_path):
    import json

    path = tmp_path / "cache.json"
    path.write_text(
        json.dumps({"version": 0, "entries": {"Key:2000ab": {"entry_hash": "abc", "result": {}}}})
    )
    cache = CheckCache(path)
    assert cache.get("Key:2000ab", {}) is None


def test_cache_multiple_keys(tmp_path):
    path = tmp_path / "cache.json"
    cache = CheckCache(path)
    for i in range(5):
        cache.put(f"Key:200{i}ab", {"year": str(2000 + i)}, _result(f"Key:200{i}ab"))
    cache.save()

    cache2 = CheckCache(path)
    for i in range(5):
        hit = cache2.get(f"Key:200{i}ab", {"year": str(2000 + i)})
        assert hit is not None
        assert hit.key == f"Key:200{i}ab"


# ---------------------------------------------------------------------------
# default_path
# ---------------------------------------------------------------------------


def test_cache_default_path_is_hidden_file():
    p = CheckCache.default_path("/some/dir/main.bib")
    assert p.name == ".main-cache.json"
    assert p.parent == Path("/some/dir")


def test_cache_default_path_uses_bib_stem():
    p = CheckCache.default_path("/tmp/thesis.bib")
    assert p.name == ".thesis-cache.json"
