import os
import tempfile
import subprocess
import thermopyl.version
import pkg_resources


BUCKET_NAME = 'thermopyl.org'
PREFIX = 'latest' if not getattr(thermopyl.version, 'release', False) else getattr(thermopyl.version, 'short_version', 'latest')

# Check for s3cmd using pkg_resources (Python 3 compatible)
if not any(d.project_name.lower() == 's3cmd' for d in pkg_resources.working_set):
    raise ImportError('The s3cmd package is required. Try: pip install s3cmd')

# The secret key is available as a secure environment variable
# on CI to push the build documentation to Amazon S3.
with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8') as f:
    f.write('[default]\n')
    f.write(f"access_key = {os.environ.get('AWS_ACCESS_KEY_ID', '')}\n")
    f.write(f"secret_key = {os.environ.get('AWS_SECRET_ACCESS_KEY', '')}\n")
    f.flush()

    # Sync docs/_build/ to S3
    cmd = [
        's3cmd', '--guess-mime-type', '--config', f.name,
        'sync', 'docs/_build/', f's3://{BUCKET_NAME}/{PREFIX}/'
    ]
    subprocess.check_call(cmd)

    # Sync index file
    cmd = [
        's3cmd', '--guess-mime-type', '--config', f.name,
        'sync', 'devtools/ci/index.html', f's3://{BUCKET_NAME}/'
    ]
    subprocess.check_call(cmd)

# Clean up the temporary file
os.remove(f.name)

