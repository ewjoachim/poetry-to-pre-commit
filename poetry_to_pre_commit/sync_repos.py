from __future__ import annotations

import argparse
import dataclasses
import pathlib
import sys
from typing import Any, Iterable

from . import common

PRE_COMMIT_CONFIG_FILE = pathlib.Path(".pre-commit-config.yaml")


@dataclasses.dataclass
class PreCommitRepo:
    repo: str
    pre_commit_rev: str


def get_sync_repos_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="PyPI names to skip. Flag can be repeated multiple times.",
    )
    parser.add_argument(
        "--map",
        action="append",
        default=[],
        type=lambda x: tuple(x.split("=")),
        help="Map repo name to PyPI name in case of mismatch "
        "(e.g. 'pyright-python=pyright'). Note: if the repo name "
        "is a mirror, the prefix 'mirrors-' is assumed, you don't need to explicit it. "
        "Flag can be repeated multiple times.",
    )
    return parser


def get_pre_commit_repos(
    config: dict[str, Any],
) -> Iterable[PreCommitRepo]:
    repos = config.get("repos", [])
    for repo in repos:
        try:
            repo = PreCommitRepo(
                repo=repo["repo"],
                pre_commit_rev=repo["rev"],
            )
        except KeyError:
            continue

        yield repo


def repo_url_to_pypi_name(repo_url: str) -> str:
    name = repo_url.rstrip("/").rsplit("/", 1)[-1]
    prefix = "mirrors-"
    if name.startswith(prefix):
        return name[len(prefix) :]
    return name


def extract_pypi_names(
    repos: Iterable[PreCommitRepo], map: dict[str, str], skip: list[str]
) -> Iterable[tuple[str, PreCommitRepo]]:
    for repo in repos:
        pypi_name = repo_url_to_pypi_name(repo.repo)
        pypi_name = map.get(pypi_name, pypi_name)
        if pypi_name in skip:
            continue

        yield pypi_name, repo


def sync_repos_in_precommit_config(
    repo_packages: Iterable[tuple[PreCommitRepo, common.PoetryPackage]],
    config: dict[str, Any],
) -> None:
    version_by_repo = {repo.repo: package.version for repo, package in repo_packages}
    for repo in config.get("repos", []):
        try:
            new_version = version_by_repo[repo["repo"]]
        except KeyError:
            continue

        rev = repo.get("rev", "")
        if rev.startswith("v"):
            new_version = f"v{new_version}"

        repo["rev"] = new_version


def sync_repos(
    argv: list[str],
    pre_commit_path: pathlib.Path = PRE_COMMIT_CONFIG_FILE,
    poetry_cwd: pathlib.Path | None = None,
) -> None:
    parser = get_sync_repos_parser()
    args = parser.parse_args(argv)

    with common.pre_commit_config_roundtrip(pre_commit_path) as config:
        precommit_repos = get_pre_commit_repos(config=config)
        precommit_repos_with_names = dict(
            extract_pypi_names(
                repos=precommit_repos,
                map=dict(args.map),
                skip=args.skip,
            )
        )
        package_names_from_repos = set(precommit_repos_with_names)
        poetry_packages = (
            package
            for package in common.get_poetry_packages(cwd=poetry_cwd)
            if package.name in package_names_from_repos
        )

        sync_repos_in_precommit_config(
            repo_packages=[
                (precommit_repos_with_names[package.name], package)
                for package in poetry_packages
            ],
            config=config,
        )


def sync_repos_cli() -> None:
    sync_repos(argv=sys.argv[1:])
