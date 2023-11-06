from __future__ import annotations
import argparse
import dataclasses
import io
import json
import pathlib
import sys
from typing import Generator, Optional

import git
from ophyd import Any


MODULE_PATH = pathlib.Path(__file__).parent.resolve().absolute()


@dataclasses.dataclass
class ProgramArgs:
    git_rev: str
    max_commits: int
    item: Optional[str]
    skip_keys: list[str]


HappiDatabaseByName = dict[str, dict[str, Any]]


def is_same(d1: dict[str, str], d2: dict[str, str]) -> bool:
    """
    Are d1/d2 the 'same' as far as happi items are concerned?

    Parameters
    ----------
    d1 : dict[str, str]

    d2 : dict[str, str]


    Returns
    -------
    bool

    """
    if set(d1) != set(d2):
        return False
    return all(d1[k] == d2[k] for k in d1)


def get_changes(
    d1: dict[str, str],
    d2: dict[str, str],
) -> Generator[tuple[str, str], None, None]:
    """
    Get changes between d1 -> d2.

    Parameters
    ----------
    d1 : dict[str, str]

    d2 : dict[str, str]


    Returns
    -------
    Generator[tuple[str, str], None, None]

    """
    for key in set(d2) - set(d1):
        yield key, f"{d2[key]}"

    for key in set(d1) - set(d2):
        yield key, "(deleted key)"

    for key in d2:
        if key in d1 and d1[key] != d2[key]:
            yield key, f"{d1[key]} -> {d2[key]}"


def iter_db_changes(
    git_rev: str, 
    max_commits: int = 50
) -> Generator[tuple[git.Commit, HappiDatabaseByName], None, None]:
    repo = git.Repo(MODULE_PATH)
    for commit in repo.iter_commits(
        git_rev,
        paths=["db.json"],
        max_count=max_commits,
        reverse=True
    ):
        blob = commit.tree / "db.json"
        with io.BytesIO() as fp:
            blob.stream_data(fp)
            raw_db = json.loads(fp.getvalue().decode("utf-8"))

        yield commit, {it["name"]: it for it in raw_db.values()}


def print_item_changes(git_rev: str, item: str, max_commits: int = 50) -> None:
    """
    Print the changes made to the specific happi item.

    Parameters
    ----------
    item : str
        The item name.
    """
    last = {}

    for commit, by_name in iter_db_changes(git_rev, max_commits=max_commits):
        if item not in by_name:
            continue

        changed = list(get_changes(last, by_name[item]))
        if changed:
            print()
            print(f"{commit.committed_datetime}")  #  {commit.author.name}")

            for key, change in changed:
                print(f"  {key}: {change}")

            last = by_name[item]
            sys.stdout.flush()


def find_renames(commit: git.Commit) -> dict[str, str]:
    renames = {}
    raw_diff = commit.repo.git.diff_tree(commit.hexsha, "--patch", "--", "db.json")
    lines = raw_diff.splitlines()
    for line, next_line in zip(lines[::2], lines[1::2]):
        if not line.startswith("-") or not next_line.startswith("+"):
            continue

        if not line.lstrip('- "').startswith('name"'):
            continue

        if not next_line.lstrip('+ "').startswith('name"'):
            continue

        old_name = line.split(": ", 1)[1].strip('":,')
        new_name = next_line.split(": ", 1)[1].strip('":,')
        if old_name != new_name:
            renames[old_name] = new_name

    return renames


def print_all_changes(
    git_rev: str,
    max_commits: int = 50,
    skip_keys: Optional[list[str]] = None,
) -> None:
    """
    Print all item changes made in the given period.
    """
    last_by_name = {}
    skip_keys = skip_keys or []

    for commit, by_name in iter_db_changes(git_rev, max_commits=max_commits):
        printed_header = False
        def print_header():
            nonlocal printed_header
            print()
            print(f"## {commit.committed_datetime}: {commit.message}")
            printed_header = True

        renames = find_renames(commit)
        for old, new in renames.items():
            print_header()
            print(f"* **Rename** ``{old}`` -> ``{new}``")
            last_by_name[new] = last_by_name[old]

        for item in last_by_name:
            if item not in by_name:
                print_header()
                print(f"* **Deleted**: ``{item}``")
                continue

            for key, change in get_changes(last_by_name[item], by_name[item]):
                if not printed_header:
                    print_header()

                if key not in skip_keys:
                    print(f"* ``{item}`` {key}: {change}")

        sys.stdout.flush()

        last_by_name = by_name


def create_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-rev", default="deploy")
    parser.add_argument("--max-commits", default=-1)
    parser.add_argument("--item", default=None)
    parser.add_argument("--skip-key", dest="skip_keys", action="append", default=["last_edit"])
    return parser


def main() -> None:
    parser = create_argparser()
    args = parser.parse_args(namespace=ProgramArgs)

    if args.item:
        print_item_changes(
            git_rev=args.git_rev,
            max_commits=args.max_commits,
            item=args.item,
        )
    else:
        print_all_changes(
            git_rev=args.git_rev,
            max_commits=args.max_commits,
            skip_keys=args.skip_keys,
        )


if __name__ == "__main__":
    main()
