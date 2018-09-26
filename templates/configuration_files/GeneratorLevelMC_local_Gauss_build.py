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
                        help='BE VERY CAREFUL WHEN USING THIS FLAG: gives permission to run if WORK_DIR already exists! Also allows overwrite of extant Opts directories.')

# -- parameters used for make_stage_list -- #
# Gauss
gaussgroup = parser.add_argument_group('Gauss parameters')
gaussgroup.add_argument('--GAUSS_VERSION', default='<<<<default version of Gauss you want to use>>>>')
gaussgroup.add_argument('--FIRST_EVENT', type=int, default=1)
gaussgroup.add_argument('--NUM_EVENT', help='number of events to generate per job', type=int, default=int('<<<<default number of events you want>>>>'))
gaussgroup.add_argument('--EVENT_TYPE', type=int, default=int('<<<<default EVENT_TYPE you want to use>>>>'))
gaussgroup.add_argument('--YEAR', type=int, default=int('<<<<default year you want to use>>>>'))


# -- evaluate and check arguments -- #
# -- mandatory section -- #
args = parser.parse_args() if basename(__main__.__file__) == 'run_stages.py' else parser.parse_known_args()[0]  # assume all arguments are for this script if 'run_stages.py' is the main file, else allow arguments to go to other scripts
for arg in vars(args):
    exec('{ARG} = args.{ARG}'.format(ARG=arg))  # eliminate need to reference things as arg.thing
# -- end mandatory section -- #


# -- create stage_list (mandatory function) -- #
def make_stage_list(USER, BASE_NAME):  # DO NOT CHANGE THIS LINE
    from datetime import datetime
    stage_list = []
    
    # -- Gauss stage -- #
    GAUSS_SCRIPT_NAME = 'myGaussOpts.py'
    GAUSS_SCRIPT_CONTENT = '''\
# -- this script's contents are based on https://gitlab.cern.ch/lhcb-datapkg/Gen/DecFiles/blob/master/CONTRIBUTING.md -- #

# -- modified $GAUSSOPTS/Gauss-Job.py -- #

from Gauss.Configuration import *

#--Generator phase, set random numbers
GaussGen = GenInit("GaussGen")
GaussGen.FirstEventNumber = {FIRST_EVENT}
GaussGen.RunNumber        = {RUN_NUMBER}

#--Number of events
nEvts = {NUM_EVENT}
LHCbApp().EvtMax = nEvts

# -- end modified $GAUSSOPTS/Gauss-Job.py -- #

# import other standard options
importOptions("$GAUSSOPTS/Gauss-{YEAR}.py")
importOptions("$GAUSSOPTS/GenStandAlone.py")
importOptions("$DECFILESROOT/options/{EVENT_TYPE}.py")  # needs to be called BEFORE setting up Pythia8, else will use Pythia6 production tool
importOptions("$LBPYTHIA8ROOT/options/Pythia8.py")


'''.format(RUN_NUMBER=RUN_NUMBER, FIRST_EVENT=FIRST_EVENT, NUM_EVENT=NUM_EVENT, YEAR=YEAR, EVENT_TYPE=EVENT_TYPE)
    stage_list.append(
        {
            'name': 'gauss',
            'scripts': {GAUSS_SCRIPT_NAME: GAUSS_SCRIPT_CONTENT},
            'log': BASE_NAME + '_gauss.log',
            'call_string': 'lb-run -c best --user-area <<<</absolute/path/to/the/directory/containing/Gauss[Dev]_version>>>> <<<<Gauss[Dev]>>>>/{GAUSS_VERSION} gaudirun.py {GAUSS_SCRIPT_NAME}'.format(GAUSS_VERSION=GAUSS_VERSION, GAUSS_SCRIPT_NAME=GAUSS_SCRIPT_NAME),
            'to_remove': [],
            'required': [],
            'dataname': 'Gauss-{ET}-{NE}ev-{DT}.xgen'.format(ET=EVENT_TYPE, NE=NUM_EVENT, DT=str(datetime.today()).split(' ')[0].replace('-', '')),  # output filename includes reference to the date
            'run': True,
            'scriptonly': False,
        }
    )
        
    return stage_list
