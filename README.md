# Poetry to Pre-Commit: a pre-commit hook to sync .pre-commit-config.yaml versions from Poetry

[![GitHub Repository](https://img.shields.io/github/stars/ewjoachim/poetry_to_pre_commit?style=flat&logo=github&color=brightgreen)](https://github.com/ewjoachim/poetry_to_pre_commit/)
[![Continuous Integration](https://img.shields.io/github/actions/workflow/status/ewjoachim/poetry_to_pre_commit/ci.yml?logo=github&branch=main)](https://github.com/ewjoachim/poetry_to_pre_commit/actions?workflow=CI)
[![Coverage badge](https://raw.githubusercontent.com/ewjoachim/poetry_to_pre_commit/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/ewjoachim/poetry_to_pre_commit/blob/python-coverage-comment-action-data/htmlcov/index.html)
[![MIT License](https://img.shields.io/github/license/ewjoachim/poetry_to_pre_commit?logo=open-source-initiative&logoColor=white)](https://github.com/ewjoachim/poetry_to_pre_commit/blob/main/LICENSE.md)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v1.4%20adopted-ff69b4.svg)](https://github.com/ewjoachim/poetry_to_pre_commit/blob/main/CODE_OF_CONDUCT.md)

Poetry to Pre-commit is a set of 2 [pre-commit](https://pre-commit.com/) hooks:

- `sync-repos` ensures that the different `rev` keys in your
  `.pre-commit-config.yaml` are in sync with the versions in your
  `pyproject.toml`.
- `sync-hooks-additional-dependencies` lets you define some hooks, and map them
  with a Poetry group. It will ensure that all the dependencies of your Poetry
  group will be added as `additional_dependencies` in the corresponding
  pre-commit hook. This is mainly useful for hooks that need a complete
  environment to run, like static type checkers (`mypy`, `pyright`, etc.).

## Installation & Usage

```yaml
# .pre-commit-config.yaml
repos:
  # ...
  - repo: https://github.com/ewjoachim/poetry-to-pre-commit
    rev: "<current release>"
    hooks:
      # Use this hook to ensure that the versions of the repos are synced
      - id: sync-repos
        # All the arguments are optional
        args: [
            # You may skip some projects if you want, they won't be updated
            "--skip=some_project",
            "--skip=another_project",
            # You can specify that a given hook id (like "pyright-python")
            # should be mapped to a given PyPI package name (like "pyright")
            "--map=pyright-python:main,pyright",
            "--map=ruff-pre-commit:ruff",
          ]

      # Use this hook to sync a specific hook with a Poetry group, adding all
      # the dependencies of the group as additional_dependencies
      - id: sync-hooks-additional-dependencies
        # "mypy" is the id of a pre-commit hook
        # "types" is the name of your poetry group containing typing dependencies
        # "main" is the automated name associated with the "default" poetry dependencies
        args: ["--bind", "mypy:types,main"]
```

## How it works

### `sync-repos`

This hook will look for all the `repo` keys in your `.pre-commit-config.yaml`,
extract the repository name (the part after the last `/`), potentially remove
the `mirrors-` prefix, potentially map to a different name you might have
provided through `--map`, (skipping the names provided by `--skip`) and then
look for the corresponding package in your `poetry.lock`. If it finds it, then
back in the `.pre-commit-config.yaml`, it will update the `rev` key to the
version found in the `poetry.lock`. If the `rev` was previously starting with a
`v`, then the new version will also start with a `v` (that's because `rev` in
`.pre-commit-config.yaml` refer to a git tag name which often but not always
has a leading `v`, whereas the version in `poetry.lock` is a
[PEP-440](https://peps.python.org/pep-0440/) version number, and never has a
leading `v`).

### `sync-hooks-additional-dependencies_cli`

This hook will iterate over all the `--bind {pre-commit-hook}:{poetry_groups}`
arguments you provided, and for each of them, it will look for the
corresponding groups in your `pyproject.toml`. If it finds it, then it will
look for the version of all the dependencies of these groups in your
`poetry.lock`. In `.pre-commit-config.yaml`, it will identify the corresponding
hook, and set the `additional_dependencies` key to the list sorted of all the
dependencies.

## Credit where it's due

This project is heavily inspired by
[sync_with_poetry](https://github.com/floatingpurr/sync_with_poetry). I
[wanted](https://github.com/floatingpurr/sync_with_poetry/issues/34) to add the
`sync-hook-with-group`, and to test a different approach for the implementation
(using poetry as a lib instead of parsing the lock file ourselves, using ruamel
rather than regex for roundtrip yaml). While all the code in the repo is
original, the insipration is strong enough that I kept the original author,
@floatingpurr, in the LICENSE file. Thank you, @floatingpurr!
