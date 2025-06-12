````markdown
# ThermoPyL

ThermoPyL is a modern Python toolkit for downloading, validating, and structuring [ThermoML](https://www.nist.gov/srd/nist-standard-reference-database-229) data from NIST’s ThermoML Archive. Designed for integration with machine learning workflows in materials science, it enables reproducible and automated extraction of thermophysical property data into long-format `pandas` DataFrames.

This refactored version of ThermoPyL is a ground-up reimplementation inspired by the original [choderalab/thermopyl](https://github.com/choderalab/thermopyl). All components have been rewritten for modern Python environments, robust schema validation, and downstream compatibility with tools like [Matminer](https://hackingmaterials.lbl.gov/matminer/) and [Citrine](https://citrine.io/).

⚖️ ThermoPyL adheres to the FAIR data principles: making ThermoML data Findable, Accessible, Interoperable, and Reusable through automated ingestion, validation, and reformatting.

---

## 🔧 Features

- Robust update system for mirroring NIST ThermoML data (RSS and archive-based)
- Validates XML files against NIST ThermoML schema (XSD)
- Converts ThermoML datasets into clean, analysis-ready DataFrames
- Resilient download logic with DOI resolution and override support
- Modular, extensible architecture using `dataclasses` and `pathlib`
- Ready for integration in machine learning pipelines

---

## 📦 Installation

### Using `pip`
```bash
pip install thermopyl
````

### From source

```bash
git clone https://github.com/YOURNAME/thermopyl.git
cd thermopyl
pip install .
```

---

## 🚀 Usage

### Update the ThermoML Archive

This downloads the latest XML files into `~/.thermoml`:

```bash
python -m thermopyl.scripts.update_archive
```

To specify a particular archive version (e.g., for reproducibility):

```bash
export THERMOML_ARCHIVE_URL=https://data.nist.gov/od/id/mds2-2422/ThermoML.v2024-05-01.tgz
python -m thermopyl.scripts.update_archive
```

---

### Python API

```python
from thermopyl.core.parser import parse_thermoml_dir
df = parse_thermoml_dir("~/path/to/thermoml")
```

---

## 🧪 Development

* Python ≥ 3.8
* Install dev dependencies:

  ```bash
  pip install -e .[dev]
  ```
* Run tests:

  ```bash
  pytest
  ```

---

## 📂 Project Layout

```
thermopyl/
├── core/           # Core update/download/parse logic
├── NIST_ThermoML/  # Constants, schema, and feeds
├── scripts/        # CLI wrappers
├── data/           # Local schema files (e.g., ThermoML.xsd)
└── tests/          # Unit tests
```

---

## 📚 Citation & Acknowledgment

This work builds on the structure and ideas introduced in:

> Beauchamp et al., "Towards Automated Benchmarking of Atomistic Forcefields"
> [arXiv:1506.00262](https://arxiv.org/abs/1506.00262)

Please cite the original ThermoML reference database and/or this repository when using ThermoPyL in publications.

---

## 👥 Maintainers

* Angela Davis
* With appreciation to the original authors at Chodera Lab (MSKCC)

```
