import argparse
import os
from os.path import join as opj
from subprocess import call
from pprint import pprint

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='''\
xrdcp from someplace with subdirectories to someplace with the same subdirectories on root://eoslhcb.cern.ch.
MAKE SURE YOUR DESTINATION DIRECTORIES EXIST.
NO OVERWRITE PREVENTION ENABLED.
Make sure to `kinit USERNAME@CERN.CH` first.
'''
)
parser.add_argument('indir')
parser.add_argument('outdir')
parser.add_argument('--filename', default='000000.AllStreams.dst')
args = parser.parse_args()
indir    = args.indir
outdir   = args.outdir
filename = args.filename

print '===================================================='
print 'copying files'
print '===================================================='

dir_without_file = []
for d in os.listdir(indir):
    if not os.path.isfile(opj(indir, d, filename)):
        dir_without_file.append(d)
        continue
    call(["xrdcp " + opj(indir, d, filename) + ' root://eoslhcb.cern.ch/' + opj(outdir, d, filename)], shell=True)
if dir_without_file:
    print '===================================================='
    print filename, 'not found in:'
    pprint(dir_without_file)
print '===================================================='
print 'done'
print '===================================================='
