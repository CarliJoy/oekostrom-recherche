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

DOMAIN = "https://www.verivox.de"
BASE_URL = "https://www.verivox.de/strom/anbieter/"
SCRAPER = "verivox"

class VerivoxBase(AnbieterBase):
    portal_url: str


def scrape_address(url: str) -> tuple[Address, str]:
    note = ""
    try:
        site = httpx.get(url)
        site.raise_for_status()
        if site.url == BASE_URL:
            raise ValueError("No subpage")
        addresses = bs4.BeautifulSoup(site.content, "html.parser").find_all(
            "div", class_="carrier-address"
        )
        if len(addresses) != 1:
            raise ValueError(f"Multiple or none addresses found ({addresses})")
        address = addresses[0]
        try:
            name, street, plz_city = address.stripped_strings
        except ValueError as e:
            print(f"{e} for '{list(address.stripped_strings)}': Try recover")
            name, *streets, plz_city, = address.stripped_strings
            street = "\n".join(streets)
            note = "Address might be wrong"
        plz, _, city = plz_city.partition(" ")
    except Exception as e:
        traceback.print_exc()
        return Address(street="", plz="", city=""), repr(e)
    else:

        return Address(street=street, plz=plz, city=city), note


def scrape() -> ScrapeResults[VerivoxBase]:
    log.info("Start scraping", scraper=SCRAPER)
    site = httpx.get(BASE_URL)
    site.raise_for_status()
    anbieters = bs4.BeautifulSoup(site.content, "html.parser").find_all(
        "a", class_="carrier-list-entry"
    )
    result: list[VerivoxBase] = []
    added: set[str] = set()
    total = len(anbieters)
    for i, anbieter in enumerate(anbieters):
        name = anbieter.text
        url = f"{DOMAIN}/{anbieter['href']}"
        log.info(
            "Start scraping address",
            scraper="verivox",
            num=f"{i+1}/{total}",
            carrier=name,
        )

        address, note = scrape_address(url)

        if name in added:
            log.info("Skipping duplicate", scraper=SCRAPER, carrier=name)
        else:
            result.append(
                VerivoxBase(
                    name=name,
                    phone="",
                    fax="",
                    plz=address.plz,
                    city=address.city,
                    street=address.street,
                    portal_url=url,
                    note=note,
                )
            )
            added.add(name)

    return ScrapeResults(results=result, source=SCRAPER)


if __name__ == "__main__":
    run_and_save(scrape)
