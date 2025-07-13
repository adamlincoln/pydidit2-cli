import os
from urllib.parse import urlparse

import pydiditbackend as backend
from pydiditbackend.utils import build_rds_db_url
import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker as sqlalchemy_sessionmaker

app = typer.Typer()

db_url = build_rds_db_url(os.environ["PYDIDIT_DB_URL"])

sessionmaker = sqlalchemy_sessionmaker(create_engine(db_url))
backend.prepare(sessionmaker)

@app.command()
def get(model_name: str) -> None:
    backend.prepare(sessionmaker)
    print(backend.get(model_name))

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

if __name__ == "__main__":
    app()
