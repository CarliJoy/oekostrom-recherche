import traceback
from typing import cast

import bs4
import httpx
from rowo_oekostrom_recherche import log
from rowo_oekostrom_recherche.scraper.base import AnbieterBase, ScrapeResults
from rowo_oekostrom_recherche.scraper.manager import run_and_save

# https://www.stromauskunft.de/oekostrom/oekostrom-anbieter/ lazy loads the following table
# which a json file that contains HTML (really!)
BASE_URL = "https://www.stromauskunft.de/"
DATA_URL = "https://www.stromauskunft.de/front/templates/stromauskunft/php/ajax/ajax-carrier-tables-v5.php?carrierType=eco_carriers"
SCRAPER = "stromauskunft"


class Stromauskunft(AnbieterBase):
    portal_url: str


def convert_data(row: int, elements: list[str | int]) -> Stromauskunft | None:
    data = elements[1]
    assert isinstance(data, str)
    try:
        soup = bs4.BeautifulSoup(data, "html.parser")
        links = soup.find_all("a")
        name = links[0]["title"]
        portal_url = BASE_URL + links[0]["href"].lstrip("/")

        street = soup.select(".carrier-street")[0].text
        plz_city = soup.select(".carrier-city")[0].text
        return Stromauskunft(
            name=name,
            street=street,
            city=plz_city.partition(" ")[2],
            plz=plz_city.partition(" ")[0],
            portal_url=portal_url,
        )
    except:
        print(f"Failed checking row {row}")
        traceback.print_exc()
        return None


def scrape() -> ScrapeResults[Stromauskunft]:
    log.info("Start scraping", scraper=SCRAPER)
    response = httpx.get(DATA_URL)
    response.raise_for_status()
    data = response.json()

    results: list[Stromauskunft] = []
    for i, elm in enumerate(data["data"]):
        result = convert_data(i, cast(list[str | int], elm))
        if result:
            results.append(result)

    return ScrapeResults(results=results, source=SCRAPER)


if __name__ == "__main__":
    run_and_save(scrape)
