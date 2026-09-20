from sqlalchemy.orm import DeclarativeBase


## mapea los modelos de python con las tablas de postgres
class Base(DeclarativeBase):
    pass
