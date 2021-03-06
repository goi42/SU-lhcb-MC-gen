#!/usr/bin/env python2
import os
from os.path import join as opj, basename
import argparse
import __main__

# -- essential parameters -- #
parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='set parameters to be used in run_stages.py')

parser.add_argument('configfile', type=os.path.abspath,
                    help='this argument must be here to ensure integration with run_stages.py')
parser.add_argument('--SIGNAL_NAME', default='TestProduction')
parser.add_argument('--RUN_NUMBER', type=int, default=300000)
parser.add_argument('--RUN_SYS', default='/data2', type=os.path.abspath,
                    help='system to run on')
cleangroup = parser.add_argument_group('cleaning options')
cleangroup.add_argument('--noCLEANSTAGES', dest='CLEANSTAGES', action='store_false',
                        help='deletes data from earlier stages as it goes.')
cleangroup.add_argument('--noCLEANWORK', dest='CLEANWORK', action='store_false',
                        help='moves files out of work directory.')
cleangroup.add_argument('--SOME_MISSING', action='store_true',
                        help='if running a later stage, you may specify this argument to let the script terminate without errors if the input files are missing')
debuggroup = parser.add_argument_group('debugging options')
debuggroup.add_argument('--SCRIPT_ONLY', action='store_true',
                        help='creates scripts without running them')
debuggroup.add_argument('--WORK_DIR_EXISTS', action='store_true',
                        help='BE VERY CAREFUL WHEN USING THIS FLAG: gives permission to run if WORK_DIR already exists!')

# -- parameters used for make_stage_list -- #
# GEN_LEVEL choices, used in ChoicesInList and argument declaration below
exclusive_choices = ['all', 'none']  # cannot have more than one of these and cannot use these with other_choices; set GEL_LEVEL to other_choices or [], respectively
other_choices = ['gauss', 'boole', 'moorel0', 'moorehlt1', 'moorehlt2', 'brunel', 'davinci']
valid_choices = exclusive_choices + other_choices


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
        # -- handle 'all' and 'none'
        if values == ['all']:
            values = other_choices
        elif values == ['none']:
            values = []
        
        setattr(args, self.dest, values)


# general
parser.add_argument('--GEN_LEVEL', nargs='*', default=other_choices, action=ChoicesInList, type=str.lower, choices=valid_choices,  # valid_choices is set in the ChoicesInList declaration above
                    help='select what stages to run')
stagegroup = parser.add_argument_group('general parameters used by stages')
stagegroup.add_argument('--DDDB_TAG', default='dddb-20170721-3',)
stagegroup.add_argument('--CONDDB_TAG', default='sim-20170721-2-vc-md100',)
stagegroup.add_argument('--noCOMPRESS', dest='COMPRESS', action='store_false',
                        help='usually runs with compression option optimized for deletion of intermediate stages; this turns that off')
allowedpols = ['md', 'mu']
stagegroup.add_argument('--MAGNETPOLARITY', default=None, choices=allowedpols,
                        help='ensures CONDB_VERSION and BEAM_VERSION use mu or md as appropriate for the specified polarity, e.g., replaces "mu" with "md".')
# Gauss
gaussgroup = parser.add_argument_group('Gauss parameters')
gaussgroup.add_argument('--GAUSS_VERSION', default='v49r10')
gaussgroup.add_argument('--EVENT_TYPE', type=int, default=15264011)
gaussgroup.add_argument('--FIRST_EVENT', type=int, default=1)
gaussgroup.add_argument('--NUM_EVENT', help='number of events to generate per job', type=int, default=100)
gaussgroup.add_argument('--BEAM_VERSION', default='Beam6500GeV-md100-2016-nu1.6.py')
# Boole
boolegroup = parser.add_argument_group('Boole parameters')
boolegroup.add_argument('--BOOLE_VERSION', default='v30r2p1')
# Moore
mooregroup = parser.add_argument_group('Moore parameters')
mooregroup.add_argument('--MOORE_VERSION', default='v25r4')
# Moore L0
moorel0group = parser.add_argument_group('Moore L0 parameters')
moorel0group.add_argument('--MOOREL0_TCK', default='0x160F')
# Moore HLT1
moorehlt1group = parser.add_argument_group('Moore HLT1 parameters')
moorehlt1group.add_argument('--MOOREHLT1_TCK', default='0x5138160F')
# Moore HLT1
moorehlt2group = parser.add_argument_group('Moore HLT2 parameters')
moorehlt2group.add_argument('--MOOREHLT2_TCK', default='0x6139160F')
# Brunel
brunelgroup = parser.add_argument_group('Brunel parameters')
brunelgroup.add_argument('--BRUNEL_VERSION', default='v50r3')
# DaVinci
strippinggroup = parser.add_argument_group('Stripping parameters')
strippinggroup.add_argument('--DAVINCI_VERSION', default='v41r4p4')
strippinggroup.add_argument('--STRIPPING_CAMPAIGN', default='28r1')

# -- evaluate and check arguments -- #
# -- mandatory section -- #
args = parser.parse_args() if basename(__main__.__file__) == 'run_stages.py' else parser.parse_known_args()[0]  # assume all arguments are for this script if 'run_stages.py' is the main file, else allow arguments to go to other scripts
for arg in vars(args):
    exec('{ARG} = args.{ARG}'.format(ARG=arg))  # eliminate need to reference things as arg.thing
# -- end mandatory section -- #


if MAGNETPOLARITY is not None:
    if not len(allowedpols) == 2:
        raise Exception('something has gone wrong in the script. There should only be 2 allowed polarities.')
    rightpol = MAGNETPOLARITY
    wrongpol = allowedpols[0] if allowedpols.index(rightpol) == 1 else allowedpols[1]
    for thingtocheck_string in ('CONDDB_TAG', 'BEAM_VERSION'):
        if eval(thingtocheck_string).count(wrongpol) > 1:
            raise parser.error('{TH} ({THSTR}) has {POL} appearing more than once!'.format(TH=eval(thingtocheck_string), THSTR=thingtocheck_string, POL=wrongpol))
        exec('{THSTR} = {THSTR}.replace(wrongpol, rightpol)'.format(THSTR=thingtocheck_string))
        if eval(thingtocheck_string).count(rightpol) != 1:
            raise parser.error('{TH} ({THSTR}) does not contain exactly one appearance of {POL}!'.format(TH=eval(thingtocheck_string), THSTR=thingtocheck_string, POL=rightpol))


# -- create stage_list (mandatory function) -- #
def make_stage_list(USER, BASE_NAME):  # DO NOT CHANGE THIS LINE
    from os.path import join as opj
    stage_list = []
    
    # -- Gauss stage -- #
    GAUSS_STAGE_NAME = 'gauss'
    GAUSS_DIR = 'GaussOpts'
    GAUSS_LOG = BASE_NAME + '_gauss.log'
    GAUSS_ROOT = BASE_NAME + '_gauss.root'
    GAUSS_SCRIPT_NAME = opj(GAUSS_DIR, 'myGauss.py')
    GAUSS_DATA = BASE_NAME + '_gauss.sim'
    GAUSS_SCRIPT_CONTENT = '''\
from Gauss.Configuration import *
from Configurables import LHCbApp, CondDB, Gauss

GaussGen                  = GenInit("GaussGen")
GaussGen.RunNumber        = {RUN_NUMBER}
GaussGen.FirstEventNumber = {FIRST_EVENT}
GaussGen.OutputLevel      = 4
LHCbApp().EvtMax          = {NUM_EVENT}
LHCbApp().DDDBtag         = "{DDDB_TAG}"
LHCbApp().CondDBtag       = "{CONDDB_TAG}"

OutputStream("GaussTape").Output = "DATAFILE='PFN:{GAUSS_DATA}' TYP='POOL_ROOTTREE' OPT='RECREATE'"

importOptions("$APPCONFIGOPTS/Gauss/{BEAM_VERSION}")
importOptions("$APPCONFIGOPTS/Gauss/EnableSpillover-25ns.py")
importOptions("$APPCONFIGOPTS/Gauss/DataType-2016.py")
if {COMPRESS}:  # COMPRESS option set in generation script
    importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")  # makes for faster writing if the intention is to delete the output
importOptions("$DECFILESROOT/options/{EVENT_TYPE}.py")  # needs to be called BEFORE setting up Pythia8, else will use Pythia6 production tool
importOptions("$LBPYTHIA8ROOT/options/Pythia8.py")
# importOptions("$GAUSSOPTS/Gauss-2016.py")  # would overwrite some options set above

HistogramPersistencySvc().OutputFile = "{GAUSS_ROOT}"

'''.format(RUN_NUMBER=RUN_NUMBER, FIRST_EVENT=FIRST_EVENT, NUM_EVENT=NUM_EVENT, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, GAUSS_DATA=GAUSS_DATA, BEAM_VERSION=BEAM_VERSION, COMPRESS=COMPRESS, EVENT_TYPE=EVENT_TYPE, GAUSS_ROOT=GAUSS_ROOT)
    stage_list.append(
        {
            'name': GAUSS_STAGE_NAME,
            'scripts': {GAUSS_SCRIPT_NAME: GAUSS_SCRIPT_CONTENT},
            'log': GAUSS_LOG,
            'call_string': 'lb-run -c best Gauss/{GAUSS_VERSION} gaudirun.py {GAUSS_SCRIPT_NAME}'.format(USER=USER, GAUSS_VERSION=GAUSS_VERSION, GAUSS_SCRIPT_NAME=GAUSS_SCRIPT_NAME),
            'to_remove': [],
            'required': [],
            'data': [GAUSS_DATA],
            'run': GAUSS_STAGE_NAME in GEN_LEVEL,
            'scriptonly': SCRIPT_ONLY,
        }
    )
    
    # -- Boole stage -- #
    BOOLE_STAGE_NAME = 'boole'
    BOOLE_DIR = 'BooleOpts'
    BOOLE_LOG = BASE_NAME + '_boole.log'
    BOOLE_ROOT = BASE_NAME + '_boole.root'
    BOOLE_SCRIPT_NAME = opj(BOOLE_DIR, 'myBoole.py')
    BOOLE_DATA = BASE_NAME + '_boole.digi'
    BOOLE_SCRIPT_CONTENT = '''\
from Gaudi.Configuration import *
from Configurables import LHCbApp, L0Conf, Boole

LHCbApp().DDDBtag   = "{DDDB_TAG}"
LHCbApp().CondDBtag = "{CONDDB_TAG}"

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
'''.format(DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, GAUSS_DATA=GAUSS_DATA, BOOLE_DATA=BOOLE_DATA, BOOLE_ROOT=BOOLE_ROOT, COMPRESS=COMPRESS, MOOREL0_TCK=MOOREL0_TCK)
    stage_list.append(
        {
            'name': BOOLE_STAGE_NAME,
            'scripts': {BOOLE_SCRIPT_NAME: BOOLE_SCRIPT_CONTENT},
            'log': BOOLE_LOG,
            'call_string': 'lb-run -c best Boole/{BOOLE_VERSION} gaudirun.py {BOOLE_SCRIPT_NAME}'.format(BOOLE_VERSION=BOOLE_VERSION, BOOLE_SCRIPT_NAME=BOOLE_SCRIPT_NAME),
            'to_remove': [GAUSS_DATA],
            'required': [GAUSS_DATA],
            'data': [BOOLE_DATA],
            'run': BOOLE_STAGE_NAME in GEN_LEVEL,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- MooreL0 stage -- #
    MOOREL0_STAGE_NAME = 'moorel0'
    MOOREL0_DIR = 'MooreOptsl0'
    MOOREL0_LOG = BASE_NAME + '_moorel0.log'
    MOOREL0_ROOT = BASE_NAME + '_moorel0.root'
    MOOREL0_SCRIPT_NAME = opj(MOOREL0_DIR, 'myMoorel0.py')
    MOOREL0_DATA = BASE_NAME + '_moorel0.digi'
    MOOREL0_SCRIPT_CONTENT = '''\
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

L0App().DDDBtag   = "{DDDB_TAG}"
L0App().CondDBtag = "{CONDDB_TAG}"

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

'''.format(MOOREL0_TCK=MOOREL0_TCK, COMPRESS=COMPRESS, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, BOOLE_DATA=BOOLE_DATA, MOOREL0_ROOT=MOOREL0_ROOT, MOOREL0_DATA=MOOREL0_DATA)
    stage_list.append(
        {
            'name': MOOREL0_STAGE_NAME,
            'scripts': {MOOREL0_SCRIPT_NAME: MOOREL0_SCRIPT_CONTENT},
            'log': MOOREL0_LOG,
            'call_string': 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREL0_SCRIPT_NAME}'.format(MOORE_VERSION=MOORE_VERSION, MOOREL0_SCRIPT_NAME=MOOREL0_SCRIPT_NAME),
            'to_remove': [BOOLE_DATA],
            'required': [BOOLE_DATA],
            'data': [MOOREL0_DATA],
            'run': MOOREL0_STAGE_NAME in GEN_LEVEL,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- MooreHlt1 stage -- #
    MOOREHLT1_STAGE_NAME = 'moorehlt1'
    MOOREHLT1_DIR = 'MooreOptshlt1'
    MOOREHLT1_LOG = BASE_NAME + '_moorehlt1.log'
    MOOREHLT1_ROOT = BASE_NAME + '_moorehlt1.root'
    MOOREHLT1_SCRIPT_NAME = opj(MOOREHLT1_DIR, 'myMoorehlt1.py')
    MOOREHLT1_DATA = BASE_NAME + '_moorehlt1.digi'
    MOOREHLT1_SCRIPT_CONTENT = '''\
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

Moore().DDDBtag   = "{DDDB_TAG}"
Moore().CondDBtag = "{CONDDB_TAG}"

Moore().EvtMax     = -1
from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles(['{MOOREL0_DATA}'],clear=True)
#HistogramPersistencySvc().OutputFile = "{MOOREHLT1_ROOT}"
Moore().outputFile = '{MOOREHLT1_DATA}'

'''.format(MOOREHLT1_TCK=MOOREHLT1_TCK, COMPRESS=COMPRESS, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, MOOREL0_DATA=MOOREL0_DATA, MOOREHLT1_ROOT=MOOREHLT1_ROOT, MOOREHLT1_DATA=MOOREHLT1_DATA)
    stage_list.append(
        {
            'name': MOOREHLT1_STAGE_NAME,
            'scripts': {MOOREHLT1_SCRIPT_NAME: MOOREHLT1_SCRIPT_CONTENT},
            'log': MOOREHLT1_LOG,
            'call_string': 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREHLT1_SCRIPT_NAME}'.format(MOORE_VERSION=MOORE_VERSION, MOOREHLT1_SCRIPT_NAME=MOOREHLT1_SCRIPT_NAME),
            'to_remove': [MOOREL0_DATA],
            'required': [MOOREL0_DATA],
            'data': [MOOREHLT1_DATA],
            'run': MOOREHLT1_STAGE_NAME in GEN_LEVEL,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- MooreHlt2 stage -- #
    MOOREHLT2_STAGE_NAME = 'moorehlt2'
    MOOREHLT2_DIR = 'MooreOptshlt2'
    MOOREHLT2_LOG = BASE_NAME + '_moorehlt2.log'
    MOOREHLT2_ROOT = BASE_NAME + '_moorehlt2.root'
    MOOREHLT2_SCRIPT_NAME = opj(MOOREHLT2_DIR, 'myMoorehlt2.py')
    MOOREHLT2_DATA = BASE_NAME + '_moorehlt2.digi'
    MOOREHLT2_SCRIPT_CONTENT = '''\
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

importOptions("$APPCONFIGOPTS/Conditions/TCK-{MOOREHLT2_TCK}.py")

Moore().Split = 'Hlt2'
Moore().CheckOdin = False
Moore().WriterRequires = []
Moore().Simulation = True
Moore().DDDBtag   = "{DDDB_TAG}"
Moore().CondDBtag = "{CONDDB_TAG}"
Moore().EvtMax = -1
from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles(['{MOOREHLT1_DATA}'],clear=True)

Moore().outputFile = '{MOOREHLT2_DATA}'

'''.format(COMPRESS=COMPRESS, MOOREHLT2_TCK=MOOREHLT2_TCK, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, MOOREHLT1_DATA=MOOREHLT1_DATA, MOOREHLT2_DATA=MOOREHLT2_DATA)
    stage_list.append(
        {
            'name': MOOREHLT2_STAGE_NAME,
            'scripts': {MOOREHLT2_SCRIPT_NAME: MOOREHLT2_SCRIPT_CONTENT},
            'log': MOOREHLT2_LOG,
            'call_string': 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREHLT2_SCRIPT_NAME}'.format(MOORE_VERSION=MOORE_VERSION, MOOREHLT2_SCRIPT_NAME=MOOREHLT2_SCRIPT_NAME),
            'to_remove': [MOOREHLT1_DATA],
            'required': [MOOREHLT1_DATA],
            'data': [MOOREHLT2_DATA],
            'run': MOOREHLT2_STAGE_NAME in GEN_LEVEL,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- Brunel stage -- #
    BRUNEL_STAGE_NAME = 'brunel'
    BRUNEL_DIR = 'BrunelOpts'
    BRUNEL_LOG = BASE_NAME + '_brunel.log'
    BRUNEL_ROOT = BASE_NAME + '_brunel.root'
    BRUNEL_SCRIPT_NAME = opj(BRUNEL_DIR, 'myBrunel.py')
    BRUNEL_DATA = BASE_NAME + '_brunel.dst'
    BRUNEL_SCRIPT_CONTENT = '''\
from Gaudi.Configuration import *
from Configurables import Brunel, LHCbApp, L0Conf

LHCbApp().DDDBtag   = "{DDDB_TAG}"
LHCbApp().CondDBtag = "{CONDDB_TAG}"

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


'''.format(DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, COMPRESS=COMPRESS, BOOLE_DATA=BOOLE_DATA, MOOREHLT2_DATA=MOOREHLT2_DATA, BRUNEL_DATA=BRUNEL_DATA, BRUNEL_ROOT=BRUNEL_ROOT)
    stage_list.append(
        {
            'name': BRUNEL_STAGE_NAME,
            'scripts': {BRUNEL_SCRIPT_NAME: BRUNEL_SCRIPT_CONTENT},
            'log': BRUNEL_LOG,
            'call_string': 'lb-run -c best Brunel/{BRUNEL_VERSION} gaudirun.py {BRUNEL_SCRIPT_NAME}'.format(BRUNEL_VERSION=BRUNEL_VERSION, BRUNEL_SCRIPT_NAME=BRUNEL_SCRIPT_NAME),
            'to_remove': [MOOREHLT2_DATA],
            'required': [MOOREHLT2_DATA],
            'data': [BRUNEL_DATA],
            'run': BRUNEL_STAGE_NAME in GEN_LEVEL,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- DaVinci stage -- #
    DAVINCI_STAGE_NAME = 'davinci'
    DAVINCI_DIR = 'DaVinciOpts'
    DAVINCI_LOG = BASE_NAME + '_davinci.log'
    DAVINCI_ROOT = BASE_NAME + '_davinci.root'
    DAVINCI_SCRIPT_NAME = opj(DAVINCI_DIR, 'myDavinci.py')
    DAVINCI_DATA = '000000.AllStreams.dst'  # this is produced by the script--do not modify unless the script change
    DAVINCI_SCRIPT_CONTENT = '''\
from Gaudi.Configuration import *
from Configurables import DaVinci, LHCbApp, DumpFSR
importOptions("$APPCONFIGOPTS/DaVinci/DV-Stripping{STRIPPING_CAMPAIGN}-Stripping-MC-NoPrescaling-DST.py")
importOptions("$APPCONFIGOPTS/DaVinci/DataType-2016.py")
importOptions("$APPCONFIGOPTS/DaVinci/InputType-DST.py")

DaVinci().DDDBtag   = "{DDDB_TAG}"
DaVinci().CondDBtag = "{CONDDB_TAG}"
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
'''.format(STRIPPING_CAMPAIGN=STRIPPING_CAMPAIGN, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, DAVINCI_ROOT=DAVINCI_ROOT, BRUNEL_DATA=BRUNEL_DATA, DAVINCI_DATA=DAVINCI_DATA)
    stage_list.append(
        {
            'name': DAVINCI_STAGE_NAME,
            'scripts': {DAVINCI_SCRIPT_NAME: DAVINCI_SCRIPT_CONTENT},
            'log': DAVINCI_LOG,
            'call_string': 'lb-run -c best DaVinci/{DAVINCI_VERSION} gaudirun.py {DAVINCI_SCRIPT_NAME}'.format(DAVINCI_VERSION=DAVINCI_VERSION, DAVINCI_SCRIPT_NAME=DAVINCI_SCRIPT_NAME),
            'to_remove': [BRUNEL_DATA],
            'required': [BRUNEL_DATA],
            'data': [DAVINCI_DATA],
            'run': DAVINCI_STAGE_NAME in GEN_LEVEL,
            'scriptonly': SCRIPT_ONLY,
        }
    )
    
    return stage_list
