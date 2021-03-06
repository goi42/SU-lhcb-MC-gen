import getpass
import os
from os.path import join as opj, isdir, exists
from shutil import move, copy, copytree
from subprocess import check_output
import argparse
from utils import nojobsrunning, Njobs, cpr, updateprogress, incname

IsMain = __name__ == '__main__'


class AtLeastZero(argparse.Action):
    'based on https://stackoverflow.com/a/8624107/4655426'
    def __call__(self, parser, args, val, option_string=None):
        if not isinstance(val, int):
            raise parser.error('expected integer')
        if val < 0:
            raise parser.error('val must be >= 0! You have given "{0}".'.format(val))
        setattr(args, self.dest, val)


parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='move completed MC jobs to final destination. Assumes CLEANWORK was used in run_stages.py. Will ignore a given output if log/ but no data/')
parser.add_argument('signal_name',
                    help='name used to sort output')
parser.add_argument('--run_sys', default='/data2', type=os.path.abspath,
                    help='system where files should be created (or moved from)')
parser.add_argument('--store_sys', default='/data6', type=os.path.abspath,
                    help='system where files should be stored (or moved to)')
parser.add_argument('--user', default=getpass.getuser(),
                    help='username (used to locate "work", "data", and "log" directories)')
parser.add_argument('--minallowed', default=None, type=int,
                    help='minimum allowed subdirectory number, inclusive')
parser.add_argument('--maxallowed', default=None, type=int,
                    help='maximum allowed subdirectory number, exclusive')
parser.add_argument('--idontcareaboutotherjobs', action='store_true',
                    help='If this flag is set, moveFiles will return True just because the work directories for signal_name are missing.'
                    ' (It won\'t matter if there are still jobs running on Condor.)'
                    ' WARNING: this can cause unusual behavior if you have other jobs running.'
                    # help text from waittilnotrunning (here for posterity):
                    # ' This can be useful if there are other jobs running for the user that might delay these jobs from starting.'
                    # ' Note that this also means moveFiles will not think it\'s finished if the user has other jobs running.'
                    # ' Does nothing if justdata used.')
                    )
parser.add_argument('--justdata', action='store_true',
                    help='flag to just move data without checking work directories or moving log directories or checking running jobs')
f = parser.add_mutually_exclusive_group()  # ensure copyfrom and movefrom are not both set
f.add_argument('--copyfrom', metavar='OLDNAME', default=None,
               help='option to copy (not move) files from OLDNAME to signal_name')
f.add_argument('--movefrom', metavar='OLDNAME', default=None,
               help='option to move files from OLDNAME to signal_name')
contgroup = parser.add_argument_group('arguments for running continuously')
contgroup.add_argument('--interval', type=float, default=0, action=AtLeastZero,
                       help='Runs moveFiles over and over every INTERVAL until WORK_DIR is empty or maxwaittime exceeded.'
                       ' (If moveFiles is run directly from the commandline, a value of 0 means do not do this.)')
contgroup.add_argument('--lessthan', default=0, type=int, action=AtLeastZero,
                       help='If there are fewer jobs than this running for the user, moveFiles returns True (and runMoveFilesContinuously starts the next iteration).'
                       ' (A value of 0 ignores this.)')
contgroup.add_argument('--maxwaittime', default=0, type=float, action=AtLeastZero,
                       help='Time after which to give up and exit (in seconds) if --interval used and WORK_DIR not empty.'
                       ' (Will not give up if 0.)')
contgroup.add_argument('--waittostart', default=0, type=float, action=AtLeastZero,
                       help='How often to check (in seconds) if ANY of the user\'s jobs have started before initial call to moveFiles.'
                       ' (0 means do not check.)')
args = parser.parse_args() if IsMain else parser.parse_args(args=['DUMMYSIGNALNAME'])


def moveFiles(signal_name=args.signal_name, run_sys=args.run_sys, store_sys=args.store_sys, user=args.user, minallowed=args.minallowed, maxallowed=args.maxallowed,
              justdata=args.justdata, lessthan=args.lessthan, copyfrom=args.copyfrom, movefrom=args.movefrom, idontcareaboutotherjobs=args.idontcareaboutotherjobs):
    '''justdata changes behavior in complicated ways--pay attention
    '''
    print '----------------moveFiles from {} to {}-----------------'.format(run_sys, store_sys)
    
    if justdata and lessthan > 0:
        raise ValueError('lessthan > 0 does not do anything if justdata=True')
    if justdata and idontcareaboutotherjobs:
        raise ValueError('idontcareaboutotherjobs=True does not do anything if justdata=True')
    if all(x is not None for x in (copyfrom, movefrom)):
        # this is critical to the logic of moveFiles
        raise IOError('One or both copyfrom and movefrom must be None!')
    
    # -- useful declarations
    cmfrom = copyfrom if movefrom is None else movefrom
    allcmNone = all(x is None for x in (copyfrom, movefrom))
    thingstr = 'move' if copyfrom is None else 'copy'
    
    # -- print program intentions
    print 'will {THING} files with signal_name "{NAME}" from {OLD} to {NEW}'.format(THING=thingstr, NAME=signal_name if allcmNone else cmfrom, OLD=run_sys, NEW=store_sys),
    if not allcmNone:
        print 'under signal_name "{NAME}"'.format(NAME=signal_name),
    print 'for user {USER}'.format(USER=user)
    if any(x is not None for x in [minallowed, maxallowed]):
        print 'subdirs [{}, {})'.format(minallowed, maxallowed)
    
    wkdir_base = opj(user, 'work', signal_name)
    dtdir_base = opj(user, 'data', signal_name)
    lgdir_base = opj(user, 'log', signal_name)
    wkdir_old = opj(run_sys, wkdir_base)
    dtdir_old = opj(run_sys, dtdir_base)
    lgdir_old = opj(run_sys, lgdir_base)
    if not allcmNone:
        wkdir_old = wkdir_old.replace(signal_name, cmfrom)
        dtdir_old = dtdir_old.replace(signal_name, cmfrom)
        lgdir_old = lgdir_old.replace(signal_name, cmfrom)
    wkdir_new = opj(store_sys, wkdir_base)
    dtdir_new = opj(store_sys, dtdir_base)
    lgdir_new = opj(store_sys, lgdir_base)
    
    def dirtruthtest(d):
        '''checks if d exists as a subdirectory in dtdir_old. if not justdata, also checks that it is in lgdir_old and not in wkdir_old
        '''
        outtest = isdir(opj(dtdir_old, d))
        if not justdata:
            outtest = (outtest and isdir(opj(lgdir_old, d)) and not isdir(opj(wkdir_old, d)))
        return outtest
    
    def subdirsinrange(d):
        '''selects subdirectories in d allowed by minallowed and maxallowed
        '''
        if not exists(d):
            return []
        dirlist = [x for x in os.listdir(d) if isdir(opj(d, x))]
        if minallowed is not None:
            dirlist = [x for x in dirlist if int(x) >= minallowed]
        if maxallowed is not None:
            dirlist = [x for x in dirlist if int(x) < maxallowed]
        return dirlist
    
    def makesubdirlist(d=dtdir_old):
        '''applies dirtruthtest, which depends on justdata, to subdirsinrange
        '''
        subdirlist = [x for x in subdirsinrange(d) if dirtruthtest(x)]
        return subdirlist
    
    def endstep():
        print '----------------end moveFiles------------'
        if justdata:
            # -- ensure all the directories have been moved or copied
            return not makesubdirlist() if copyfrom is None else (len(makesubdirlist(dtdir_old)) == len(makesubdirlist(dtdir_new)))
        else:
            if nojobsrunning(user) and subdirsinrange(wkdir_old):
                print 'there are still directories in {}, but all the condor jobs have finished'.format(wkdir_old)
            if Njobs(user) < lessthan and not nojobsrunning(user):
                print 'there are still {} condor jobs running, but this is fewer than {}'.format(Njobs(user), lessthan)
            return True if (nojobsrunning(user) or (not subdirsinrange(wkdir_old) and idontcareaboutotherjobs) or Njobs(user) < lessthan) else False
    
    subdirlist = makesubdirlist()
    if not subdirlist:
        print 'no directories to {}'.format(thingstr)
        return endstep()
    
    print len(subdirlist), 'directories to {}...'.format(thingstr)
    dirbar = updateprogress(len(subdirlist))
    dirbar.start()
    
    for i, subdir in enumerate(subdirlist):
        # -- declare old and new, data and log absolute paths
        dtold, dtnew = opj(dtdir_old, subdir), opj(dtdir_new, subdir)
        lgold, lgnew = opj(lgdir_old, subdir), opj(lgdir_new, subdir)
        
        # -- declare list of new and old directories to-be-affected
        listofdirs = [(dtold, dtnew)]
        if not justdata:
            listofdirs += [(lgold, lgnew)]
        
        # -- do the move or copy
        thing_to_do = move if copyfrom is None else cpr
        for oldd, newd in listofdirs:
            
            # -- create new directories
            if not exists(newd):
                os.makedirs(newd)
            elif not isdir(newd):
                raise IOError('{} already exists but is not a directory!'.format(newd))
            
            # -- loop over things
            for oldthname in os.listdir(oldd):
                oldth = opj(oldd, oldthname)
                newthname = oldthname if allcmNone else oldthname.replace(cmfrom, signal_name)
                newth = incname(opj(newd, newthname))
                
                # -- check to make sure new things do not exist
                if exists(newth):
                    # sanity check only: incname above ought to prevent this
                    raise IOError('{} already exists!'.format(newth))
                
                # -- do the move or copy
                thing_to_do(oldth, newth)
            
            # -- remove now empty directories
            if not os.listdir(oldd):
                os.rmdir(oldd)
        
        dirbar.update(i)
    
    dirbar.finish()
    return endstep()
    
    
def runMoveFilesContinuously(user=args.user, interval=args.interval, maxwaittime=args.maxwaittime, waittostart=args.waittostart, *largs, **kwargs):
    '''runs moveFiles(user=user, *largs, **kwargs) continuously (see parser description and help)
    '''
    import time
    import datetime
    
    def chopd(tm):
        return str(tm).split('.')[0]
    
    starttime = datetime.datetime.now()
    endtime = starttime + datetime.timedelta(seconds=maxwaittime) if maxwaittime else None
    
    print 'starting at {}'.format(starttime)
    print 'will run moveFiles continuously until finished',
    print 'or until {}'.format(endtime) if maxwaittime else ''
    
    done = False  # has moveFiles finished?
    jobs_started = False if waittostart else True  # have any jobs started running?
    while not done:
        if jobs_started:
            done = moveFiles(user=user, *largs, **kwargs)
        if not done:
            now = datetime.datetime.now()
            if maxwaittime and now >= endtime:
                print 'maxwaittime reached at {}'.format(now)
                if not jobs_started:
                    print 'Something is wrong. Why have the jobs not started?'
                return False
            if not jobs_started:
                check = check_output(['condor_q {}'.format(user)], shell=True)
                if ', 0 running' not in check and not nojobsrunning(user):  # '10000 jobs; 0 completed, 0 removed, 10000 idle, 0 running, 0 held, 0 suspended'
                    
                    jobs_started = True
                    
                    continue  # skip the rest of this iteration
                    
                elif nojobsrunning(user):
                    raise Exception('There may be a problem with the jobs. They seem not to have started.')
                
                print 'Waiting for jobs to start...'
                ntdelt = datetime.timedelta(seconds=waittostart)
            else:
                print 'Not done moving (or copying) files yet...'
                ntdelt = datetime.timedelta(seconds=interval)
            
            waited = now - starttime
            nexttime = now + ntdelt
            print 'Have waited {}. It is now {}. Will try again after {} at {}.'.format(chopd(waited), chopd(now), chopd(ntdelt), chopd(nexttime)),
            print 'Will end after {}.'.format(chopd(endtime)) if maxwaittime else 'No endtime set.'
            time.sleep(ntdelt.total_seconds())
    
    print 'finished at {}'.format(datetime.datetime.now())
    return True


if IsMain:
    if args.interval:
        runMoveFilesContinuously()
    else:
        moveFiles()
