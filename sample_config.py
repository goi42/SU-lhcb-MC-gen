from os import listdir
from os.path import join as opj
# -- essential parameters -- #
SIGNAL_NAME = 'TestProduction'
RUN_NUMBER = 300000
GEN_LEVEL = 'all'
RUN_SYS = '/data2'  # system to run on; path should be absolute
CLEANSTAGES = True  # CLEANSTAGES deletes data from earlier stages as it goes
CLEANWORK = True  # CLEANWORK moves files out of work directory
PRECLEANED = False  # if this script has already been run, you can specify this argument so that it moves appropriate files to the work directory first
SOME_MISSING = False  # if running a later stage, you may specify this argument to let the script terminate without errors if the input files are missing
WORK_DIR_EXISTS = False  # BE VERY CAREFUL WHEN USING THIS FLAG: gives permission to run if WORK_DIR already exists! Also allows overwrite of extant Opts directories.

# -- parameters for make_stage_list -- #
SCRIPT_ONLY = False  # flag used to set all stage's scriptonly parameter
# general
DDDB_TAG = 'dddb-20170721-3'
CONDDB_TAG = 'sim-20170721-2-vc-md100'
COMPRESS = True  # use compression option optimized for deletion of intermediate stages
MAGNETPOLARITY = None  # 'md', 'mu'  # ensures CONDDB_TAG and BEAM_VERSION use mu or md as appropriate for the specified polarity, e.g., replaces "mu" with "md".
# Gauss
EVENT_TYPE = 28196040
FIRST_EVENT = 1
NUM_EVENT = 100
REDECAY = 100
RICHOFF = False
BEAM_VERSION = 'Beam6500GeV-md100-2016-nu1.6.py'
GAUSS_VERSION = 'v49r10'
# Boole
BOOLE_VERSION = 'v30r2p1'
# Moore
MOORE_VERSION = 'v25r4'
# Moore L0
MOOREL0_TCK = '0x160F'
# Moore HLT1
MOOREHLT1_TCK = '0x5138160F'
# Moore HLT2
MOOREHLT2_TCK = '0x6139160F'
NOPIDTRIG = False
NEWCONFIG = '/home/mwilkins/LcLc/MCgeneration/devrun/config.cdb'
# Brunel
BRUNEL_VERSION = 'v50r3'
# Stripping
DAVINCI_STRIPPING_VERSION = 'v41r4p4'
STRIPPING_CAMPAIGN = '28r1'
# allstuple and tuple
TUPOPTS = '/home/mwilkins/LcLc/options/LcLc.py'
DAVINCI_TUPLE_VERSION = 'v42r6p1'
# slim
SLIMOPTS = ['/home/mwilkins/LcLc/analysis/prep_files.py', '/home/mwilkins/LcLc/analysis/fileprep']

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
def make_stage_list(BASE_NAME):
    stage_list = []
    
    additional_pre_script = 'setenv PYTHONPATH $HOME/algorithms/python:$PYTHONPATH && '  # declares stuff used by scripts called here
    # -- Gauss stage -- #
    GAUSS_LOG = BASE_NAME + '_gauss.log'
    GAUSS_ROOT = BASE_NAME + '_gauss.root'
    GAUSS_SCRIPT_NAME = 'myGauss.py'
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

if {REDECAY}:  # REDECAY option set in generation script
    importOptions("$APPCONFIGROOT/options/Gauss/ReDecay-100times.py")
# importOptions("$GAUSSOPTS/Gauss-2016.py")  # would overwrite some options set above

HistogramPersistencySvc().OutputFile = "{GAUSS_ROOT}"

'''.format(RUN_NUMBER=RUN_NUMBER, FIRST_EVENT=FIRST_EVENT, NUM_EVENT=NUM_EVENT, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, GAUSS_DATA=GAUSS_DATA, BEAM_VERSION=BEAM_VERSION, COMPRESS=COMPRESS, REDECAY=REDECAY, RICHOFF=RICHOFF, EVENT_TYPE=EVENT_TYPE, GAUSS_ROOT=GAUSS_ROOT)
    stage_list.append(
        {
            'name': 'Gauss',
            'dirname': 'GaussOpts',
            'scripts': {GAUSS_SCRIPT_NAME: GAUSS_SCRIPT_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best --user-area /home/{USER}/cmtuser Gauss/{GAUSS_VERSION} gaudirun.py {GAUSS_SCRIPT_NAME} | tee {GAUSS_LOG}'.format(USER=USER, GAUSS_VERSION=GAUSS_VERSION, GAUSS_SCRIPT_NAME=GAUSS_SCRIPT_NAME, GAUSS_LOG=GAUSS_LOG),
            'to_remove': [],
            'dataname': BASE_NAME + '_gauss.sim',
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- Boole stage -- #
    BOOLE_LOG = BASE_NAME + '_boole.log'
    BOOLE_ROOT = BASE_NAME + '_boole.root'
    BOOLE_SCRIPT_NAME = 'myBoole.py'
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
            'name': 'Boole',
            'dirname': 'BooleOpts',
            'scripts': {BOOLE_SCRIPT_NAME: BOOLE_SCRIPT_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best Boole/{BOOLE_VERSION} gaudirun.py {BOOLE_SCRIPT_NAME} | tee {BOOLE_LOG}'.format(BOOLE_VERSION=BOOLE_VERSION, BOOLE_SCRIPT_NAME=BOOLE_SCRIPT_NAME, BOOLE_LOG=BOOLE_LOG),
            'to_remove': [GAUSS_DATA],
            'dataname': BASE_NAME + '_boole.digi',
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- MooreL0 stage -- #
    MOOREL0_LOG = BASE_NAME + '_moorel0.log'
    MOOREL0_ROOT = BASE_NAME + '_moorel0.root'
    MOOREL0_SCRIPT_NAME = 'myMoorel0.py'
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
            'name': 'Moorel0',
            'dirname': 'MooreOptsl0',
            'scripts': {MOOREL0_SCRIPT_NAME: MOOREL0_SCRIPT_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREL0_SCRIPT_NAME} | tee {MOOREL0_LOG}'.format(MOORE_VERSION=MOORE_VERSION, MOOREL0_SCRIPT_NAME=MOOREL0_SCRIPT_NAME, MOOREL0_LOG=MOOREL0_LOG),
            'to_remove': [BOOLE_DATA],
            'dataname': BASE_NAME + '_moorel0.digi',
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- MooreHlt1 stage -- #
    MOOREHLT1_LOG = BASE_NAME + '_moorehlt1.log'
    MOOREHLT1_ROOT = BASE_NAME + '_moorehlt1.root'
    MOOREHLT1_SCRIPT_NAME = 'myMoorehlt1.py'
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
            'name': 'Moorehlt1',
            'dirname': 'MooreOptshlt1',
            'scripts': {MOOREHLT1_SCRIPT_NAME: MOOREHLT1_SCRIPT_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREHLT1_SCRIPT_NAME} | tee {MOOREHLT1_LOG}'.format(MOORE_VERSION=MOORE_VERSION, MOOREHLT1_SCRIPT_NAME=MOOREHLT1_SCRIPT_NAME, MOOREHLT1_LOG=MOOREHLT1_LOG),
            'to_remove': [MOOREL0_DATA],
            'dataname': BASE_NAME + '_moorehlt1.digi',
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- MooreHlt2 stage -- #
    MOOREHLT2_LOG = BASE_NAME + '_moorehlt2.log'
    MOOREHLT2_ROOT = BASE_NAME + '_moorehlt2.root'
    MOOREHLT2_SCRIPT_NAME = 'myMoorehlt2.py'
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

'''.format(COMPRESS=COMPRESS, NOPIDTRIG=NOPIDTRIG, newTCKdir=os.path.dirname(NEWCONFIG), WORK_DIR=WORK_DIR, MOOREHLT2_TCK=MOOREHLT2_TCK, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, MOOREHLT1_DATA=MOOREHLT1_DATA, MOOREHLT2_DATA=MOOREHLT2_DATA)
    stage_list.append(
        {
            'name': 'Moorehlt2',
            'dirname': 'MooreOptshlt2',
            'scripts': {MOOREHLT2_SCRIPT_NAME: MOOREHLT2_SCRIPT_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best Moore/{MOORE_VERSION} gaudirun.py {MOOREHLT2_SCRIPT_NAME} | tee {MOOREHLT2_LOG}'.format(MOORE_VERSION=MOORE_VERSION, MOOREHLT2_SCRIPT_NAME=MOOREHLT2_SCRIPT_NAME, MOOREHLT2_LOG=MOOREHLT2_LOG),
            'to_remove': [MOOREHLT1_DATA],
            'dataname': BASE_NAME + '_moorehlt2.digi',
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- Brunel stage -- #
    BRUNEL_LOG = BASE_NAME + '_brunel.log'
    BRUNEL_ROOT = BASE_NAME + '_brunel.root'
    BRUNEL_SCRIPT_NAME = 'myBrunel.py'
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
            'name': 'Brunel',
            'dirname': 'BrunelOpts',
            'scripts': {BRUNEL_SCRIPT_NAME: BRUNEL_SCRIPT_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best Brunel/{BRUNEL_VERSION} gaudirun.py {BRUNEL_SCRIPT_NAME} | tee {BRUNEL_LOG}'.format(BRUNEL_VERSION=BRUNEL_VERSION, BRUNEL_SCRIPT_NAME=BRUNEL_SCRIPT_NAME, BRUNEL_LOG=BRUNEL_LOG),
            'to_remove': [MOOREHLT2_DATA],
            'dataname': BASE_NAME + '_brunel.dst',
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- DaVinci stage -- #
    DAVINCI_LOG = BASE_NAME + '_davinci.log'
    DAVINCI_ROOT = BASE_NAME + '_davinci.root'
    DAVINCI_SCRIPT_NAME = 'myDavinci.py'
    DAVINCI_SCRIPT_CONTENT = '''\
from Gaudi.Configuration import *
from Configurables import DaVinci, LHCbApp, DumpFSR
importOptions("$APPCONFIGOPTS/DaVinci/DV-Stripping{STRIPPING_VERSION}-Stripping-MC-NoPrescaling-DST.py")
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
'''.format(STRIPPING_VERSION=STRIPPING_VERSION, NOPIDTRIG=NOPIDTRIG, NEWCONFIG=NEWCONFIG, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, DAVINCI_ROOT=DAVINCI_ROOT, BRUNEL_DATA=BRUNEL_DATA, DAVINCI_DATA=DAVINCI_DATA)
    stage_list.append(
        {
            'name': 'DaVinci',
            'dirname': 'DaVinciOpts',
            'scripts': {DAVINCI_SCRIPT_NAME: DAVINCI_SCRIPT_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_STRIPPING_VERSION} gaudirun.py {DAVINCI_SCRIPT_NAME} | tee {DAVINCI_LOG}'.format(DAVINCI_STRIPPING_VERSION=DAVINCI_STRIPPING_VERSION, DAVINCI_SCRIPT_NAME=DAVINCI_SCRIPT_NAME, DAVINCI_LOG=DAVINCI_LOG),
            'to_remove': [BRUNEL_DATA],
            'dataname': '000000.AllStreams.dst',  # this is produced by the script--do not modify unless the script changes
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- allstuple stage -- #
    ALLSTUPLE_LOG = BASE_NAME + '_allstuple.log'
    ALLSTUPLE_ROOT = BASE_NAME + '_allstuple.root'
    ALLSTUPLE_SCRIPT_NAME = 'myAllstuple.py'
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
    with open(TUPOTS, 'r') as f:
        ALLSTUPLE_SCRIPT_CONTENT = f.read()  # use pre-written options file rather than writing a new one
    stage_list.append(
        {
            'name': 'allstuple',
            'dirname': 'allstupleOpts',
            'scripts': {ALLSTUPLE_SCRIPT_NAME: ALLSTUPLE_SCRIPT_CONTENT, 'steering.py': ALLSTUPLE_STEERING_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_TUPLE_VERSION} gaudirun.py {ALLSTUPLE_SCRIPT_NAME} | tee {ALLSTUPLE_LOG}'.format(DAVINCI_TUPLE_VERSION=DAVINCI_TUPLE_VERSION, ALLSTUPLE_SCRIPT_NAME=ALLSTUPLE_SCRIPT_NAME, ALLSTUPLE_LOG=ALLSTUPLE_LOG),
            'to_remove': [],  # bad idea to delete DST...
            'dataname': BASE_NAME + '_allstuple.root',
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- restrip stage -- #
    RESTRIP_LOG = BASE_NAME + '_restrip.log'
    RESTRIP_ROOT = BASE_NAME + '_restrip.root'
    RESTRIP_SCRIPT_NAME = 'myRestrip.py'
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

'''.format(NOPIDTRIG=NOPIDTRIG, STRIPPING_VERSION=STRIPPING_VERSION, NEWCONFIG=NEWCONFIG, DDDB_TAG=DDDB_TAG, CONDDB_TAG=CONDDB_TAG, DAVINCI_DATA=DAVINCI_DATA, RESTRIP_ROOT=RESTRIP_ROOT, RESTRIP_DATA=RESTRIP_DATA)
    stage_list.append(
        {
            'name': 'restrip',
            'dirname': 'restripOpts',
            'scripts': {RESTRIP_SCRIPT_NAME: RESTRIP_SCRIPT_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_STRIPPING_VERSION} gaudirun.py {RESTRIP_SCRIPT_NAME} | tee {RESTRIP_LOG}'.format(DAVINCI_STRIPPING_VERSION=DAVINCI_STRIPPING_VERSION, RESTRIP_SCRIPT_NAME=RESTRIP_SCRIPT_NAME, RESTRIP_LOG=RESTRIP_LOG),
            'to_remove': [opj(WORK_DIR, x) for x in ['tmp_stripping_config.db', 'RestrippedMC.Bhadron.dst', 'RestrippedMC.BhadronCompleteEvent.dst', 'RestrippedMC.Leptonic.dst', 'RestrippedMC.CharmCompleteEvent.dst', 'RestrippedMC.Radiative.dst', 'RestrippedMC.Dimuon.dst']],  # do not delete initial DaVinci output, do delete extra streams (trying to stop their generation produced errors, but they aren't needed), do delete file created by shelve
            'dataname': 'RestrippedMC.Charm.dst',  # this is produced by the script--do not modify unless the script changes
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- tuple stage -- #
    TUPLE_LOG = BASE_NAME + '_tuple.log'
    TUPLE_ROOT = BASE_NAME + '_tuple.root'
    TUPLE_SCRIPT_NAME = 'myTuple.py'
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
    with open(TUPOTS, 'r') as f:
        TUPLE_SCRIPT_CONTENT = f.read()  # use pre-written options file rather than writing a new one
    stage_list.append(
        {
            'name': 'tuple',
            'dirname': 'tupleOpts',
            'scripts': {TUPLE_SCRIPT_NAME: TUPLE_SCRIPT_CONTENT, 'steering.py': TUPLE_STEERING_CONTENT},
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_TUPLE_VERSION} gaudirun.py {TUPLE_SCRIPT_NAME} | tee {TUPLE_LOG}'.format(DAVINCI_TUPLE_VERSION=DAVINCI_TUPLE_VERSION, TUPLE_SCRIPT_NAME=TUPLE_SCRIPT_NAME, TUPLE_LOG=TUPLE_LOG),
            'to_remove': [],  # bad idea to delete DST...
            'dataname': BASE_NAME + '_tuple.root',
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )

    # -- slim stage -- #
    SLIM_LOG = BASE_NAME + '_slim.log'
    SLIM_ROOT = BASE_NAME + '_slim.root'
    SLIM_SCRIPT_NAME = 'mySlim.py'
    if os.path.basename(SLIMOPTS[0]) != 'prep_files.py':
        raise Exception('script designed with prep_files.py in mind, i.e., it uses particular commandline options. You have selected {SLIMOPTS}. See script.'.format(SLIMOPTS=SLIMOPTS))
    SLIM_SCRIPT_CONTENT = None
    with open(SLIMOPTS[0], 'r') as f:
        SLIM_SCRIPT_CONTENT = f.read()
    slimoptsdirname = SLIMOPTS[1].strip('/').split('/')[-1]
    dict_of_support_files = {}
    for fname in listdir(SLIMOPTS[1]):
        with open(opj(SLIMOPTS[1], fname), 'r') as f:
            dict_of_support_files[opj(slimoptsdirname, fname)] = f.read()
    stage_list.append(
        {
            'name': 'slim',
            'dirname': 'slimOpts',
            'scripts': dict({SLIM_SCRIPT_NAME: SLIM_SCRIPT_CONTENT}, **dict_of_support_files),
            'call_string': additional_pre_script + 'lb-run -c best DaVinci/{DAVINCI_TUPLE_VERSION} python {SLIM_SCRIPT_NAME} MC 16 --failgracefully --outfolder {SLIM_DATA} --input {TUPLE_DATA} X2LcLcTree/DecayTree --logfilename {SLIM_LOG}'.format(DAVINCI_TUPLE_VERSION=DAVINCI_TUPLE_VERSION, SLIM_SCRIPT_NAME=SLIM_SCRIPT_NAME, SLIM_DATA=SLIM_DATA, TUPLE_DATA=TUPLE_DATA, SLIM_LOG=SLIM_LOG),
            'to_remove': [],  # bad idea to delete tuple file...
            'dataname': BASE_NAME + '_slim',
            'run': True,
            'scriptonly': SCRIPT_ONLY,
        }
    )
    
    return stage_list
