from sqlmodel import SQLModel, create_engine, Session

from .config import DATA_DIR

DB_PATH = DATA_DIR / "research_progress.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
