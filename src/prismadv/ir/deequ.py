from __future__ import annotations

import ast
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

import yaml

from pydantic import BaseModel, ConfigDict, Field

from prismadv.ir.utils import ast_literal


_CMP_OPS: dict[type[ast.cmpop], str] = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Lt: "<",
    ast.LtE: "<=",
}

_BOOL_OPS: dict[type[ast.boolop], str] = {
    ast.And: "and",
    ast.Or: "or",
}


class DeequCallSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)

    def to_string(self) -> str:
        def _v(v: Any) -> str:
            if isinstance(v, DeequLambdaAssertionSpec):
                return v.to_lambda_string()
            if isinstance(v, DeequEnumValueSpec):
                return v.to_string()
            return repr(v)

        parts: list[str] = []
        parts.extend(_v(a) for a in self.args)
        parts.extend(f"{k}={_v(v)}" for k, v in self.kwargs.items())
        return f"{self.method}({', '.join(parts)})"


class DeequSatisfiesAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["==", "!=", "<", "<=", ">", ">="]
    value: float

    def to_expr_string(self, var: str) -> str:
        return f"{var} {self.op} {self.value}"


class DeequLambdaAssertionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clauses: list[DeequSatisfiesAssertion] = Field(min_length=1)
    combiner: Literal["and", "or"] | None = None

    def to_lambda_string(self) -> str:
        var = "x"
        if len(self.clauses) == 1:
            body = self.clauses[0].to_expr_string(var)
        else:
            if self.combiner is None:
                raise ValueError("combiner must be set when clauses has more than one item")
            body = f" {self.combiner} ".join(c.to_expr_string(var) for c in self.clauses)
        return f"lambda {var}: {body}"


class DeequEnumValueSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enum: Literal["ConstrainableDataTypes"]
    value: str

    def to_string(self) -> str:
        return f"{self.enum}.{self.value}"


class DeequSatisfiesSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_condition: str
    constraint_name: str
    assertion: DeequLambdaAssertionSpec | None = None

    def to_string(self) -> str:
        args = [repr(self.column_condition), repr(self.constraint_name)]
        if self.assertion is not None:
            args.append(self.assertion.to_lambda_string())
        return f"satisfies({', '.join(args)})"


DeequConstraintSpec = DeequCallSpec | DeequSatisfiesSpec


class DeequConstraintSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    can_use_satisfies: bool | None = None
    can_be_used_for_multiple_columns: bool | None = None
    examples: list[str] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, *, name: str, raw: dict[str, Any]) -> "DeequConstraintSignature":
        required = list(raw.get("required") or [])
        optional_raw = raw.get("optional")
        optional = list(optional_raw or []) if isinstance(optional_raw, list) else []

        examples: list[str] = []
        if "examples" in raw:
            examples = list(raw.get("examples") or [])
        elif "example" in raw and raw.get("example") is not None:
            examples = [str(raw["example"])]

        can_be_used_for_multiple_columns = raw.get("canBeUsedForMultipleColumns")
        if can_be_used_for_multiple_columns is None and "forMultipleColumns" in raw:
            can_be_used_for_multiple_columns = bool(raw["forMultipleColumns"])

        return cls(
            name=name,
            description=str(raw.get("description") or "").strip(),
            required=required,
            optional=optional,
            can_use_satisfies=raw.get("canUseSatisfies"),
            can_be_used_for_multiple_columns=can_be_used_for_multiple_columns,
            examples=examples,
        )


@lru_cache
def load_deequ_constraint_signatures() -> dict[str, DeequConstraintSignature]:
    """
    Load Deequ constraint grammars shipped with this package.

    Source: `prismadv/ir/deequ_constraints/info.yaml` (ported from legacy `code/`).
    """
    path = resources.files("prismadv.ir").joinpath("deequ_constraints", "info.yaml")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("Deequ grammar YAML must be a mapping of constraint_name -> schema")

    out: dict[str, DeequConstraintSignature] = {}
    for name, schema in raw.items():
        if not isinstance(name, str) or not isinstance(schema, dict):
            continue
        out[name] = DeequConstraintSignature.from_yaml(name=name, raw=schema)
    return out


def _strip_deequ_prefix(s: str) -> str:
    t = s.strip()
    if t.startswith("check."):
        t = t[len("check.") :]
    if t.startswith("."):
        t = t[1:]
    return t.strip()


def _parse_deequ_lambda_assertion(node: ast.AST) -> DeequLambdaAssertionSpec:
    if not isinstance(node, ast.Lambda):
        raise ValueError("Expected a lambda assertion for satisfies(...)")
    if len(node.args.args) != 1:
        raise ValueError("satisfies assertion must be a single-arg lambda")
    arg_name = node.args.args[0].arg or "x"

    def parse_clause(expr: ast.AST) -> DeequSatisfiesAssertion:
        if not isinstance(expr, ast.Compare):
            raise ValueError(
                "assertion lambda must be a comparison or a boolean combination of comparisons, "
                "e.g. `lambda x: x >= 0.95` or `lambda x: x >= 0.1 and x <= 0.9`"
            )
        if len(expr.ops) != 1 or len(expr.comparators) != 1:
            raise ValueError("assertion comparisons must be simple binary comparisons")

        if not (isinstance(expr.left, ast.Name) and expr.left.id == arg_name):
            raise ValueError("assertion comparison must compare the lambda argument directly")

        op = _CMP_OPS.get(type(expr.ops[0]))
        if op is None:
            raise ValueError("Unsupported comparison operator in assertion")

        rhs = ast_literal(expr.comparators[0])
        if not isinstance(rhs, (int, float)):
            raise ValueError("assertion RHS must be a number")

        return DeequSatisfiesAssertion(op=op, value=float(rhs))

    def parse_body(expr: ast.AST) -> tuple[list[DeequSatisfiesAssertion], str | None]:
        if isinstance(expr, ast.BoolOp):
            combiner = _BOOL_OPS.get(type(expr.op))
            if combiner is None:
                raise ValueError("Unsupported boolean operator in assertion")
            clauses: list[DeequSatisfiesAssertion] = []
            for v in expr.values:
                nested_clauses, nested_combiner = parse_body(v)
                if nested_combiner is not None and nested_combiner != combiner:
                    raise ValueError("Mixed boolean operators in assertion are not supported")
                clauses.extend(nested_clauses)
            return clauses, combiner
        return [parse_clause(expr)], None

    clauses, combiner = parse_body(node.body)
    return DeequLambdaAssertionSpec(clauses=clauses, combiner=combiner)


def _parse_constrainable_datatype(node: ast.AST) -> DeequEnumValueSpec:
    if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
        raise ValueError("datatype must be a ConstrainableDataTypes.<Type> enum value")
    if node.value.id != "ConstrainableDataTypes":
        raise ValueError("datatype must be a ConstrainableDataTypes.<Type> enum value")
    return DeequEnumValueSpec(enum="ConstrainableDataTypes", value=node.attr)


def _parse_deequ_value(param_name: str | None, node: ast.AST) -> Any:
    if isinstance(node, ast.Lambda):
        return _parse_deequ_lambda_assertion(node)
    if param_name == "datatype":
        return _parse_constrainable_datatype(node)
    return ast_literal(node)


def _bind_deequ_args(
    call: ast.Call, sig: DeequConstraintSignature
) -> tuple[dict[str, ast.AST], dict[str, ast.AST]]:
    param_order = list(sig.required) + list(sig.optional)
    bound: dict[str, ast.AST] = {}
    extra: dict[str, ast.AST] = {}

    if len(call.args) > len(param_order):
        raise ValueError(
            f"Too many positional args for `{sig.name}`: {len(call.args)} > {len(param_order)}"
        )
    for i, node in enumerate(call.args):
        bound[param_order[i]] = node

    for kw in call.keywords:
        if kw.arg is None:
            raise ValueError("**kwargs are not supported in Deequ expressions")
        if kw.arg in bound:
            raise ValueError(f"Duplicate argument for `{kw.arg}` in `{sig.name}`")
        if kw.arg in param_order:
            bound[kw.arg] = kw.value
        else:
            extra[kw.arg] = kw.value

    missing = [p for p in sig.required if p not in bound]
    if missing:
        raise ValueError(f"Missing required args for `{sig.name}`: {', '.join(missing)}")

    return bound, extra


def parse_deequ_constraint(expr: str) -> DeequConstraintSpec:
    """
    Parse a Deequ constraint expression into a canonical, structured form.

    Supported:
      - `.isComplete("col")` / `isComplete("col")`
      - `satisfies("<sql>", "<name>", lambda x: x >= 0.95)` (restricted lambda form)
    """
    normalized = _strip_deequ_prefix(expr)
    if not normalized:
        raise ValueError("Empty Deequ constraint expression")

    tree = ast.parse(f"check.{normalized}", mode="eval")
    call = tree.body
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
        raise ValueError("Expected a Deequ method call like `isComplete(\"col\")`")
    if not (isinstance(call.func.value, ast.Name) and call.func.value.id == "check"):
        raise ValueError("Only `check.<method>(...)` expressions are supported")

    method = call.func.attr

    sig = load_deequ_constraint_signatures().get(method)
    if sig is not None:
        bound, extra = _bind_deequ_args(call, sig)
        if method == "satisfies":
            condition = _parse_deequ_value("columnCondition", bound["columnCondition"])
            name = _parse_deequ_value("constraintName", bound["constraintName"])
            if not isinstance(condition, str):
                raise ValueError("satisfies(...) columnCondition must be a string")
            if not isinstance(name, str):
                raise ValueError("satisfies(...) constraintName must be a string")

            assertion_val: DeequLambdaAssertionSpec | None = None
            if "assertion" in bound:
                assertion_parsed = _parse_deequ_value("assertion", bound["assertion"])
                if not isinstance(assertion_parsed, DeequLambdaAssertionSpec):
                    raise ValueError("satisfies(...) assertion must be a lambda")
                assertion_val = assertion_parsed

            return DeequSatisfiesSpec(
                column_condition=condition, constraint_name=name, assertion=assertion_val
            )

        args: list[Any] = []
        for p in sig.required:
            args.append(_parse_deequ_value(p, bound[p]))

        if sig.optional:
            present_optional = [p for p in sig.optional if p in bound]
            if present_optional:
                last = max(sig.optional.index(p) for p in present_optional)
                for p in sig.optional[: last + 1]:
                    if p in bound:
                        args.append(_parse_deequ_value(p, bound[p]))
                    else:
                        args.append(None)

        kwargs: dict[str, Any] = {k: _parse_deequ_value(k, v) for k, v in extra.items()}
        return DeequCallSpec(method=method, args=args, kwargs=kwargs)

    args = [_parse_deequ_value(None, a) for a in call.args]
    kwargs: dict[str, Any] = {}
    for kw in call.keywords:
        if kw.arg is None:
            raise ValueError("**kwargs are not supported in Deequ expressions")
        kwargs[kw.arg] = _parse_deequ_value(kw.arg, kw.value)

    return DeequCallSpec(method=method, args=args, kwargs=kwargs)
