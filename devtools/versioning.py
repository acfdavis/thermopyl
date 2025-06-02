import os
import subprocess

def git_version():
    """Return the git revision as a string."""
    def _minimal_ext_cmd(cmd):
        env = {k: os.environ.get(k) for k in ['SYSTEMROOT', 'PATH'] if os.environ.get(k) is not None}
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env).communicate()[0]
        return out
    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        GIT_REVISION = out.strip().decode('utf-8')
    except Exception:
        GIT_REVISION = 'Unknown'
    return GIT_REVISION

def write_version_py(VERSION, ISRELEASED, filename='thermopyl/version.py'):
    cnt = """
# THIS FILE IS GENERATED FROM THERMOPYL SETUP.PY
short_version = '%(version)s'
version = '%(version)s'
full_version = '%(full_version)s'
git_revision = '%(git_revision)s'
release = %(isrelease)s

if not release:
    version = full_version
"""
    FULLVERSION = VERSION
    if os.path.exists('.git'):
        GIT_REVISION = git_version()
    else:
        GIT_REVISION = 'Unknown'
    if not ISRELEASED:
        FULLVERSION += '.dev-' + GIT_REVISION[:7]
    with open(filename, 'w', encoding='utf-8') as a:
        a.write(cnt % {'version': VERSION,
                       'full_version': FULLVERSION,
                       'git_revision': GIT_REVISION,
                       'isrelease': str(ISRELEASED)})
