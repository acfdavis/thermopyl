# Temporarily change directory to $HOME to install software
pushd .
cd $HOME

# Install Miniconda (Python 3 compatible, modern URL)
MINICONDA=Miniconda3-latest-Linux-x86_64.sh
MINICONDA_HOME=$HOME/miniconda
wget -q https://repo.anaconda.com/miniconda/$MINICONDA
bash $MINICONDA -b -p $MINICONDA_HOME

# Configure miniconda
export PIP_ARGS="-U"
export PATH=$MINICONDA_HOME/bin:$PATH
conda update --yes conda
conda install --yes conda-build jinja2 anaconda-client pip

# Restore original directory
popd
