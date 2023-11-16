import io
import json
import sys
from typing import Any, Generator

import git


def is_same(d1: dict[str, Any], d2: dict[str, Any]) -> bool:
    """
    Are d1/d2 the 'same' as far as deployed IOCs are concerned?

    Parameters
    ----------
    d1 : dict[str, Any]
    d2 : dict[str, Any]

    Returns
    -------
    bool
    """
    if set(d1) != set(d2):
        return False
    return all(str(d1[k]) == str(d2[k]) for k in d1)


def get_changes(
    d1: dict[str, Any], d2: dict[str, Any]
) -> Generator[tuple[str, str, Any], None, None]:
    """
    Get changes between d1 -> d2.

    Parameters
    ----------
    d1 : dict[str, Any]

    d2 : dict[str, Any]


    Yields
    ------
    str
        added/deleted/changed
    str
        The key name
    Any
        The new/updated value
    """
    for key in set(d2) - set(d1):
        yield "added", key, d2[key]

    for key in set(d1) - set(d2):
        yield "deleted", key, None

    for key in d2:
        if key in d1 and d1[key] != d2[key]:
            yield "changed", key, d2[key]


def get_database_from_commit(commit_hash: str) -> dict[str, Any]:
    """
    Given a commit hash, get the (deserialized) happi database.

    Parameters
    ----------
    commit_hash : str
        The commit hash.

    Returns
    -------
    dict[str, Any]
        The loaded happi database.
    """
    blob = git.Repo(".").commit(commit_hash).tree / "db.json"
    with io.BytesIO() as fp:
        blob.stream_data(fp)
        return json.loads(fp.getvalue().decode("utf-8"))


def print_changes(hash1: str, hash2: str) -> None:
    """
    Print the changes made to the database between the two hashes.
    """
    db1, db2 = [get_database_from_commit(sha) for sha in (hash1, hash2)]

    device_changes = sorted(get_changes(db1, db2))
    print("## Summary")
    print(f"Device changes {len(device_changes)} of total devices {len(db2)}")

    for action, device, _ in device_changes:
        print()
        print(f"## {device}: {action}")
        if action == "deleted":
            continue
        dev1 = db1.get(device, {})
        dev2 = db2.get(device, {})
        for action, key, value in sorted(get_changes(dev1, dev2)):
            if key == "last_edit":
                continue
            if action == "deleted":
                print(f"* ``{key!r}`` deleted")
            elif action == "added":
                print(f"* ``{key}``: ``{value!r}``")
            else:
                old_value = dev1.get(key, "(no value)")
                new_value = dev2.get(key, "(no value)")
                print(f"* {key}: ``{old_value!r}`` -> ``{new_value!r}``")


if __name__ == "__main__":
    hash1, hash2 = sys.argv[1:3]
    print_changes(hash1, hash2)
