import random

from file_flag.detectors.tfn import TFNDetector, is_valid_tfn

# TFNs that are known to pass the modulus-11 checksum.
KNOWN_VALID = ["123456782", "123 456 782", "459599230"]


def test_known_valid_tfns():
    for tfn in KNOWN_VALID:
        assert is_valid_tfn(tfn.replace(" ", ""))


def test_invalid_checksum_rejected():
    assert not is_valid_tfn("123456789")
    assert not is_valid_tfn("123456781")  # one off from a valid number
    assert not is_valid_tfn("12345")      # wrong length
    assert not is_valid_tfn("12abc6782")  # non-digits


def test_generator_round_trips():
    # The generator must produce numbers the detector accepts.
    from tools.generate_sample_pdfs import make_valid_tfn
    rng = random.Random(1)
    for _ in range(200):
        tfn = make_valid_tfn(rng)
        assert is_valid_tfn(tfn.replace(" ", ""))


def test_detector_flags_valid_only():
    det = TFNDetector()
    text = "Valid: 123 456 782, invalid: 123 456 789."
    findings = det.detect(text, page=1)
    assert len(findings) == 1
    assert findings[0].raw_value == "123 456 782"
    assert findings[0].kind == "tfn"


def test_detector_can_report_invalid_when_configured():
    det = TFNDetector(options={"require_valid": False})
    findings = det.detect("number 123 456 789", page=1)
    assert len(findings) == 1
    assert findings[0].confidence < 1.0


def test_masking_hides_middle():
    det = TFNDetector()
    f = det.detect("123 456 782", page=1)[0]
    masked = f.masked_value()
    assert masked.startswith("12") and masked.endswith("82")
    assert "*" in masked
