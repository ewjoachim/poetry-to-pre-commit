from __future__ import annotations

import contextlib
import copy
import dataclasses
import pathlib
from typing import Any, Generator, Iterable, cast

import ruamel.yaml
from poetry import factory


@contextlib.contextmanager
def pre_commit_config_roundtrip(
    path: pathlib.Path,
) -> Generator[dict[str, Any], None, None]:
    yaml = ruamel.yaml.YAML()
    config = cast(dict[str, Any], yaml.load(path.read_text()))
    old_config = copy.deepcopy(config)
    yield config
    if config != old_config:
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.dump(config, path)


@dataclasses.dataclass
class PoetryPackage:
    name: str
    version: str


def get_poetry_packages(cwd: pathlib.Path | None = None) -> Iterable[PoetryPackage]:
    locker = factory.Factory().create_poetry(cwd=cwd).locker
    repository = locker.locked_repository()

    for package in repository.packages:
        yield PoetryPackage(
            name=package.name,
            version=package.version.text,
        )
