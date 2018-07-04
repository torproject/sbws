from tempfile import TemporaryFile
import subprocess
import os


def test_simple_init(tmpdir):
    # out = None
    err = None
    with TemporaryFile('w+t') as stdout, TemporaryFile('w+t') as stderr:
        retcode = subprocess.call(
            'sbws -d {} --log-level debug init'.format(tmpdir).split(),
            stdout=stdout, stderr=stderr)
        stdout.seek(0, 0)
        stderr.seek(0, 0)
        # out = stdout.read()
        err = stderr.read()
    assert retcode == 0
    assert len(err) == 0
    conf_fname = os.path.join(str(tmpdir), 'config.ini')
    assert os.path.exists(conf_fname)
    with open(conf_fname, 'rt') as fd:
        assert len(fd.read()) > 0
