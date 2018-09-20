#!/usr/bin/env python2
import os
from os.path import join as abspath, basename
import argparse
import __main__

# -- essential parameters -- #
parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='set parameters to be used in run_stages.py')

parser.add_argument('configfile', type=abspath,
                    help='this argument must be here to ensure integration with run_stages.py')
parser.add_argument('--SIGNAL_NAME', default='TestProduction')
parser.add_argument('--RUN_NUMBER', type=int, default=300000)
parser.add_argument('--RUN_SYS', default='/data2',
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
# args = parser.parse_args() if basename(__main__.__file__) == 'run_stages.py' else parser.parse_known_args()[0]
args = parser.parse_args(['test'])
for arg in vars(args):
    exec('{ARG} = args.{ARG}'.format(ARG=arg))
# -- end mandatory section -- #


# -- create stage_list (mandatory function) -- #
def make_stage_list(USER, BASE_NAME):  # DO NOT CHANGE THIS LINE
    from datetime import datetime
    evtnum = int('<<<<your event-number here>>>>')
    stage_list = [
        {
            'name': 'gauss',
            'scripts': {},
            'log': BASE_NAME + '_gauss.log',
            'call_string': 'lb-run -c best --user-area <<<</path/to/your/Gauss/Build>>>> Gauss/<<<<Gauss Version>>>> gaudirun.py $GAUSSOPTS/Gauss-Job.py $GAUSSOPTS/Gauss-2016.py $GAUSSOPTS/GenStandAlone.py $DECFILESROOT/options/{0}.py $LBPYTHIA8ROOT/options/Pythia8.py'.format(evtnum),
            'to_remove': [],
            'dataname': 'Gauss-{0}-5ev-{1}.xgen'.format(evtnum, str(datetime.today()).split(' ')[0].replace('-', '')),  # output filename includes reference to the date
            'run': True,
            'scriptonly': False,
        }
    ]
        
    return stage_list