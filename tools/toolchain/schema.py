# SPDX-License-Identifier: Apache-2.0
"""Lazy JSON Schema validation with Python integers and caller-owned schemas."""

import json
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from toolchain.jsonutil import unique_object

if TYPE_CHECKING:
    from jsonschema.protocols import Validator


def _is_integer(_checker: object, value: object) -> bool:
    return type(value) is int


@cache
def _validator_class() -> type[Validator]:
    # Defer importing jsonschema until validation is requested.
    from jsonschema import Draft202012Validator, validators  # noqa: PLC0415

    checker = Draft202012Validator.TYPE_CHECKER.redefine("integer", _is_integer)
    return validators.extend(Draft202012Validator, type_checker=checker)


def validate(schema_path: Path, value: object) -> None:
    """Validate `value` against the JSON Schema at `schema_path` with offline reference resolution."""
    from jsonschema.exceptions import SchemaError  # noqa: PLC0415
    from referencing import Registry  # noqa: PLC0415
    from referencing.exceptions import Unresolvable  # noqa: PLC0415

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"),
                            object_pairs_hook=unique_object)
        validator = _validator_class()
        validator.check_schema(schema)
        errors = sorted(validator(schema, registry=Registry()).iter_errors(value),
                        key=lambda error: error.json_path)
    except (OSError, ValueError, SchemaError, Unresolvable) as error:
        raise ValueError(f"{schema_path}: cannot read a valid schema: {error}") from error
    if errors:
        raise ValueError(f"{schema_path}: " + "; ".join(
            f"{error.json_path}: {error.message}" for error in errors))
