import re
import sys
from typing import List, Dict, Tuple, Union, Optional
from datetime import datetime, timedelta

from . import constants


class ParseError(ValueError):
    pass


class CLI:
    token_types = {
        '!': 'priority',
        '/': 'project',
        '@': 'tag',
        '^': 'deadline',
        ':': 'status',
        '=': 'sort',
        '-': 'delete'
    }

    @staticmethod
    def parse_id_range(id_str: str, max_id: int) -> List[int]:
        ids = set()
        parts = id_str.split(',')
        for part in parts:
            if '..' in part:
                start, end = part.split('..')
                start = int(start) if start else 1
                end = int(end) if end else max_id
                if end < 0:
                    end += max_id + 1
                ids.update(range(start, end + 1))
            else:
                ids.add(int(part))
        return sorted(ids)

    @classmethod
    def tokenize_command(cls, command):
        pattern = re.compile(r"""
            # Separator
            (->)
            # Modifiers
            |(\.-?\d+(?:\.\.-?\d+)?(?:,-?\d+(?:\.\.-?\d+)?)*)
            # Delete
            |(-\s+-?\d+(?:\.\.-?\d+)?(?:,-?\d+(?:\.\.-?\d+)?)*)
            # Standalone delete
            |(-\s*$)|(-\s+)
            # Selectors
            |(-?\d+(?:\.\.-?\d+)?(?:,-?\d+(?:\.\.-?\d+)?)*)
            # Standalone dot (creation)
            |(\.)(?!\d)
            # Prefix with value
            |([!/@^:=])(?:"([^"]*)"|'([^']*)'|([^\s"']*))
            # Standalone double-quoted
            |"([^"]*)"
            # Standalone single-quoted
            |'([^']*)'
            # Other non-whitespace
            |(\S+)
        """, re.VERBOSE)

        tokens = []
        for match in pattern.finditer(command.strip()):
            (
                separator, modifier,
                delete_with_args, delete_end, delete_mid,
                selector, creation_dot,
                prefix, dq_val, sq_val, plain_val, dq, sq, other
            ) = match.groups()

            if separator:
                tokens.append(('separator', separator))
            elif modifier:
                if modifier.startswith('.-'):
                    tokens.append(('modifier', modifier[2:]))
                else:
                    tokens.append(('modifier', modifier[1:]))
            elif delete_with_args:
                tokens.append(('delete', delete_with_args[2:]))
            elif delete_end or delete_mid:
                tokens.append(('delete', None))
            elif selector:
                tokens.append(('selector', selector))
            elif creation_dot:
                tokens.append(('creation', None))
            elif prefix:
                token_type = cls.token_types[prefix]
                value = dq_val or sq_val or plain_val or ''
                tokens.append((token_type, value))
            elif dq is not None:
                tokens.append(('text', dq))
            elif sq is not None:
                tokens.append(('text', sq))
            elif other:
                tokens.append(('text', other))
        return tokens

    def separate_task_parts(full_command: str) -> Tuple[str, List[str]]:
        """
        Separate a task creation/modification command into main text and special parts.

        Args:
            full_command: The complete command (e.g., "Buy milk /grocery @home ^today")

        Returns:
            Tuple of (main_text, special_parts) where special_parts are all the
            prefixed tokens (/project, @tag, etc.)
        """
        parts = full_command.split()
        main_text_parts = []
        special_parts = []

        for part in parts:
            if any(part.startswith(prefix) for prefix in ('/', '@', '^', ':', '!')):
                special_parts.append(part)
            else:
                main_text_parts.append(part)

        return ' '.join(main_text_parts), special_parts
