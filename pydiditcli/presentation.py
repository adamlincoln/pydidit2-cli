from datetime import datetime, timedelta

from rich.markup import escape

due_threshold = timedelta(days=1)

def todo_rich(todo) -> str:
    due_past_threshold = False
    if todo.due is not None:
        now = datetime.now()
        due_past_threshold = todo.due - now < due_threshold
    due = "" if todo.due is None else f"Due: {"[bold red]" if due_past_threshold else ""}{todo.due.isoformat()}{"[/bold red]" if due_past_threshold else ""} "
    return f"[bold]{todo.description}[/bold] (ID {todo.id}, {todo.state}) {due}{escape("[")}Tags: {", ".join(tag.name for tag in todo.tags)}{escape("]")} {escape("[")}Projects: {", ".join(project.description for project in todo.contained_by_projects)}{escape("]")}{", ".join(f":notebook:{note.id}" for note in todo.notes)}"

def project_rich(project) -> str:
    return f"[bold]{project.description}[/bold] (ID {project.id}, {project.state}){", ".join(f":notebook:{note.id}" for note in project.notes)}:\n  [italic]{"\n  ".join(f"* {todo.description} (ID {todo.id}, {todo.state}){", ".join(f":notebook:{note.id}" for note in todo.notes)}" for todo in project.contain_todos)}[/italic]"

def tag_rich(tag) -> str:
    return f"[bold]{tag.name}[/bold] (ID {tag.id}):\n  [italic]{"\n  ".join(f"* {todo.description} ({todo.state})" for todo in tag.todos)}[/italic]"

def note_rich(note):
    return f"Note ID {note.id} ({len(note.todos)} todos): [italic]{repr(note)}[/italic]"
