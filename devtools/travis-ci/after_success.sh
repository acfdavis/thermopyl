#!/bin/bash
# Must be invoked with $PACKAGENAME

# Print PR and branch info
echo $TRAVIS_PULL_REQUEST $TRAVIS_BRANCH
PUSH_DOCS_TO_S3=false

# Only deploy on master branch and not pull requests
if [ "$TRAVIS_PULL_REQUEST" != "false" ]; then
    echo "This is a pull request. No deployment will be done."; exit 0
fi

if [ "$TRAVIS_BRANCH" != "master" ]; then
    echo "No deployment on BRANCH='$TRAVIS_BRANCH'"; exit 0
fi

# Deploy to Anaconda (binstar is now anaconda-client)
conda install --yes anaconda-client jinja2
anaconda -t $BINSTAR_TOKEN upload --force -u choderalab -p ${PACKAGENAME}-dev $HOME/miniconda/conda-bld/*/${PACKAGENAME}-dev-*.tar.bz2

if [ "$PUSH_DOCS_TO_S3" = true ]; then
    # Create the docs and push them to S3
    conda install --yes pip
    conda config --add channels https://conda.anaconda.org/omnia
    conda install --yes $(conda build devtools/conda-recipe --output)
    pip install numpydoc s3cmd msmb_theme
    conda install --yes $(xargs < docs/requirements.txt)

    conda list -e

    (cd docs && make html && cd -)
    ls -lt docs/_build
    pwd
    python devtools/travis-ci/push-docs-to-s3.py
fi
