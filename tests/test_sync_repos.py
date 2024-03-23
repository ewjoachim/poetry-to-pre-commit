from __future__ import annotations

import pytest
import ruamel.yaml

from poetry_to_pre_commit import common, sync_repos


@pytest.mark.parametrize(
    "input,expected",
    [
        ("https://github.com/foo/bar", "bar"),
        ("https://github.com/foo/bar/", "bar"),
        ("https://github.com/foo/mirrors-bar", "bar"),
    ],
)
def test_repo_url_to_pypi_name(input, expected):
    assert sync_repos.repo_url_to_pypi_name(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        ([], {"filenames": [], "map": [], "skip": []}),
        (["foo"], {"filenames": ["foo"], "map": [], "skip": []}),
        (
            ["--skip", "foo", "bar"],
            {"filenames": ["bar"], "map": [], "skip": ["foo"]},
        ),
        (
            ["--skip", "foo", "--skip", "bar"],
            {"filenames": [], "map": [], "skip": ["foo", "bar"]},
        ),
        (
            ["--map", "foo:bar", "--map", "baz:qux"],
            {"filenames": [], "map": [("foo", "bar"), ("baz", "qux")], "skip": []},
        ),
    ],
)
def test_get_parser(input, expected):
    parser = sync_repos.get_sync_repos_parser()
    args = parser.parse_args(input)
    assert vars(args) == expected


def test_get_pre_commit_repos():
    result = sync_repos.get_pre_commit_repos(
        config={
            "repos": [
                {"repo": "https://github.com/foo/bar", "rev": "v1.2.3"},
                {"malformed": "foo"},
            ]
        },
    )
    assert list(result) == [
        sync_repos.PreCommitRepo(
            repo="https://github.com/foo/bar",
            pre_commit_rev="v1.2.3",
        )
    ]


bar = sync_repos.PreCommitRepo(
    repo="https://github.com/foo/bar",
    pre_commit_rev="v1.2.3",
)


@pytest.mark.parametrize(
    "repos, skip, map, expected",
    [
        ([bar], [], {}, [("bar", bar)]),
        ([bar], ["bar"], {}, []),
        ([bar], [], {"bar": "baz"}, [("baz", bar)]),
        ([bar], ["baz"], {"bar": "baz"}, []),
    ],
)
def test_extract_pypi_names(repos, skip, map, expected):
    result = sync_repos.extract_pypi_names(repos=repos, skip=skip, map=map)
    assert list(result) == expected


def test_write_precommit_config():
    projects = [
        (
            sync_repos.PreCommitRepo(
                repo="https://github.com/foo/bar",
                pre_commit_rev="v1.2.3",
            ),
            common.PoetryPackage(name="bar", version="2.3.4"),
        ),
        (
            sync_repos.PreCommitRepo(
                repo="https://github.com/foo/baz",
                pre_commit_rev="2.4",
            ),
            common.PoetryPackage(name="baz", version="2.5"),
        ),
    ]
    config = {
        "repos": [
            {"repo": "https://github.com/foo/bar", "rev": "v1.2.3"},
            {"repo": "https://github.com/foo/baz", "rev": "2.4"},
            {"repo": "https://github.com/foo/qux", "rev": "2.6"},
        ],
    }
    sync_repos.sync_repos_in_precommit_config(repo_packages=projects, config=config)

    assert config == {
        "repos": [
            {"repo": "https://github.com/foo/bar", "rev": "v2.3.4"},
            {"repo": "https://github.com/foo/baz", "rev": "2.5"},
            {"repo": "https://github.com/foo/qux", "rev": "2.6"},
        ],
    }


def test_sync_repos(tmp_path, poetry_cwd):
    pre_commit_path = tmp_path / ".pre-commit-config.yaml"
    ruamel.yaml.YAML().dump(
        {
            "repos": [
                {"repo": "https://github.com/foo/pyright-python", "rev": "v1.1.300"}
            ]
        },
        pre_commit_path,
    )

    sync_repos.sync_repos(
        argv=["foo", "--map", "pyright-python:pyright"],
        pre_commit_path=pre_commit_path,
        poetry_cwd=poetry_cwd,
    )
    result = ruamel.yaml.YAML().load(pre_commit_path.read_text())

    assert result["repos"][0]["rev"] == "v1.1.355"
