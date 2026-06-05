from __future__ import annotations

import ast
import re
from functools import lru_cache
from importlib import resources
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from prismadv.ir.utils import ast_literal


def _camel_to_snake(s: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def _snake_to_camel(s: str) -> str:
    parts = s.split("_")
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


class GXParameterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str | None = None
    description: str = ""


class GXExpectationSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    url: str | None = None
    description: str = ""
    args: dict[str, GXParameterSpec] = Field(default_factory=dict)
    other_parameters: dict[str, GXParameterSpec] = Field(default_factory=dict)

    @property
    def type(self) -> str:
        if not self.name.startswith("Expect"):
            raise ValueError("GX expectation signature name must start with `Expect`")
        return "expect_" + _camel_to_snake(self.name[len("Expect") :])

    def allowed_kwargs(self) -> set[str]:
        return set(self.args) | set(self.other_parameters)

    @classmethod
    def from_yaml(cls, raw: dict[str, Any]) -> "GXExpectationSignature":
        def parse_params(v: Any) -> dict[str, GXParameterSpec]:
            if v is None:
                return {}
            if not isinstance(v, list):
                raise TypeError("Expected a list of parameter blocks")
            out: dict[str, GXParameterSpec] = {}
            for block in v:
                if not isinstance(block, dict):
                    continue
                for k, spec in block.items():
                    if not isinstance(k, str):
                        continue
                    if not isinstance(spec, dict):
                        out[k] = GXParameterSpec(type=None, description=str(spec))
                        continue
                    out[k] = GXParameterSpec(
                        type=str(spec.get("type")) if spec.get("type") is not None else None,
                        description=str(spec.get("description") or "").strip(),
                    )
            return out

        return cls(
            name=str(raw.get("Name") or "").strip(),
            url=str(raw.get("URL")).strip() if raw.get("URL") is not None else None,
            description=str(raw.get("Description") or "").strip(),
            args=parse_params(raw.get("Args")),
            other_parameters=parse_params(raw.get("Other Parameters")),
        )


@lru_cache
def load_gx_expectation_signatures() -> dict[str, GXExpectationSignature]:
    """
    Load GX expectation grammars shipped with this package.

    Source: `prismadv/ir/gx_expectations/expectations/*.yaml` (ported from legacy `code/`).
    """
    base = resources.files("prismadv.ir").joinpath("gx_expectations", "expectations")
    out: dict[str, GXExpectationSignature] = {}
    for entry in base.iterdir():
        if not entry.name.endswith(".yaml"):
            continue
        raw = yaml.safe_load(entry.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            continue
        sig = GXExpectationSignature.from_yaml(raw)
        if not sig.name:
            continue
        out[sig.type] = sig
    return out


class GXExpectationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Canonical GX expectation type, e.g. "expect_column_values_to_not_be_null"
    type: str
    kwargs: dict[str, Any] = Field(default_factory=dict)

    def to_class_name(self) -> str:
        if not self.type.startswith("expect_"):
            raise ValueError("GX expectation type must start with 'expect_'")
        return "Expect" + _snake_to_camel(self.type[len("expect_") :])

    def to_string(self) -> str:
        class_name = self.to_class_name()
        args = ", ".join(f"{k}={repr(v)}" for k, v in self.kwargs.items())
        return f"{class_name}({args})"


def _strip_gx_prefix(s: str) -> str:
    t = s.strip()
    for prefix in ("gx.expectations.", "great_expectations.expectations.", "validator."):
        if t.startswith(prefix):
            t = t[len(prefix) :]
            break
    return t.strip()


def parse_gx_expectation(expr: str) -> GXExpectationSpec:
    """
    Parse a GX expectation constructor/method expression into a canonical spec.

    Supported:
      - `ExpectColumnValuesToNotBeNull(column="a")`
      - `expect_column_values_to_not_be_null(column="a")`
      - `validator.expect_column_values_to_not_be_null(column="a")`
    """
    s = _strip_gx_prefix(expr)
    if not s:
        raise ValueError("Empty GX expectation expression")

    tree = ast.parse(s, mode="eval")
    call = tree.body
    if not isinstance(call, ast.Call):
        raise ValueError("Expected an expectation constructor call")

    if isinstance(call.func, ast.Name):
        name = call.func.id
    elif isinstance(call.func, ast.Attribute):
        name = call.func.attr
    else:
        raise ValueError("Unsupported expectation expression")

    if call.args:
        raise ValueError("GX canonical parsing only supports keyword arguments (no positional args)")

    kwargs: dict[str, Any] = {}
    for kw in call.keywords:
        if kw.arg is None:
            raise ValueError("**kwargs are not supported in GX expressions")
        kwargs[kw.arg] = ast_literal(kw.value)

    if name.startswith("Expect"):
        type_str = "expect_" + _camel_to_snake(name[len("Expect") :])
    elif name.startswith("expect_"):
        type_str = name
    else:
        raise ValueError("GX expectation must start with `Expect` or `expect_`")

    sig = load_gx_expectation_signatures().get(type_str)
    if sig is not None:
        allowed = sig.allowed_kwargs()
        unknown = sorted(k for k in kwargs if k not in allowed)
        if unknown:
            raise ValueError(
                f"Unknown GX kwargs for `{sig.name}`: {', '.join(unknown)}. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )

    return GXExpectationSpec(type=type_str, kwargs=kwargs)
