# Thermopyl Conda Recipe

This folder contains the recipe for building the current development package into a conda binary.

## CI/CD and Installation

- On CI (e.g., GitHub Actions or Travis CI), the package is built as a conda package, installed, tested, and if successful, uploaded to Anaconda Cloud (formerly binstar).
- Documentation can optionally be pushed to AWS S3.

## Authentication

The Anaconda (binstar) auth token is stored as an encrypted environment variable. To generate and encrypt a new token for CI:

```sh
gem install travis
travis encrypt BINSTAR_TOKEN=$(anaconda auth -n thermopyl-travis -o choderalab --max-age 22896000 -c --scopes api:write)
```

The final command prints a line (containing 'secure') for inclusion in your `.travis.yml` or CI secrets.

## Notes

- This recipe and workflow are fully compatible with Python 3 and pip-based environments.
- All dependencies and scripts have been modernized for best practices and repository consistency.
