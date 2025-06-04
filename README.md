# ThermoPyL

ThermoPyL is a Python package for exploring and using the [ThermoML Archive](http://trc.nist.gov/ThermoML.html) from the [NIST TRC](http://trc.nist.gov). It provides tools for downloading, parsing, and analyzing ThermoML data, including conversion to pandas DataFrames for further analysis.

[![Build Status](https://travis-ci.org/choderalab/thermopyl.png?branch=master)](https://travis-ci.org/choderalab/thermopyl)
[![Binstar Badge](https://binstar.org/choderalab/thermopyl-dev/badges/version.svg)](https://binstar.org/choderalab/thermopyl-dev)

## Features

- Download and update a local mirror of the ThermoML Archive.
- Parse ThermoML XML files and convert them to pandas DataFrames.
- Command-line tools for updating the archive and building pandas datasets.

## Installation

### With pip

```sh
pip install thermopyl
```

### With conda (recommended)

```sh
conda config --add channels choderalab
conda install thermopyl
```

### From source

```sh
git clone https://github.com/choderalab/thermopyl.git
cd thermopyl
pip install .
```

## Usage

### Command-line

- Update the ThermoML archive:

  ```sh
  thermoml-update-mirror
  ```

- Build the pandas DataFrame from the ThermoML XML files:

  ```sh
  thermoml-build-pandas
  ```

### Python API

```python
import thermopyl
# Read ThermoML archive data into pandas dataframe
df = thermopyl.pandas_dataframe()
```

## Development

- Python >= 3.7 is required.
- To install for development: `pip install -e .[dev]`
- Tests can be run with `pytest`.
- Code style: follow [PEP8](https://www.python.org/dev/peps/pep-0008/).

## Project Structure

- `thermopyl/` - Main package code
- `thermopyl/data/` - ThermoML schema and data files
- `thermopyl/scripts/` - CLI entry points
- `tests/` - Unit tests

## License

This project is licensed under the GNU General Public License v2 or later (GPLv2+). See the [LICENSE](LICENSE) file for details.

## Citation

If you use ThermoPyL in your research, please cite:

> Towards Automated Benchmarking of Atomistic Forcefields: Neat Liquid Densities and Static Dielectric Constants from the ThermoML Data Archive  
> Kyle A. Beauchamp, Julie M. Behr, Ariën S. Rustenburg, Christopher I. Bayly, Kenneth Kroenlein, John D. Chodera  
> [arXiv:1506.00262](https://arxiv.org/abs/1506.00262)

## Maintainers

- Kyle A. Beauchamp (MSKCC)
- John D. Chodera (MSKCC)
- Arien Sebastian Rustenburg (MSKCC)
