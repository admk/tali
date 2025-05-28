from re import T
from box import Box
from rich.table import Table
from rich.box import ROUNDED


class CheatSheet:
    token = {
        "separator": (
            "Separates selection from action",
            "1{id}3 {separator} {status}pending"),
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
            "{description} A detailed description."),
        "stdin": ("Reads from stdin and replace", "{stdin}"),
    }

    def __init__(self, config: Box):
        super().__init__()
        self.config = config

    def render(self) -> Table:
        table = Table(
            title="[bold]:man_mage: Tusk Cheat Sheet :scroll:[/bold]",
            box=ROUNDED)
        table.add_column("Token", style="bold yellow")
        table.add_column("Name", style="bold blue")
        table.add_column("Description")
        table.add_column("Example", style="italic green")
        for key, (desc, example) in self.token.items():
            table.add_row(
                self.config.token[key], key, desc,
                example.format(**self.config.token))
        return table
