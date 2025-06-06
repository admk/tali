from typing import List


def _min_indent(lines):
    return min(
        len(line) - len(line.lstrip())
        for line in lines if line.strip())


def _process_block(block: List[str]) -> List[str]:
    if not block:
        return []
    prefix_line, suffix_lines = block[0], block[1:]
    if not suffix_lines:
        return [prefix_line.rstrip()]
    suffix_lines = process_prefix_sharing_lines(suffix_lines)
    prefix = prefix_line.rstrip()
    return [f"{prefix} {suffix}" for suffix in suffix_lines]


def process_prefix_sharing_lines(lines: List[str]) -> List[str]:
    if not lines:
        return []
    indent = _min_indent(lines)
    lines = [line[indent:] for line in lines if line.strip()]
    block_indices = [
        i for i, line in enumerate(lines) if not line.startswith(" ")]
    processed = []
    for start, end in zip([0] + block_indices, block_indices + [len(lines)]):
        block = lines[start:end]
        processed += _process_block(block)
    return processed
