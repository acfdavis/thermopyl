import os
import tarfile
import feedparser
from .utils import make_path
import urllib.request
import urllib.parse

THERMOML_FEEDS = {
    "jced": "http://trc.nist.gov/RSS/jced.xml",
    "jct": "http://trc.nist.gov/RSS/jct.xml",
    "fpe": "http://trc.nist.gov/RSS/fpe.xml",
    "tca": "http://trc.nist.gov/RSS/tca.xml",
    "ijt": "http://trc.nist.gov/RSS/ijt.xml"
}

THERMOML_TARBALLS = {
    "jced": "http://trc.nist.gov/ThermoML/JCED.tgz",
    "jct": "http://trc.nist.gov/ThermoML/JCT.tgz",
    "fpe": "http://trc.nist.gov/ThermoML/FPE.tgz",
    "tca": "http://trc.nist.gov/ThermoML/TCA.tgz",
    "ijt": "http://trc.nist.gov/ThermoML/IJT.tgz"
}

def update_archive(thermoml_path=None):
    """Use RSS feeds to find and download ThermoML tar files
    from the ThermoML archive, then download any missing entries by enumerating the
    RSS feeds. The output will be a flat directory of XML files in `thermoml_path`
    """
    if thermoml_path is None:
        # Try to obtain the path to the local ThermoML Archive mirror from an environment variable.
        thermoml_path = os.environ.get("THERMOML_PATH")
        if thermoml_path is None:
            # Use default path of ~/.thermoml (cross-platform)
            thermoml_path = os.path.join(os.path.expanduser("~"), '.thermoml')

    os.makedirs(thermoml_path, exist_ok=True)

    for key, url in THERMOML_TARBALLS.items():
        print(f"Downloading {url}")
        local_filename = f"{key}.tgz"
        urllib.request.urlretrieve(url, local_filename)
        with tarfile.open(local_filename) as tarball:
            tarball.extractall(thermoml_path)
        os.remove(local_filename)

    # Update local repository according to feeds.
    for key, url in THERMOML_FEEDS.items():
        print(f"Fetching RSS {url}")
        feed = feedparser.parse(url)
        for entry in feed["entries"]:
            link = str(entry["link"])
            base_filename = urllib.parse.urlsplit(link).path
            base_filename = os.path.split(base_filename)[-1]  # Flattens the directory structure
            filename = os.path.join(thermoml_path, base_filename)
            make_path(filename)
            if os.path.exists(filename):
                print(f"Already downloaded {filename} from {link}")
            else:
                print(f"Fetching {filename} from {link}")
                urllib.request.urlretrieve(link, filename)
