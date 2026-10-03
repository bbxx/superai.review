import pytest
from sqlalchemy.orm import Session

from superai_review.db.base import Base
from superai_review.db.session import build_engine, build_session_factory


@pytest.fixture
def db() -> Session:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    with factory() as session:
        yield session
    engine.dispose()
