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


def makedirsif(d):
    if not os.path.isdir(d) and d != '':
        os.makedirs(d)


def makedirs_inc(basedir, suffix, i_start=0):
    basedir = basedir.rstrip('/')
    if not os.path.isdir(basedir):
        raise TypeError
    i = i_start
    succeeded = False
    while not succeeded:
        try:
            os.makedirs(basedir + '_' + suffix + str(i))
            succeeded = True
        except OSError:
            i += 1
    return basedir + '_' + suffix + str(i)


def shutil_safemove(afile, adir, suffix='ConflictedFiles', diroverride=False):
    if not (os.path.isfile(afile) and os.path.isdir(adir)):
        if os.path.isdir(afile) and os.path.isdir(adir) and diroverride:
            pass
        else:
            raise TypeError('\n{F} is a file? {Ft}\n{D} is a dir? {Dt}\ndiroverride? {DOR}'.format(F=afile, Ft=str(os.path.isfile(afile)), D=adir, Dt=str(os.path.isdir(adir)), DOR=diroverride))
    try:
        shutil.move(afile, adir)
    except shutil.Error:
        shutil.move(afile, makedirs_inc(adir, suffix))
        

def safecall(acommand):
    sc = subprocess.call([acommand], shell=True, executable='/bin/tcsh')
    if sc:  # should be 0 if `call` worked
        with open(GENERAL_LOG, 'a') as f:
            f.write("subprocess.call({acomm}) failed. Returned {anum} Goodbye!\n".format(acomm=acommand, anum=sc))
        sys.exit()
        

def stage_makedirs(d):
    '''if WORK_DIR_EXISTS (argparse flag), removes directory before making it. Primarily useful for creating a stage's option files.
    '''
    if WORK_DIR_EXISTS and os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)


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
parser.add_argument('configfile', type=str,
                    help='')
args = parser.parse_args()
configfile = args.configfile

SIGNAL_NAME     = load_source('SIGNAL_NAME', configfile).SIGNAL_NAME
RUN_NUMBER      = load_source('RUN_NUMBER', configfile).RUN_NUMBER
GEN_LEVEL       = load_source('GEN_LEVEL', configfile).GEN_LEVEL
RUN_SYS         = load_source('RUN_SYS', configfile).RUN_SYS
CLEANSTAGES     = load_source('CLEANSTAGES', configfile).CLEANSTAGES
CLEANWORK       = load_source('CLEANWORK', configfile).CLEANWORK
PRECLEANED      = load_source('PRECLEANED', configfile).PRECLEANED
SOME_MISSING    = load_source('SOME_MISSING', configfile).SOME_MISSING
WORK_DIR_EXISTS = load_source('WORK_DIR_EXISTS', configfile).WORK_DIR_EXISTS
make_stage_list = load_source('make_stage_list', configfile).make_stage_list

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
os.chdir(WORK_DIR)  # passed references in this script are absolute, but the output is generally sent to the current working directory

# -- redirect error output -- #
with open(GENERAL_LOG, 'a') as f:
    os.dup2(f.fileno(), sys.stdout.fileno())
    os.dup2(f.fileno(), sys.stderr.fileno())

# -- write parameter values to the log -- #
with open(GENERAL_LOG, 'w') as f:
    f.write('''\
====================================================
NODE:\t\t{NODE}
START@:\t\t{DATE}
SIGNAL_NAME:\t\t {SIGNAL_NAME}
RUN_NUMBER:\t\t {RUN_NUMBER}
GEN_LEVEL:\t\t {GEN_LEVEL}
RUN_SYS:\t\t {RUN_SYS}
CLEANSTAGES:\t\t {CLEANSTAGES}
CLEANWORK:\t\t {CLEANWORK}
PRECLEANED:\t\t {PRECLEANED}
SOME_MISSING:\t\t {SOME_MISSING}
WORK_DIR_EXISTS:\t\t {WORK_DIR_EXISTS}
make_stage_list:\t\t {make_stage_list}
====================================================
'''.format(NODE=NODE, DATE=DATE, SIGNAL_NAME=SIGNAL_NAME, RUN_NUMBER=RUN_NUMBER, GEN_LEVEL=GEN_LEVEL, RUN_SYS=RUN_SYS, CLEANSTAGES=CLEANSTAGES, CLEANWORK=CLEANWORK, PRECLEANED=PRECLEANED, SOME_MISSING=SOME_MISSING, WORK_DIR_EXISTS=WORK_DIR_EXISTS, make_stage_list=make_stage_list,))

# -- run stages -- #
stage_list = make_stage_list(USER, BASE_NAME)
for istage, stage in enumerate(stage_list):
    # is this stage selected to run?
    if not stage['run']:
        with open(GENERAL_LOG, 'a') as f:
            f.write('{name} stage not selected to run. Next stage...\n'.format(name=stage['name']))
        continue
    
    # declare stage parameters
    stagedir = opj(WORK_DIR, stage['dirname'])
    stagedata = opj(WORK_DIR, stage['dataname'])
    
    # create stage scripts
    with open(GENERAL_LOG, 'a') as f:
        f.write("making {name} scripts\n".format(name=stage['name']))
        stage_makedirs(stagedir)  # create the directory where scripts will be executed
        for scriptname, scriptcontent in stage['scripts'].iteritems():
            makedirsif(os.path.dirname(scriptname))
            with open(scriptname, 'w') as stagef:
                stagef.write(scriptcontent)
        if stage['scriptonly']:
            f.write("scriptonly option used. Will not start this stage.\n")
            continue
        f.write('starting {name} stage\n'.format(name=stage['name']))
    
    if PRECLEANED and istage > 0:
        wkfile = stage_list[istage - 1]['data']
        wkdir  = os.path.dirname(wkfile)
        flnm   = os.path.basename(wkfile)
        fnfile = opj(DATA_DIR, flnm)
        if os.path.isfile(fnfile):
            # make the work directory
            if not os.path.isdir(wkdir):
                os.makedirs(wkdir)
            # move it from its final directory to its work directory
            shutil.move(fnfile, wkfile)
        if os.path.isfile(wkfile):
            pass
        elif SOME_MISSING:
            with open(GENERAL_LOG, 'a') as f:
                f.write('\n{FILE} not found, but SOME_MISSING option used. Moving on...\n'.format(FILE=wkfile))
            continue
        else:
            raise Exception('PRECLEANED file {FILE} not found for stage {STAGE}'.format(FILE=wkfile, STAGE=stage['name']))
    
    if istage == 0 or os.path.isfile(stage_list[istage - 1]['data']):
        safecall(PRE_SCRIPT + ' && ' + stage['call_string'])
    else:
        with open(GENERAL_LOG, 'a') as f:
            f.write("\nCannot find {data}\n".format(data=stage_list[istage - 1]['data']))
        if SOME_MISSING:
            with open(GENERAL_LOG, 'a') as f:
                f.write("But SOME_MISSING option used. Moving on...\n")
            continue
    
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
        f.write(str(os.listdir(WORK_DIR)))
    for datafile in [x['data'] for x in stage_list]:
        if os.path.exists(datafile):
            shutil_safemove(datafile, DATA_DIR, diroverride=True)
    for f in os.listdir(WORK_DIR):
        if os.path.isfile(f):
            shutil_safemove(f, LOG_DIR)
            
    os.chdir('../')
    shutil.rmtree(WORK_DIR)
