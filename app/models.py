from sqlalchemy import Column, Integer, Numeric, String, Text

from app.database import Base


class WishORM(Base):
    __tablename__ = "wishes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(50), nullable=False)
    link = Column(String, nullable=True)
    price_estimate = Column(Numeric(10, 2), nullable=True)
    updated_at = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
