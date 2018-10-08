from shutil import move, rmtree
from subprocess import call
import os
from os.path import join as opj
from time import sleep
from imp import load_source
from utils import makelohilist, incfilename
from moveFiles import moveFiles, runMoveFilesContinuously, parser  # some args overridden--see below

print '\n'
print "           _               _ _      _                              _                         "
print " ___ _   _| |__  _ __ ___ (_) |_   | |_ ___     ___ ___  _ __   __| | ___   _ __ _ __  _   _ "
print "/ __| | | | '_ \| '_ ` _ \| | __|  | __/ _ \   / __/ _ \| '_ \ / _` |/ _ \ | '__| '_ \| | | |"
print "\__ \ |_| | |_) | | | | | | | |_   | || (_) | | (_| (_) | | | | (_| | (_) || | _| |_) | |_| |"
print "|___/\__,_|_.__/|_| |_| |_|_|\__|___\__\___/___\___\___/|_| |_|\__,_|\___/ |_|(_) .__/ \__, |"
print "                               |_____|    |_____|                               |_|    |___/ "
print '\n'

# -- make adjustments to parser -- #
parser.description = '''\
Run run_stages.py using the specified configfile by transferring files from store_sys to run_sys, running, then moving them back.
Arguments specific to this script are in the 'submit_to_condor options' group.
Unknown arguments are assumed to be intended for configfile.
This script uses a number of arguments from moveFiles.py (with some changes to default values; use --help), but it overrides some of them:
minallowed, maxallowed, justdata, lessthan, copyfrom, waittilnotrunning are overriden.
lessthan is overridden for all movement from store_sys and for the final chunk of movement to store_sys (set to 0).
copyfrom is only overriden for the move back (set to None)
(therefore, specifying copyfrom copies from store_sys to run_sys but then moves them from store_sys to run_sys under signal_name).
waittilnotrunning is only overridden for the initial movement (though it doesn't actually matter since justdata gets used anyway).
'''
parser.set_defaults(interval=240, maxwaittime=0, lessthan=50, waittostart=60)
submit_to_condorgroup = parser.add_argument_group('submit_to_condor options')
submit_to_condorgroup.add_argument('configfile', type=os.path.abspath,
                                   help='the configfile you want run_stages to use')
submit_to_condorgroup.add_argument('--setlohi', nargs=2, type=int, default=None, metavar=('LO', 'HI'),
                                   help='set the lowest (inclusive) and highest (exclusive) job numbers;'
                                   ' if set, these limits also apply to run numbers found by runfromstorage')
submit_to_condorgroup.add_argument('--runfromstorage', action='store_true',
                                   help='move data files from store_sys to run_sys, then submit the moved run numbers (in chunks);'
                                   ' if setlohi used, will ignore run numbers not in-range.'
                                   ' (Useful for running later stages of a multi-stage job; make sure you set the correct stages to run.)')
submit_to_condorgroup.add_argument('--chunks_of', type=int, default=20,
                                   help='how many jobs to move and submit at a time')
submit_to_condorgroup.add_argument('--donotstore', action='store_true',
                                   help='flag to prevent files from being moved from run_sys to store_sys')
submit_to_condorgroup.add_argument('--test', action='store_true',
                                   help='use error script in condor submission and preserve submission script')

# -- evaluate args -- #
allargs = parser.parse_known_args()  # unknown args are assumed to be handled by the configfile
args = allargs[0]
if not args.runfromstorage and args.setlohi is None:
    raise parser.error('must runfromstorage or setlohi (or both)')

# handle unknown arguments
args_for_configfile = ' '.join(allargs[1])  # arguments unknown to this script as a string to pass run_stages.py
conf = load_source('conf', args.configfile)
try:  # if the configfile has a parser, pass arguments to it
    configparser = getattr(conf, 'parser')
except AttributeError:  # else don't
    configparser = None
    if args_for_configfile != '':
        raise parser.error('Unknown arguments passed and configfile has no parser! Unknown arguments: {}'.format(args_for_configfile))

# useful definitions
cmfrom = args.copyfrom if args.movefrom is None else args.movefrom  # will be None or a string; same logic as used in moveFiles

# parse run numbers
if args.runfromstorage:
    startpath = '{start_sys}/{user}/data/{signal_name}/'.format(start_sys=args.store_sys, user=args.user, signal_name=args.signal_name if cmfrom is None else cmfrom)
    intlistdirs = [int(x) for x in os.listdir(startpath) if os.path.isdir(opj(startpath, x))]
    if args.setlohi is not None:
        intlistdirs = [x for x in intlistdirs if args.setlohi[0] <= x < args.setlohi[1]]
else:
    intlistdirs = range(args.setlohi[0], args.setlohi[1])
lowest = int(min(intlistdirs))
highest = int(max(intlistdirs))
number = len(intlistdirs)
submissionlist = makelohilist(intlistdirs, args.chunks_of)

# -- submit jobs in a loop -- #
print '----------------submit "{}" from configfile "{}" to Condor-----------------'.format(args.signal_name, args.configfile)
for minnum, maxnum in submissionlist:
    print 'lowest (inclusive) = {}, highest (inclusive) = {}, number = {}'.format(lowest, highest, number)
    print '----------------on files in range [{}, {})-----------------'.format(minnum, maxnum)
    
    if args.runfromstorage:
        # move files to run_sys
        print 'moving files from store_sys to run_sys...'
        succeeded = moveFiles(store_sys=args.run_sys, run_sys=args.store_sys, minallowed=minnum, maxallowed=maxnum, justdata=True, lessthan=0, waittilnotrunning=False,
                              signal_name=args.signal_name, user=args.user, copyfrom=args.copyfrom)  # returns True when done
        if not succeeded:
            raise Exception('problem with moveFiles. [{}, {})'.format(minnum, maxnum))
    
    # create condor submission file
    print 'writing condor_submit file...'
    submissionfilename = incfilename('CondorSubmission_{}.submit'.format(args.signal_name))
    Nqueue = maxnum - minnum
    with open(submissionfilename, 'w') as f:
        f.write('Executable = run_stages.py\n')
        f.write('ConfigFile = {}\n'.format(args.configfile))
        f.write('StartRun   = {}\n'.format(minnum))
        f.write('RunNumber  = $$([$(StartRun)+$(process)])\n')
        f.write('Arguments  = $(ConfigFile) --SIGNAL_NAME {} --RUN_NUMBER $(RunNumber) --SOME_MISSING {}\n'.format(args.signal_name, args_for_configfile))
        if args.test:
            f.write('Error      = error_{}_{}_$(RunNumber)_$(cluster)_$(process).log\n'.format(submissionfilename, args.signal_name))
        f.write('Queue {}\n'.format(Nqueue))
    
    # submit jobs
    succeeded = 0 == call(['condor_submit {}'.format(submissionfilename)], shell=True)  # returns 0 if successful
    if succeeded:
        if not args.test:
            os.remove(submissionfilename)
    else:
        raise Exception('failed to submit. [{}, {})'.format(minnum, maxnum))
    
    if not args.donotstore:
        # move files to store_sys
        print 'moving files from run_sys to store_sys...'
        lt = 0 if minnum is submissionlist[-1][0] else args.lessthan
        succeeded = runMoveFilesContinuously(lessthan=lt, justdata=False, minallowed=None, maxallowed=None, copyfrom=None, signal_name=args.signal_name, run_sys=args.run_sys,
                                             store_sys=args.store_sys, user=args.user, interval=args.interval, maxwaittime=args.maxwaittime, waittostart=args.waittostart,
                                             waittilnotrunning=args.waittilnotrunning, )  # returns True when done
        if not succeeded:
            raise Exception('problem with runMoveFilesContinuously. [{}, {})'.format(minnum, maxnum))
print '----------------{} submission done-----------------'.format(args.signal_name)
