from typing import NewType, cast

from rowo_oekostrom_recherche.scraper import (
    base,
    okpower,
    oekotest,
    rowo_2019,
    stromauskunft,
    verivox,
)
import json
from thefuzz import process
from pydantic import Field
from typing_extensions import TypedDict


Source = NewType("source", str)
NameNormal = NewType("NameNormal", str)

SELECTION_FILE = base.DATA_DIR / "combine_selections.csv"
TARGET = Source("rowo2019")


class SourceData(TypedDict, total=False):
    oekotest: oekotest.Oekotest
    okpower: okpower.OkPower
    stromauskunft: stromauskunft.Stromauskunft
    verivox: verivox.VerivoxBase


class Combined(rowo_2019.RoWo):
    rowo2019: bool = True
    sources: SourceData = Field(default_factory=SourceData)


class LoadedSourceData(SourceData):
    rowo_2019: Combined


SOURCE_TYPES: dict[Source, type[base.AnbieterBase]] = {
    Source(k): cast(type[base.AnbieterBase], v)
    for k, v in LoadedSourceData.__annotations__.items()
}


replaces = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "sz",
    ";": "",
}


def normalize_name(name: str) -> NameNormal:
    name = name.lower()
    for search, replace in replaces.items():
        name = name.replace(search, replace)
    return NameNormal(name)


def to_keydict(
    scrape_results: base.ScrapeResults,
) -> dict[NameNormal, base.AnbieterBase]:
    return {normalize_name(r.name): r for r in scrape_results.results}


def load_data() -> dict[Source, dict[NameNormal, base.AnbieterBase]]:
    loaded_data: dict[Source, dict[NameNormal, base.AnbieterBase]] = {}
    for source_file in base.DATA_DIR.glob("*.json"):
        source = Source(source_file.name.removesuffix(".json"))
        target_type: type[base.AnbieterBase]
        if source == TARGET:
            target_type = Combined
        else:
            target_type = SOURCE_TYPES[source]
        scrape_results = base.ScrapeResults[target_type].model_validate_json(
            source_file.read_text()
        )
        loaded_data[source] = to_keydict(scrape_results)

    return loaded_data


def load_selections() -> dict[tuple[Source, NameNormal], NameNormal | None]:
    """
    Load selections that have been already done
    """
    selections: dict[tuple[Source, NameNormal], NameNormal | None] = {}
    if SELECTION_FILE.exists():
        for line in SELECTION_FILE.read_text().splitlines(keepends=False):
            choice: str | None
            source, anbieter, choice = line.split(";")
            if choice == "":
                choice = None
            selections[(source, anbieter)] = choice
    return selections


def extract_combination(
    source: Source,
    data_source: base.AnbieterBase,
    anbieter_name: NameNormal,
    target_data: dict[NameNormal, Combined],
    taken_choices: set[NameNormal],
) -> NameNormal | None:
    selections = load_selections()
    if (source, anbieter_name) in selections:
        return selections[(source, anbieter_name)]
    candidates = process.extract(anbieter_name, set(target_data.keys()), limit=4)
    if (
        candidates[0][1] > 95
        and candidates[1][1] < 90
        and candidates[0][0] not in taken_choices
    ):
        print(f" -> Selection {candidates[0][0]} for {anbieter_name}")
        return candidates[0][0]
    print(f"Looking for match: {data_source}")
    for i, candidate in enumerate(candidates, start=1):
        dup = "!taken already!" if candidate[0] in taken_choices else ""
        print(f" ({i}) [{candidate[1]} %] {dup} {target_data[candidate[0]]}")
    print(" (x) Add as new entry")
    return None


def combine() -> None:
    sources_data = load_data()
    target_data = cast(dict[NameNormal, Combined], sources_data[TARGET])

    for source, anbieter_dict in sources_data.items():
        if source == TARGET:
            continue
        print("#" * 120)
        print(f"# Finding connection for {source}")
        print("#" * 120)
        take_choices: set[NameNormal] = set()
        for anbieter_name, source_data in anbieter_dict.items():
            target = extract_combination(
                source, source_data, anbieter_name, target_data, take_choices
            )
            if target:
                take_choices.add(target)
                target_data[target].sources[source] = sources_data
            else:
                # add new entry as it was missing in original data
                target_data[anbieter_name] = Combined.model_validate(
                    {
                        **source_data.model_dump(),
                        "rowo2019": False,
                        "sources": {source: source_data},
                    },
                    strict=False,
                )


if __name__ == "__main__":
    combine()
