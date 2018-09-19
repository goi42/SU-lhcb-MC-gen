#!/usr/bin/env python2
import os
from os.path import join as opj
import argparse
parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='set parameters to be used in Generate_LHCb_MC_2016.py')

# -- essential parameters -- #
parser.add_argument('configfile', type=str,
                    help='')
parser.add_argument('--SIGNAL_NAME', default='TestProduction')
parser.add_argument('--RUN_NUMBER', type=int, default=300000)
parser.add_argument('--RUN_SYS', default='/data2',
                    help='system to run on')
cleangroup = parser.add_argument_group('cleaning options')
cleangroup.add_argument('--CLEAN_UP', choices=['CLEANSTAGES', 'CLEANWORK', 'both', 'none'], default='both',
                        help='''CLEANSTAGES deletes data from earlier stages as it goes.
                             CLEANWORK moves files out of work directory.''')
cleangroup.add_argument('--PRECLEANED', action='store_true',
                        help='if this script has already been run, you can specify this argument so that it moves appropriate files to the work directory first')
cleangroup.add_argument('--SOME_MISSING', action='store_true',
                        help='if running a later stage, you may specify this argument to let the script terminate without errors if the input files are missing')
debuggroup = parser.add_argument_group('debugging options')
debuggroup.add_argument('--SCRIPT_ONLY', action='store_true',
                        help='creates scripts without running them')
debuggroup.add_argument('--WORK_DIR_EXISTS', action='store_true',
                        help='BE VERY CAREFUL WHEN USING THIS FLAG: gives permission to run if WORK_DIR already exists! Also allows overwrite of extant Opts directories.')

# -- parameters for make_stage_list -- #
# general
parser.add_argument('--GEN_LEVEL', default='all',
                    help='')
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
gaussgroup.add_argument('--EVENT_TYPE', type=int, default=28196040)
gaussgroup.add_argument('--FIRST_EVENT', type=int, default=1)
gaussgroup.add_argument('--NUM_EVENT', type=int, default=100)
gaussgroup.add_argument('--noREDECAY', dest='REDECAY', action='store_false',
                        help='turns off ReDecay (ReDecay 100 times by default) in GAUSS_SCRIPT')
gaussgroup.add_argument('--noRICHOFF', dest='RICHOFF', action='store_false',
                        help='activates RICH and Cherenkov photons in GAUSS_SCRIPT')
gaussgroup.add_argument('--noPYTHMOD', dest='PYTHMOD', action='store_false',
                        help='turns off Pythia modifications in GAUSS_SCRIPT')
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
moorehlt2group.add_argument('--noNOPIDTRIG', dest='NOPIDTRIG', action='store_false',
                            help='leaves PID active in HLT2 trigger lines (removes nopidtrig from the stage list AND tells later stages to use the original TCK)')
moorehlt2group.add_argument('--NEWCONFIG', default='/home/mwilkins/LcLc/MCgeneration/devrun/config.cdb',
                            help='config.cdb with new TCK inside to use if NOPIDTRIG active (active by default). Script assumes newtck = (oldtck | 0x0c000000)')
# Brunel
brunelgroup = parser.add_argument_group('Brunel parameters')
brunelgroup.add_argument('--BRUNEL_VERSION', default='v50r3')
# Stripping
strippinggroup = parser.add_argument_group('Stripping parameters')
strippinggroup.add_argument('--DAVINCI_STRIPPING_VERSION', default='v41r4p4')
strippinggroup.add_argument('--STRIPPING_CAMPAIGN', default='28r1')
# allstuple and tuple
tupgroup = parser.add_argument_group('Allstuple and Tuple parameters')
tupgroup.add_argument('--DAVINCI_TUPLE_VERSION', default='v42r6p1')
tupgroup.add_argument('--TUPOPTS', default='/home/mwilkins/LcLc/options/LcLc.py',
                      help='options script to-be-copied for tuple (AllStreams and otherwise) creation')
# slim
slimgroup = parser.add_argument_group('Slim parameters')
slimgroup.add_argument('--SLIMOPTS', default=['/home/mwilkins/LcLc/analysis/prep_files.py', '/home/mwilkins/LcLc/analysis/fileprep'], nargs=2,
                       help='python script to-be-copied for tuple slimming and a directory with modules to-be-imported')

args = parser.parse_args()

# -- evaluate arguments -- #
for arg in vars(args):
    exec('{ARG} = args.{ARG}'.format(ARG=arg))
CLEANSTAGES  = True if any(CLEAN_UP == x for x in ['CLEANSTAGES', 'both']) else False
CLEANWORK    = True if any(CLEAN_UP == x for x in ['CLEANWORK', 'both']) else False


# -- check arguments -- #
if NOPIDTRIG and not all([MOOREHLT2_TCK == '0x6139160F', os.path.basename(NEWCONFIG) == 'config.cdb']):
    raise parser.error('NOPIDTRIG uses a config.cdb generated with certain assumptions. See script.')
if NOPIDTRIG:
    MOOREHLT2_TCK = str(hex((eval(MOOREHLT2_TCK) | 0x0c000000)))
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


# -- create stage_list -- #
def make_stage_list(USER, BASE_NAME):
    stage_list = []
    
    additional_pre_script = 'setenv PYTHONPATH $HOME/algorithms/python:$PYTHONPATH && '  # declares stuff used by scripts called here
    # -- Gauss stage -- #
    GAUSS_STAGE_NAME = 'Gauss'
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
if {RICHOFF}:  # RICHOFF option set in generation script
    importOptions("$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts_noLHCbphys.py")  # turn off Cherenkov photons
else:
    importOptions("$APPCONFIGOPTS/Gauss/RICHRandomHits.py")  # as in $GAUSSOPTS/Gauss-2016.py  # removed because we are not using RICH info
    importOptions("$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py")  # not sure this is necessary
if {COMPRESS}:  # COMPRESS option set in generation script
    importOptions("$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py")  # makes for faster writing if the intention is to delete the output
importOptions("$DECFILESROOT/options/{EVENT_TYPE}.py")  # needs to be called BEFORE setting up Pythia8, else will use Pythia6 production tool
importOptions("$LBPYTHIA8ROOT/options/Pythia8.py")

if {PYTHMOD}:  # PYTHMOD option set in generation script
    # -- modify Pythia8 to only generate from Charmonium processes -- #
    from Configurables import Pythia8Production

    Pythia8TurnOffMinbias = [ "SoftQCD:all = off" ]
    Pythia8TurnOffMinbias += [ "Bottomonium:all = off" ]
    Pythia8TurnOffMinbias += [ "Charmonium:all = on" ]

    gen = Generation()
    gen.addTool( MinimumBias , name = "MinimumBias" )
    gen.MinimumBias.ProductionTool = "Pythia8Production"
    gen.MinimumBias.addTool( Pythia8Production , name = "Pythia8Production" )
    gen.MinimumBias.Pythia8Production.Commands += Pythia8TurnOffMinbias

    gen.addTool( Inclusive , name = "Inclusive" )
    gen.Inclusive.ProductionTool = "Pythia8Production"
    gen.Inclusive.addTool( Pythia8Production , name = "Pythia8Production" )
    gen.Inclusive.Pythia8Production.Commands += Pythia8TurnOffMinbias

    gen.addTool( SignalPlain , name = "SignalPlain" )
    gen.SignalPlain.ProductionTool = "Pythia8Production"
    gen.SignalPlain.addTool( Pythia8Production , name = "Pythia8Production" )
    gen.SignalPlain.Pythia8Production.Commands += Pythia8TurnOffMinbias

    gen.addTool( SignalRepeatedHadronization , name = "SignalRepeatedHadronization" )
    gen.SignalRepeatedHadronization.ProductionTool = "Pythia8Production"
    gen.SignalRepeatedHadronization.addTool( Pythia8Production , name = "Pythia8Production" )
    gen.SignalRepeatedHadronization.Pythia8Production.Commands += Pythia8TurnOffMinbias

    gen.addTool( Special , name = "Special" )
    gen.Special.ProductionTool = "Pythia8Production"
    gen.Special.addTool( Pythia8Production , name = "Pythia8Production" )
    gen.Special.Pythia8Production.Commands += Pythia8TurnOffMinbias
    # -- END  -- #

if {REDECAY}:  # REDECAY option set in generation script
    importOptions("$APPCONFIGROOT/options/Gauss/ReDecay-100times.py")
# importOptions("$GAUSSOPTS/Gauss-2016.py")  # would overwrite some options set above

HistogramPersistencySvc().OutputFile = "{GAUSS_ROOT}"

'''.format(RUN_NUMBER=RUN_NUMBER, FIRST_EVENT=FIRST_EVENT, NUM_EVENT=NUM_EVENT, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, GAUSS_DATA=GAUSS_DATA, BEAM_VERSION=BEAM_VERSION, COMPRESS=COMPRESS, REDECAY=REDECAY, PYTHMOD=PYTHMOD, RICHOFF=RICHOFF, EVENT_TYPE=EVENT_TYPE, GAUSS_ROOT=GAUSS_ROOT)
    stage_list.append(
        {
            'name': GAUSS_STAGE_NAME,
            'dirname': GAUSS_DIR,
            'scripts': {GAUSS_SCRIPT_NAME: GAUSS_SCRIPT_CONTENT},
            'log': GAUSS_LOG,
            'call_string': additional_pre_script + 'lb-run -c best --user-area /home/{USER}/cmtuser Gauss/{GAUSS_VERSION} gaudirun.py {GAUSS_SCRIPT_NAME}'.format(USER=USER, GAUSS_VERSION=GAUSS_VERSION, GAUSS_SCRIPT_NAME=GAUSS_SCRIPT_NAME),
            'to_remove': [],
            'dataname': GAUSS_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- Boole stage -- #
    BOOLE_STAGE_NAME = 'Boole'
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
            'dirname': BOOLE_DIR,
            'scripts': {BOOLE_SCRIPT_NAME: BOOLE_SCRIPT_CONTENT},
            'log': BOOLE_LOG,
            'call_string': additional_pre_script + 'lb-run -c best Boole/{BOOLE_VERSION} gaudirun.py {BOOLE_SCRIPT_NAME}'.format(BOOLE_VERSION=BOOLE_VERSION, BOOLE_SCRIPT_NAME=BOOLE_SCRIPT_NAME),
            'to_remove': [GAUSS_DATA],
            'dataname': BOOLE_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- MooreL0 stage -- #
    MOOREL0_STAGE_NAME = 'Moorel0'
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
            'dirname': MOOREL0_DIR,
            'scripts': {MOOREL0_SCRIPT_NAME: MOOREL0_SCRIPT_CONTENT},
            'log': MOOREL0_LOG,
            'call_string': additional_pre_script + 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREL0_SCRIPT_NAME}'.format(MOORE_VERSION=MOORE_VERSION, MOOREL0_SCRIPT_NAME=MOOREL0_SCRIPT_NAME),
            'to_remove': [BOOLE_DATA],
            'dataname': MOOREL0_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- MooreHlt1 stage -- #
    MOOREHLT1_STAGE_NAME = 'Moorehlt1'
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
            'dirname': MOOREHLT1_DIR,
            'scripts': {MOOREHLT1_SCRIPT_NAME: MOOREHLT1_SCRIPT_CONTENT},
            'log': MOOREHLT1_LOG,
            'call_string': additional_pre_script + 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREHLT1_SCRIPT_NAME}'.format(MOORE_VERSION=MOORE_VERSION, MOOREHLT1_SCRIPT_NAME=MOOREHLT1_SCRIPT_NAME),
            'to_remove': [MOOREL0_DATA],
            'dataname': MOOREHLT1_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- MooreHlt2 stage -- #
    MOOREHLT2_STAGE_NAME = 'Moorehlt2'
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
Moore().DDDBtag   = "{DDDB_TAG}"
Moore().CondDBtag = "{CONDDB_TAG}"
Moore().EvtMax = -1
from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles(['{MOOREHLT1_DATA}'],clear=True)

Moore().outputFile = '{MOOREHLT2_DATA}'

'''.format(COMPRESS=COMPRESS, NOPIDTRIG=NOPIDTRIG, newTCKdir=os.path.dirname(NEWCONFIG), MOOREHLT2_TCK=MOOREHLT2_TCK, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, MOOREHLT1_DATA=MOOREHLT1_DATA, MOOREHLT2_DATA=MOOREHLT2_DATA)
    stage_list.append(
        {
            'name': MOOREHLT2_STAGE_NAME,
            'dirname': MOOREHLT2_DIR,
            'scripts': {MOOREHLT2_SCRIPT_NAME: MOOREHLT2_SCRIPT_CONTENT},
            'log': MOOREHLT2_LOG,
            'call_string': additional_pre_script + 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREHLT2_SCRIPT_NAME}'.format(MOORE_VERSION=MOORE_VERSION, MOOREHLT2_SCRIPT_NAME=MOOREHLT2_SCRIPT_NAME),
            'to_remove': [MOOREHLT1_DATA],
            'dataname': MOOREHLT2_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- Brunel stage -- #
    BRUNEL_STAGE_NAME = 'Brunel'
    BRUNEL_DIR = 'BrunelOpts'
    BRUNEL_LOG = BASE_NAME + '_brunel.log'
    BRUNEL_ROOT = BASE_NAME + '_brunel.root'
    BRUNEL_SCRIPT_NAME = opj(BRUNEL_DIR, 'myBrunel.py')
    BRUNEL_DATA = BASE_NAME + '_brunel.dst'
    BRUNEL_SCRIPT_CONTENT = '''\
from Gaudi.Configuration import *
from Configurables import Brunel, LHCbApp, L0Conf
if {NOPIDTRIG}:
    from Configurables import ConfigCDBAccessSvc
    ConfigCDBAccessSvc().File = '{NEWCONFIG}'

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


'''.format(NOPIDTRIG=NOPIDTRIG, NEWCONFIG=NEWCONFIG, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, COMPRESS=COMPRESS, BOOLE_DATA=BOOLE_DATA, MOOREHLT2_DATA=MOOREHLT2_DATA, BRUNEL_DATA=BRUNEL_DATA, BRUNEL_ROOT=BRUNEL_ROOT)
    stage_list.append(
        {
            'name': BRUNEL_STAGE_NAME,
            'dirname': BRUNEL_DIR,
            'scripts': {BRUNEL_SCRIPT_NAME: BRUNEL_SCRIPT_CONTENT},
            'log': BRUNEL_LOG,
            'call_string': additional_pre_script + 'lb-run -c best Brunel/{BRUNEL_VERSION} gaudirun.py {BRUNEL_SCRIPT_NAME}'.format(BRUNEL_VERSION=BRUNEL_VERSION, BRUNEL_SCRIPT_NAME=BRUNEL_SCRIPT_NAME),
            'to_remove': [MOOREHLT2_DATA],
            'dataname': BRUNEL_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- DaVinci stage -- #
    DAVINCI_STAGE_NAME = 'DaVinci'
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
if {NOPIDTRIG}:
    from Configurables import ConfigCDBAccessSvc
    ConfigCDBAccessSvc().File = '{NEWCONFIG}'

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
'''.format(STRIPPING_CAMPAIGN=STRIPPING_CAMPAIGN, NOPIDTRIG=NOPIDTRIG, NEWCONFIG=NEWCONFIG, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, DAVINCI_ROOT=DAVINCI_ROOT, BRUNEL_DATA=BRUNEL_DATA, DAVINCI_DATA=DAVINCI_DATA)
    stage_list.append(
        {
            'name': DAVINCI_STAGE_NAME,
            'dirname': DAVINCI_DIR,
            'scripts': {DAVINCI_SCRIPT_NAME: DAVINCI_SCRIPT_CONTENT},
            'log': DAVINCI_LOG,
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_STRIPPING_VERSION} gaudirun.py {DAVINCI_SCRIPT_NAME}'.format(DAVINCI_STRIPPING_VERSION=DAVINCI_STRIPPING_VERSION, DAVINCI_SCRIPT_NAME=DAVINCI_SCRIPT_NAME),
            'to_remove': [BRUNEL_DATA],
            'dataname': DAVINCI_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- allstuple stage -- #
    ALLSTUPLE_STAGE_NAME = 'allstuple'
    ALLSTUPLE_DIR = 'allstupleOpts'
    ALLSTUPLE_LOG = BASE_NAME + '_allstuple.log'
    ALLSTUPLE_ROOT = BASE_NAME + '_allstuple.root'
    ALLSTUPLE_SCRIPT_NAME = opj(ALLSTUPLE_DIR, 'myAllstuple.py')
    ALLSTUPLE_DATA = BASE_NAME + '_allstuple.root'
    if os.path.basename(TUPOPTS) != 'LcLc.py':
        raise Exception('script designed with LcLc.py in mind, i.e., it writes steering.py in a particular way. You have selected {TUPOPTS}. See script.'.format(TUPOPTS=TUPOPTS))
    # steering.py is picked up by LcLc.py aka TUPOPTS
    ALLSTUPLE_STEERING_CONTENT = '''\
MC = True
devMC = True
testing = False
smalltest = False
MCtruthonly = False
Lconly = False
year = '2016'
dbtag = '{DDDB_TAG}'
cdbtag = '{CONDDB_TAG}'
condor_run = ['{DAVINCI_DATA}']
tuplename = '{ALLSTUPLE_DATA}'
newTCK = {NEWCONFIGorNone}
restripped = False
'''.format(DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, DAVINCI_DATA=DAVINCI_DATA, ALLSTUPLE_DATA=ALLSTUPLE_DATA, NEWCONFIGorNone='"{0}"'.format(NEWCONFIG) if NOPIDTRIG else None)
    ALLSTUPLE_SCRIPT_CONTENT = None
    with open(TUPOPTS, 'r') as f:
        ALLSTUPLE_SCRIPT_CONTENT = f.read()  # use pre-written options file rather than writing a new one
    stage_list.append(
        {
            'name': ALLSTUPLE_STAGE_NAME,
            'dirname': ALLSTUPLE_DIR,
            'scripts': {ALLSTUPLE_SCRIPT_NAME: ALLSTUPLE_SCRIPT_CONTENT, opj(ALLSTUPLE_DIR, 'steering.py'): ALLSTUPLE_STEERING_CONTENT},
            'log': ALLSTUPLE_LOG,
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_TUPLE_VERSION} gaudirun.py {ALLSTUPLE_SCRIPT_NAME}'.format(DAVINCI_TUPLE_VERSION=DAVINCI_TUPLE_VERSION, ALLSTUPLE_SCRIPT_NAME=ALLSTUPLE_SCRIPT_NAME),
            'to_remove': [],  # bad idea to delete DST...
            'dataname': ALLSTUPLE_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- restrip stage -- #
    RESTRIP_STAGE_NAME = 'restrip'
    RESTRIP_DIR = 'restripOpts'
    RESTRIP_LOG = BASE_NAME + '_restrip.log'
    RESTRIP_ROOT = BASE_NAME + '_restrip.root'
    RESTRIP_SCRIPT_NAME = opj(RESTRIP_DIR, 'myRestrip.py')
    RESTRIP_DATA = 'RestrippedMC.Charm.dst'  # this is produced by the script--do not modify unless the script change
    RESTRIP_SCRIPT_CONTENT = '''\
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

stripping = 'stripping{STRIPPING_CAMPAIGN}'
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
DaVinci().DDDBtag   = "{DDDB_TAG}"
DaVinci().CondDBtag = "{CONDDB_TAG}"
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

'''.format(NOPIDTRIG=NOPIDTRIG, STRIPPING_CAMPAIGN=STRIPPING_CAMPAIGN, NEWCONFIG=NEWCONFIG, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, DAVINCI_DATA=DAVINCI_DATA, RESTRIP_ROOT=RESTRIP_ROOT, RESTRIP_DATA=RESTRIP_DATA)
    stage_list.append(
        {
            'name': RESTRIP_STAGE_NAME,
            'dirname': RESTRIP_DIR,
            'scripts': {RESTRIP_SCRIPT_NAME: RESTRIP_SCRIPT_CONTENT},
            'log': RESTRIP_LOG,
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_STRIPPING_VERSION} gaudirun.py {RESTRIP_SCRIPT_NAME}'.format(DAVINCI_STRIPPING_VERSION=DAVINCI_STRIPPING_VERSION, RESTRIP_SCRIPT_NAME=RESTRIP_SCRIPT_NAME),
            'to_remove': ['tmp_stripping_config.db', 'RestrippedMC.Bhadron.dst', 'RestrippedMC.BhadronCompleteEvent.dst', 'RestrippedMC.Leptonic.dst', 'RestrippedMC.CharmCompleteEvent.dst', 'RestrippedMC.Radiative.dst', 'RestrippedMC.Dimuon.dst'],  # do not delete initial DaVinci output, do delete extra streams (trying to stop their generation produced errors, but they aren't needed), do delete file created by shelve
            'dataname': RESTRIP_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- tuple stage -- #
    TUPLE_STAGE_NAME = 'tuple'
    TUPLE_DIR = 'tupleOpts'
    TUPLE_LOG = BASE_NAME + '_tuple.log'
    TUPLE_ROOT = BASE_NAME + '_tuple.root'
    TUPLE_SCRIPT_NAME = opj(TUPLE_DIR, 'myTuple.py')
    TUPLE_DATA = BASE_NAME + '_tuple.root'
    if os.path.basename(TUPOPTS) != 'LcLc.py':
        raise Exception('script designed with LcLc.py in mind, i.e., it writes steering.py in a particular way. You have selected {TUPOPTS}. See script.'.format(TUPOPTS=TUPOPTS))
    # steering.py is picked up by LcLc.py aka TUPOPTS
    TUPLE_STEERING_CONTENT = '''\
MC = True
devMC = True
testing = False
smalltest = False
MCtruthonly = False
Lconly = False
year = '2016'
dbtag = '{DDDB_TAG}'
cdbtag = '{CONDDB_TAG}'
condor_run = ['{RESTRIP_DATA}']
tuplename = '{TUPLE_DATA}'
newTCK = {NEWCONFIGorNone}
restripped = True
'''.format(DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, RESTRIP_DATA=RESTRIP_DATA, TUPLE_DATA=TUPLE_DATA, NEWCONFIGorNone='"{0}"'.format(NEWCONFIG) if NOPIDTRIG else None)
    TUPLE_SCRIPT_CONTENT = None
    with open(TUPOPTS, 'r') as f:
        TUPLE_SCRIPT_CONTENT = f.read()  # use pre-written options file rather than writing a new one
    stage_list.append(
        {
            'name': TUPLE_STAGE_NAME,
            'dirname': TUPLE_DIR,
            'scripts': {TUPLE_SCRIPT_NAME: TUPLE_SCRIPT_CONTENT, opj(TUPLE_DIR, 'steering.py'): TUPLE_STEERING_CONTENT},
            'log': TUPLE_LOG,
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_TUPLE_VERSION} gaudirun.py {TUPLE_SCRIPT_NAME}'.format(DAVINCI_TUPLE_VERSION=DAVINCI_TUPLE_VERSION, TUPLE_SCRIPT_NAME=TUPLE_SCRIPT_NAME),
            'to_remove': [],  # bad idea to delete DST...
            'dataname': TUPLE_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- slim stage -- #
    SLIM_STAGE_NAME = 'slim'
    SLIM_DIR = 'slimOpts'
    SLIM_LOG = BASE_NAME + '_slim.log'
    SLIM_ROOT = BASE_NAME + '_slim.root'
    SLIM_SCRIPT_NAME = opj(SLIM_DIR, 'mySlim.py')
    SLIM_DATA = BASE_NAME + '_slim'
    if os.path.basename(SLIMOPTS[0]) != 'prep_files.py':
        raise Exception('script designed with prep_files.py in mind, i.e., it uses particular commandline options. You have selected {SLIMOPTS}. See script.'.format(SLIMOPTS=SLIMOPTS))
    SLIM_SCRIPT_CONTENT = None
    with open(SLIMOPTS[0], 'r') as f:
        SLIM_SCRIPT_CONTENT = f.read()
    slimoptsdirname = SLIMOPTS[1].strip('/').split('/')[-1]
    dict_of_support_files = {}
    for fname in os.listdir(SLIMOPTS[1]):
        if fname == 'experimental':
            continue
        with open(opj(SLIMOPTS[1], fname), 'r') as f:
            dict_of_support_files[opj(SLIM_DIR, slimoptsdirname, fname)] = f.read()
    stage_list.append(
        {
            'name': SLIM_STAGE_NAME,
            'dirname': SLIM_DIR,
            'scripts': dict({SLIM_SCRIPT_NAME: SLIM_SCRIPT_CONTENT}, **dict_of_support_files),
            'log': SLIM_LOG,
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_TUPLE_VERSION} python {SLIM_SCRIPT_NAME} MC 16 --failgracefully --outfolder {SLIM_DATA} --input {TUPLE_DATA} X2LcLcTree/DecayTree --logfilename {SLIM_LOG}'.format(DAVINCI_TUPLE_VERSION=DAVINCI_TUPLE_VERSION, SLIM_SCRIPT_NAME=SLIM_SCRIPT_NAME, SLIM_DATA=SLIM_DATA, TUPLE_DATA=TUPLE_DATA, SLIM_LOG=SLIM_LOG),
            'to_remove': [],  # bad idea to delete tuple file...
            'dataname': SLIM_DATA,
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )
    
    return stage_list
