#!/usr/bin/env python3
# File: plot-v3bw-xy.py
# Author: Matt Traudt
# License: CC0
#
# Requires matplotlib; pip install matplotlib
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
import matplotlib; matplotlib.use('Agg')  # noqa; for systems without X11
from matplotlib.backends.backend_pdf import PdfPages
import pylab as plt

colors = "krbgcmy"

plt.rcParams.update({
    'axes.grid': True,
})


def get_all_values_from_fd(fd):
    values = []
    for line in fd:
        try:
            x, y = line.strip().split()
            x, y = str(x), float(y)
            assert len(x) == 40
            values.append((x, y))
        except ValueError:
            print('ignoring', line)
            continue
    return values


def common_elements(l1, l2):
    ret = set()
    for item in l1:
        if item in l2:
            ret.add(item)
    return ret


def main(args, pdf):
    plt.figure()
    data = {}
    # Read all data in
    all_labels = []
    for fname, label in args.input:
        with open(fname, 'rt') as fd:
            data[label] = {
                'label': label,
                'data': get_all_values_from_fd(fd)
            }
            all_labels.append(label)
    # Determine what relay fingerprints have data from all input sources
    common_fingerprints = None
    for label1 in data:
        fp_list1 = set([point[0] for point in data[label1]['data']])
        for label2 in data:
            if label2 == label1:
                continue
            fp_list2 = set([point[0] for point in data[label2]['data']])
            fp_list1 = common_elements(fp_list1, fp_list2)
        common_fingerprints = fp_list1
        break
    # Remove unneeded data, then
    # sort by fingerprint
    for label in data:
        points = [p for p in data[label]['data']
                  if p[0] in common_fingerprints]
        points = sorted(points, key=lambda p: p[0])
        data[label]['data'] = points
    # combine the y values for each fingerprint
    # {
    #    'fp1': {'label1': 10, 'label2': 30},
    #    'fp2': {'label1': 20, 'label2': 15},
    # }
    # and change dict data's structure to that
    new_data = {}
    for fp in common_fingerprints:
        new_data[fp] = {}
        for label in data:
            y = [p[1] for p in data[label]['data'] if p[0] == fp]
            assert len(y) == 1
            y = y[0]
            new_data[fp].update({label: y})
    data = new_data
    sort_label = all_labels[0]
    all_labels_sorted = sorted(all_labels)
    # Sort the data points such that sort_label's highest value is first.
    # Assuming sort_label is label1, then turn into this list
    # [
    #    {'label1': 20, 'label2': 15},
    #    {'label1': 10, 'label2': 30},
    # ]
    # and change dict data's structure to that
    new_data = []
    for fp in data:
        new_data.append(data[fp])
    new_data = sorted(new_data, key=lambda k: k[sort_label], reverse=True)
    data = new_data
    # Plot data
    for label_i, label in enumerate(all_labels_sorted):
        x = []
        y = []
        for point_i, point in enumerate(data):
            x.append(point_i)
            if 'sbws' in label:
                y.append(point[label] / 1000)
            else:
                y.append(point[label])
        plt.scatter(x, y, c=colors[label_i], s=args.size, label=label)
    plt.legend(loc='upper right')
    plt.xlabel(args.xlabel)
    plt.ylabel(args.ylabel)
    if args.xmin is not None:
        plt.xlim(xmin=args.xmin)
    if args.ymin is not None:
        plt.ylim(ymin=args.ymin)
    if args.xmax is not None:
        plt.xlim(xmax=args.xmax)
    if args.ymax is not None:
        plt.ylim(ymax=args.ymax)
    plt.title(args.title)
    pdf.savefig()


if __name__ == '__main__':
    d = 'Takes one or more lists of (fingerprint, bandwidth) points, 1 per '\
        'line, and plots a scatter plot of them. Data points are sorted by '\
        'the first input\'s bandwidth values, thus this script can be used '\
        'to visually determine how similar the results are from various '\
        'instances of a bandwidth scanner, or even across different '\
        'bandwidth scanning tools.'
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter, description=d)
    parser.add_argument(
        '-i', '--input', nargs=2, metavar=('FNAME', 'LABEL'),
        action='append', help='Specify a file to read values from and what '
        'to label its points in the PDF. Can be given more than once.')
    parser.add_argument('-o', '--output', default='temp.pdf')
    parser.add_argument('-x', '--xlabel', type=str, default='Relay #',
                        help='What to label the X axis in the PDF')
    parser.add_argument('-y', '--ylabel', type=str,
                        default='"Bandwidth" units (thousands)',
                        help='What to label the Y axis in the PDF')
    parser.add_argument('-t', '--title', type=str,
                        default='Correlation of various bwscanning systems',
                        help='What to title the plot in the PDF')
    parser.add_argument('--xmin', type=float, default=0)
    parser.add_argument('--ymin', type=float, default=0)
    parser.add_argument('--xmax', type=float)
    parser.add_argument('--ymax', type=float)
    parser.add_argument('-s', '--size', type=float, default=1,
                        help='Size of scatter plot points')
    args = parser.parse_args()
    with PdfPages(args.output) as pdf:
        exit(main(args, pdf))
