"""Utilities for parallel LLM processing."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Sequence, TypeVar

T = TypeVar("T")


def run_in_parallel_with_progress(
    func: Callable[[T], Any],
    items: Sequence[T],
    max_workers: int | None = None,
    done_callback: "Callable[[int, int], None] | None" = None,
    item_result_callback: "Callable[[T, Any], None] | None" = None,
) -> list[Any]:
    """Run a function on multiple items in parallel, calling done_callback after each completes.

    Args:
        func: Function to call for each item
        items: Items to process
        max_workers: Maximum number of worker threads
        done_callback: Optional callback(completed, total) called after each item finishes
        item_result_callback: Optional callback(input_item, result) called with each item's result

    Returns:
        List of results in the same order as input items
    """
    if not items:
        return []

    total = len(items)
    results_map: dict[int, Any] = {}
    completed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, item): i for i, item in enumerate(items)}
        for future in as_completed(futures):
            idx = futures[future]
            result = future.result()
            results_map[idx] = result
            completed_count += 1
            if item_result_callback:
                item_result_callback(items[idx], result)
            if done_callback:
                done_callback(completed_count, total)

    return [results_map[i] for i in range(total)]
