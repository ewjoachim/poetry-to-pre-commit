from __future__ import annotations

import pytest
import ruamel.yaml

from poetry_to_pre_commit import sync_hooks_additional_dependencies


@pytest.mark.parametrize(
    "value,expected",
    [
        ("foo=bar", ("foo", {"bar"})),
        ("foo=bar,baz", ("foo", {"bar", "baz"})),
    ],
)
def test_format_bind(value, expected):
    assert sync_hooks_additional_dependencies.format_bind(value=value) == expected


def test_format_bind__error():
    with pytest.raises(ValueError):
        sync_hooks_additional_dependencies.format_bind(value="foo")


def test_combine_bind_values():
    bind = [("foo", {"bar"}), ("foo", {"baz"}), ("qux", {"quux"})]
    assert sync_hooks_additional_dependencies.combine_bind_values(bind=bind) == {
        "foo": {"bar", "baz"},
        "qux": {"quux"},
    }


def test_get_sync_hooks_additional_dependencies_parser():
    parser = sync_hooks_additional_dependencies.get_sync_hooks_additional_dependencies_parser()
    assert parser.parse_args(["--bind", "foo=bar,baz", "--bind", "foo=qux"]).bind == [
        ("foo", {"bar", "baz"}),
        ("foo", {"qux"}),
    ]


def test_get_poetry_deps(poetry_cwd):
    results = list(
        sync_hooks_additional_dependencies.get_poetry_deps(
            cwd=poetry_cwd,
            group="dev",
        )
    )

    assert sorted(results) == [
        "flake8==7.0.0",
        "pylint==3.1.0",
        "pyright==1.1.355",
    ]


def test_get_poetry_deps__error(poetry_cwd):
    with pytest.raises(SystemError):
        list(
            sync_hooks_additional_dependencies.get_poetry_deps(
                cwd=poetry_cwd,
                group="unknown",
            )
        )


def test_sync_hook_additional_deps():
    config = {"repos": [{"hooks": [{"id": "mypy"}, {"id": "foo"}]}]}
    deps_by_group = {
        "types": ["bar==1", "baz[e]==2"],
        "main": ["qux==3"],
    }
    bind = {"mypy": {"types", "main", "unknown"}, "other_unknown": {"abc"}}
    sync_hooks_additional_dependencies.sync_hook_additional_deps(
        config=config,
        deps_by_group=deps_by_group,
        bind=bind,
    )
    assert config == {
        "repos": [
            {
                "hooks": [
                    {
                        "id": "mypy",
                        "additional_dependencies": [
                            "bar==1",
                            "baz[e]==2",
                            "qux==3",
                        ],
                    },
                    {"id": "foo"},
                ]
            }
        ]
    }


def test_sync_hooks_additional_dependencies(tmp_path, poetry_cwd):
    pre_commit_path = tmp_path / ".pre-commit-config.yaml"
    ruamel.yaml.YAML().dump(
        {
            "repos": [
                {
                    "repo": "https://github.com/foo/pyright-python",
                    "rev": "v1.1.300",
                    "hooks": [{"id": "pyright"}],
                }
            ]
        },
        pre_commit_path,
    )

    sync_hooks_additional_dependencies.sync_hooks_additional_dependencies(
        argv=["foo", "--bind", "pyright=types,main"],
        pre_commit_path=pre_commit_path,
        poetry_cwd=poetry_cwd,
    )
    result = ruamel.yaml.YAML().load(pre_commit_path.read_text())
    print(result)
    assert result["repos"][0]["hooks"][0]["additional_dependencies"] == [
        "attrs==23.2.0",
        "psycopg[pool]==3.1.18",
        "types-requests==2.31.0.20240311",
    ]