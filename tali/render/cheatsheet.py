from typing import List, Tuple

from box import Box
from rich import box
from rich.table import Table

from .. import __toolname__ as _NAME


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

    def _creation_commands(self) -> List[Tuple[str, str]]:
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

    def _modification_commands(self) -> List[Tuple[str, str]]:
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

    def _deadline_commands(self) -> List[Tuple[str, str]]:
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

    def _selection_commands(self) -> List[Tuple[str, str]]:
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

    def _batch_commands(self) -> List[Tuple[str, str]]:
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

    def render_examples(self) -> Table:
        title = (
            f"[bold]~ :scroll: {_NAME.capitalize()} Command Reference ~[/bold]"
        )
        table = Table("Commands", "Description", title=title, box=box.ROUNDED)
        sections = [
            ("Task Creation", self._creation_commands()),
            ("Task Modifications", self._modification_commands()),
            ("Deadlines", self._deadline_commands()),
            ("Selection Operations", self._selection_commands()),
            ("Batch Actions", self._batch_commands()),
        ]
        for title, commands in sections:
            table.add_row(f"[italic]# {title}[/italic]")
            for i, (cmd, desc) in enumerate(commands):
                end_section = i == len(commands) - 1
                table.add_row(
                    f"[dim]{_NAME}[/dim] {cmd}", desc, end_section=end_section
                )
        return table

    def render_token_cheat(self) -> Table:
        title = f"[bold]~ :man_mage: {_NAME.capitalize()} Symbol Cheat Sheet ~[/bold]"
        table = Table(title=title, box=box.ROUNDED)
        table.add_column("Token", style="bold yellow")
        table.add_column("Name", style="bold blue")
        table.add_column("Description")
        table.add_column("Example", style="italic green")
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
        for key, (desc, example) in token.items():
            table.add_row(
                self.config.token[key],
                key,
                desc,
                example.format(**self.config.token),
            )
        return table

    def render(self) -> List[Table]:
        return [self.render_examples(), self.render_token_cheat()]
