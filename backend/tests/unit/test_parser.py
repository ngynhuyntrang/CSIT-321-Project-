from app.ingestion.parser import parse_module_name


def test_single_subject_module_name():
    assert parse_module_name("AUTM-CSCI235-WG-OC") == ["CSCI235"]


def test_joint_subject_module_name():
    assert parse_module_name("AUTM-CSCI410-WG-OC, AUTM-CSCI910-WG-OC") == ["CSCI410", "CSCI910"]


def test_no_recognizable_subject_code():
    assert parse_module_name("AUTM-WG-OC") == []
