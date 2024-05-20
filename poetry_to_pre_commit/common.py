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
    config = cast("dict[str, Any]", yaml.load(path.read_text()))
    old_config = copy.deepcopy(config)
    yield config
    if config != old_config:
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.dump(config, path)


@dataclasses.dataclass(frozen=True, order=True)
class PoetryPackage:
    name: str
    version: str = "*"
    extras: frozenset[str] = dataclasses.field(default_factory=frozenset)

    def __str__(self) -> str:
        if self.extras:
            extras = ",".join(sorted(self.extras))
            return f"{self.name}[{extras}]=={self.version}"
        else:
            return f"{self.name}=={self.version}"


def get_poetry_packages(cwd: pathlib.Path | None = None) -> Iterable[PoetryPackage]:
    locker = factory.Factory().create_poetry(cwd=cwd).locker
    repository = locker.locked_repository()

    for package in repository.packages:
        yield PoetryPackage(
            name=package.name, version=package.version.text, extras=package.features
        )
