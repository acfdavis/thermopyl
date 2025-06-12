import os
import re
import tarfile
import gzip
import shutil
import requests
import json # Added import
from pathlib import Path
from urllib.parse import urlsplit, urljoin

NIST_PAGE_URL = "https://data.nist.gov/od/id/mds2-2422"
FALLBACK_ARCHIVE_URL = "https://data.nist.gov/od/ds/mds2-2422/ThermoML.v2020-09-30.tgz"
FALLBACK_VERSION = "v2020-09-30"
FALLBACK_REVISION_DATE = "2020-09-30"

DOI_URL = "https://doi.org/10.18434/MDS2-2422"

def safe_extract(tar: tarfile.TarFile, path: Path = Path(".")):
    """Safely extract tarball to prevent path traversal attacks."""
    # Convert path to string for os.path.abspath checks, as it requires strings.
    # tar.extractall can handle Path objects directly.
    path_abs_str = str(path.resolve()) 
    for member in tar.getmembers():
        # Resolve the member path to an absolute path for comparison
        member_path_abs = (path / member.name).resolve()
        if not str(member_path_abs).startswith(path_abs_str):
            raise Exception(f"Attempted Path Traversal in Tar File: {member.name}")
    tar.extractall(path)

def download_file(url, dest_path, chunk_size=8192):
    """Download a file with error handling."""
    response = requests.get(url, stream=True, timeout=(10, 300))  # (connect timeout, read timeout)
    response.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            f.write(chunk)

def resolve_archive_url():
    archive_url = None
    archive_version = None
    archive_revision_date = None
    repository_metadata = None

    # Only fetch metadata from the NERDm repository (fallback ark ID URL)
    nerdm_fallback_url = "https://data.nist.gov/od/id/ark:/88434/mds2-2422?format=nerdm"
    try:
        print(f"Attempting to fetch NERDm metadata from: {nerdm_fallback_url}")
        fallback_resp = requests.get(nerdm_fallback_url, timeout=(10, 60))
        fallback_resp.raise_for_status()
        if 'application/json' in fallback_resp.headers.get('Content-Type', ''):
            repository_metadata = fallback_resp.json()
            print("✅ Fetched NERDm repository metadata from fallback ark ID URL.")
        else:
            print("⚠️ Fallback ark ID URL did not return JSON.")
    except requests.exceptions.RequestException as fallback_err:
        print(f"⚠️ Fallback request for NERDm metadata failed: {fallback_err}")
    except json.JSONDecodeError as fallback_jexc:
        print(f"⚠️ Failed to parse fallback NERDm metadata: {fallback_jexc}")

    # --- NERDm metadata parsing and override logic ---
    if repository_metadata:
        import datetime
        nerdm_version = repository_metadata.get('version')
        nerdm_issued = repository_metadata.get('issued')
        nerdm_modified = repository_metadata.get('modified')
        nerdm_title = repository_metadata.get('title')
        retrieved_date = datetime.datetime.utcnow().isoformat() + 'Z'
        repository_metadata['retrieved'] = retrieved_date
        print(f"NERDm metadata found:")
        print(f"  title: {nerdm_title}")
        print(f"  version: {nerdm_version}")
        print(f"  issued: {nerdm_issued}")
        print(f"  modified: {nerdm_modified}")
        print(f"  retrieved: {retrieved_date}")
        # Prefer NERDm version and revision date if available
        if nerdm_version:
            archive_version = nerdm_version
        # Use 'modified' as revision date if available, else 'issued'
        if nerdm_modified:
            archive_revision_date = nerdm_modified[:10]  # ISO date, just YYYY-MM-DD
        elif nerdm_issued:
            archive_revision_date = nerdm_issued[:10]
        # Try to get the archive URL from the NERDm metadata if present
        # (If not, fallback to the known static URL)
        dist = repository_metadata.get('distribution', [])
        if isinstance(dist, list):
            for d in dist:
                if isinstance(d, dict) and d.get('downloadURL', '').endswith('.tgz'):
                    archive_url = d['downloadURL']
                    break
        elif isinstance(dist, dict) and dist.get('downloadURL', '').endswith('.tgz'):
            archive_url = dist['downloadURL']
    # Fallback to known static URL if not found in NERDm
    if not archive_url:
        archive_url = FALLBACK_ARCHIVE_URL
    if not archive_version:
        archive_version = FALLBACK_VERSION
    if not archive_revision_date:
        archive_revision_date = FALLBACK_REVISION_DATE

    return archive_url, archive_version, archive_revision_date, repository_metadata

def update_archive(thermoml_path=None):
    if thermoml_path is None:
        thermoml_path = os.environ.get("THERMOML_PATH", Path.home() / ".thermoml")

    thermoml_path = Path(thermoml_path)
    thermoml_path.mkdir(parents=True, exist_ok=True)

    archive_url_env = os.environ.get("THERMOML_ARCHIVE_URL")
    actual_archive_url = None
    archive_version = None
    archive_revision_date = None
    repository_metadata = None # Initialize

    # Check cache before downloading (moved from resolve_archive_url)
    archive_info_file = thermoml_path / "archive_info.json"
    cache_dir = thermoml_path
    import time
    if archive_info_file.exists():
        try:
            mtime = archive_info_file.stat().st_mtime
            xml_files = list(cache_dir.rglob("*.xml"))
            print(f"[DEBUG] Found {len(xml_files)} XML files in cache dir {cache_dir}")
            if (time.time() - mtime) < 24*3600 and xml_files:
                with open(archive_info_file, 'r') as jf:
                    data = json.load(jf)
                if all(k in data for k in ("archiveURL", "version", "revisionDate")):
                    print(f"Using cached archive info and XML files from {cache_dir}")
                    final_url = data.get("archiveURL", "unknown")
                    final_version = data.get("version", "unknown")
                    final_revision_date = data.get("revisionDate", "unknown")
                    metadata_status = "saved to archive_info.json" if data.get("repositoryMetadata") else "not found during fetch, see archive_info.json"
                    print(f"\n✅ Update complete.")
                    print(f"🗂 Archive path: {thermoml_path}")
                    print(f"🔗 Archive URL Used: {final_url}")
                    print(f"📜 Archive Version: {final_version}")
                    print(f"🗓️ Archive Revision Date: {final_revision_date}")
                    print(f"📄 Repository Metadata: {metadata_status}")
                    print(f"📄 XML files available: {len(xml_files)}")
                    print("💡 Tip: You can override the archive URL, version, and revision date with environment variables:")
                    print("   THERMOML_ARCHIVE_URL, THERMOML_ARCHIVE_VERSION, THERMOML_ARCHIVE_REVISION_DATE")
                    return  # Skip download and extraction
            else:
                print(f"[DEBUG] Cache not valid: archive_info.json mtime: {mtime}, xml_files: {len(xml_files)}")
        except Exception as e:
            print(f"Cache read error: {e}. Will fetch new data.")
    if archive_url_env:
        actual_archive_url = archive_url_env
        archive_version = os.environ.get("THERMOML_ARCHIVE_VERSION", "unknown (manual URL override)")
        archive_revision_date = os.environ.get("THERMOML_ARCHIVE_REVISION_DATE", "unknown (manual URL override)")
        # For manual URL, we don't fetch repository_metadata unless a specific URL for it is also provided (future enhancement)
        print(f"Using manually specified archive URL: {actual_archive_url}")
        if archive_version != "unknown (manual URL override)":
            print(f"Using manually specified archive version: {archive_version}")
        if archive_revision_date != "unknown (manual URL override)":
            print(f"Using manually specified archive revision date: {archive_revision_date}")
    else:
        actual_archive_url, archive_version, archive_revision_date, repository_metadata = resolve_archive_url()

    combined_tgz = thermoml_path / "ThermoML_all.tgz"
    # Store version and date info in a JSON file
    archive_info_file = thermoml_path / "archive_info.json"

    try:
        print(f"Downloading combined archive: {actual_archive_url}")
        download_file(actual_archive_url, combined_tgz)

        if not combined_tgz.exists() or combined_tgz.stat().st_size == 0:
            raise FileNotFoundError("Downloaded archive is missing or empty.")

        # Check for GZIP magic bytes
        with open(combined_tgz, 'rb') as f:
            magic_bytes = f.read(2)
            if magic_bytes != b'\x1f\x8b':
                print("Downloaded file does not appear to be a GZIP archive. Attempting to extract anyway.")
                # Potentially handle non-gzipped tar or other formats if necessary, or just let tarfile try

        print(f"Extracting {combined_tgz} to {thermoml_path}")
        with tarfile.open(combined_tgz, "r:gz") as tar:
            safe_extract(tar, thermoml_path)
        print("Extraction complete.")
        # Remove the tarball after extraction to save space
        try:
            combined_tgz.unlink()
            print(f"Removed archive file {combined_tgz} after extraction.")
        except Exception as e:
            print(f"Warning: Could not remove archive file {combined_tgz}: {e}")

        # Save archive info after successful download and extraction
        archive_info_data = {
            "archiveURL": actual_archive_url,
            "version": archive_version,
            "revisionDate": archive_revision_date,
            "repositoryMetadata": repository_metadata # This could be None
        }
        with open(archive_info_file, 'w') as jf:
            json.dump(archive_info_data, jf, indent=4)
        print(f"Archive information (including metadata if found) saved to {archive_info_file}")

    except FileNotFoundError as e:
        print(f"File not found during download/extraction: {e}")
        print("Skipping bulk download. Will proceed with RSS feeds if available.")
    except tarfile.ReadError as e:
        print(f"Error reading tar file (it might be corrupted or not a tar.gz file): {e}")
        print("Please check the downloaded file or the source URL.")
        print("Skipping bulk download. Will proceed with RSS feeds if available.")
    except requests.exceptions.RequestException as e:
        print(f"HTTP error during download: {e}")
        print("Skipping bulk download. Will proceed with RSS feeds if available.")
    except Exception as e:
        print(f"Failed bulk download or extraction: {e}") # Catch-all for other issues
        print("Skipping bulk download. Will proceed with RSS feeds if available.")


    # Summary
    xml_files = list(thermoml_path.glob("**/*.xml"))
    print(f"\n✅ Update complete.")
    print(f"🗂 Archive path: {thermoml_path}")
    
    final_url = "unknown"
    final_version = "unknown"
    final_revision_date = "unknown"
    metadata_status = "not found or not saved"

    if archive_info_file.exists():
        try:
            with open(archive_info_file, 'r') as jf:
                data = json.load(jf)
                final_url = data.get("archiveURL", "unknown")
                final_version = data.get("version", "unknown")
                final_revision_date = data.get("revisionDate", "unknown")
                if data.get("repositoryMetadata"):
                    metadata_status = f"saved to {archive_info_file}"
                else:
                    metadata_status = f"not found during fetch, see {archive_info_file}"
        except Exception as e:
            print(f"Could not read archive info file {archive_info_file}: {e}")
            metadata_status = f"error reading {archive_info_file}"

    if archive_url_env:
        print(f"📦 Archive Source: Manually specified URL ({actual_archive_url})")
    else:
        print(f"📦 Archive Source: NIST Page ({NIST_PAGE_URL}) or fallback")
    
    print(f"🔗 Archive URL Used: {final_url}")
    print(f"📜 Archive Version: {final_version}")
    print(f"🗓️ Archive Revision Date: {final_revision_date}")
    print(f"📄 Repository Metadata: {metadata_status}")
    
    print(f"📄 XML files available: {len(xml_files)}")
    print("💡 Tip: You can override the archive URL, version, and revision date with environment variables:")
    print("   THERMOML_ARCHIVE_URL, THERMOML_ARCHIVE_VERSION, THERMOML_ARCHIVE_REVISION_DATE")

if __name__ == "__main__":
    update_archive()
