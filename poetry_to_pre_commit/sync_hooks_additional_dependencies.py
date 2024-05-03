from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Iterable

from packaging.requirements import Requirement
from poetry import factory
from poetry.core.packages.dependency_group import MAIN_GROUP

from . import common

PRE_COMMIT_CONFIG_FILE = pathlib.Path(".pre-commit-config.yaml")


def format_bind(value: str) -> tuple[str, set[str]]:
    try:
        key, value = value.split("=", 1)
    except ValueError:
        raise ValueError(
            f"Invalid bind value: {value}. Expected format: pre_commit_hook_id=poetry_group[,poetry_group,...]."
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
        help="Bind pre-commit hook ids to poetry group names (e.g. mypy=types). "
        "To add the main package dependencies, use the poetry group name "
        f"`{MAIN_GROUP}`. You can bind multiple poetry groups to a single hook "
        "id by either using multiple flags, or by providing a comma-separated "
        "list of poetry group names (e.g. "
        f"`--bind mypy={MAIN_GROUP} --bind mypy:types` or "
        f"`--bind mypy={MAIN_GROUP},types`).",
    )
    parser.add_argument(
        "--no-new-deps",
        action="store_true",
        help="Update or remove dependencies, but don't add any new one.",
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


def update_or_remove_additional_deps(
    poetry_deps: set[str], hook_additional_deps: list[str]
) -> set[str]:
    # Additional packages that are already in pre-commit configuration could be listed with
    # any format that is accepted by pip - use `Requirement` to parse them properly.
    current_deps = [Requirement(dep).name for dep in hook_additional_deps]

    return {
        package
        for package in poetry_deps
        # package is yielded by `get_poetry_deps` above, and we are pretty sure that this won't raise `IndexError`
        if package.split("==")[0].split("[")[0] in current_deps
    }


def _sync_hooks_additional_dependencies(
    *,
    config: dict[str, Any],
    deps_by_group: dict[str, list[str]],
    bind: dict[str, set[str]],
    no_new_deps: bool = False,
) -> None:
    """Sync additional dependencies from `deps_by_group` to `config`.

    Args:
        config: pre-commit config
        deps_by_group: packages from poetry.lock, by poetry dependency group
        bind: poetry dependency groups to consider for each pre-commit hook
        no_new_deps: Update or remove existing dependencies from the "additional_dependencies"
            section of pre-commit config, but do not add new dependencies from poetry.
    """
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

            hook["additional_dependencies"] = sorted(
                update_or_remove_additional_deps(
                    poetry_deps=deps,
                    hook_additional_deps=hook["additional_dependencies"],
                )
                if no_new_deps
                else deps
            )


def sync_hooks_additional_dependencies(
    argv: list[str],
    pre_commit_path: pathlib.Path = PRE_COMMIT_CONFIG_FILE,
    poetry_cwd: pathlib.Path | None = None,
) -> None:
    """Sync additional dependencies with the packages versions from poetry lock file."""
    parser = get_sync_hooks_additional_dependencies_parser()
    args = parser.parse_args(argv)

    bind = combine_bind_values(args.bind)
    deps_by_group = {}

    for groups in bind.values():
        for group in groups:
            deps_by_group[group] = set(get_poetry_deps(cwd=poetry_cwd, group=group))

    with common.pre_commit_config_roundtrip(pre_commit_path) as config:
        _sync_hooks_additional_dependencies(
            config=config,
            bind=bind,
            deps_by_group=deps_by_group,
            no_new_deps=args.no_new_deps,
        )


def sync_hooks_additional_dependencies_cli() -> None:
    """Entrypoint when running from the shell."""
    sync_hooks_additional_dependencies(argv=sys.argv[1:])
