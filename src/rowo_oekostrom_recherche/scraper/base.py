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

    def __str__(self) -> str:
        result = self.name
        addr = (self.street, self.city, self.plz)
        if addr != ("", "", ""):
            result += f" {'-'.join(addr)}"
        vals = self.model_dump(exclude={'name', 'street', 'city', 'plz', 'sources', 'rowo2019'})
        for k, v in vals.items():
            if v:
                result += f" {k}={v}"
        return result


TAnbieterBase = TypeVar("TAnbieterBase", bound=AnbieterBase)


class ScrapeResults(BaseModel, Generic[TAnbieterBase]):
    results: list[TAnbieterBase]
    source: str
    create: datetime.datetime = Field(default_factory=datetime.datetime.now)


class Scraper(Protocol):
    def __call__(self) -> ScrapeResults:
        ...

