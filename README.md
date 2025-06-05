# tali 🧙‍♂️

> **The CLI magic 🔮 for task alchemists** --
> Weave productivity spells with symbols
> that conjure order 📓 from chaos 🌀.

[![GitHub](https://img.shields.io/badge/Repo-GitHub-blue)](https://github.com/admk/tali)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/tali-cli)](https://pypi.org/project/tali-cli/)
[![Python Version](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
<!-- [![Action Status](https://github.com/admk/tali/actions/workflows/ci.yml/badge.svg)](https://github.com/astral-sh/uv/actions) -->

`tali` is a magical command-line task manager.
It manipulates tasks with intuitive symbols
for fast yet powerful filtering, grouping, sorting and batch operations.

## ✨ Features

- 🚀 **Fast Symbolic Syntax** --
  Intuitive symbols for fast task filtering and editing:
  `@tag`, `/project`, `^1week`.
- 🔎 **Powerful Filtering, Grouping and Sorting** --
  Filter, group and sort items with ease: `tali /work ! ^today @ =^`.
- 📒 **Batch Operations** --
  Modify multiple filtered tasks at once:
  `tali /grocery @fruit . ,d`
  marks tasks with tag `@fruit` in `/grocery` project as done.
- 😄 **Emoji Support** --
  Use Emoji markups for visual flair: 💥 = `:boom:`.
- ⏪ **Undo/Redo** --
  Never fear accidental changes
  with `-u`/`--undo` and `-r`/`--redo`.
- ⚙️ **Highly Customizable** --
  Configure symbols, aliases, rendering format/style, editor, pager,
  database location, and more
  in `~/.config/tali/config.toml`.
- 📁 **Folder-specific Task Management** --
  Organize tasks in specific directories
  by creating a `.tali` folder in any directory.
- 📇 **JSON Storage/Export** --
  Machine-readable output with `-j`/`--json`.
- 📜 **Cheatsheet Built-in** --
  Always available with `-c`/`--cheatsheet`.
- 1️⃣ **Idempotent Operations** --
  Use interactive editor or scripts to modify tasks.

## 📦 Installation

- Using [pip](https://pypi.org/project/pip/)
  ```bash
  pip install tali-cli
  ```

- Using [uv](https://github.com/astral-sh/uv)
  ```bash
  uv tool install tali-cli
  ```

- From source
  ```bash
  git clone https://github.com/admk/tali && cd tali && pip install .
  ```

- Requires `Python 3.10+`.

## 📖 Usage Examples

### 🪄 Basic Usage

```bash
tali . "Buy milk" /grocery ^today  # Create a task with project and deadline
tali . "Meeting notes" /work ^"tue 4pm" ,n  # Create a note
tali . "Fix bug" /tali !high @urgent  # Create high-priority task with tag
tali 42 . ,  # Toggle completion for task 42
tali 42 . ,x  # Delete task
tali ^today . @star  # Toggle star tag for all tasks due today
```

### 🔎 Filtering & Querying

```bash
tali /work !high ^today  # Show high-priority work tasks due today
tali @ =^  # Group tasks by tag sorted by deadline
tali 42 ?^  # Query deadline of task 42
```

### ✏️ Task Modifications

```bash
tali 42 . ,done  # Mark task 42 as done ☑️
tali 42 . ,  # Toggle task status
tali 42 . @star  # Toggle star tag ⭐
tali 42 . @fav  # Toggle favorite tag ❤️
tali 42 . !h  # Set high priority ‼️
tali 42 . ,x  # Delete task 🗑️
tali 42 . : "Details..."  # Add description
tali 42 . "New title" /newproject ,n  # Edit multiple properties
```

### ⏰ Deadline Management

```bash
tali 42 . ^+3d  # Postpone deadline by 3 days
tali 42 . ^2mon  # Set to Monday after next
tali 42 . ^M  # Set to end of month
tali 42 . ^oo  # Remove deadline
```

### 📒 Batch Operations

```bash
tali 1..5 . ,x  # Delete tasks 1-5
tali @urgent . !high  # Set all @urgent tasks to high priority
tali /home .  # Edit all tasks in /home project in text editor
```

### 🧪 Advanced Options

```bash
tali (-d|--debug) <...>  # Debug mode
tali (-j|--json) <...>  # Output in JSON format
tali (-H|--history)  # Show commit history
tali (-u|--undo)  # Undo last operation
tali (-r|--redo)  # Redo last undone operation
tali (-R|--re-index)  # Re-index database
```

## ⚙️ Configuration

Global configuration is stored in `~/.config/tali/config.yaml`
(or `$XDG_CONFIG_HOME/tali/config.yaml`).
It also uses `.tali/config.yaml` in your project directory
for project-specific setting overrides if it exists.
Edit with:
```bash
tali --edit-rc
```
See [config.yaml](tali/config.yaml) for all default configurations.

## 📜 Symbol Cheat Sheet

| Token | Name        | Description                     | Example         |
|------:|-------------|---------------------------------|-----------------|
| `.`   | separator   | Separates selection from action | `1..3 . ,done`  |
| `..`  | id range    | Range of item IDs               | `1..5`          |
| `,`   | status      | Task status                     | `,pending`      |
| `/`   | project     | Project category                | `/work`         |
| `@`   | tag         | Custom tag                      | `@critical`     |
| `!`   | priority    | Priority level                  | `!high`         |
| `^`   | deadline    | Due date/time                   | `^tomorrow`     |
| `=`   | sort        | Sort results                    | `=!` (priority) |
| `?`   | query       | Query attributes                | `?^` (deadline) |
| `:`   | description | Long description                | `: details...`  |
| `-`   | stdin       | Read from standard input        | `-`             |

## 📚 Documentations

- [Documentation](https://github.com/admk/tali/wiki)
- [Tutorial](https://github.com/admk/tali/blob/main/TUTORIAL.md)
- [Configuration Guide](https://github.com/admk/tali/blob/main/CONFIGURATION.md)

## 🚀 Productivity Tips

- Use `t` as an alias for `tali`.
  For example,
  add the following line to your `~/.bashrc` or `~/.zshrc`:
  ```bash
  alias t='tali'
  ```

## 🧙‍♂️ Contribute

- ❓ Need Help? [FAQs](https://github.com/admk/tali/wiki/faqs)
- 🔮 Report bugs: [Issue Tracker](https://github.com/admk/tali/issues)
- 📥 Submit PRs: [Pull Requests](https://github.com/admk/tali/pulls)
- 💬 Discuss: [Discussions](https://github.com/admk/tali/discussions)
