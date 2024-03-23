from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Iterable

from poetry import factory
from poetry.core.packages.dependency_group import MAIN_GROUP

from . import common

PRE_COMMIT_CONFIG_FILE = pathlib.Path(".pre-commit-config.yaml")


def format_bind(value: str) -> tuple[str, set[str]]:
    try:
        key, value = value.split(":", 1)
    except ValueError:
        raise ValueError(
            f"Invalid bind value: {value}. Expected format: pre_commit_hook_id:poetry_group[,poetry_group,...]."
        )
    return key, set(value.split(","))


def combine_bind_values(bind: list[tuple[str, set[str]]]) -> dict[str, set[str]]:
    result = {}
    for key, value in bind:
        result.setdefault(key, set()).update(value)
    return result


def get_sync_hooks_additional_dependencies_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    parser.add_argument(
        "--bind",
        type=format_bind,
        action="append",
        default=[],
        help="Bind pre-commit hook ids to poetry group names (e.g. mypy:types). "
        "To add the main package dependencies, use the poetry group name "
        f"`{MAIN_GROUP}`. You can bind multiple poetry groups to a single hook "
        "id by either using multiple flags, or by providing a comma-separated "
        "list of poetry group names (e.g. "
        f"`--bind mypy:{MAIN_GROUP} --bind mypy:types` or "
        f"`--bind mypy:{MAIN_GROUP},types`).",
    )
    return parser


def get_poetry_deps(*, cwd: pathlib.Path | None = None, group: str) -> Iterable[str]:
    package_by_name = {p.name: p for p in common.get_poetry_packages(cwd=cwd)}
    main_package = factory.Factory().create_poetry(cwd=cwd).package
    try:
        dep_group = main_package.dependency_group(group)
    except ValueError:
        raise SystemError(f"Group not found in pyproject.toml: {group}.")

    for dep in dep_group.dependencies:
        try:
            package = package_by_name[dep.name]
        except KeyError as e:
            raise SystemError(
                f"Package not found in poetry.lock: {dep.name}. "
                "Is your poetry.lock up-to-date?"
            ) from e
        yield f"{dep.complete_name}=={package.version}"


def sync_hook_additional_deps(
    *,
    config: dict[str, Any],
    deps_by_group: dict[str, list[str]],
    bind: dict[str, set[str]],
) -> None:
    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            hook_id = hook["id"]
            try:
                groups = bind[hook_id]
            except KeyError:
                continue
            deps = set()

            for group in groups:
                deps.update(deps_by_group.get(group, set()))

            hook["additional_dependencies"] = sorted(deps)


def sync_hooks_additional_dependencies(
    argv: list[str],
    pre_commit_path: pathlib.Path = PRE_COMMIT_CONFIG_FILE,
    poetry_cwd: pathlib.Path | None = None,
):
    parser = get_sync_hooks_additional_dependencies_parser()
    args = parser.parse_args(argv)

    bind = combine_bind_values(args.bind)
    deps_by_group = {}

    for groups in bind.values():
        for group in groups:
            deps_by_group[group] = set(get_poetry_deps(cwd=poetry_cwd, group=group))

    with common.pre_commit_config_roundtrip(pre_commit_path) as config:
        sync_hook_additional_deps(config=config, bind=bind, deps_by_group=deps_by_group)


def sync_hooks_additional_dependencies_cli():
    sync_hooks_additional_dependencies(argv=sys.argv[1:])
