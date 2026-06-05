from __future__ import annotations

import ast
from typing import Any


def ast_literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [ast_literal(elt) for elt in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(ast_literal(elt) for elt in node.elts)
    if isinstance(node, ast.Dict):
        return {ast_literal(k): ast_literal(v) for k, v in zip(node.keys, node.values, strict=True)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = ast_literal(node.operand)
        if isinstance(v, (int, float)):
            return -v
    raise ValueError(f"Unsupported literal: {ast.dump(node, include_attributes=False)}")

