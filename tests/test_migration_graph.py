"""Guard the Alembic revision graph against duplicate IDs and stray heads."""
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_migration_history_has_one_linear_head():
    config = Config("alembic.ini")
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == ["0005"]
    assert scripts.get_revision("0005").down_revision == "0004"
    assert scripts.get_revision("0004").down_revision == "0003"
    assert scripts.get_revision("0003").down_revision == "0002"
    assert scripts.get_revision("0002").down_revision == "0001"
    assert scripts.get_revision("0001").down_revision is None
