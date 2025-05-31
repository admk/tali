class CommonMixin:
    def _unquote_str(self, text: str) -> str:
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        if text.startswith("'") and text.endswith("'"):
            return text[1:-1]
        return text

    def _visit_any_of_or_none(self, node, visited_children):
        for c in visited_children:
            if c is not None:
                return c
        return None

    def _visit_any_of(self, node, visited_children):
        v = self._visit_any_of_or_none(node, visited_children)
        if v is None:
            raise ValueError("No valid children found.")
        return v

    def _visit_str(self, node, visited_children):
        return node.text

    def _visit_int(self, node, visited_children):
        return int(node.text)

    def _visit_noop(self, node, visited_children):
        return None

    def _visit_expr_name(self, node, visited_children):
        return node.expr_name
