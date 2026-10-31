"""Independent SQLAlchemy metadata for the parallel SchoolSmartEYE database."""
from sqlalchemy.orm import DeclarativeBase


class NextBase(DeclarativeBase):
    """Metadata owned exclusively by the next-generation database."""

    pass
