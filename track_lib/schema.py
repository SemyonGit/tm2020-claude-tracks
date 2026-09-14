"""Local JSON-schema checks shared by the composer and converter."""
from functools import lru_cache
import json
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker


@lru_cache(maxsize=2)
def _validator(kind: str) -> Draft7Validator:
    path = Path(__file__).resolve().parents[1] / "tools" / f"{kind}_schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema, format_checker=FormatChecker())


def schema_errors(value: object, kind: str) -> list[str]:
    errors = sorted(_validator(kind).iter_errors(value), key=lambda e: str(list(e.path)))
    return [f"{kind}.{'.'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]
