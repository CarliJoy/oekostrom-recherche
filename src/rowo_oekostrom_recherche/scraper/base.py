import datetime
from pathlib import Path
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scraped_data"


class Address(BaseModel):
    street: str = ""
    city: str = ""
    plz: str = ""


class AnbieterBase(Address):
    name: str
    phone: str = ""
    fax: str = ""
    note: str = ""
    mail: str = ""
    homepage: str = ""


TAnbieterBase = TypeVar("TAnbieterBase", bound=AnbieterBase)


class ScrapeResults(BaseModel, Generic[TAnbieterBase]):
    results: list[TAnbieterBase]
    source: str
    create: datetime.datetime = Field(default_factory=datetime.datetime.now)


class Scraper(Protocol):
    def __call__(self) -> ScrapeResults:
        ...

