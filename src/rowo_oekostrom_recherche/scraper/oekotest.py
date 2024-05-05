import httpx
import bs4
import traceback
from rowo_oekostrom_recherche.scraper.base import (
    AnbieterBase,
    Address,
    ScrapeResults,
)
from rowo_oekostrom_recherche.scraper.manager import run_and_save
from rowo_oekostrom_recherche import log

# Note: Die Seite wird nicht aktualisiert. Es muss jeweils der aktuelle Test
#       herausgesucht werden
DOMAIN = "https://www.oekotest.de"
BASE_URL = "https://www.oekotest.de/bauen-wohnen/Oekostrom-Vergleich-Diese-Tarife-der-Oekostromanbieter-sind-mangelhaft_12592_1.html"
SCRAPER = "oekotest"


class Oekotest(AnbieterBase):
    tarif: str
    tarif_url: str
    bewertung: str


def scrape_table(tag: bs4.Tag) -> Oekotest | None:
    i = -1
    phone: str = ""
    fax: str = ""
    mail: str = ""
    homepage: str = ""
    street: str = ""
    plz_city: str = ""

    try:
        bewertung = tag["data-grade"]
        tarif_url = f"{DOMAIN}{tag['href']}"
        name = tag.select(".product-distributor")[0].text.strip()
        tarif = tag.select(".product-name")[0].text.strip()
        if not name:
            raise ValueError("Could not determine name of carrier")

        return Oekotest(
            name=name,
            tarif=tarif,
            tarif_url=tarif_url,
            phone=phone,
            fax=fax,
            mail=mail,
            homepage=homepage,
            street=street,
            bewertung=bewertung,
            city=plz_city.partition(" ")[2],
            plz=plz_city.partition(" ")[0],
        )
    except:
        print(f"Failed checking row {i}")
        traceback.print_exc()
        return None


def scrape() -> ScrapeResults[Oekotest]:
    log.info("Start scraping", scraper=SCRAPER)
    site = httpx.get(BASE_URL)
    site.raise_for_status()
    soup = bs4.BeautifulSoup(site.content, "html.parser")
    results: list[Oekotest] = []
    links = soup.find_all("a", class_="product-link")
    total = len(links)
    for i, table in enumerate(links):
        result = scrape_table(table)
        if result:
            results.append(result)
            log.info("Scrape ok", num=f"{i + 1}/{total}", scraper=SCRAPER)
        else:
            log.info("Scrape failed", num=f"{i+1}/{total}", scraper=SCRAPER)
    return ScrapeResults(results=results, source=SCRAPER)


if __name__ == "__main__":
    run_and_save(scrape)
