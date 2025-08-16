import os
from collections.abc import Iterable
from functools import partial
from itertools import product
from typing import Annotated

import dateparser
import pydiditbackend as backend
import typer
from pydiditbackend.utils import build_rds_db_url
from rich import print as rich_print
from rich.console import Console
from rich.pretty import Pretty
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker as sqlalchemy_sessionmaker

from pydiditcli import presentation

app = typer.Typer()

db_url = build_rds_db_url(os.environ["PYDIDIT_DB_URL"])

sessionmaker = sqlalchemy_sessionmaker(create_engine(db_url, echo=False))
backend.prepare(sessionmaker)

backend.models.Todo.__rich__ = presentation.todo_rich
backend.models.Project.__rich__ = presentation.project_rich
backend.models.Tag.__rich__ = presentation.tag_rich
backend.models.Note.__rich__ = presentation.note_rich

def _separate_identifiers(identifiers: Iterable[str]) -> tuple[set[int], set[str]]:
    unique_identifiers = set(identifiers)
    ids = {int(potential_id) for potential_id in unique_identifiers if potential_id.isdigit()}
    primary_descriptors = unique_identifiers - ids
    return ids, primary_descriptors

def _build_related_filter(model_name: str, identifiers: Iterable[str]):
    ids, primary_descriptors = _separate_identifiers(identifiers)
    model = getattr(backend.models, model_name)
    return or_(
        getattr(model, model.primary_descriptor).in_(primary_descriptors),
        model.id.in_(ids),
    )

def _build_instance_identifier_filter_by(
    model_name: str,
    instance_identifier: str,
) -> dict[str, int | str]:
    if instance_identifier.isdigit():
        return {"id": int(instance_identifier)}
    else:
        return {
            getattr(
                backend.models,
                model_name,
            ).primary_descriptor: instance_identifier,
        }

_build_project_filter = partial(_build_related_filter, "Project")
_build_tag_filter = partial(_build_related_filter, "Tag")

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
    projects: Annotated[
        list[str] | None,
        typer.Option("--project", "-p"),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", "-g"),
    ] = None,
) -> None:
    kwargs = {
        "include_completed": include_completed,
    }
    if primary_descriptor is not None:
        kwargs["filter_by"] = _build_instance_identifier_filter_by(
            model_name,
            primary_descriptor,
        )
    if projects is not None:
        kwargs["where"] = getattr(backend.models, model_name).contained_by_projects.any(_build_project_filter(projects))
    if tags is not None:
        tags_where = getattr(backend.models, model_name).tags.any(_build_tag_filter(tags))
        if "where" not in kwargs:
            kwargs["where"] = tags_where
        else:
            kwargs["where"] = and_(kwargs["where"], tags_where)
    for el in backend.get(
        model_name,
        **kwargs,
    ):
        if model_name == "Note":
            console = Console()
            with console.pager():
                console.print(Pretty(el))
                console.print(el.text)
        else:
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
            project_instances = backend.get(
                "Project",
                where=_build_project_filter(projects),
                session=session,
            )
            if len(project_instances) == 0:
                raise ValueError("There are no matching projects.")

            instance.contained_by_projects.extend(project_instances)

        if tags is not None:
            tag_instances = backend.get(
                "Tag",
                where=_build_tag_filter(tags),
                session=session,
            )
            if len(tag_instances) == 0:
                raise ValueError("There are no matching tags.")

            instance.tags.extend(tag_instances)

        backend.put(instance, session=session)

@app.command()
def edit(
    model_name: str,
    instance_identifier: str,
    new_value: str,
) -> None:
    with sessionmaker() as session, session.begin():
        instances = backend.get(
            model_name,
            filter_by=_build_instance_identifier_filter_by(
                model_name,
                instance_identifier,
            ),
            session=session,
        )

        for instance in instances:
            setattr(instance, instance.primary_descriptor, new_value)

@app.command()
def move(
    model_name: str,
    instance_identifier: str,
    new_display_position: str,
    *,
    direct_display_position: Annotated[
        bool,
        typer.Option(
            help="Use the provided integer as the new display position.  (By default, the provided integer is used as the ID of the instance currently in the target position.)",
        ),
    ] = False,
) -> None:
    instances = backend.get(
        model_name,
        filter_by=_build_instance_identifier_filter_by(
            model_name,
            instance_identifier,
        ),
    )

    if len(instances) != 1:
        raise ValueError("There must be only one instance to move.")

    instance = instances[0]

    if new_display_position in ("start", "end"):
        backend.move(instance, new_display_position)
        return

    if direct_display_position:
        target_display_position = int(new_display_position)
    else:
        targets = backend.get(
            model_name,
            filter_by=_build_instance_identifier_filter_by(
                model_name,
                new_display_position,
            ),
        )

        if len(targets) != 1:
            raise ValueError("There must be only one target.")

        target_display_position = targets[0].display_position

    backend.move(instance, target_display_position)

@app.command()
def delete(model_name: str, instance_id: int) -> None:
    backend.delete(model_name, instance_id)

@app.command()
def complete(model_name: str, instance_identifier: str) -> None:
    with sessionmaker() as session, session.begin():
        instances = backend.get(
            model_name,
            filter_by=_build_instance_identifier_filter_by(
                model_name,
                instance_identifier,
            ),
            session=session,
        )

        for instance in instances:
            backend.mark_completed(model_name, instance.id, session=session)

@app.command()
def due(model_name: str, instance_identifier: str, due: str) -> None:
    with sessionmaker() as session, session.begin():
        instances = backend.get(
            model_name,
            filter_by=_build_instance_identifier_filter_by(
                model_name,
                instance_identifier,
            ),
            session=session,
        )

        for instance in instances:
            if len(due) == 0:
                instance.due = None
            else:
                due_dt = dateparser.parse(due)
                if due_dt is None:
                    raise ValueError(f"{due} could not be made into a datetime.")
                instance.due = due_dt

@app.command()
def contain_todo(project_id: int, todo_id: int) -> None:
    with sessionmaker() as session, session.begin():
        project = backend.get("Project", filter_by={"id": project_id}, session=session)[0]
        project.contain_todos.append(
            backend.get("Todo", filter_by={"id": todo_id}, session=session)[0],
        )

@app.command()
def untag(model_name: str, instance_identifier: str, tag_identifier: str) -> None:
    with sessionmaker() as session, session.begin():
        instances = backend.get(
            model_name,
            filter_by=_build_instance_identifier_filter_by(
                model_name,
                instance_identifier,
            ),
            session=session,
        )

        tags = backend.get(
            "Tag",
            filter_by=_build_instance_identifier_filter_by(
                "Tag",
                tag_identifier,
            ),
            session=session,
        )

        if len(instances) != 1:
            raise ValueError("Must specify exactly one instance.")

        if len(tags) != 1:
            raise ValueError("Must specify exactly one real tag to remove.")

        try:
            instances[0].tags.remove(tags[0])
        except ValueError:
            raise ValueError(
                f"The tag {tags[0].name} is not found on {model_name} {instances[0].id}.",
            )

@app.command()
def tag(model_name: str, instance_identifier: str, tag_identifier: str) -> None:
    with sessionmaker() as session, session.begin():
        instances = backend.get(
            model_name,
            filter_by=_build_instance_identifier_filter_by(
                model_name,
                instance_identifier,
            ),
            session=session,
        )

        tags = backend.get(
            "Tag",
            filter_by=_build_instance_identifier_filter_by(
                "Tag",
                tag_identifier,
            ),
            session=session,
        )

        for instance, tag in product(instances, tags):
            instance.tags.append(tag)

@app.command()
def attach_note(model_name: str, instance_identifier: str, note_identifier: str) -> None:
    with sessionmaker() as session, session.begin():
        instances = backend.get(
            model_name,
            filter_by=_build_instance_identifier_filter_by(
                model_name,
                instance_identifier,
            ),
            session=session,
        )

        notes = backend.get(
            "Note",
            filter_by=_build_instance_identifier_filter_by(
                "Note",
                note_identifier,
            ),
            session=session,
        )

        for instance, note in product(instances, notes):
            instance.notes.append(note)

@app.command()
def search(search_string: str) -> None:
    for instance in backend.search(search_string):
        rich_print(instance)

if __name__ == "__main__":
    app()
