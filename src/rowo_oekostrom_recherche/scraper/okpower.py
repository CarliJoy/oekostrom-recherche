import httpx
import bs4
import traceback
from rowo_oekostrom_recherche.scraper.base import (
    AnbieterBase,
    ScrapeResults,
)
from rowo_oekostrom_recherche.scraper.manager import run_and_save
from rowo_oekostrom_recherche import log

DOMAIN = "https://www.ok-power.de"
BASE_URL = "https://www.ok-power.de/fuer-strom-kunden/anbieter-uebersicht.html"
SCRAPER = "ok-power"


class OkPower(AnbieterBase):
    tarif: str
    tarif_url: str
    cert_info: str


def scrape_table(table: bs4.Tag) -> OkPower | None:
    i = -1
    name: str = ""
    tarif: str = ""
    tarif_url: str = ""
    cert_info: str = ""

    phone: str = ""
    fax: str = ""
    mail: str = ""
    homepage: str = ""
    street: str = ""
    plz_city: str = ""

    try:
        rows = table.find_all("tr")
        for i, row in enumerate(rows):
            col1, col2 = row.find_all("td")
            if i == 0:
                # first line are always name and tarif
                name = col1.text
                tarif = col2.text
                tarif_url_soup = col2.find_all("a")
                if len(tarif_url_soup) == 1:
                    tarif_url = f"{DOMAIN}/{tarif_url_soup[0]['href']}"
                continue
            if i == 1:
                # second line always contains cert info
                cert_info = col2.text
            col2_text = col2.text.strip()
            if col1_text := col1.text.strip():
                if not street:
                    street = col1_text
                elif not plz_city:
                    plz_city = col1_text
                else:
                    # col 1 only contains:
                    # - name
                    # - str
                    # - plz city
                    # in this order, nothing else is expected
                    raise ValueError(
                        "Parse Error, didn't expect more info on first col"
                    )
            if col2_text.lower().startswith("tel."):
                phone = col2_text.lower().removeprefix("tel.").strip()
            elif col2_text.lower().startswith("fax"):
                fax = col2_text.lower().removeprefix("fax").strip()
            elif "@" in col2_text:
                mail = col2_text
            elif links := col2.find_all("a"):
                if len(links) == 1:
                    homepage = links[0]["href"]
        if not name:
            raise ValueError("Could not determine name of carrier")

        return OkPower(
            name=name,
            tarif=tarif,
            tarif_url=tarif_url,
            phone=phone,
            fax=fax,
            mail=mail,
            homepage=homepage,
            street=street,
            cert_info=cert_info,
            city=plz_city.partition(" ")[2],
            plz=plz_city.partition(" ")[0],
        )
    except:
        print(f"Failed checking row {i}")
        traceback.print_exc()
        return None


def scrape() -> ScrapeResults[OkPower]:
    log.info("Start scraping", scraper=SCRAPER)
    site = httpx.get(BASE_URL)
    site.raise_for_status()
    soup = bs4.BeautifulSoup(site.content, "html.parser")
    results: list[OkPower] = []
    tables = soup.select("#anbieterliste .anbieter")
    total = len(tables)
    for i, table in enumerate(tables):
        result = scrape_table(table)
        if result:
            results.append(result)
            log.info("Scrape ok", num=f"{i + 1}/{total}", scraper=SCRAPER)
        else:
            log.info("Scrape failed", num=f"{i+1}/{total}", scraper=SCRAPER)
    return ScrapeResults(results=results, source=SCRAPER)


if __name__ == "__main__":
    run_and_save(scrape)
