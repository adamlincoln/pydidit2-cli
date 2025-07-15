import os
from itertools import product
from typing import Annotated

import pydiditbackend as backend
import typer
from pydiditbackend.utils import build_rds_db_url
from rich import print as rich_print
from rich.markup import escape
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker as sqlalchemy_sessionmaker

app = typer.Typer()

db_url = build_rds_db_url(os.environ["PYDIDIT_DB_URL"])

sessionmaker = sqlalchemy_sessionmaker(create_engine(db_url))
backend.prepare(sessionmaker)

backend.models.Todo.__rich__ = lambda self: f"[bold]{self.description}[/bold] ({self.state}) {escape("[")}Tags: {", ".join(tag.name for tag in self.tags)}{escape("]")} {escape("[")}Projects: {", ".join(project.description for project in self.contained_by_projects)}{escape("]")}"
backend.models.Project.__rich__ = lambda self: f"[bold]{self.description}[/bold] (ID {self.id}, {self.state}):\n  [italic]{"\n  ".join(f"* {todo.description} ({todo.state})" for todo in self.contain_todos)}[/italic]"
backend.models.Tag.__rich__ = lambda self: f"[bold]{self.name}[/bold] (ID {self.id}):\n  [italic]{"\n  ".join(f"* {todo.description} ({todo.state})" for todo in self.todos)}[/italic]"

@app.command()
def get(
    model_name: str,
    primary_descriptor: Annotated[
        str | None,
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
def put(
    model_name: str,
    primary_descriptor: str,
    projects: Annotated[
        list[str] | None,
        typer.Option("--project", "-p"),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", "-g"),
    ] = None,
) -> None:
    with sessionmaker() as session, session.begin():
        model = getattr(backend.models, model_name)
        kwargs = {
            model.primary_descriptor: primary_descriptor,
        }
        if hasattr(model, "state"):
            kwargs["state"] = backend.models.enums.State.active
        instance = model(**kwargs)

        if projects is not None:
            unique_projects = set(projects)
            project_ids = {potential_id for potential_id in unique_projects if potential_id.isdigit()}
            project_descriptions = unique_projects - project_ids
            project_instances = backend.get(
                "Project",
                where=or_(
                    backend.models.Project.description.in_(project_descriptions),
                    backend.models.Project.id.in_(project_ids),
                ),
                session=session,
            )
            if len(project_instances) == 0:
                raise ValueError("There are no matching projects.")

            instance.contained_by_projects.extend(project_instances)

        if tags is not None:
            unique_tags = set(tags)
            tag_ids = {potential_id for potential_id in unique_tags if potential_id.isdigit()}
            tag_descriptions = unique_tags - tag_ids
            tag_instances = backend.get(
                "Tag",
                where=or_(
                    backend.models.Tag.name.in_(tag_descriptions),
                    backend.models.Tag.id.in_(tag_ids),
                ),
                session=session,
            )
            if len(tag_instances) == 0:
                raise ValueError("There are no matching tags.")

            instance.tags.extend(tag_instances)

        backend.put(instance, session=session)

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
            backend.get("Todo", filter_by={"id": todo_id}, session=session)[0],
        )

@app.command()
def tag(model_name: str, model_identifier: str, tag_identifier: str) -> None:
    with sessionmaker() as session, session.begin():
        target_filter_by = {}
        if model_identifier.isdigit():
            target_filter_by["id"] = int(model_identifier)
        else:
            target_filter_by[getattr(backend.models, model_name).primary_descriptor] = model_identifier
        instances = backend.get(model_name, filter_by=target_filter_by, session=session)

        tag_filter_by = {}
        if tag_identifier.isdigit():
            tag_filter_by["id"] = int(tag_identifier)
        else:
            tag_filter_by["name"] = tag_identifier
        tags = backend.get("Tag", filter_by=tag_filter_by, session=session)

        for instance, tag in product(instances, tags):
            instance.tags.append(tag)

if __name__ == "__main__":
    app()
