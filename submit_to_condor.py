from shutil import move, rmtree
from subprocess import call
import os
from os.path import join as opj, abspath
from time import sleep
import progressbar
from imp import load_source
from moveFiles import moveFiles, runMoveFilesContinuously, parser  # some args overridden--see below; note that store_sys is interpreted as where files begin and end in this script; run_sys is where they are moved to run with run_stages.py

# -- make adjustments to parser -- #
parser.description = '''\
Run run_stages.py using the specified configfile by transferring files from store_sys to run_sys, running, then moving them back.
Arguments specific to this script are in the 'submit_to_condor options' group.
This script uses a number of arguments from moveFiles.py (with some changes to default values; use --help), but it overrides some of them.
(minallowed, maxallowed, justdata, lessthan, copyfrom, waittilnotrunning are overriden.
lessthan is overridden for initial movement and for the final submission chunk (set to 0).
copyfrom is only overriden for the move back (set to None) (therefore, specifying copyfrom copies from store_sys to run_sys but then moves them from store_sys to run_sys under signal_name).
waittilnotrunning is only overridden for the initial movement (though it doesn't actually matter since justdata gets used anyway).)
'''
parser.set_defaults(interval=240, maxwaittime=0, waitcheckdelay=60, lessthan=50, waittostart=True)
submit_to_condorgroup = parser.add_argument_group('submit_to_condor options')
submit_to_condorgroup.add_argument('configfile', type=abspath,
                                   help='the configfile you want run_stages to use')
submit_to_condorgroup.add_argument('--chunks_of', type=int, default=1000,
                                   help='how many jobs to move and submit at a time')
submit_to_condorgroup.add_argument('--donotmovefrom', dest='transfilesfrom', action='store_false',
                                   help='flag to prevent files from being moved from store_sys back to run_sys (default is misleading)')
submit_to_condorgroup.add_argument('--donotmoveto', dest='transfilesto', action='store_false',
                                   help='flag to prevent files from being moved from run_sys to store_sys (default is misleading)')
submit_to_condorgroup.add_argument('--setlowest', type=int, default=None,
                                   help='manually set lowest (inclusive) job number instead of letting the script find it')
submit_to_condorgroup.add_argument('--sethighest', type=int, default=None,
                                   help='manually set highest (exclusive) job number instead of letting the script find it')

# -- evaluate args -- #
allargs = parser.parse_known_args()  # unknown args are assumed to be handled by the configfile
args = allargs[0]
conf = load_source('conf', args.configfile)
try:
    configparser = getattr(conf, 'parser')
    args_for_configfile = ' '.join(allargs[1])  # arguments unknown to this script as a string to pass run_stages.py
except AttributeError:
    configparser = None
    args_for_configfile = ''

startpath = '{start_sys}/mwilkins/data/{signal_name}/'.format(start_sys=args.store_sys if args.transfilesfrom else args.run_sys, signal_name=args.signal_name if args.copyfrom is None else args.copyfrom)
if all([args.setlowest, args.sethighest]):
    intlistdirs = range(args.setlowest, args.sethighest)
else:
    intlistdirs = [int(x) for x in os.listdir(startpath) if os.path.isdir(opj(startpath, x))]
if args.setlowest:
    lowest = args.setlowest
    inlistdirs = [x for x in intlistdirs if x >= lowest]
else:
    lowest = int(min(intlistdirs))
if args.sethighest:
    highest = args.sethighest
    inlistdirs = [x for x in intlistdirs if x < highest]
else:
    highest = int(max(intlistdirs))
number = len(intlistdirs)
looprange = xrange(lowest, highest, args.chunks_of)


# -- define useful functions -- #
def incfilename(filename, i_start=0, i=None):
    '''chooses a name for a file by appending numbers incrementally (from i_start) to filename
    '''
    from os.path import exists, splitext
    if exists(filename):
        basename = splitext(filename)[0]
        suffname = splitext(filename)[1]
        newname = basename + str(i_start) + suffname
        if exists(newname):
            return incfilename(filename, i_start + 1)
        else:
            return newname
    else:
        return filename


# -- submit jobs in a loop -- #
for minnum in looprange:
    maxnum = minnum + args.chunks_of
    print 'lowest = {}, highest = {}, number = {}'.format(lowest, highest, number)
    print '----------------on files in range [{}, {})-----------------'.format(minnum, maxnum)
    
    if args.transfilesfrom:
        print 'moving files from {} to {}...'.format(args.store_sys, args.run_sys)
        succeeded = moveFiles(store_sys=args.run_sys, run_sys=args.store_sys, minallowed=minnum, maxallowed=maxnum, justdata=True, waittilnotrunning=False, signal_name=args.signal_name, user=args.user, lessthan=args.lessthan, copyfrom=args.copyfrom)  # returns True when done
        if not succeeded:
            raise Exception('problem with moveFiles. [{}, {})'.format(minnum, maxnum))
    
    print 'writing condor_submit file...'
    submissionfilename = incfilename('MCGen.submit')
    with open(submissionfilename, 'w') as f:
        f.write('Executable = run_stages.py\n')
        f.write('ConfigFile = {}\n'.format(args.configfile))
        f.write('StartRun   = {}\n'.format(minnum))
        f.write('RunNumber  = $$([$(StartRun)+$(process)])\n')
        f.write('Arguments  = $(ConfigFile) --RUN_NUMBER $(RunNumber) --PRECLEANED --SOME_MISSING {}\n'.format(args_for_configfile))
        f.write('Queue {}\n'.format(args.chunks_of))
    
    print 'submitting jobs...'
    succeeded = 0 == call(['condor_submit {}'.format(submissionfilename)], shell=True)  # returns 0 if successful
    if succeeded:
        os.remove(submissionfilename)
    else:
        raise Exception('failed to submit. [{}, {})'.format(minnum, maxnum))
    
    if args.transfilesto:
        print 'moving files back...'
        lt = 0 if minnum == looprange[-1] else args.lessthan
        succeeded = runMoveFilesContinuously(lessthan=lt, justdata=False, minallowed=None, maxallowed=None, copyfrom=None, signal_name=args.signal_name, run_sys=args.run_sys, store_sys=args.store_sys, user=args.user, interval=args.interval, maxwaittime=args.maxwaittime, waittostart=args.waittostart, waitcheckdelay=args.waitcheckdelay, waittilnotrunning=args.waittilnotrunning, )  # returns True when done
        if not succeeded:
            raise Exception('problem with runMoveFilesContinuously. [{}, {})'.format(minnum, maxnum))
print '----------------done-----------------'
