from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional


@dataclass(frozen=True)
class EditorCommand:
    text: str
    parent_ref: Optional[int] = None
    parent_id: Optional[int] = None


@dataclass
class _EditorLine:
    text: str
    indent: int
    children: List["_EditorLine"]


def _token_chars(tokens: Iterable[str]) -> set[str]:
    return {char for token in tokens if token for char in token}


def escape_command_text(text: str, tokens: Iterable[str]) -> str:
    special_chars = _token_chars(tokens)
    escaped = []
    for char in text:
        if char == "\\" or char in special_chars:
            escaped.append("\\")
        escaped.append(char)
    return "".join(escaped)


def unescape_command_text(text: str, tokens: Iterable[str]) -> str:
    special_chars = _token_chars(tokens) | {"\\"}
    unescaped = []
    escaped = False
    for char in text:
        if escaped:
            if char not in special_chars:
                unescaped.append("\\")
            unescaped.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        unescaped.append(char)
    if escaped:
        unescaped.append("\\")
    return "".join(unescaped)


def _strip_comment(line: str, comment_token: str) -> str:
    if not comment_token:
        return line.rstrip()

    quote = None
    escaped = False
    for i, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            continue
        if line.startswith(comment_token, i):
            return line[:i].rstrip()
    return line.rstrip()


def strip_comments(lines: List[str], comment_token: str = "#") -> List[str]:
    new_lines = []
    for line in lines:
        new_lines.append(_strip_comment(line, comment_token))
    return new_lines


def _min_indent(lines):
    indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
    return min(indents) if indents else 0


def _process_block(block: List[str]) -> List[str]:
    if not block:
        return []
    prefix_line, suffix_lines = block[0], block[1:]
    if not suffix_lines:
        return [prefix_line.rstrip()]
    suffix_lines = process_prefix_sharing_lines(suffix_lines)
    prefix = prefix_line.rstrip()
    return [f"{prefix} {suffix}" for suffix in suffix_lines]


def _leading_indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _is_editor_add_line(line: str, separator_token: str) -> bool:
    return line.lstrip().startswith(f"{separator_token} ")


def _is_nested_add_block(block: List[str], separator_token: str) -> bool:
    return any(
        _is_editor_add_line(line, separator_token)
        for line in block[1:]
        if line.strip()
    )


def _build_editor_tree(block: List[str]) -> List[_EditorLine]:
    roots: List[_EditorLine] = []
    stack: List[_EditorLine] = []

    for line in block:
        if not line.strip():
            continue
        indent = _leading_indent(line)
        node = _EditorLine(line.strip(), indent, [])
        while stack and stack[-1].indent >= indent:
            stack.pop()
        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)
        stack.append(node)
    return roots


def _has_add_descendant(node: _EditorLine, separator_token: str) -> bool:
    for child in node.children:
        if _is_editor_add_line(child.text, separator_token):
            return True
        if _has_add_descendant(child, separator_token):
            return True
    return False


def _command_body(text: str, separator_token: str) -> str:
    if text.startswith(f"{separator_token} "):
        return text[len(separator_token) :].strip()
    return text


def _default_add_has_title(text: str, separator_token: str) -> bool:
    body = _command_body(text, separator_token)
    title_prefixes = ("/", "@", "!", ",", "^", "_", ":", "=", "?")
    return any(
        word and not word.startswith(title_prefixes) for word in body.split()
    )


def _add_command(parts: List[str], separator_token: str) -> str:
    body = " ".join(part for part in parts if part).strip()
    return f"{separator_token} {body}".rstrip()


def _expand_prefix_paths(
    nodes: List[_EditorLine],
    prefix: List[str],
    separator_token: str,
) -> List[List[str]]:
    paths: List[List[str]] = []
    for node in nodes:
        node_prefix = prefix + [_command_body(node.text, separator_token)]
        if node.children:
            paths.extend(
                _expand_prefix_paths(
                    node.children, node_prefix, separator_token
                )
            )
        else:
            paths.append(node_prefix)
    return paths


def _process_nested_child(
    node: _EditorLine,
    commands: List[EditorCommand],
    parent_ref: Optional[int],
    prefix: List[str],
    separator_token: str,
    add_has_title: Callable[[str, str], bool],
) -> None:
    if _is_editor_add_line(node.text, separator_token):
        body = _command_body(node.text, separator_token)
        if _has_add_descendant(node, separator_token):
            if not add_has_title(node.text, separator_token):
                for child in node.children:
                    _process_nested_child(
                        child,
                        commands,
                        parent_ref,
                        prefix + [body],
                        separator_token,
                        add_has_title,
                    )
                return
            command_ref = len(commands)
            commands.append(
                EditorCommand(
                    _add_command(prefix + [body], separator_token),
                    parent_ref=parent_ref,
                )
            )
            for child in node.children:
                _process_nested_child(
                    child,
                    commands,
                    command_ref,
                    [],
                    separator_token,
                    add_has_title,
                )
            return
        if node.children:
            for parts in _expand_prefix_paths(
                node.children, prefix + [body], separator_token
            ):
                commands.append(
                    EditorCommand(
                        _add_command(parts, separator_token),
                        parent_ref=parent_ref,
                    )
                )
            return
        commands.append(
            EditorCommand(
                _add_command(prefix + [body], separator_token),
                parent_ref=parent_ref,
            )
        )
        return

    node_prefix = prefix + [_command_body(node.text, separator_token)]
    if _has_add_descendant(node, separator_token):
        if parent_ref is None:
            command_ref = len(commands)
            commands.append(
                EditorCommand(_add_command(node_prefix, separator_token))
            )
            for child in node.children:
                _process_nested_child(
                    child,
                    commands,
                    command_ref,
                    [],
                    separator_token,
                    add_has_title,
                )
            return
        for child in node.children:
            _process_nested_child(
                child,
                commands,
                parent_ref,
                node_prefix,
                separator_token,
                add_has_title,
            )
        return
    if node.children:
        for parts in _expand_prefix_paths(
            node.children, node_prefix, separator_token
        ):
            commands.append(
                EditorCommand(
                    _add_command(parts, separator_token),
                    parent_ref=parent_ref,
                )
            )
        return
    commands.append(
        EditorCommand(
            _add_command(node_prefix, separator_token),
            parent_ref=parent_ref,
        )
    )


def _process_nested_add_block(
    block: List[str],
    separator_token: str,
    add_has_title: Callable[[str, str], bool],
) -> List[EditorCommand]:
    commands: List[EditorCommand] = []
    for root in _build_editor_tree(block):
        if _is_editor_add_line(
            root.text, separator_token
        ) and not add_has_title(root.text, separator_token):
            root_prefix = [_command_body(root.text, separator_token)]
            for child in root.children:
                _process_nested_child(
                    child,
                    commands,
                    None,
                    root_prefix,
                    separator_token,
                    add_has_title,
                )
            continue
        root_ref = len(commands)
        commands.append(EditorCommand(root.text))
        for child in root.children:
            _process_nested_child(
                child, commands, root_ref, [], separator_token, add_has_title
            )
    return commands


def process_prefix_sharing_lines(lines: List[str]) -> List[str]:
    if not lines:
        return []
    indent = _min_indent(lines)
    lines = [line[indent:] for line in lines if line.strip()]
    block_indices = [
        i for i, line in enumerate(lines) if not line.startswith(" ")
    ]
    processed = []
    for start, end in zip([0] + block_indices, block_indices + [len(lines)]):
        block = lines[start:end]
        processed += _process_block(block)
    return processed


def process_editor_commands(
    lines: List[str],
    separator_token: str = ".",
    add_has_title: Callable[[str, str], bool] = _default_add_has_title,
) -> List[EditorCommand]:
    if not lines:
        return []
    indent = _min_indent(lines)
    lines = [line[indent:] for line in lines if line.strip()]
    block_indices = [
        i for i, line in enumerate(lines) if not line.startswith(" ")
    ]
    processed: List[EditorCommand] = []
    for start, end in zip([0] + block_indices, block_indices + [len(lines)]):
        block = lines[start:end]
        if _is_nested_add_block(block, separator_token):
            processed += _process_nested_add_block(
                block, separator_token, add_has_title
            )
        else:
            processed += [EditorCommand(text) for text in _process_block(block)]
    return processed
