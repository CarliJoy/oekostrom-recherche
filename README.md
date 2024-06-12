# rowo_oekostrom_recherche

[![PyPI - Version](https://img.shields.io/pypi/v/rowo-oekostrom-recherche.svg)](https://pypi.org/project/rowo-oekostrom-recherche)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rowo-oekostrom-recherche.svg)](https://pypi.org/project/rowo-oekostrom-recherche)

-----

## Table of Contents

- [Installation](#installation)
- [License](#license)

## Installation

```console
# clone repo
git clone https://github.com/CarliJoy/oekostrom-recherche.git
# go to the newly cloned folder
cd oekostrom-recherche
# create new python virtual environment
python3 -m venv .venv
# activate the python environment
source .venv/bin/activate
# install the requirements
pip install -r requirements.txt
# install the package
pip install -e .
# run the script
python3 src/rowo_oekostrom_recherche/combine.py

# The status is saved under scraped_data/combine_selections.csv
```

## Usage
```console
cd <folder of installation>
source .venv/bin/activate
python src/rowo_oekostrom_recherche/combine.py
```

## License

`rowo-oekostrom-recherche` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
