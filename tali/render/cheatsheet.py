from typing import List, Tuple

from box import Box
from rich import box
from rich.table import Table

from .. import __toolname__ as _NAME
from .common import strip_rich

CommandRows = List[Tuple[str, str]]
CommandSections = List[Tuple[str, CommandRows]]
TokenRows = List[Tuple[str, str, str, str]]


class CheatSheet:
    def __init__(self, config: Box):
        super().__init__()
        self.config = config

    def _id(self, text: int | str, symbol: bool = True) -> str:
        return f"[cyan]{text}[/cyan]"

    def _title(self, text: str, symbol: bool = True) -> str:
        return f"[underline]{text}[/underline]"

    def _status(self, text: str, symbol: bool = True) -> str:
        token = self.config.token.status if symbol else ""
        return f"[yellow]{token}{text}[/yellow]"

    def _project(self, *text: str, symbol: bool = True) -> str:
        token = self.config.token.project if symbol else ""
        return f"[magenta]{token}{token.join(text)}[/magenta]"

    def _tag(self, text: str, symbol: bool = True) -> str:
        token = self.config.token.tag if symbol else ""
        return f"[blue]{token}{text}[/blue]"

    def _priority(self, text: str, symbol: bool = True) -> str:
        token = self.config.token.priority if symbol else ""
        return f"[red]{token}{text}[/red]"

    def _deadline(self, text: str, symbol: bool = True) -> str:
        if symbol:
            token = self.config.token.deadline
            text = repr(text) if " " in text else text
        else:
            token = ""
        return f"[green]{token}{text}[/green]"

    def _description(self, text: str, symbol: bool = True) -> str:
        token = self.config.token.description + " " if symbol else ""
        return f"[italic dim]{token}{text}[/italic dim]"

    def _sort(self, text: str, symbol: bool = True) -> str:
        token = self.config.token.sort if symbol else ""
        return f"{token}{text}"

    def _query(self, text: str, symbol: bool = True) -> str:
        token = self.config.token.query if symbol else ""
        return f"{token}{text}"

    def _separator(self, symbol: bool = True) -> str:
        if symbol:
            return f"[bold]{self.config.token.separator}[/bold]"
        return "[bold]separator[/bold]"

    def _creation_commands(self) -> CommandRows:
        sep = self._separator()
        title = self._title
        project = self._project
        tag = self._tag
        deadline = self._deadline
        status = self._status
        priority = self._priority
        return [
            (
                f"{sep} {title('Buy milk')} {project('home', 'grocery')} "
                f"{deadline('today')}",
                f"Create a task with {project('project', symbol=False)} "
                f"and {deadline('deadline', False)}",
            ),
            (
                f"{sep} {title('Meeting')} {project('work')} "
                f"{deadline('tue 4pm')} {status('n')}",
                f"Create a {status('note', False)}",
            ),
            (
                f"{sep} {title('Fix bug')} {project(_NAME)} {priority('high')} "
                f"{tag('urgent')}",
                f"{priority('High', False)}-priority task with an {tag('urgent')} tag",
            ),
        ]

    def _modification_commands(self) -> CommandRows:
        id = self._id
        title = self._title
        sep = self._separator()
        project = self._project
        status = self._status
        tag = self._tag
        status = self._status
        priority = self._priority
        description = self._description
        return [
            (
                f"{id(1)} {sep} {status('')}",
                f"Toggle task {id(1, False)} {status('status', False)} between "
                f"{status('pending', False)} and {status('done', False)}",
            ),
            (f"{id(1)} {sep} {tag('tag')}", f"Toggle {tag('tag', False)}"),
            (
                f"{id(1)} {sep} {tag('star')}",
                f"Set as starred {self.config.item.tag.format.star}",
            ),
            (
                f"{id(1)} {sep} {tag('fav')}",
                f"Set as favorite {self.config.item.tag.format.like}",
            ),
            (
                f"{id(1)} {sep} {priority('h')}",
                f"Set priority to {priority('high', False)}",
            ),
            (f"{id(1)} {sep} {status('x')}", f"{status('Delete', False)} task"),
            (
                f"{id(1)} {sep} {description('detailed description...')}",
                f"Add {description('description', False)}",
            ),
            (
                f"{id(1)} {sep} {title('New title')} "
                f"{project('awesome')} {status('n')}",
                f"Edit {title('title', False)}, "
                f"{project('project', symbol=False)} "
                f"and convert to {status('note', False)}",
            ),
        ]

    def _deadline_commands(self) -> CommandRows:
        id = self._id
        sep = self._separator()
        deadline = self._deadline
        return [
            (
                f"{id(1)} {sep} {deadline('+3d')}",
                f"Postpone by {deadline('3 days', False)}",
            ),
            (
                f"{id(1)} {sep} {deadline('2mon')}",
                f"Set deadline to the {deadline('Monday after next', False)}",
            ),
            (
                f"{id(1)} {sep} {deadline('M')}",
                f"Set deadline to the {deadline('end of the month', False)}",
            ),
            (
                f"{id(1)} {sep} {deadline('oo')}",
                f"{deadline('Remove', False)} deadline",
            ),
        ]

    def _selection_commands(self) -> CommandRows:
        id = self._id
        project = self._project
        tag = self._tag
        deadline = self._deadline
        priority = self._priority
        sort = self._sort
        query = self._query
        return [
            (
                f"{project('work')} {priority('high')} {deadline('today')}",
                f"[bold]Filter[/bold] high-priority {project('work')} tasks "
                f"due {deadline('today')}",
            ),
            (
                f"{tag('')} {sort(deadline(''))}",
                f"[bold]Group[/bold] tasks by {tag('tag', False)} "
                f"and [bold]sort[/bold] by {deadline('deadline', False)}",
            ),
            (
                f"{id(1)} {query(deadline(''))}",
                f"[bold]Query[/bold] the {deadline('deadline', False)} "
                f"of task {id(1, False)}",
            ),
        ]

    def _batch_commands(self) -> CommandRows:
        id = self._id
        sep = self._separator()
        project = self._project
        tag = self._tag
        status = self._status
        status = self._status
        priority = self._priority
        return [
            (
                f"{id('1..5')} {sep} {status('x')}",
                f"{status('Delete', False)} tasks {id('1-5')}",
            ),
            (
                f"{tag('urgent')} {sep} {priority('high')}",
                f"Set {tag('urgent')} tasks to {priority('high', False)} priority",
            ),
            (
                f"{project('home')} {sep}",
                f"Open an [underline]editor[/underline] for {project('home')} tasks",
            ),
            (f"{sep}", "Edit everything in the [underline]editor[/underline]"),
        ]

    def _command_sections(self) -> CommandSections:
        return [
            ("Task Creation", self._creation_commands()),
            ("Task Modifications", self._modification_commands()),
            ("Deadlines", self._deadline_commands()),
            ("Selection Operations", self._selection_commands()),
            ("Batch Actions", self._batch_commands()),
        ]

    def render_examples(self) -> Table:
        title = (
            f"[bold]~ :scroll: {_NAME.capitalize()} Command Reference ~[/bold]"
        )
        table = Table("Commands", "Description", title=title, box=box.ROUNDED)
        sections = self._command_sections()
        for title, commands in sections:
            table.add_row(f"[italic]# {title}[/italic]")
            for i, (cmd, desc) in enumerate(commands):
                end_section = i == len(commands) - 1
                table.add_row(
                    f"[dim]{_NAME}[/dim] {cmd}", desc, end_section=end_section
                )
        return table

    def _token_rows(self) -> TokenRows:
        token = {
            "separator": (
                "Separates selection from action",
                "1{id}3 {separator} {status}pending",
            ),
            "id": ("Range of item IDs", "1{id}3"),
            "status": ("Status of the item", "{status}pending"),
            "project": ("Project", "{project}work"),
            "tag": ("Tag", "{tag}urgent"),
            "priority": ("Priority", "{priority}high"),
            "deadline": ("Deadline", "{deadline}today"),
            "sort": ("Sort by", "{sort}{priority}"),
            "query": ("Query attributes of the item", "{query}{tag}"),
            "description": (
                "Description of the item",
                "{description} detailed description.",
            ),
            "stdin": ("Reads from stdin and replace", "{stdin}"),
        }
        return [
            (
                self.config.token[key],
                key,
                desc,
                example.format(**self.config.token),
            )
            for key, (desc, example) in token.items()
        ]

    def render_token_cheat(self) -> Table:
        title = f"[bold]~ :man_mage: {_NAME.capitalize()} Symbol Cheat Sheet ~[/bold]"
        table = Table(title=title, box=box.ROUNDED)
        table.add_column("Token", style="bold yellow")
        table.add_column("Name", style="bold blue")
        table.add_column("Description")
        table.add_column("Example", style="italic green")
        for token, name, description, example in self._token_rows():
            table.add_row(token, name, description, example)
        return table

    def render(self) -> List[Table]:
        return [self.render_examples(), self.render_token_cheat()]


class AgentCheatSheet(CheatSheet):
    @staticmethod
    def _plain(text: str) -> str:
        return strip_rich(text)

    @staticmethod
    def _cell(text: str) -> str:
        return text.replace("|", r"\|").replace("\n", " ")

    @classmethod
    def _table(
        cls,
        headers: Tuple[str, ...],
        rows: List[Tuple[str, ...]],
    ) -> List[str]:
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in rows:
            lines.append(
                "| " + " | ".join(cls._cell(cell) for cell in row) + " |"
            )
        return lines

    def _placeholder_lines(self) -> List[str]:
        token = self.config.token
        rows = [
            (
                "`<selection>`",
                "Expression before the separator: IDs, filters, grouping, "
                "sorting, or queries.",
            ),
            (
                "`<action>`",
                "Expression after the separator: title words or edits such as "
                f"`{token.status}done`, `{token.tag}tag`, `{token.priority}h`, "
                f"or `{token.description} details`.",
            ),
            (
                "`<field>`",
                f"Query target after `{token.query}`; use one of the Query "
                "fields below.",
            ),
        ]
        return ["## Placeholders", "", *self._table(("Name", "Meaning"), rows)]

    def _command_form_lines(self) -> List[str]:
        token = self.config.token
        rows = [
            ("`tali -i`", "List current todos with stable IDs before editing."),
            ("`tali -j <command>`", "Return machine-readable JSON."),
            ("`tali <selection>`", "List todos matching a selection."),
            (
                f"`tali {token.separator} <action>`",
                "Add a todo. The action must include a title.",
            ),
            (
                f"`tali <selection> {token.separator} <action>`",
                "Update every todo matched by the selection.",
            ),
            (
                f"`tali <selection> {token.separator}`",
                "Open the selected todos in the configured editor.",
            ),
            (
                f"`tali <selection> {token.query}<field>`",
                "Print selected field values.",
            ),
            ("`tali --undo`", "Undo the last saved mutation."),
            ("`tali --redo`", "Redo the last undone mutation."),
        ]
        return [
            "## Command Forms",
            "",
            *self._table(("Command", "Meaning"), rows),
        ]

    def _token_reference_lines(self) -> List[str]:
        rows = [
            (f"`{token}`", name, description, f"`{example}`")
            for token, name, description, example in self._token_rows()
        ]
        return [
            "## Token Reference",
            "",
            *self._table(("Token", "Name", "Description", "Example"), rows),
        ]

    def _query_field_lines(self) -> List[str]:
        token = self.config.token
        rows = [
            (f"`{token.query}{token.query}`", "`title`"),
            (f"`{token.query}{token.project}`", "`project`"),
            (f"`{token.query}{token.tag}`", "`tags`"),
            (f"`{token.query}{token.status}`", "`status`"),
            (f"`{token.query}{token.priority}`", "`priority`"),
            (f"`{token.query}{token.deadline}`", "`deadline`"),
            (f"`{token.query}{token.description}`", "`description`"),
            (f"`{token.query}{token.parent}`", "`parent`"),
        ]
        return ["## Query Fields", "", *self._table(("Query", "Field"), rows)]

    def _date_expression_lines(self) -> List[str]:
        token = self.config.token
        intro = [
            "## Date Expressions",
            "",
            f"Use date expressions after `{token.deadline}`, e.g. "
            f"`{token.deadline}today`.",
            "Date-only forms resolve to end-of-day.",
            (
                "A selection with two deadline expressions creates a range, "
                f"e.g. `{token.deadline}today {token.deadline}friday`."
            ),
            (
                "For expressions with spaces, make sure quotes reach the "
                f"parser; through a shell, use `'{token.deadline}\"tue 4pm\"'`."
            ),
            "",
        ]
        rows = [
            (
                "Named",
                "Today, tomorrow, or distant endpoint sentinels.",
                "`today`, `tomorrow`, `oo`, `+oo`, `-oo`",
            ),
            (
                "Absolute",
                "Month/day with optional year; omitted past years roll "
                "forward.",
                "`feb 21`, `2026/feb/21`, `february 21 8am`",
            ),
            (
                "Time-only",
                "Today if still future, otherwise tomorrow.",
                "`20:00`, `10am`",
            ),
            (
                "End",
                "End of weekday, month, or unit; numeric prefix selects nth.",
                "`mon`, `2tue`, `M`, `month`, `3month`",
            ),
            (
                "Relative",
                "Signed offset from now; combine y, M, w, d, h, and m units.",
                "`+3d`, `-1w`, `+M1d`",
            ),
        ]
        return [
            *intro,
            *self._table(("Form", "Convention", "Examples"), rows),
        ]

    def _example_lines(self) -> List[str]:
        lines = ["## Examples"]
        for title, rows in self._command_sections():
            lines.extend(["", f"### {title}"])
            for command, description in rows:
                plain_command = self._plain(command)
                plain_description = self._plain(description)
                lines.append(
                    f"- `{_NAME} {plain_command}`: {plain_description}"
                )
        return lines

    def render_text(self) -> str:
        lines = [
            "# Tali Agent Cheatsheet",
            "",
            "## Agent Workflow",
            "",
            "- Run `tali -i` first to get current IDs before mutating todos.",
            "- Prefer ID selections for targeted edits.",
            "- Use `tali -j <command>` when downstream code needs JSON.",
            (
                "- Mutations are saved immediately; use `tali --undo` for "
                "one-step rollback."
            ),
            (
                "- Multi-word parser values must keep quotes after shell "
                "parsing; wrap the token, e.g. `'^\"tue 4pm\"'`."
            ),
        ]
        sections = [
            self._placeholder_lines(),
            self._command_form_lines(),
            self._token_reference_lines(),
            self._query_field_lines(),
            self._date_expression_lines(),
            self._example_lines(),
        ]
        for section in sections:
            lines.extend(["", *section])
        return "\n".join(lines)

    def render(self) -> List[str]:
        return [self.render_text()]
