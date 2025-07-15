import os
from typing import Annotated

import pydiditbackend as backend
import typer
from pydiditbackend.utils import build_rds_db_url
from rich import print as rich_print
from rich.markup import escape
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker as sqlalchemy_sessionmaker

app = typer.Typer()

db_url = build_rds_db_url(os.environ["PYDIDIT_DB_URL"])

sessionmaker = sqlalchemy_sessionmaker(create_engine(db_url))
backend.prepare(sessionmaker)

backend.models.Todo.__rich__ = lambda self: f"[bold]{self.description}[/bold] ({self.state}) {escape("[")}{escape("]")}"
backend.models.Project.__rich__ = lambda self: f"[bold]{self.description}[/bold] ({self.state}):\n  [italic]{"\n  ".join(f"* {todo.description} ({todo.state})" for todo in self.contain_todos)}[/italic]"

@app.command()
def get(
    model_name: str,
    primary_descriptor: Annotated[
        str,
        typer.Argument(),
    ] = None,
    *,
    include_completed: Annotated[
        bool,
        typer.Option("--all"),
    ] = False,
) -> None:
    filter_by = {}
    if primary_descriptor is not None:
        filter_by[getattr(
            backend.models,
            model_name,
        ).primary_descriptor] = primary_descriptor
    for el in backend.get(
        model_name,
        include_completed=include_completed,
        filter_by=filter_by,
    ):
        rich_print(el)

@app.command()
def put(model_name: str, primary_descriptor: str) -> None:
    model = getattr(backend.models, model_name)
    kwargs = {
        model.primary_descriptor: primary_descriptor,
        "state": backend.models.enums.State.active,
    }
    instance = model(**kwargs)
    backend.put(instance)

@app.command()
def delete(model_name: str, instance_id: int) -> None:
    backend.delete(model_name, instance_id)

@app.command()
def complete(model_name: str, instance_id: int) -> None:
    backend.mark_completed(model_name, instance_id)

@app.command()
def contain_todo(project_id: int, todo_id: int) -> None:
    with sessionmaker() as session, session.begin():
        project = backend.get("Project", filter_by={"id": project_id}, session=session)[0]
        project.contain_todos.append(
            backend.get("Todo", filter_by={"id": todo_id}, session=session)[0]
        )

if __name__ == "__main__":
    app()
