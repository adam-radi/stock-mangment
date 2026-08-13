import pytest

from app import app, get_db
from scan_helpers import normalize_scan_code


def test_normalize_scan_code_accepts_digits():
    assert normalize_scan_code(" 123456 ") == "123456"


def test_normalize_scan_code_rejects_letters():
    with pytest.raises(ValueError):
        normalize_scan_code("ABC123")


def test_normalize_scan_code_rejects_empty_value():
    with pytest.raises(ValueError):
        normalize_scan_code("   ")


def test_db_enables_foreign_keys():
    with app.app_context():
        db = get_db()
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
