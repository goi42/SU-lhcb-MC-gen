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


class ChoicesInList(argparse.Action):
    'based on https://stackoverflow.com/a/8624107/4655426'
    def __call__(self, parser, args, values, option_string=None):
        # -- ensure valid_choices
        for v in values:
            if v not in valid_choices:
                raise parser.error('invalid choice of GEN_LEVEL {val}!\nValid choices are {vcs}'.format(val=v, vcs=valid_choices))
        # -- ensure exclusive_choices
        found = False
        for ec in exclusive_choices:
            if ec in values and found:
                raise parser.error('cannot have more than one of {ecs} in GEN_LEVEL'.format(ecs=exclusive_choices))
            elif ec in values:
                found = True
        if any(x in exclusive_choices for x in values) and any(x in other_choices for x in values):
            raise parser.error('cannot have any {ecs} in GEN_LEVEL while also having any {ocs}!\nYou have {vs}'.format(ecs=exclusive_choices, ocs=other_choices, vs=values))
        
        setattr(args, self.dest, values)


######################################################################
#  This is a template of LHCb MC generation
#      Michael Wilkinson: Jan 11, 2018
#      based on a script by
#            Jianchun Wang 01/13/2012
#            Updated for 2016 MC by Scott Ely: Aug 30, 2017
######################################################################

# -- basic info
DATE = str(datetime.datetime.now()).replace(' ', '_')
USER = getpass.getuser()
NODE = socket.gethostname()

# -- set or pass job parameters
parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--SIGNAL_NAME', default='TestProduction')
parser.add_argument('--EVENT_TYPE', type=int, default=28196041)
parser.add_argument('--RUN_NUMBER', type=int, default=300000)
parser.add_argument('--FIRST_EVENT', type=int, default=1)
parser.add_argument('--NUM_EVENT', type=int, default=100)
#
# these are referenced above by ChoicesInList
exclusive_choices = ['all', 'none']  # cannot have more than one of these and cannot use these with other_choices; set GEL_LEVEL to other_choices or [], respectively
other_choices = ['gauss', 'boole', 'moorel0', 'moorehlt1', 'moorehlt2', 'brunel', 'davinci', 'allstuple', 'restrip', 'tuple', 'slim']
valid_choices = exclusive_choices + other_choices
#
parser.add_argument('--GEN_LEVEL', nargs='*', default=['all'], action=ChoicesInList, choices=valid_choices, type=str.lower,
                    help='select what stages to run')
parser.add_argument('--ALL_EXCEPT', action='store_true',
                    help='''option to interpret GEN_LEVEL as "run except".
                    The script will run everything _except_ the specified stages if this option is used.
                    Use with "all" is equivalent to running with GEN_LEVEL "None" ''')
parser.add_argument('--RUN_SYS', default='/data2',
                    help='system to run on')
scriptgroup = parser.add_argument_group('script controls')
scriptgroup.add_argument('--noCOMPRESS', dest='COMPRESS', action='store_false',
                         help='usually runs with compression option optimized for deletion of intermediate stages; this turns that off')
scriptgroup.add_argument('--noREDECAY', dest='REDECAY', action='store_false',
                         help='turns off ReDecay (ReDecay 100 times by default) in GAUSS_SCRIPT')
scriptgroup.add_argument('--noRICHOFF', dest='RICHOFF', action='store_false',
                         help='activates RICH and Cherenkov photons in GAUSS_SCRIPT')
scriptgroup.add_argument('--noNOPIDTRIG', dest='NOPIDTRIG', action='store_false',
                         help='leaves PID active in HLT2 trigger lines (removes nopidtrig from the stage list AND tells later stages to use the original TCK)')
scriptgroup.add_argument('--NEWCONFIG', default='/home/mwilkins/LcLc/MCgeneration/devrun/config.cdb',
                         help='config.cdb with new TCK inside to use if NOPIDTRIG active (active by default). Script assumes newtck = (oldtck | 0x0c000000)')
scriptgroup.add_argument('--TUPOPTS', default='/home/{USER}/LcLc/options/LcLc.py'.format(USER=USER),
                         help='options script to-be-copied for tuple (AllStreams and otherwise) creation')
scriptgroup.add_argument('--SLIMOPTS', default=['/home/{USER}/LcLc/analysis/prep_files.py'.format(USER=USER), '/home/{USER}/LcLc/analysis/fileprep'.format(USER=USER)], nargs=2,
                         help='python script to-be-copied for tuple slimming and a directory with modules to-be-imported')
cleangroup = parser.add_argument_group('cleaning options')
cleangroup.add_argument('--CLEAN_UP', choices=['CLEANSTAGES', 'CLEANWORK', 'both', 'none'], default='both',
                        help='''CLEANSTAGES deletes data from earlier stages as it goes.
                        CLEANWORK moves files out of work directory.''')
cleangroup.add_argument('--PRECLEANED', action='store_true',
                        help='if this script has already been run, you can specify this argument so that it moves appropriate files to the work directory first')
cleangroup.add_argument('--SOME_MISSING', action='store_true',
                        help='if running a later stage, you may specify this argument to let the script terminate without errors if the input files are missing')
paramgroup = parser.add_argument_group('physics paramters (beam, conddb, etc.)')
paramgroup.add_argument('--DDDB_VERSION', default='dddb-20170721-3')
paramgroup.add_argument('--CONDB_VERSION', default='sim-20170721-2-vc-md100')
paramgroup.add_argument('--MOOREL0_TCK', default='0x160F')
paramgroup.add_argument('--MOOREHLT1_TCK', default='0x5138160F')
paramgroup.add_argument('--MOOREHLT2_TCK', default='0x6139160F')
paramgroup.add_argument('--BEAM_VERSION', default='Beam6500GeV-md100-2016-nu1.6.py')
paramgroup.add_argument('--STRIPPING_VERSION', default='28r1')
allowedpols = ['md', 'mu']
paramgroup.add_argument('--MAGNETPOLARITY', default=None, choices=allowedpols,
                        help='ensures CONDB_VERSION and BEAM_VERSION use mu or md as appropriate for the specified polarity, e.g., replaces "mu" with "md".')
packagegroup = parser.add_argument_group('package versions to use')
packagegroup.add_argument('--GAUSS_VERSION', default='v49r10')
packagegroup.add_argument('--BOOLE_VERSION', default='v30r2p1')
packagegroup.add_argument('--MOORE_VERSION', default='v25r4')
packagegroup.add_argument('--BRUNEL_VERSION', default='v50r3')
packagegroup.add_argument('--DAVINCI_STRIPPING_VERSION', default='v41r4p4')
packagegroup.add_argument('--DAVINCI_TUPLE_VERSION', default='v42r6p1')
debuggroup = parser.add_argument_group('debugging options')
debuggroup.add_argument('--SCRIPT_ONLY', action='store_true',
                        help='creates scripts without running them')
debuggroup.add_argument('--WORK_DIR_EXISTS', action='store_true',
                        help='BE VERY CAREFUL WHEN USING THIS FLAG: gives permission to run if WORK_DIR already exists! Also allows overwrite of extant Opts directories.')

args = parser.parse_args()

# -- evaluate arguments
for arg in vars(args):
    exec('{ARG} = args.{ARG}'.format(ARG=arg))
CLEANSTAGES  = True if any(CLEAN_UP == x for x in ['CLEANSTAGES', 'both']) else False
CLEANWORK    = True if any(CLEAN_UP == x for x in ['CLEANWORK', 'both']) else False

# -- check arguments
if NOPIDTRIG and not all([MOOREHLT2_TCK == '0x6139160F', os.path.basename(NEWCONFIG) == 'config.cdb']):
    raise parser.error('NOPIDTRIG uses a config.cdb generated with certain assumptions. See script.')
if NOPIDTRIG:
    MOOREHLT2_TCK = str(hex((eval(MOOREHLT2_TCK) | 0x0c000000)))
if MAGNETPOLARITY is not None:
    if not len(allowedpols) == 2:
        raise Exception('something has gone wrong in the script. There should only be 2 allowed polarities.')
    rightpol = MAGNETPOLARITY
    wrongpol = allowedpols[0] if allowedpols.index(rightpol) == 1 else allowedpols[1]
    for thingtocheck_string in ('CONDB_VERSION', 'BEAM_VERSION'):
        if eval(thingtocheck_string).count(wrongpol) > 1:
            raise parser.error('{TH} ({THSTR}) has {POL} appearing more than once!'.format(TH=eval(thingtocheck_string), THSTR=thingtocheck_string, POL=wrongpol))
        exec('{THSTR} = {THSTR}.replace(wrongpol, rightpol)'.format(THSTR=thingtocheck_string))
        if eval(thingtocheck_string).count(rightpol) != 1:
            raise parser.error('{TH} ({THSTR}) does not contain exactly one appearance of {POL}!'.format(TH=eval(thingtocheck_string), THSTR=thingtocheck_string, POL=rightpol))

# -- Directory and files
BASE_NAME = '%s_%d' % (SIGNAL_NAME, RUN_NUMBER)
WORK_DIR  = '%s/%s/work/%s/%d' % (RUN_SYS, USER, SIGNAL_NAME, RUN_NUMBER)
DATA_DIR  = '%s/%s/data/%s/%d' % (RUN_SYS, USER, SIGNAL_NAME, RUN_NUMBER)  # because the output dst all have the same name
LOG_DIR   = '%s/%s/log/%s/%d' % (RUN_SYS, USER, SIGNAL_NAME, RUN_NUMBER)  # because some log output files have the same name

# -- set environment parameters missing in Condor
PRE_SCRIPT = 'setenv HOME /home/{USER} && setenv PATH /bin:/usr/bin:/usr/local/bin && setenv LC_ALL C && set MCGEN_DIR = /home/{USER}/lhcbAnal/MCGen && setenv User_release_area /home/{USER}/lhcbAnal && setenv APPCONFIGOPTS /cvmfs/lhcb.cern.ch/lib/lhcb/DBASE/AppConfig/v3r340/options && source /cvmfs/lhcb.cern.ch/group_login.csh'.format(USER=USER)
PRE_SCRIPT += ' && setenv PYTHONPATH $HOME/algorithms/python:$PYTHONPATH'  # declares stuff used by scripts called here

# -- Steer running and set parameters
if "all" in GEN_LEVEL:
    GEN_LEVEL = copy(other_choices)  # other_choices declares all available stages
# e.g., STAGE_GAUSS = True if Gauss is supposed to run
start_val, set_val = (False, True) if not ALL_EXCEPT else (True, False)
for st in other_choices:
    exec('''\
STAGE_{ST} = start_val
{ST}_LOG = opj(WORK_DIR, BASE_NAME + "_{st}.log")
{ST}_ROOT = opj(WORK_DIR, BASE_NAME + "_{st}.root")
{ST}_DIR = opj(WORK_DIR, "{st}Opts")
{ST}_SCRIPT = opj({ST}_DIR, "my{st}.py")
'''.format(ST=st.upper(), st=st.lower())
         )
    if st in GEN_LEVEL:
        exec('STAGE_{ST} = set_val'.format(ST=st.upper()))
GENERAL_LOG = opj(WORK_DIR, BASE_NAME + '_%s_general.log' % DATE)
GAUSS_DATA     = opj(WORK_DIR, BASE_NAME + '_gauss.sim')
BOOLE_DATA     = opj(WORK_DIR, BASE_NAME + '_boole.digi')
MOOREL0_DATA   = opj(WORK_DIR, BASE_NAME + '_moorel0.digi')
MOOREHLT1_DATA = opj(WORK_DIR, BASE_NAME + '_moorehlt1.digi')
MOOREHLT2_DATA = opj(WORK_DIR, BASE_NAME + '_moorehlt2.digi')
BRUNEL_DATA    = opj(WORK_DIR, BASE_NAME + '_brunel.dst')
DAVINCI_DATA   = opj(WORK_DIR, '000000.AllStreams.dst')  # this is produced by the script--do not modify unless the script changes
ALLSTUPLE_DATA = opj(WORK_DIR, BASE_NAME + '_allstuple.root')
RESTRIP_DATA   = opj(WORK_DIR, 'RestrippedMC.Charm.dst')  # this is produced by the script--do not modify unless the script changes
TUPLE_DATA     = opj(WORK_DIR, BASE_NAME + '_tuple.root')
SLIM_DATA      = opj(WORK_DIR, BASE_NAME + '_slim')

# -- redirect error output
with open(GENERAL_LOG, 'a') as f:
    os.dup2(f.fileno(), sys.stdout.fileno())
    os.dup2(f.fileno(), sys.stderr.fileno())

# -- write argument values to the log
with open(GENERAL_LOG, 'w') as f:
    f.write('''\
====================================================
NODE:\t\t{NODE}
START@:\t\t{DATE}
'''.format(NODE=NODE, DATE=DATE))
    
    for arg in sorted(vars(args)):
        f.write('{ARG}:\t\t{VAL}\n'.format(ARG=arg, VAL=eval(arg)))
    
    f.write('''\
====================================================
''')

# -- declare stages/scripts
stage_dict = []

# -- check, make, and change directories
if os.path.isdir(WORK_DIR) and not WORK_DIR_EXISTS:
    raise IOError(WORK_DIR + " exists")
for d in (DATA_DIR, LOG_DIR, WORK_DIR):
    if not os.path.isdir(d):
        os.makedirs(d)

os.chdir(WORK_DIR)  # passed references in this script are absolute, but the output is generally sent to the current working directory

# -- Gauss script
if STAGE_GAUSS:
    with open(GENERAL_LOG, 'a') as f:
        f.write("making gauss script\n")
    stage_makedirs(GAUSS_DIR)
    with open(GAUSS_SCRIPT, 'w') as f:
        f.write('''\
from Gauss.Configuration import *
from Configurables import LHCbApp, CondDB, Gauss

GaussGen                  = GenInit("GaussGen")
GaussGen.RunNumber        = {RUN_NUMBER}
GaussGen.FirstEventNumber = {FIRST_EVENT}
GaussGen.OutputLevel      = 4
LHCbApp().EvtMax          = {NUM_EVENT}
LHCbApp().DDDBtag         = "{DDDB_VERSION}"
LHCbApp().CondDBtag       = "{CONDB_VERSION}"

OutputStream("GaussTape").Output = "DATAFILE='PFN:{GAUSS_DATA}' TYP='POOL_ROOTTREE' OPT='RECREATE'"

importOptions("$APPCONFIGOPTS/Gauss/{BEAM_VERSION}")
importOptions("$APPCONFIGOPTS/Gauss/EnableSpillover-25ns.py")
importOptions("$APPCONFIGOPTS/Gauss/DataType-2016.py")
if {RICHOFF}:  # RICHOFF option set in generation script
    importOptions("$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts_noLHCbphys.py")  # turn off Cherenkov photons
else:
    importOptions("$APPCONFIGOPTS/Gauss/RICHRandomHits.py")  # as in $GAUSSOPTS/Gauss-2016.py  # removed because we are not using RICH info
    importOptions("$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py")  # not sure this is necessary
if {COMPRESS}:  # COMPRESS option set in generation script
    importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")  # makes for faster writing if the intention is to delete the output
importOptions("$DECFILESROOT/options/{EVENT_TYPE}.py")  # needs to be called BEFORE setting up Pythia8, else will use Pythia6 production tool
importOptions("$LBPYTHIA8ROOT/options/Pythia8.py")

if {REDECAY}:  # REDECAY option set in generation script
    importOptions("$APPCONFIGROOT/options/Gauss/ReDecay-100times.py")
# importOptions("$GAUSSOPTS/Gauss-2016.py")  # would overwrite some options set above

HistogramPersistencySvc().OutputFile = "{GAUSS_ROOT}"

'''.format(RUN_NUMBER=RUN_NUMBER, FIRST_EVENT=FIRST_EVENT, NUM_EVENT=NUM_EVENT, DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, GAUSS_DATA=GAUSS_DATA, BEAM_VERSION=BEAM_VERSION, COMPRESS=COMPRESS, REDECAY=REDECAY, RICHOFF=RICHOFF, EVENT_TYPE=EVENT_TYPE, GAUSS_ROOT=GAUSS_ROOT))
stage_dict.append(
    {
        'name': 'Gauss',
        'script': GAUSS_SCRIPT,
        'call_string': 'lb-run -c best --user-area /home/{USER}/cmtuser Gauss/{GAUSS_VERSION} gaudirun.py {GAUSS_SCRIPT} | tee {GAUSS_LOG}'.format(USER=USER, GAUSS_VERSION=GAUSS_VERSION, GAUSS_SCRIPT=GAUSS_SCRIPT, GAUSS_LOG=GAUSS_LOG),
        'to_remove': [],
        'data': GAUSS_DATA,
        'run': STAGE_GAUSS
    }
)

# -- Boole script
if STAGE_BOOLE:
    with open(GENERAL_LOG, 'a') as f:
        f.write("making boole script\n")
    stage_makedirs(BOOLE_DIR)
    with open(BOOLE_SCRIPT, 'w') as f:
        f.write('''\
from Gaudi.Configuration import *
from Configurables import LHCbApp, L0Conf, Boole

LHCbApp().DDDBtag   = "{DDDB_VERSION}"
LHCbApp().CondDBtag = "{CONDB_VERSION}"

EventSelector().Input                = ["DATAFILE='PFN:{GAUSS_DATA}' TYP='POOL_ROOTTREE' OPT='READ'"]
OutputStream("DigiWriter").Output    =  "DATAFILE='PFN:{BOOLE_DATA}' TYP='POOL_ROOTTREE' OPT='RECREATE'"
HistogramPersistencySvc().OutputFile = "{BOOLE_ROOT}"


# Boole().DigiType     = "Extended"
# Boole().OutputLevel  = INFO

importOptions("$APPCONFIGOPTS/Boole/Default.py")
importOptions("$APPCONFIGOPTS/Boole/EnableSpillover.py")
# importOptions("$APPCONFIGOPTS/Boole/Boole-SiG4EnergyDeposit.py")  # switch off all geometry (and related simulation) save that of calorimeters area
if {COMPRESS}:  # COMPRESS option set in generation script
    importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")  # makes for faster writing if the intention is to delete the output
importOptions("$APPCONFIGOPTS/Boole/DataType-2015.py")  # there is no 2016 available
importOptions("$APPCONFIGOPTS/Boole/Boole-SetOdinRndTrigger.py")  # idk whether this is good or necessary

L0Conf().TCK = '{MOOREL0_TCK}'
FileCatalog().Catalogs = [ "xmlcatalog_file:NewCatalog.xml" ]
'''.format(DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, GAUSS_DATA=GAUSS_DATA, BOOLE_DATA=BOOLE_DATA, BOOLE_ROOT=BOOLE_ROOT, COMPRESS=COMPRESS, MOOREL0_TCK=MOOREL0_TCK))
stage_dict.append(
    {
        'name': 'Boole',
        'script': BOOLE_SCRIPT,
        'call_string': 'lb-run -c best Boole/{BOOLE_VERSION} gaudirun.py {BOOLE_SCRIPT} | tee {BOOLE_LOG}'.format(BOOLE_VERSION=BOOLE_VERSION, BOOLE_SCRIPT=BOOLE_SCRIPT, BOOLE_LOG=BOOLE_LOG),
        'to_remove': [GAUSS_DATA],
        'data': BOOLE_DATA,
        'run': STAGE_BOOLE
    }
)

# -- Moore script for L0
if STAGE_MOOREL0:
    stage_makedirs(MOOREL0_DIR)
    with open(GENERAL_LOG, 'a') as f:
        f.write("making moore script for L0\n")
    with open(MOOREL0_SCRIPT, 'w') as f:
        f.write('''\
from Gaudi.Configuration import importOptions
from Configurables import L0App, L0Conf

#--- These options come from existing Official LHCb MC Production ---#
#-- L0 step
importOptions("$APPCONFIGOPTS/L0App/L0AppSimProduction.py")
importOptions("$APPCONFIGOPTS/L0App/L0AppTCK-{MOOREL0_TCK}.py")
# importOptions("$APPCONFIGOPTS/L0App/ForceLUTVersionV8.py")  # prefer to let this default
importOptions("$APPCONFIGOPTS/L0App/DataType-2016.py")
if {COMPRESS}:  # COMPRESS option set in generation script
    importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")

L0App().DDDBtag   = "{DDDB_VERSION}"
L0App().CondDBtag = "{CONDB_VERSION}"

#####
L0App().Simulation = True
# L0Conf().L0MuonForceLUTVersion = "V8"  # see above
#####

L0App().TCK = '{MOOREL0_TCK}'
L0App().ReplaceL0Banks = False
L0App().EvtMax = -1

from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles(['{BOOLE_DATA}'],clear=True)
#HistogramPersistencySvc().OutputFile = "{MOOREL0_ROOT}"
L0App().outputFile = '{MOOREL0_DATA}'

'''.format(MOOREL0_TCK=MOOREL0_TCK, COMPRESS=COMPRESS, DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, BOOLE_DATA=BOOLE_DATA, MOOREL0_ROOT=MOOREL0_ROOT, MOOREL0_DATA=MOOREL0_DATA))
stage_dict.append(
    {
        'name': 'Moore L0',
        'script': MOOREL0_SCRIPT,
        'call_string': 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREL0_SCRIPT} | tee {MOOREL0_LOG}'.format(MOORE_VERSION=MOORE_VERSION, MOOREL0_SCRIPT=MOOREL0_SCRIPT, MOOREL0_LOG=MOOREL0_LOG),
        'to_remove': [BOOLE_DATA],
        'data': MOOREL0_DATA,
        'run': STAGE_MOOREL0
    }
)

# -- Moore script for Hlt1
if STAGE_MOOREHLT1:
    stage_makedirs(MOOREHLT1_DIR)
    with open(GENERAL_LOG, 'a') as f:
        f.write("making moore script for Hlt1\n")
    with open(MOOREHLT1_SCRIPT, 'w') as f:
        f.write('''\
from Gaudi.Configuration import importOptions
from Configurables import Moore, L0App, L0Conf, HltConf

#--- These options come from existing Official LHCb MC Production ---#

#-- Hlt1 step
importOptions("$APPCONFIGOPTS/Moore/MooreSimProductionForSeparateL0AppStep2015.py")
importOptions("$APPCONFIGOPTS/Conditions/TCK-{MOOREHLT1_TCK}.py")
if {COMPRESS}:  # COMPRESS option set in generation script
    importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")
importOptions("$APPCONFIGOPTS/Moore/MooreSimProductionHlt1.py")
importOptions("$APPCONFIGOPTS/Moore/DataType-2016.py")


Moore().Split = 'Hlt1'
Moore().CheckOdin = False
Moore().WriterRequires = []
Moore().Simulation = True

Moore().DDDBtag   = "{DDDB_VERSION}"
Moore().CondDBtag = "{CONDB_VERSION}"

Moore().EvtMax     = -1
from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles(['{MOOREL0_DATA}'],clear=True)
#HistogramPersistencySvc().OutputFile = "{MOOREHLT1_ROOT}"
Moore().outputFile = '{MOOREHLT1_DATA}'

'''.format(MOOREHLT1_TCK=MOOREHLT1_TCK, COMPRESS=COMPRESS, DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, MOOREL0_DATA=MOOREL0_DATA, MOOREHLT1_ROOT=MOOREHLT1_ROOT, MOOREHLT1_DATA=MOOREHLT1_DATA))
stage_dict.append(
    {
        'name': 'Moore HLT1',
        'script': MOOREHLT1_SCRIPT,
        'call_string': 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREHLT1_SCRIPT} | tee {MOOREHLT1_LOG}'.format(MOORE_VERSION=MOORE_VERSION, MOOREHLT1_SCRIPT=MOOREHLT1_SCRIPT, MOOREHLT1_LOG=MOOREHLT1_LOG),
        'to_remove': [MOOREL0_DATA],
        'data': MOOREHLT1_DATA,
        'run': STAGE_MOOREHLT1
    }
)

# -- Moore script for Hlt2
if STAGE_MOOREHLT2:
    stage_makedirs(MOOREHLT2_DIR)
    with open(GENERAL_LOG, 'a') as f:
        f.write("making moore script for Hlt2\n")
    with open(MOOREHLT2_SCRIPT, 'w') as f:
        f.write('''\
from Gaudi.Configuration import importOptions
from Configurables import Moore, L0App, L0Conf, HltConf, HltConfigSvc

#--- These options come from existing Official LHCb MC Production ---#
#-- Hlt2 step
importOptions("$APPCONFIGOPTS/Moore/MooreSimProductionForSeparateL0AppStep2015.py")
importOptions("$APPCONFIGOPTS/Moore/DataType-2016.py")
if {COMPRESS}:  # COMPRESS option set in generation script
    importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")
importOptions("$APPCONFIGOPTS/Moore/MooreSimProductionHlt2.py")
#--- END ---#

if {NOPIDTRIG}:  # NOPIDTRIG options set in generation script
    Moore().TCKData = '{newTCKdir}'
    Moore().InitialTCK = '{MOOREHLT2_TCK}'
    HltConfigSvc().initialTCK = '{MOOREHLT2_TCK}'
else:
    importOptions("$APPCONFIGOPTS/Conditions/TCK-{MOOREHLT2_TCK}.py")

Moore().Split = 'Hlt2'
Moore().CheckOdin = False
Moore().WriterRequires = []
Moore().Simulation = True
Moore().DDDBtag   = "{DDDB_VERSION}"
Moore().CondDBtag = "{CONDB_VERSION}"
Moore().EvtMax = -1
from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles(['{MOOREHLT1_DATA}'],clear=True)

Moore().outputFile = '{MOOREHLT2_DATA}'

'''.format(COMPRESS=COMPRESS, NOPIDTRIG=NOPIDTRIG, newTCKdir=os.path.dirname(NEWCONFIG), WORK_DIR=WORK_DIR, MOOREHLT2_TCK=MOOREHLT2_TCK, DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, MOOREHLT1_DATA=MOOREHLT1_DATA, MOOREHLT2_DATA=MOOREHLT2_DATA))
stage_dict.append(
    {
        'name': 'Moore HLT2',
        'script': MOOREHLT2_SCRIPT,
        'call_string': 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREHLT2_SCRIPT} | tee {MOOREHLT2_LOG}'.format(MOORE_VERSION=MOORE_VERSION, MOOREHLT2_SCRIPT=MOOREHLT2_SCRIPT, MOOREHLT2_LOG=MOOREHLT2_LOG),
        'to_remove': [MOOREHLT1_DATA],
        'data': MOOREHLT2_DATA,
        'run': STAGE_MOOREHLT2
    }
)

# -- Brunel script
if STAGE_BRUNEL:
    with open(GENERAL_LOG, 'a') as f:
        f.write("making brunel script\n")
    stage_makedirs(BRUNEL_DIR)
    with open(BRUNEL_SCRIPT, 'w') as f:
        f.write('''\
from Gaudi.Configuration import *
from Configurables import Brunel, LHCbApp, L0Conf
if {NOPIDTRIG}:
    from Configurables import ConfigCDBAccessSvc
    ConfigCDBAccessSvc().File = '{NEWCONFIG}'

LHCbApp().DDDBtag   = "{DDDB_VERSION}"
LHCbApp().CondDBtag = "{CONDB_VERSION}"

if {COMPRESS}:  # COMPRESS option set in generation script
    importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")
importOptions("$APPCONFIGOPTS/Brunel/MC-WithTruth.py")
importOptions("$APPCONFIGOPTS/Brunel/DataType-2016.py")
importOptions("$APPCONFIGOPTS/Brunel/SplitRawEventOutput.4.3.py") # not sure this is necessary

###
#importOptions("\$APPCONFIGOPTS/Brunel/saveAllTrackTypes.py")
#Brunel().RecL0Only = True
###

EventSelector().Input                = ["DATAFILE='PFN:{MOOREHLT2_DATA}' TYP='POOL_ROOTTREE' OPT='READ'"]

OutputStream("DstWriter").Output     =  "DATAFILE='PFN:{BRUNEL_DATA}' TYP='POOL_ROOTTREE' OPT='RECREATE'"
HistogramPersistencySvc().OutputFile = "{BRUNEL_ROOT}"

L0Conf.EnsureKnownTCK = False # not sure this is necessary
FileCatalog().Catalogs = [ "xmlcatalog_file:NewCatalog.xml" ]


'''.format(NOPIDTRIG=NOPIDTRIG, NEWCONFIG=NEWCONFIG, DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, COMPRESS=COMPRESS, BOOLE_DATA=BOOLE_DATA, MOOREHLT2_DATA=MOOREHLT2_DATA, BRUNEL_DATA=BRUNEL_DATA, BRUNEL_ROOT=BRUNEL_ROOT))
stage_dict.append(
    {
        'name': 'Brunel',
        'script': BRUNEL_SCRIPT,
        'call_string': 'lb-run -c best Brunel/{BRUNEL_VERSION} gaudirun.py {BRUNEL_SCRIPT} | tee {BRUNEL_LOG}'.format(BRUNEL_VERSION=BRUNEL_VERSION, BRUNEL_SCRIPT=BRUNEL_SCRIPT, BRUNEL_LOG=BRUNEL_LOG),
        'to_remove': [MOOREHLT2_DATA],
        'data': BRUNEL_DATA,
        'run': STAGE_BRUNEL
    }
)

# -- DaVinci script
if STAGE_DAVINCI:
    with open(GENERAL_LOG, 'a') as f:
        f.write("making davinci script\n")
    stage_makedirs(DAVINCI_DIR)
    with open(DAVINCI_SCRIPT, 'w') as f:
        f.write('''\
from Gaudi.Configuration import *
from Configurables import DaVinci, LHCbApp, DumpFSR
importOptions("$APPCONFIGOPTS/DaVinci/DV-Stripping{STRIPPING_VERSION}-Stripping-MC-NoPrescaling-DST.py")
importOptions("$APPCONFIGOPTS/DaVinci/DataType-2016.py")
importOptions("$APPCONFIGOPTS/DaVinci/InputType-DST.py")
if {NOPIDTRIG}:
    from Configurables import ConfigCDBAccessSvc
    ConfigCDBAccessSvc().File = '{NEWCONFIG}'

DaVinci().DDDBtag   = "{DDDB_VERSION}"
DaVinci().CondDBtag = "{CONDB_VERSION}"
DaVinci().Simulation = True
DaVinci().HistogramFile = "{DAVINCI_ROOT}"
DaVinci().EvtMax = -1
DaVinci().ProductionType = "Stripping"
DaVinci().InputType = 'DST'
DaVinci().Lumi = False
DaVinci().MoniSequence += [DumpFSR()]  # adjusts the monitoring sequence

from Configurables import TimingAuditor, SequencerTimerTool
TimingAuditor().addTool(SequencerTimerTool,name="TIMER")
TimingAuditor().TIMER.NameSize = 60

DumpFSR().OutputLevel = 3
DumpFSR().AsciiFileName = "dumpfsr_check_output.txt"

from GaudiConf import IOHelper
IOHelper().inputFiles(["{BRUNEL_DATA}"],clear=True)
# OutputStream("DstWriter").Output     =  "DATAFILE='PFN:{DAVINCI_DATA}' TYP='POOL_ROOTTREE' OPT='RECREATE'"  # Doesn't actually do anything
'''.format(STRIPPING_VERSION=STRIPPING_VERSION, NOPIDTRIG=NOPIDTRIG, NEWCONFIG=NEWCONFIG, DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, DAVINCI_ROOT=DAVINCI_ROOT, BRUNEL_DATA=BRUNEL_DATA, DAVINCI_DATA=DAVINCI_DATA))
stage_dict.append(
    {
        'name': 'DaVinci',
        'script': DAVINCI_SCRIPT,
        'call_string': 'lb-run -c best DaVinci/{DAVINCI_STRIPPING_VERSION} gaudirun.py {DAVINCI_SCRIPT} | tee {DAVINCI_LOG}'.format(DAVINCI_STRIPPING_VERSION=DAVINCI_STRIPPING_VERSION, DAVINCI_SCRIPT=DAVINCI_SCRIPT, DAVINCI_LOG=DAVINCI_LOG),
        'to_remove': [BRUNEL_DATA],
        'data': DAVINCI_DATA,
        'run': STAGE_DAVINCI
    }
)

# -- allstuple script
if STAGE_ALLSTUPLE:
    with open(GENERAL_LOG, 'a') as f:
        f.write("making allstuple script\n")
    stage_makedirs(ALLSTUPLE_DIR)
    if os.path.basename(TUPOPTS) != 'LcLc.py':
        raise Exception('script designed with LcLc.py in mind, i.e., it writes steering.py in a particular way. You have selected {TUPOPTS}. See script.'.format(TUPOPTS=TUPOPTS))
    with open(opj(os.path.dirname(ALLSTUPLE_SCRIPT), 'steering.py'), 'w') as f:  # picked up by LcLc.py aka TUPOPTS aka ALLSTUPLE_SCRIPT
        f.write('''\
MC = True
devMC = True
testing = False
smalltest = False
MCtruthonly = False
Lconly = False
year = '2016'
dbtag = '{DDDB_VERSION}'
cdbtag = '{CONDB_VERSION}'
condor_run = ['{DAVINCI_DATA}']
tuplename = '{ALLSTUPLE_DATA}'
newTCK = {NEWCONFIGorNone}
restripped = False
'''.format(DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, DAVINCI_DATA=DAVINCI_DATA, ALLSTUPLE_DATA=ALLSTUPLE_DATA, NEWCONFIGorNone='"{0}"'.format(NEWCONFIG) if NOPIDTRIG else None)
        )
    shutil.copyfile(TUPOPTS, ALLSTUPLE_SCRIPT)  # use pre-written options file rather than writing a new one
stage_dict.append(
    {
        'name': 'allstuple',
        'script': ALLSTUPLE_SCRIPT,
        'call_string': 'lb-run -c best DaVinci/{DAVINCI_TUPLE_VERSION} gaudirun.py {ALLSTUPLE_SCRIPT} | tee {ALLSTUPLE_LOG}'.format(DAVINCI_TUPLE_VERSION=DAVINCI_TUPLE_VERSION, ALLSTUPLE_SCRIPT=ALLSTUPLE_SCRIPT, ALLSTUPLE_LOG=ALLSTUPLE_LOG),
        'to_remove': [],  # bad idea to delete DST...
        'data': ALLSTUPLE_DATA,
        'run': STAGE_ALLSTUPLE
    }
)

# -- restrip script
if STAGE_RESTRIP:
    with open(GENERAL_LOG, 'a') as f:
        f.write("making restrip script\n")
    stage_makedirs(RESTRIP_DIR)
    with open(RESTRIP_SCRIPT, 'w') as f:
        f.write('''\
from Gaudi.Configuration import *
from Configurables import DaVinci
from DSTWriters.microdstelements import *
from DSTWriters.Configuration import (SelDSTWriter,
                                      stripDSTStreamConf,
                                      stripDSTElements
                                      )
from Configurables import DaVinciInit
from Gaudi.Configuration import *
from GaudiConf import IOHelper
from StrippingConf.Configuration import StrippingConf
from StrippingSettings.Utils import strippingConfiguration
from StrippingArchive.Utils import buildStreams
from StrippingArchive import strippingArchive
import shelve
from Configurables import ProcStatusCheck
from Configurables import StrippingReport
from Configurables import EventNodeKiller
if {NOPIDTRIG}:
    from Configurables import ConfigCDBAccessSvc
    ConfigCDBAccessSvc().File = '{NEWCONFIG}'

stripping = 'stripping{STRIPPING_VERSION}'
# get the configuration dictionary from the database
config_db = strippingConfiguration(stripping)
config = dict(config_db)  # need to do this since the config_db is read-only
config['PromptCharm']['CONFIG']['NOPIDHADRONS'] = True
config_db_updated = shelve.open('tmp_stripping_config.db')
config_db_updated.update(config)
# get the line builders from the archive
archive = strippingArchive(stripping)
myWG = "BandQ"

streams = buildStreams(stripping=config_db_updated, archive=archive, WGs=myWG)

filterBadEvents = ProcStatusCheck()

sc = StrippingConf(Streams=streams,
                   MaxCandidates=2000,
                   AcceptBadEvents=False,
                   BadEventSelection=filterBadEvents,
                   TESPrefix='Strip' )

sr = StrippingReport(Selections=sc.selections())
sr.OnlyPositive = False
location = ''

# Need to remove stripping banks (if stripping has previously been run)
eventNodeKiller = EventNodeKiller('Stripkiller')
eventNodeKiller.Nodes = ['/Event/AllStreams', '/Event/Strip' ]

##################################################################
# If we want to write a DST do this
##################################################################
SelDSTWriterElements = {{
    'default': stripDSTElements()
}}
SelDSTWriterConf = {{
    'default': stripDSTStreamConf()
}}
dstWriter = SelDSTWriter("MyDSTWriter",
                         StreamConf=SelDSTWriterConf,
                         MicroDSTElements=SelDSTWriterElements,
                         OutputFileSuffix='RestrippedMC',
                         SelectionSequences=sc.activeStreams()
                         )

######################
# DAVINCI SETTINGS
######################

DaVinci().SkipEvents = 0
DaVinci().PrintFreq = 1000
DaVinci().EvtMax = -1
DaVinci().InputType = "DST"
DaVinci().DDDBtag   = "{DDDB_VERSION}"
DaVinci().CondDBtag = "{CONDB_VERSION}"
DaVinci().Simulation = True
DaVinci().HistogramFile = "{RESTRIP_ROOT}"
DaVinci().Lumi = False
DaVinci().DataType = "2016"
DaVinci().appendToMainSequence([eventNodeKiller])
DaVinci().appendToMainSequence([sc.sequence()])
DaVinci().appendToMainSequence([sr])
DaVinci().appendToMainSequence([dstWriter.sequence()])

DaVinciInit().OutputLevel = ERROR
MessageSvc().Format = "% F%60W%S%7W%R%T %0W%M"

IOHelper().inputFiles(["{DAVINCI_DATA}"],clear=True)
# OutputStream("DstWriter").Output     =  "DATAFILE='PFN:{RESTRIP_DATA}' TYP='POOL_ROOTTREE' OPT='RECREATE'"  # doesn't actually do anything

'''.format(NOPIDTRIG=NOPIDTRIG, STRIPPING_VERSION=STRIPPING_VERSION, NEWCONFIG=NEWCONFIG, DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, DAVINCI_DATA=DAVINCI_DATA, RESTRIP_ROOT=RESTRIP_ROOT, RESTRIP_DATA=RESTRIP_DATA))
stage_dict.append(
    {
        'name': 'restrip',
        'script': RESTRIP_SCRIPT,
        'call_string': 'lb-run -c best DaVinci/{DAVINCI_STRIPPING_VERSION} gaudirun.py {RESTRIP_SCRIPT} | tee {RESTRIP_LOG}'.format(DAVINCI_STRIPPING_VERSION=DAVINCI_STRIPPING_VERSION, RESTRIP_SCRIPT=RESTRIP_SCRIPT, RESTRIP_LOG=RESTRIP_LOG),
        'to_remove': [opj(WORK_DIR, x) for x in ['tmp_stripping_config.db', 'RestrippedMC.Bhadron.dst', 'RestrippedMC.BhadronCompleteEvent.dst', 'RestrippedMC.Leptonic.dst', 'RestrippedMC.CharmCompleteEvent.dst', 'RestrippedMC.Radiative.dst', 'RestrippedMC.Dimuon.dst']],  # do not delete initial DaVinci output, do delete extra streams (trying to stop their generation produced errors, but they aren't needed), do delete file created by shelve
        'data': RESTRIP_DATA,
        'run': STAGE_RESTRIP
    }
)

# -- tuple script
if STAGE_TUPLE:
    with open(GENERAL_LOG, 'a') as f:
        f.write("making tuple script\n")
    stage_makedirs(TUPLE_DIR)
    if os.path.basename(TUPOPTS) != 'LcLc.py':
        raise Exception('script designed with LcLc.py in mind, i.e., it writes steering.py in a particular way. You have selected {TUPOPTS}. See script.'.format(TUPOPTS=TUPOPTS))
    with open(opj(os.path.dirname(TUPLE_SCRIPT), 'steering.py'), 'w') as f:  # picked up by LcLc.py/TUPOPTS/TUPLE_SCRIPT
        f.write('''\
MC = True
devMC = True
testing = False
smalltest = False
MCtruthonly = False
Lconly = False
year = '2016'
dbtag = '{DDDB_VERSION}'
cdbtag = '{CONDB_VERSION}'
condor_run = ['{RESTRIP_DATA}']
tuplename = '{TUPLE_DATA}'
newTCK = {NEWCONFIGorNone}
restripped = True
'''.format(DDDB_VERSION=DDDB_VERSION, CONDB_VERSION=CONDB_VERSION, RESTRIP_DATA=RESTRIP_DATA, TUPLE_DATA=TUPLE_DATA, NEWCONFIGorNone='"{0}"'.format(NEWCONFIG) if NOPIDTRIG else None)
        )
    shutil.copyfile(TUPOPTS, TUPLE_SCRIPT)  # use pre-written options file rather than writing a new one
stage_dict.append(
    {
        'name': 'tuple',
        'script': TUPLE_SCRIPT,
        'call_string': 'lb-run -c best DaVinci/{DAVINCI_TUPLE_VERSION} gaudirun.py {TUPLE_SCRIPT} | tee {TUPLE_LOG}'.format(DAVINCI_TUPLE_VERSION=DAVINCI_TUPLE_VERSION, TUPLE_SCRIPT=TUPLE_SCRIPT, TUPLE_LOG=TUPLE_LOG),
        'to_remove': [],  # bad idea to delete DST...
        'data': TUPLE_DATA,
        'run': STAGE_TUPLE
    }
)

# -- slim script
if STAGE_SLIM:
    with open(GENERAL_LOG, 'a') as f:
        f.write("making slim script\n")
    stage_makedirs(SLIM_DIR)
    if os.path.basename(SLIMOPTS[0]) != 'prep_files.py':
        raise Exception('script designed with prep_files.py in mind, i.e., it uses particular commandline options. You have selected {SLIMOPTS}. See script.'.format(SLIMOPTS=SLIMOPTS))
    shutil.copyfile(SLIMOPTS[0], SLIM_SCRIPT)  # use pre-written slim file rather than writing a new one
    shutil.copytree(SLIMOPTS[1], opj(SLIM_DIR, SLIMOPTS[1].strip('/').split('/')[-1]))  # use pre-written slim import directory rather than writing a new one
stage_dict.append(
    {
        'name': 'slim',
        'script': SLIM_SCRIPT,
        'call_string': 'lb-run -c best DaVinci/{DAVINCI_TUPLE_VERSION} python {SLIM_SCRIPT} MC 16 --failgracefully --outfolder {SLIM_DATA} --input {TUPLE_DATA} X2LcLcTree/DecayTree --logfilename {SLIM_LOG}'.format(DAVINCI_TUPLE_VERSION=DAVINCI_TUPLE_VERSION, SLIM_SCRIPT=SLIM_SCRIPT, SLIM_DATA=SLIM_DATA, TUPLE_DATA=TUPLE_DATA, SLIM_LOG=SLIM_LOG),
        'to_remove': [],  # bad idea to delete tuple file...
        'data': SLIM_DATA,
        'run': STAGE_SLIM
    }
)

if SCRIPT_ONLY:
    with open(GENERAL_LOG, 'a') as f:
        f.write("SCRIPT_ONLY option used. Goodbye!\n")
    sys.exit()

# -- Run Scripts
for istage, stage in enumerate(stage_dict):
    if not stage['run']:
        with open(GENERAL_LOG, 'a') as f:
            f.write('{name} stage not selected to run. Next stage...\n'.format(name=stage['name']))
        continue
    
    with open(GENERAL_LOG, 'a') as f:
        f.write('''starting {name} stage

======================= {name} script ============\n'''.format(name=stage['name']))
        with open(stage['script'], 'r') as fin:
            f.writelines(fin.readlines())

    if PRECLEANED and istage > 0:
        wkfile = stage_dict[istage - 1]['data']
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
            
    if istage == 0 or os.path.isfile(stage_dict[istage - 1]['data']):
        safecall(PRE_SCRIPT + ' && ' + stage['call_string'])
    else:
        with open(GENERAL_LOG, 'a') as f:
            f.write("\nCannot find {data}\n".format(data=stage_dict[istage - 1]['data']))
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

# -- mv files to final location and cleanup
if CLEANWORK:
    with open(GENERAL_LOG, 'a') as f:
        f.write(str(os.listdir(WORK_DIR)))
    for datafile in [x['data'] for x in stage_dict]:
        if os.path.exists(datafile):
            shutil_safemove(datafile, DATA_DIR, diroverride=True)
    for f in os.listdir(WORK_DIR):
        if os.path.isfile(f):
            shutil_safemove(f, LOG_DIR)
            
    os.chdir('../')
    shutil.rmtree(WORK_DIR)
