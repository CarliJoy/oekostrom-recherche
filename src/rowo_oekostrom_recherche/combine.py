from typing import NewType, cast
import sys
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
from pydantic import Field, ValidationError
from typing_extensions import TypedDict, Literal

from rowo_oekostrom_recherche.scraper.base import NameNormal

Source = NewType("source", str)

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


class Result(TypedDict):
    rowo2019: str
    oekotest: str
    okpower: str
    stromauskunft: str
    verivox: str


class LoadedSourceData(SourceData):
    rowo_2019: Combined


SOURCE_TYPES: dict[Source, type[base.AnbieterBase]] = {
    Source(k): cast(type[base.AnbieterBase], v)
    for k, v in LoadedSourceData.__annotations__.items()
}


def to_keydict(
    scrape_results: base.ScrapeResults,
) -> dict[NameNormal, base.AnbieterBase]:
    results: dict[NameNormal, base.AnbieterBase] = {}
    duplicates: dict[NameNormal, list[base.AnbieterBase]] = {}
    duplicate_keys: set[NameNormal] = set()
    for r in scrape_results.results:
        name = r.name_normalized
        duplicates.setdefault(name, []).append(r)
        if name in results:
            duplicate_keys.add(name)
        results[name] = r
    if scrape_results.source == "oekotest":
        duplicate_keys.remove(NameNormal("westfalenwind"))
    if duplicate_keys:
        for key in sorted(duplicate_keys):
            print(f" -> {key} ({scrape_results.source})")
            for obj in duplicates[key]:
                print(f"      -> {obj}")
        raise ValueError("Duplicate normalized names")
    return results


def load_data() -> dict[Source, dict[NameNormal, base.AnbieterBase]]:
    loaded_data: dict[Source, dict[NameNormal, base.AnbieterBase]] = {}
    for source_file in base.DATA_DIR.glob("*.json"):
        if source_file.name == "combined.json":
            continue

        source = Source(source_file.name.removesuffix(".json"))
        target_type: type[base.AnbieterBase]
        if source == TARGET:
            target_type = Combined
        else:
            target_type = SOURCE_TYPES[source]
        try:
            scrape_results = base.ScrapeResults[target_type].model_validate_json(
                source_file.read_text()
            )
        except ValidationError as e:
            print(f"Could not read {source_file.name}: {e}")
            sys.exit(1)
        loaded_data[source] = to_keydict(scrape_results)

    return loaded_data


def load_selections() -> dict[tuple[Source, str], str | None]:
    """
    Load selections that have been already done
    """
    selections: dict[tuple[Source, str], str | None] = {}
    if SELECTION_FILE.exists():
        for line in SELECTION_FILE.read_text().splitlines(keepends=False):
            choice: str | None
            source, anbieter, choice = line.split(";")
            if choice == "":
                choice = None
            selections[(source, anbieter)] = choice
    return selections


def input_selection(choices: list[NameNormal]) -> NameNormal | None | Literal[-1]:
    while True:
        try:
            result = input("> ").lower()
            if result == "" and len(choices) == 1:
                return choices[0]
            if result == "x":
                return None
            if result == "s":
                return -1
            if result == "q":
                print("Selected to exit")
                raise KeyboardInterrupt()
            return choices[int(result) - 1]
        except (ValueError, IndexError):
            print(
                "Invalid input. Try again. Input must be number between 1 and 4 or x or q."
            )


def extract_combination(
    source: Source,
    data_source: base.AnbieterBase,
    check_for: NameNormal,
    check_against: dict[NameNormal, Combined],
    full_names_to_val: dict[str, Combined],
    taken_choices: set[NameNormal],
) -> Combined | None | Literal[-1]:
    selections = load_selections()
    if (source, data_source.name) in selections:
        pre_result = selections[(source, data_source.name)]
        if pre_result == "-1":
            return -1
        if pre_result is None:
            return None
        return full_names_to_val[pre_result]
    candidates = process.extractBests(
        check_for, set(check_against.keys()), limit=20, score_cutoff=75
    )
    if len(candidates) == 0:
        print(f" -> Selected  *NOTHING* (neuer Anbieter)")
        print(f"    ↪    for  {data_source}\n")
        return None

    best_choice = check_against[candidates[0][0]]
    select_best_choice = False

    if (
        len(best_choice.name_normalized) > 5
        and best_choice.name_normalized == data_source.name_normalized
        or best_choice.name.lower() == data_source.name.lower()
    ):
        select_best_choice = True
    elif (
        candidates[0][1] > 95
        and (len(candidates) == 1 or candidates[1][1] <= 90)
        and candidates[0][0] not in taken_choices
    ):
        select_best_choice = True

    if select_best_choice:
        print(f" -> Selected  {best_choice}")
        print(f"    ↪    for  {data_source}\n")
        return best_choice
    print(f"Looking for match: {data_source}")
    for i, candidate in enumerate(candidates, start=1):
        dup = "!taken already!" if candidate[0] in taken_choices else ""
        indent = " " * 5
        print(
            f" ({i:>2}) [{candidate[1]:>3} %] {dup}{indent}{check_against[candidate[0]]}"
        )
    print(" (x) Add as new entry (q to quit, s to skip)")
    selection = input_selection([candidate[0] for candidate in candidates])
    if selection == -1 or selection is None:
        with SELECTION_FILE.open("a") as f:
            f.write(f"{source};{data_source.name};{selection or ''}\n")
        return selection
    result = check_against[selection]
    with SELECTION_FILE.open("a") as f:
        f.write(f"{source};{data_source.name};{result.name}\n")
    return result


def get_dupes(lst: list[str]) -> list[str]:
    """
    Get all duplicated items

    see  https://stackoverflow.com/a/9835819/3813064
    """
    seen: set[str] = set()
    return [x for x in lst if x and x in seen or seen.add(x)]


def combine() -> None:
    sources_data = load_data()
    target_data = cast(dict[NameNormal, Combined], sources_data[TARGET])
    target_data_plz: dict[NameNormal, Combined] = {
        v.name_normalized_plz: v for v in target_data.values()
    }
    full_names_to_val: dict[str, Combined] = {
        v.name: v for v in target_data_plz.values()
    }
    found: int = 0
    skipped: int = 0
    added: int = 0
    loaded_names: dict[Source, list[str]] = {}
    try:
        for source, anbieter_dict in sorted(sources_data.items()):
            if source == TARGET:
                continue
            print("#" * 120)
            print(f"# Finding connection for {source}")
            print("#" * 120)
            taken_choices: set[NameNormal] = set()
            loaded_names[source] = []
            for anbieter_name, source_data in anbieter_dict.items():
                loaded_names[source].append(source_data.name)
                check_for = anbieter_name
                check_against = target_data
                if source_data.plz:
                    check_for = NameNormal(f"{source_data.plz} {anbieter_name}")
                    check_against = target_data_plz
                selection = extract_combination(
                    source=source,
                    data_source=source_data,
                    check_for=check_for,
                    check_against=check_against,
                    full_names_to_val=full_names_to_val,
                    taken_choices=taken_choices,
                )
                if selection == -1:
                    # skipping entry
                    skipped += 1
                    continue
                elif selection:
                    # found match
                    found += 1
                    taken_choices.add(selection.name_normalized)
                    selection.sources[source] = source_data
                else:
                    # add new entry as it was missing in original data
                    added += 1
                    new_obj = Combined.model_validate(
                        {
                            **source_data.model_dump(),
                            "rowo2019": False,
                            "sources": {source: source_data},
                        },
                        strict=False,
                    )
                    target_data[anbieter_name] = new_obj
                    target_data_plz[new_obj.name_normalized_plz] = new_obj
                    full_names_to_val[new_obj.name] = new_obj
    except KeyboardInterrupt:
        print(f"{found=}, {skipped=}, {added=}, exiting")
    else:
        print(f"{found=}, {skipped=}, {added=}")

    results: list[Result] = []

    combined: Combined
    for combined in target_data.values():
        results.append(
            {
                "rowo2019": combined.name if combined.rowo2019 else "",
                "oekotest": (
                    combined.sources["oekotest"].name
                    if "oekotest" in combined.sources
                    else ""
                ),
                "okpower": (
                    combined.sources["okpower"].name
                    if "okpower" in combined.sources
                    else ""
                ),
                "stromauskunft": (
                    combined.sources["stromauskunft"].name
                    if "stromauskunft" in combined.sources
                    else ""
                ),
                "verivox": (
                    combined.sources["verivox"].name
                    if "verivox" in combined.sources
                    else ""
                ),
            }
        )

    # Ensure everything was combined and nothing is duplicated
    transposed: dict[str, list[str]] = {}
    for result in results:
        for source, anbieter in result.items():
            if anbieter:
                transposed.setdefault(source, []).append(anbieter)

    # no duplicates
    for source, anbieters in transposed.items():
        if len(anbieters) != len(set(anbieters) - {""}):
            raise ValueError(f"Duplicates in {source}: {get_dupes(anbieters)}")

    for source, anbieters in loaded_names.items():
        if len(anbieters) != len(set(anbieters) - {""}):
            raise ValueError(f"Duplicates in {source}: {get_dupes(anbieters)}")

    # everything combined
    missing_sources = ""
    for source, anbieters in loaded_names.items():
        anbieter_combined = transposed[source]
        missing = set(anbieters) - set(anbieter_combined)
        if missing:

            missing_sources += f'{source}: {", ".join(sorted(missing))}\n'

    if missing_sources:
        raise ValueError(missing_sources)

    with base.DATA_DIR.joinpath("combined.json").open("w") as f:
        json.dump(results, f, indent=2, sort_keys=True, ensure_ascii=False)


if __name__ == "__main__":
    combine()
