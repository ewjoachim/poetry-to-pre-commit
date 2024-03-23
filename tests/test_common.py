from __future__ import annotations

from poetry_to_pre_commit import common


def test_get_poetry_packages(poetry_cwd):
    result = list(
        common.get_poetry_packages(
            cwd=poetry_cwd,
        )
    )

    assert common.PoetryPackage(name="attrs", version="23.2.0") in result


def test_pre_commit_config_roundtrip__no_change(tmp_path):
    file = tmp_path / "file.yaml"
    yaml = "a: 1\nb: 2\n"
    file.write_text(yaml)
    with common.pre_commit_config_roundtrip(path=file) as content:
        assert content == {"a": 1, "b": 2}
    assert file.read_text() == yaml


def test_pre_commit_config_roundtrip__write_back(tmp_path):
    file = tmp_path / "file.yaml"
    yaml = "a: 1\nb: 2\n"
    file.write_text(yaml)
    with common.pre_commit_config_roundtrip(path=file) as content:
        content["a"] = 3
        content["c"] = 5
    assert file.read_text() == "a: 3\nb: 2\nc: 5\n"
