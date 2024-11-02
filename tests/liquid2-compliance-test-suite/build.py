"""Liquid2 compliance test suite build script.

This script and the accompanying JSON schema were inspired by the JSONPath
Compliance Test Suite.

https://github.com/jsonpath-standard/jsonpath-compliance-test-suite
"""

import itertools
import json
import os
import sys
from pathlib import Path
from typing import Any

from jsonschema import validate

ROOT = Path(__file__).parent / "tests"
SCHEMA_PATH = Path(__file__).parent / "schema.json"

with open(SCHEMA_PATH, encoding="utf-8") as fd:
    SCHEMA = json.load(fd)


def build() -> str:
    files = ROOT.rglob("*.json")
    tests = list(itertools.chain.from_iterable(load_tests(f) for f in files))

    cts = {
        "description": "Liquid2 compliance test suite",
        "tests": tests,
    }

    validate(instance=cts, schema=SCHEMA)
    return json.dumps(cts, indent=2)


def load_tests(path: Path) -> list[dict[str, Any]]:
    relative_path = path.relative_to(ROOT)
    parts = relative_path.with_suffix("").parts
    prefix = ", ".join(part.replace("_", " ") for part in parts)

    sys.stderr.write(f"Loading {relative_path} with prefix '{prefix}'{os.linesep}")

    # TODO: check for duplicate test names

    with open(path, encoding="utf8") as fd:
        tests = json.load(fd)

    validate(instance=tests, schema=SCHEMA)
    return [add_prefix(prefix, test) for test in tests["tests"]]


def add_prefix(prefix: str, test: dict[str, Any]) -> dict[str, Any]:
    name = prefix + ", " + test["name"]
    return {**test, "name": name}


if __name__ == "__main__":
    sys.stdout.write(build())
