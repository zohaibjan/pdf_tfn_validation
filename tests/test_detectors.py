from pdf_pii_scanner.detectors import build_detectors
from pdf_pii_scanner.detectors.pii import PIIDetector, _luhn_ok
from pdf_pii_scanner.detectors.gri import is_valid_abn, is_valid_medicare


def test_build_detectors_respects_enabled():
    cfg = {"tfn": {"enabled": True}, "pii": {"enabled": False}}
    dets = build_detectors(cfg)
    assert [d.name for d in dets] == ["tfn"]


def test_build_detectors_unknown_raises():
    try:
        build_detectors({"nope": {"enabled": True}})
    except ValueError as e:
        assert "Unknown detector" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_pii_email_and_phone():
    det = PIIDetector(options={"types": ["email", "phone_au"]})
    text = "Contact a@b.com.au or call 0412 345 678 today."
    kinds = {f.kind for f in det.detect(text)}
    assert kinds == {"email", "phone_au"}


def test_credit_card_requires_luhn():
    assert _luhn_ok("4111111111111111")      # valid Visa test number
    assert not _luhn_ok("4111111111111112")
    det = PIIDetector(options={"types": ["credit_card"]})
    assert len(det.detect("card 4111 1111 1111 1111")) == 1
    assert len(det.detect("card 4111 1111 1111 1112")) == 0


def test_abn_checksum():
    assert is_valid_abn("51824753556")        # ATO published test ABN
    assert not is_valid_abn("51824753557")


def test_medicare_checksum():
    # Construct: first 8 digits + computed check digit.
    base = "29512948"
    weights = (1, 3, 7, 9, 1, 3, 7, 9)
    check = sum(int(d) * w for d, w in zip(base, weights)) % 10
    assert is_valid_medicare(f"{base}{check}0")
