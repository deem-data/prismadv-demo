"""Utility for prepending line numbers to code before sending to an LLM."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from prismadv.ir import SourceSpan


def _add_line_numbers(code: str) -> str:
    """Prepend line numbers to each line of code.

    This helps LLMs accurately reference specific line numbers
    in their output, rather than guessing/hallucinating them.

    Example::

        >>> _add_line_numbers("import os\\nprint('hi')")
        '  1 | import os\\n  2 | print(\\'hi\\')'
    """
    lines = code.splitlines()
    width = len(str(len(lines)))
    return "\n".join(
        f"{i:{width}d} | {line}" for i, line in enumerate(lines, 1)
    )


def _add_highlighted_line_numbers(
    code: str,
    source_spans: Sequence[SourceSpan],
) -> str:
    """Prepend line numbers with data-flow highlighting markers.

    Lines that fall within any of the given source spans are prefixed
    with ``-**->`` to signal relevance; other lines get plain padding.

    Format::

        -**-> 0010: relevant_code
              0011: context_code

    Falls back to :func:`_add_line_numbers` when *source_spans* is empty.
    """
    if not source_spans:
        return _add_line_numbers(code)

    lines = code.splitlines()
    highlights: set[int] = set()
    for span in source_spans:
        highlights.update(range(span.start_line, span.end_line + 1))

    return "\n".join(
        f"-**-> {i:04d}: {line}" if i in highlights else f"      {i:04d}: {line}"
        for i, line in enumerate(lines, 1)
    )
