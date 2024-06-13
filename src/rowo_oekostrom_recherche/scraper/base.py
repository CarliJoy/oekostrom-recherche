import datetime
from pathlib import Path
from typing import Generic, NewType, Protocol, TypeVar

from pydantic import BaseModel, Field


NameNormal = NewType("NameNormal", str)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scraped_data"

replaces = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "sz",
    "&": "",
    ";": "",
    ":": " ",
    "-": " ",
    "marke der": "",
    # remove things not giving information
}

# This word occur many times and only confuse fuzzy
word_to_remove = {
    "gmbh",
    "stadtwerke",
    "e-werk",
    "energie",
    "gemeindewerke",
    "gmbh",
    "ag",
    "co.",
    "kg",
    "gas",
    "strom",
    "Stromversorgung",
    "eg",
}


def normalize_name(name: str) -> NameNormal:
    name = name.lower()
    if name[0].isnumeric():
        # if name start with number, add something so it is not remove
        name = f"_ {name}"
    for search, replace in replaces.items():
        name = name.replace(search, replace)
    name = " ".join([word for word in name.split(" ") if word not in word_to_remove])
    return NameNormal(name)


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

    @property
    def name_normalized(self) -> NameNormal:
        return normalize_name(self.name)

    @property
    def name_normalized_plz(self) -> NameNormal:
        return NameNormal(f"{self.plz} {self.name_normalized}")

    def __str__(self) -> str:
        result = self.name
        addr = (self.plz, self.city, self.street, self.city)
        if addr != ("", "", ""):
            result += f" {' - '.join(addr)}"
        vals = self.model_dump(
            exclude={"name", "street", "city", "plz", "sources", "rowo2019"}
        )
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
    def __call__(self) -> ScrapeResults: ...
