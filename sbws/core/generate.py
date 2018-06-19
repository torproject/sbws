from sbws.globals import (fail_hard, is_initted, SCALE_CONSTANT)
from sbws.lib.v3bwfile import V3BWFile
from sbws.lib.resultdump import load_recent_results_in_datadir
from argparse import ArgumentDefaultsHelpFormatter
import os
import logging
from sbws.util.filelock import DirectoryLock
from sbws.util.timestamp import now_fname

log = logging.getLogger(__name__)


def gen_parser(sub):
    d = 'Generate a v3bw file based on recent results. A v3bw file is the '\
        'file Tor directory authorities want to read and base their '\
        'bandwidth votes on.'
    p = sub.add_parser('generate', description=d,
                       formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('--output', default=None, type=str,
                   help='If specified, write the v3bw here instead of what is'
                   'specified in the configuration')
    # The reason for --scale-constant defaulting to 7500 is because at one
    # time, torflow happened to generate output that averaged to 7500 bw units
    # per relay. We wanted the ability to try to be like torflow. See
    # https://lists.torproject.org/pipermail/tor-dev/2018-March/013049.html
    p.add_argument('--scale-constant', default=SCALE_CONSTANT, type=int,
                   help='When scaling bw weights, scale them using this const '
                   'multiplied by the number of measured relays')
    p.add_argument('--scale', action='store_true',
                   help='If specified, do not use bandwidth values as they '
                   'are, but scale them such that we have a budget of '
                   'scale_constant * num_measured_relays = bandwidth to give '
                   'out, and we do so proportionally')


def _write_v3bw_file(v3bwfile, output):
    log.info('Writing v3bw file to %s', output)
    out_dir = os.path.dirname(output)
    out_link = os.path.join(out_dir, 'latest.v3bw')
    if os.path.exists(out_link):
        log.debug('Deleting existing symlink before creating a new one.')
        os.remove(out_link)
    # to keep test_generate.py working
    if output != '/dev/stdout':
        with DirectoryLock(out_dir):
            with open(output, 'wt') as fd:
                fd.write(str(v3bwfile.header))
                for line in v3bwfile.bw_lines:
                    fd.write(str(line))
            output_basename = os.path.basename(output)
            log.debug('Creating symlink from {} to {}.'
                      .format(output_basename, out_link))
            os.symlink(output_basename, out_link)
    else:
        with open(output, 'wt') as fd:
            fd.write(str(v3bwfile.header))
            for line in v3bwfile.bw_lines:
                fd.write(str(line))


def main(args, conf):
    if not is_initted(args.directory):
        fail_hard('Sbws isn\'t initialized.  Try sbws init')

    os.makedirs(conf['paths']['v3bw_dname'], exist_ok=True)

    datadir = conf['paths']['datadir']
    if not os.path.isdir(datadir):
        fail_hard('%s does not exist', datadir)
    if args.scale_constant < 1:
        fail_hard('--scale-constant must be positive')

    fresh_days = conf.getint('general', 'data_period')
    reset_bw_ipv4_changes = conf.getboolean('general', 'reset_bw_ipv4_changes')
    reset_bw_ipv6_changes = conf.getboolean('general', 'reset_bw_ipv6_changes')
    results = load_recent_results_in_datadir(
        fresh_days, datadir, success_only=True,
        on_changed_ipv4=reset_bw_ipv4_changes,
        on_changed_ipv6=reset_bw_ipv6_changes)
    if len(results) < 1:
        log.warning('No recent results, so not generating anything. (Have you '
                    'ran sbws scanner recently?)')
        return
    bw_file = V3BWFile.from_arg_results(args, conf, results)
    output = args.output or conf['paths']['v3bw_fname'].format(now_fname())
    _write_v3bw_file(bw_file, output)
    log.info('Mean bandwidth per line: %f "KiB"', bw_file.avg_bw)
