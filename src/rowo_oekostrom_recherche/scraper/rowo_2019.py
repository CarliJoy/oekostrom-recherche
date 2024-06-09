import traceback
from pathlib import Path

import bs4
import httpx
import numpy as np
import pandas as pd
from rowo_oekostrom_recherche import log
from rowo_oekostrom_recherche.scraper.base import AnbieterBase, ScrapeResults
from rowo_oekostrom_recherche.scraper.manager import run_and_save

BASEDIR = Path(__file__).parent.parent.parent.parent.parent

FILE = f"{BASEDIR}/Ökostromreport 2019/anbieterliste-2020_final.xlsx"
SCRAPER = "rowo2019"


class RoWo(AnbieterBase):
    kennzeichnung_url: str = ""


def to_string(val: float | str) -> str:
    if not isinstance(val, str) and np.isnan(val):
        return ""
    return str(val)


def to_url(val: float | str) -> str:
    text = to_string(val)
    if not text:
        return text
    if not text.startswith("http"):
        return f"http://{text}"
    return text


def to_plz(val: float) -> str:
    if np.isnan(val):
        return ""
    return f"{int(val):05d}"


def scrape() -> ScrapeResults[RoWo]:
    data = pd.read_excel(FILE)
    records = data.to_dict(orient="records")
    return ScrapeResults(
        results=[
            RoWo(
                name=to_string(r["Erneuerbare Energien 1"]),
                street=to_string(r["Adresse"]),
                city=to_string(r["Stadt"]),
                plz=to_string(r["PLZ"]),
                phone=to_string(r["Telefon"]),
                mail=to_string(r["Kontakt (nur für relevante Anbieter)"]),
                homepage=to_url(r['URL']),
                kennzeichnung_url=to_url(r['Kennzeichnung Link']),
            )
            for r in records
        ],
        source=SCRAPER,
    )


if __name__ == "__main__":
    run_and_save(scrape)
