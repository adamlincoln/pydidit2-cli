from rich.markup import escape

def todo_rich(todo) -> str:
    return f"[bold]{todo.description}[/bold] (ID {todo.id}, {todo.state}) {escape("[")}Tags: {", ".join(tag.name for tag in todo.tags)}{escape("]")} {escape("[")}Projects: {", ".join(project.description for project in todo.contained_by_projects)}{escape("]")}{", ".join(f":notebook:{note.id}" for note in todo.notes)}"

def project_rich(project) -> str:
    return f"[bold]{project.description}[/bold] (ID {project.id}, {project.state}){", ".join(f":notebook:{note.id}" for note in project.notes)}:\n  [italic]{"\n  ".join(f"* {todo.description} (ID {todo.id}, {todo.state}){", ".join(f":notebook:{note.id}" for note in todo.notes)}" for todo in project.contain_todos)}[/italic]"

def tag_rich(tag) -> str:
    return f"[bold]{tag.name}[/bold] (ID {tag.id}):\n  [italic]{"\n  ".join(f"* {todo.description} ({todo.state})" for todo in tag.todos)}[/italic]"

def note_rich(note):
    return f"Note ID {note.id} ({len(note.todos)} todos): [italic]{repr(note)}[/italic]"
