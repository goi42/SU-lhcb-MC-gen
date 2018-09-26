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
cleangroup.add_argument('--PRECLEANED', action='store_true',
                        help='if this script has already been run with CLEANWORK active, you can specify this argument so that it moves appropriate files to the work directory first')
cleangroup.add_argument('--SOME_MISSING', action='store_true',
                        help='if running a later stage, you may specify this argument to let the script terminate without errors if the input files are missing')
debuggroup = parser.add_argument_group('debugging options')
debuggroup.add_argument('--SCRIPT_ONLY', action='store_true',
                        help='creates scripts without running them')
debuggroup.add_argument('--WORK_DIR_EXISTS', action='store_true',
                        help='BE VERY CAREFUL WHEN USING THIS FLAG: gives permission to run if WORK_DIR already exists! Also allows overwrite of extant Opts directories.')

# -- evaluate and check arguments -- #
# -- mandatory section -- #
args = parser.parse_args() if basename(__main__.__file__) == 'run_stages.py' else parser.parse_known_args()[0]  # assume all arguments are for this script if 'run_stages.py' is the main file, else allow arguments to go to other scripts
for arg in vars(args):
    exec('{ARG} = args.{ARG}'.format(ARG=arg))  # eliminate need to reference things as arg.thing
# -- end mandatory section -- #


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
GaussGen.FirstEventNumber = 1
GaussGen.OutputLevel      = 4
LHCbApp().EvtMax          = 100
LHCbApp().DDDBtag         = "dddb-20170721-3"
LHCbApp().CondDBtag       = "sim-20170721-2-vc-md100"

OutputStream("GaussTape").Output = "DATAFILE='PFN:{GAUSS_DATA}' TYP='POOL_ROOTTREE' OPT='RECREATE'"

importOptions("$APPCONFIGOPTS/Gauss/Beam6500GeV-md100-2016-nu1.6.py")
importOptions("$APPCONFIGOPTS/Gauss/EnableSpillover-25ns.py")
importOptions("$APPCONFIGOPTS/Gauss/DataType-2016.py")
importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")  # makes for faster writing if the intention is to delete the output
importOptions("$DECFILESROOT/options/15264011.py")  # needs to be called BEFORE setting up Pythia8, else will use Pythia6 production tool
importOptions("$LBPYTHIA8ROOT/options/Pythia8.py")
# importOptions("$GAUSSOPTS/Gauss-2016.py")  # would overwrite some options set above

HistogramPersistencySvc().OutputFile = "{GAUSS_ROOT}"

'''.format(RUN_NUMBER=RUN_NUMBER, GAUSS_DATA=GAUSS_DATA, GAUSS_ROOT=GAUSS_ROOT)
    stage_list.append(
        {
            'name': GAUSS_STAGE_NAME,
            'scripts': {GAUSS_SCRIPT_NAME: GAUSS_SCRIPT_CONTENT},
            'log': GAUSS_LOG,
            'call_string': 'lb-run -c best Gauss/v49r10 gaudirun.py {GAUSS_SCRIPT_NAME}'.format(GAUSS_SCRIPT_NAME=GAUSS_SCRIPT_NAME),
            'to_remove': [],
            'dataname': GAUSS_DATA,
            'run': True,
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

LHCbApp().DDDBtag   = "dddb-20170721-3"
LHCbApp().CondDBtag = "sim-20170721-2-vc-md100"

EventSelector().Input                = ["DATAFILE='PFN:{GAUSS_DATA}' TYP='POOL_ROOTTREE' OPT='READ'"]
OutputStream("DigiWriter").Output    =  "DATAFILE='PFN:{BOOLE_DATA}' TYP='POOL_ROOTTREE' OPT='RECREATE'"
HistogramPersistencySvc().OutputFile = "{BOOLE_ROOT}"


# Boole().DigiType     = "Extended"
# Boole().OutputLevel  = INFO

importOptions("$APPCONFIGOPTS/Boole/Default.py")
importOptions("$APPCONFIGOPTS/Boole/EnableSpillover.py")
# importOptions("$APPCONFIGOPTS/Boole/Boole-SiG4EnergyDeposit.py")  # switch off all geometry (and related simulation) save that of calorimeters area
importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")  # makes for faster writing if the intention is to delete the output
importOptions("$APPCONFIGOPTS/Boole/DataType-2015.py")  # there is no 2016 available
importOptions("$APPCONFIGOPTS/Boole/Boole-SetOdinRndTrigger.py")  # idk whether this is good or necessary

L0Conf().TCK = '0x160F'
FileCatalog().Catalogs = [ "xmlcatalog_file:NewCatalog.xml" ]
'''.format(GAUSS_DATA=GAUSS_DATA, BOOLE_DATA=BOOLE_DATA, BOOLE_ROOT=BOOLE_ROOT)
    stage_list.append(
        {
            'name': BOOLE_STAGE_NAME,
            'scripts': {BOOLE_SCRIPT_NAME: BOOLE_SCRIPT_CONTENT},
            'log': BOOLE_LOG,
            'call_string': 'lb-run -c best Boole/v30r2p1 gaudirun.py {BOOLE_SCRIPT_NAME}'.format(BOOLE_SCRIPT_NAME=BOOLE_SCRIPT_NAME),
            'to_remove': [GAUSS_DATA],
            'dataname': BOOLE_DATA,
            'run': True,
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
importOptions("$APPCONFIGOPTS/L0App/L0AppTCK-0x160F.py")
# importOptions("$APPCONFIGOPTS/L0App/ForceLUTVersionV8.py")  # prefer to let this default
importOptions("$APPCONFIGOPTS/L0App/DataType-2016.py")
importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")

L0App().DDDBtag   = "dddb-20170721-3"
L0App().CondDBtag = "sim-20170721-2-vc-md100"

#####
L0App().Simulation = True
# L0Conf().L0MuonForceLUTVersion = "V8"  # see above
#####

L0App().TCK = '0x160F'
L0App().ReplaceL0Banks = False
L0App().EvtMax = -1

from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles(['{BOOLE_DATA}'],clear=True)
#HistogramPersistencySvc().OutputFile = "{MOOREL0_ROOT}"
L0App().outputFile = '{MOOREL0_DATA}'

'''.format(BOOLE_DATA=BOOLE_DATA, MOOREL0_ROOT=MOOREL0_ROOT, MOOREL0_DATA=MOOREL0_DATA)
    stage_list.append(
        {
            'name': MOOREL0_STAGE_NAME,
            'scripts': {MOOREL0_SCRIPT_NAME: MOOREL0_SCRIPT_CONTENT},
            'log': MOOREL0_LOG,
            'call_string': 'lb-run -c best Moore/v25r4 gaudirun.py {MOOREL0_SCRIPT_NAME}'.format(MOOREL0_SCRIPT_NAME=MOOREL0_SCRIPT_NAME),
            'to_remove': [BOOLE_DATA],
            'dataname': MOOREL0_DATA,
            'run': True,
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
importOptions("$APPCONFIGOPTS/Conditions/TCK-0x5138160F.py")
importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")
importOptions("$APPCONFIGOPTS/Moore/MooreSimProductionHlt1.py")
importOptions("$APPCONFIGOPTS/Moore/DataType-2016.py")


Moore().Split = 'Hlt1'
Moore().CheckOdin = False
Moore().WriterRequires = []
Moore().Simulation = True

Moore().DDDBtag   = "dddb-20170721-3"
Moore().CondDBtag = "sim-20170721-2-vc-md100"

Moore().EvtMax     = -1
from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles(['{MOOREL0_DATA}'],clear=True)
#HistogramPersistencySvc().OutputFile = "{MOOREHLT1_ROOT}"
Moore().outputFile = '{MOOREHLT1_DATA}'

'''.format(MOOREL0_DATA=MOOREL0_DATA, MOOREHLT1_ROOT=MOOREHLT1_ROOT, MOOREHLT1_DATA=MOOREHLT1_DATA)
    stage_list.append(
        {
            'name': MOOREHLT1_STAGE_NAME,
            'scripts': {MOOREHLT1_SCRIPT_NAME: MOOREHLT1_SCRIPT_CONTENT},
            'log': MOOREHLT1_LOG,
            'call_string': 'lb-run -c best Moore/v25r4 gaudirun.py {MOOREHLT1_SCRIPT_NAME}'.format(MOOREHLT1_SCRIPT_NAME=MOOREHLT1_SCRIPT_NAME),
            'to_remove': [MOOREL0_DATA],
            'dataname': MOOREHLT1_DATA,
            'run': True,
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
importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")
importOptions("$APPCONFIGOPTS/Moore/MooreSimProductionHlt2.py")
#--- END ---#

importOptions("$APPCONFIGOPTS/Conditions/TCK-0x6139160F.py")

Moore().Split = 'Hlt2'
Moore().CheckOdin = False
Moore().WriterRequires = []
Moore().Simulation = True
Moore().DDDBtag   = "dddb-20170721-3"
Moore().CondDBtag = "sim-20170721-2-vc-md100"
Moore().EvtMax = -1
from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles(['{MOOREHLT1_DATA}'],clear=True)

Moore().outputFile = '{MOOREHLT2_DATA}'

'''.format(MOOREHLT1_DATA=MOOREHLT1_DATA, MOOREHLT2_DATA=MOOREHLT2_DATA)
    stage_list.append(
        {
            'name': MOOREHLT2_STAGE_NAME,
            'scripts': {MOOREHLT2_SCRIPT_NAME: MOOREHLT2_SCRIPT_CONTENT},
            'log': MOOREHLT2_LOG,
            'call_string': 'lb-run -c best Moore/v25r4 gaudirun.py {MOOREHLT2_SCRIPT_NAME}'.format(MOOREHLT2_SCRIPT_NAME=MOOREHLT2_SCRIPT_NAME),
            'to_remove': [MOOREHLT1_DATA],
            'dataname': MOOREHLT2_DATA,
            'run': True,
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

LHCbApp().DDDBtag   = "dddb-20170721-3"
LHCbApp().CondDBtag = "sim-20170721-2-vc-md100"

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


'''.format(BOOLE_DATA=BOOLE_DATA, MOOREHLT2_DATA=MOOREHLT2_DATA, BRUNEL_DATA=BRUNEL_DATA, BRUNEL_ROOT=BRUNEL_ROOT)
    stage_list.append(
        {
            'name': BRUNEL_STAGE_NAME,
            'scripts': {BRUNEL_SCRIPT_NAME: BRUNEL_SCRIPT_CONTENT},
            'log': BRUNEL_LOG,
            'call_string': 'lb-run -c best Brunel/v50r3 gaudirun.py {BRUNEL_SCRIPT_NAME}'.format(BRUNEL_SCRIPT_NAME=BRUNEL_SCRIPT_NAME),
            'to_remove': [MOOREHLT2_DATA],
            'dataname': BRUNEL_DATA,
            'run': True,
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
importOptions("$APPCONFIGOPTS/DaVinci/DV-Stripping28r1-Stripping-MC-NoPrescaling-DST.py")
importOptions("$APPCONFIGOPTS/DaVinci/DataType-2016.py")
importOptions("$APPCONFIGOPTS/DaVinci/InputType-DST.py")

DaVinci().DDDBtag   = "dddb-20170721-3"
DaVinci().CondDBtag = "sim-20170721-2-vc-md100"
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
'''.format(DAVINCI_ROOT=DAVINCI_ROOT, BRUNEL_DATA=BRUNEL_DATA, DAVINCI_DATA=DAVINCI_DATA)
    stage_list.append(
        {
            'name': DAVINCI_STAGE_NAME,
            'scripts': {DAVINCI_SCRIPT_NAME: DAVINCI_SCRIPT_CONTENT},
            'log': DAVINCI_LOG,
            'call_string': 'lb-run -c best DaVinci/v41r4p4 gaudirun.py {DAVINCI_SCRIPT_NAME}'.format(DAVINCI_SCRIPT_NAME=DAVINCI_SCRIPT_NAME),
            'to_remove': [BRUNEL_DATA],
            'dataname': DAVINCI_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )
    
    return stage_list
