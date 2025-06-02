# ThermoPyL

ThermoPyL is a Python package for exploring and using the [ThermoML Archive](http://trc.nist.gov/ThermoML.html) from the [NIST TRC](http://trc.nist.gov).

[![Build Status](https://travis-ci.org/choderalab/thermopyl.png?branch=master)](https://travis-ci.org/choderalab/thermopyl)
[![Binstar Badge](https://binstar.org/choderalab/thermopyl-dev/badges/version.svg)](https://binstar.org/choderalab/thermopyl-dev)

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

## Usage

See the [ThermoML Archive](http://trc.nist.gov/ThermoML.html) for data sources.

### Example: Querying the ThermoML Archive

```python
import thermopyl
# Read ThermoML archive data into pandas dataframe
df = thermopyl.pandas_dataframe()
```

## Development

* Python >= 3.7 is required.
* To install for development: `pip install -e .[dev]`
* Tests can be run with `pytest`.

## References

See the arXiv preprint:

> Towards Automated Benchmarking of Atomistic Forcefields: Neat Liquid Densities and Static Dielectric Constants from the ThermoML Data Archive
> Kyle A. Beauchamp, Julie M. Behr, Ariën S. Rustenburg, Christopher I. Bayly, Kenneth Kroenlein, John D. Chodera
> [arXiv:1506.00262](arXiv:1506.00262)

## Maintainers

* Kyle A Beaucamp (MSKCC)
* John D. Chodera (MSKCC)
* Arien Sebastian Rustenburg (MSKCC)
