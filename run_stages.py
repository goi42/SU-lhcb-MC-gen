#!/usr/bin/env python2
import sys
import os
from os.path import join as opj
from copy import copy
import shutil
import datetime
import argparse
import subprocess
import getpass
import socket
from imp import load_source


def check_stage(ist, st, nm, typ):
    if nm not in st:
        raise IOError('"{0}" parameter missing from stage_list[{1}]'.format(nm, ist))
    else:
        if not isinstance(st[nm], typ):
            raise TypeError('stage_list[{0}] is a {1} and not a {2}?'.format(ist, type(st), repr(typ)))


def makedirsif(d):
    if not os.path.isdir(d) and d != '':
        os.makedirs(d)


def incmove(afile, adir, suffix='ConflictedFiles', diroverride=False, i_start=0):
    '''moves afile to adir
    if adir/afile exists, moves to adir_suffix<i>, where <i> is the first integer directory without afile in it
    diroverride alows afile to be a directory instead of a file
    '''
    from os.path import isfile, isdir
    import shutil
    
    if not (isfile(afile) and isdir(adir)):
        if isdir(afile) and isdir(adir) and diroverride:
            pass
        else:
            raise TypeError('\n{F} is a file? {Ft}\n{D} is a dir? {Dt}\ndiroverride? {DOR}'.format(F=afile, Ft=str(os.path.isfile(afile)), D=adir, Dt=str(os.path.isdir(adir)), DOR=diroverride))
    
    def incmove_suffix(afile, adir, suffix, i):
        suffdir = '{adir}_{suff}{i}'.format(adir=adir.strip('/'), suff=suffix, i=i)
        makedirsif(suffdir)
        try:
            shutil.move(afile, suffdir)
        except shutil.Error as e:
            if all(x in str(e) for x in ('Destination path', 'already exists')):
                incmove_suffix(afile, adir, suffix, i + 1)
            else:
                raise
    
    try:
        shutil.move(afile, adir)
    except shutil.Error as e:
        if all(x in str(e) for x in ('Destination path', 'already exists')):
            incmove_suffix(afile, adir, suffix, i_start)
        else:
            raise


def safecall(acommand):
    sc = subprocess.call([acommand], shell=True, executable='/bin/tcsh')
    if sc != 0:  # should be 0 if `call` worked
        with open(GENERAL_LOG, 'a') as f:
            f.write("subprocess.call({acomm}) failed. Returned {anum} Goodbye!\n".format(acomm=acommand, anum=sc))
        sys.exit()
        

def stage_makedirs(d):
    '''if WORK_DIR_EXISTS (flag from configfile), removes directory before making it. Primarily useful for creating a stage's option files.
    '''
    if WORK_DIR_EXISTS and os.path.exists(d):
        shutil.rmtree(d)
    if d != '':
        os.makedirs(d)


def capture_stdouterr(log):
    import os
    import sys
    with open(log, 'a') as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())


######################################################################
#  This is a template of LHCb MC generation
#      Michael Wilkinson: Jan 11, 2018
#      based on a script by
#            Jianchun Wang 01/13/2012
#            Updated for 2016 MC by Scott Ely: Aug 30, 2017
######################################################################

# -- basic info -- #
DATE = str(datetime.datetime.now()).replace(' ', '_')
USER = getpass.getuser()
NODE = socket.gethostname()

# -- set or pass job parameters -- #
parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('configfile', type=os.path.abspath,
                    help='')
args = parser.parse_known_args()[0]  # abandon unknown args, assumed to be handled by configfile
configfile = args.configfile

conf = load_source('conf', configfile)
SIGNAL_NAME     = conf.SIGNAL_NAME
RUN_NUMBER      = conf.RUN_NUMBER
RUN_SYS         = conf.RUN_SYS
CLEANSTAGES     = conf.CLEANSTAGES
CLEANWORK       = conf.CLEANWORK
SOME_MISSING    = conf.SOME_MISSING
WORK_DIR_EXISTS = conf.WORK_DIR_EXISTS
make_stage_list = conf.make_stage_list

# -- Directories and files -- #
BASE_NAME   = '%s_%d' % (SIGNAL_NAME, RUN_NUMBER)
WORK_DIR    = '%s/%s/work/%s/%d' % (RUN_SYS, USER, SIGNAL_NAME, RUN_NUMBER)
DATA_DIR    = '%s/%s/data/%s/%d' % (RUN_SYS, USER, SIGNAL_NAME, RUN_NUMBER)  # because the output dst all have the same name
LOG_DIR     = '%s/%s/log/%s/%d' % (RUN_SYS, USER, SIGNAL_NAME, RUN_NUMBER)  # because some log output files have the same name
GENERAL_LOG = opj(WORK_DIR, BASE_NAME + '_{0}_general.log'.format(DATE))

# -- set environment parameters missing in Condor -- #
PRE_SCRIPT = 'setenv HOME /home/{USER} && setenv PATH /bin:/usr/bin:/usr/local/bin && setenv LC_ALL C && set MCGEN_DIR = /home/{USER}/lhcbAnal/MCGen && setenv User_release_area /home/{USER}/lhcbAnal && setenv APPCONFIGOPTS /cvmfs/lhcb.cern.ch/lib/lhcb/DBASE/AppConfig/v3r340/options && source /cvmfs/lhcb.cern.ch/group_login.csh'.format(USER=USER)

# -- check, make, and change directories -- #
if os.path.isdir(WORK_DIR) and not WORK_DIR_EXISTS:
    raise IOError(WORK_DIR + " exists")
for d in (DATA_DIR, LOG_DIR, WORK_DIR):
    if not os.path.isdir(d):
        os.makedirs(d)
os.chdir(WORK_DIR)  # all references should be relative to the WORK_DIR or absolute

# -- redirect stdout and stderr -- #
capture_stdouterr(GENERAL_LOG)

# -- write parameter values to the log -- #
with open(GENERAL_LOG, 'w') as f:
    f.write('''\
====================================================
NODE:\t\t\t{NODE}
START@:\t\t\t{DATE}
SIGNAL_NAME:\t\t{SIGNAL_NAME}
RUN_NUMBER:\t\t{RUN_NUMBER}
RUN_SYS:\t\t{RUN_SYS}
CLEANSTAGES:\t\t{CLEANSTAGES}
CLEANWORK:\t\t{CLEANWORK}
SOME_MISSING:\t\t{SOME_MISSING}
WORK_DIR_EXISTS:\t{WORK_DIR_EXISTS}
make_stage_list:\t{make_stage_list}
====================================================
'''.format(NODE=NODE, DATE=DATE, SIGNAL_NAME=SIGNAL_NAME, RUN_NUMBER=RUN_NUMBER, RUN_SYS=RUN_SYS, CLEANSTAGES=CLEANSTAGES, CLEANWORK=CLEANWORK, SOME_MISSING=SOME_MISSING, WORK_DIR_EXISTS=WORK_DIR_EXISTS, make_stage_list=make_stage_list,))

# -- make stages -- #
stage_list = make_stage_list(USER, BASE_NAME)

# verify stage_list
if not isinstance(stage_list, list):
    raise TypeError('stage_list is a {0} not a list?'.format(type(stage_list)))
for istage, stage in enumerate(stage_list):
    if not isinstance(stage, dict):
        raise TypeError('stage_list[{0}] is a {1} and not a dict?'.format(istage, type(stage)))
    to_check = [
        ('name', str),
        ('scripts', dict),
        ('log', str),
        ('call_string', str),
        ('to_remove', list),
        ('required', list),
        ('data', list),
        ('run', bool),
        ('scriptonly', bool),
    ]
    for nm, typ in to_check:
        check_stage(istage, stage, nm, typ)

# -- loop stages -- #
for istage, stage in enumerate(stage_list):
    # is this stage selected to run?
    if not stage['run']:
        with open(GENERAL_LOG, 'a') as f:
            f.write('{name} stage not selected to run. Next stage...\n'.format(name=stage['name']))
        continue

    DATE = str(datetime.datetime.now())
    with open(GENERAL_LOG, 'a') as f:
        f.write('''\
====================================================
Start {name} @   {DATE}
====================================================
'''.format(name=stage['name'], DATE=DATE))
        
    # create stage scripts
    with open(GENERAL_LOG, 'a') as f:
        f.write("making {name} scripts\n".format(name=stage['name']))
        for scriptname, scriptcontent in stage['scripts'].iteritems():
            stage_makedirs(os.path.dirname(scriptname))  # create any needed directories
            with open(scriptname, 'w') as stagef:
                stagef.write(scriptcontent)
        if stage['scriptonly']:
            f.write("scriptonly option used. Will not start this stage.\n")
            continue
        f.write('starting {name} stage\n'.format(name=stage['name']))
    
    # check required files exist
    pass_req_check = True
    for required in stage['required']:
        required = required.rstrip('/')  # if a directory, leaving the slash at the end could cause confusion
        if os.path.exists(required):
            continue
        elif os.path.exists(opj(DATA_DIR, required)):  # if the file is in DATA_DIR, move it to WORK_DIR
            if os.path.exists(required):
                pass_req_check = False
                raise Exception('Something went wrong. Found {r} in {d}, but {r} is already in {w}!'.format(r=required, d=DATA_DIR, w=WORK_DIR))
            makedirsif(os.path.dirname(required))
            shutil.move(opj(DATA_DIR, required), required)
        # if the file still doesn't exist:
        if not os.path.exists(required):
            pass_req_check = False
            if SOME_MISSING:
                with open(GENERAL_LOG, 'a') as f:
                    f.write('\n{r} not found for stage {s}, but SOME_MISSING option used. Will not run this stage.\n'.format(r=required, s=stage['name']))
            else:
                raise Exception('{r} not found for stage {s}'.format(r=required, s=stage['name']))
    # skip this stage if not pass_req_check
    if not pass_req_check:
        if not SOME_MISSING:
            raise Exception('Not all requirements were found for stage {s}!'.format(s=stage['name']))
        continue
    
    # redirect stdout and stderr
    capture_stdouterr(opj(WORK_DIR, stage['log']))
    # run stage
    safecall(PRE_SCRIPT + ' && ' + stage['call_string'])
    # redirect stdout and stderr
    capture_stdouterr(GENERAL_LOG)
    
    if CLEANSTAGES:
        for torm in stage['to_remove']:
            if os.path.isfile(torm):
                os.remove(torm)
            else:
                with open(GENERAL_LOG, 'a') as f:
                    f.write("file {TORM} does not exist or is not a file; will not remove\n".format(TORM=torm))
    
    DATE = str(datetime.datetime.now())
    with open(GENERAL_LOG, 'a') as f:
        f.write('''\
====================================================
Finish {name} @   {DATE}
====================================================
'''.format(name=stage['name'], DATE=DATE))

# -- mv files to final location and cleanup -- #
if CLEANWORK:
    with open(GENERAL_LOG, 'a') as f:
        f.write('contents of {WORK_DIR}:\n'.format(WORK_DIR=WORK_DIR))
        f.write(str(os.listdir(WORK_DIR)))
    for d in set([y for x in stage_list for y in x['required'] + x['data']]):
        if os.path.exists(d):
            incmove(d, DATA_DIR, diroverride=True)
    for f in os.listdir(WORK_DIR):  # move everything else to logdir
        incmove(f, LOG_DIR, diroverride=True)
    
    os.chdir('../')
    shutil.rmtree(WORK_DIR)
