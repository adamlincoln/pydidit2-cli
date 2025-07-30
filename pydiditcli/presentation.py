from datetime import datetime, timedelta

from rich.markup import escape

todo_due_threshold = timedelta(days=1)
project_due_threshold = timedelta(days=2)

def todo_rich(todo) -> str:
    due_past_threshold = False
    if todo.due is not None:
        now = datetime.now()
        due_past_threshold = todo.due - now < todo_due_threshold
    due = "" if todo.due is None else f"Due: {"[bold red]" if due_past_threshold else "[blue]"}{todo.due.isoformat()}{"[/bold red]" if due_past_threshold else "[/blue]"} "
    return f"[bold]{"[strike]" if todo.state == "completed" else ""}{todo.description}{"[/strike]" if str(todo.state) == "completed" else ""}[/bold] (ID {todo.id}, {todo.state}) {due}{escape("[")}Tags: {", ".join(tag.name for tag in todo.tags)}{escape("]")} {escape("[")}Projects: {", ".join(project.description for project in todo.contained_by_projects)}{escape("]")}{", ".join(f":notebook:{note.id}" for note in todo.notes)}"

def project_rich(project) -> str:
    due_past_threshold = False
    if project.due is not None:
        now = datetime.now()
        due_past_threshold = project.due - now < project_due_threshold
    due = "" if project.due is None else f"Due: {"[bold red]" if due_past_threshold else "[blue]"}{project.due.isoformat()}{"[/bold red]" if due_past_threshold else "[/blue]"} "
    return f"[bold]{"[strike]" if project.state == "completed" else ""}{project.description}{"[/strike]" if project.state == "completed" else ""}[/bold] (ID {project.id}, {project.state}) {due}{", ".join(f":notebook:{note.id}" for note in project.notes)}:\n  [italic]{"\n  ".join(f"* {todo.description} (ID {todo.id}, {todo.state}){", ".join(f":notebook:{note.id}" for note in todo.notes)}" for todo in project.contain_todos)}[/italic]"

def tag_rich(tag) -> str:
    return f"[bold]{tag.name}[/bold] (ID {tag.id}):\nTodos:\n  [italic]{"\n  ".join(f"* {todo.description} ({todo.state})" for todo in tag.todos)}[/italic]\nProjects:\n [italic]{"\n  ".join(f"* {project.description} ({project.state})" for project in tag.projects)}[/italic]"

def note_rich(note):
    return f"Note ID {note.id} ({len(note.todos)} todos): [italic]{repr(note)}[/italic]"
