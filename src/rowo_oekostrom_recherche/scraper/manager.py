from rowo_oekostrom_recherche.scraper.base import Scraper, DATA_DIR


def run_and_save(scraper: Scraper) -> None:
    data = scraper()
    target = DATA_DIR / f"{data.source}.json"
    target.write_text(data.model_dump_json(indent=2))

