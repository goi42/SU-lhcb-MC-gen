# SU-lhcb-MC-gen
A suite of scripts for generating MC on lhcb-dev

## About
This is a suite of scripts designed to make life easier for people submitting MC jobs
(or any jobs) to Condor on lhcb-dev. It revolves around the use of configuration files
and the script run_stages.py.

In order to use this suite, simply clone the git repo, create a configuration file,
and off you go! There are sample configuration files and templates in the `samples/`
and `templates/` directories. You should be able to find what you need there.

Don't be shy about contributing! If you have a configuration file you're proud of, add
it to the samples! See CONTRIBUTING.md.

## Getting Started
To get a feel for the suite, try running a basic job. Just do
```bash
python submit_to_condor.py mytestjob samples/configuration_files/GeneratorLevelMC_2016.py --setlohi 100000 100001
```
(You can use <kbd>^C</kbd> to cancel if you want.)

`submit_to_condor.py` is your primary interaction point with this suite. It takes a
name for your job, a configuration file, and the runnumbers you want to use and submits
them in batches to Condor. (It's best to run it using `nohup` or in a `tmux` or
`screen` session.) It will wait while your jobs run and periodically check on their
progress, submitting more jobs as they complete. This helps you be a good citizen in
your use of Condor by avoiding having too many jobs running at once. It will even move
your jobs from their running device (usually `/data2`) to a storage device
inaccessible to Condor (e.g., `/data6`)!

While the job is running, if you look in `/data2/<your username>/work/mytestjob/100000/`
(the job's `WORK_DIR`), you should see the files created by the job; this is the
directory where they are stored while the job runs. One, called
`mytestjob_*_general.log`, summarizes the job progress; each stage of the job generates
an additional log file, usually called `<jobname>_<jobnumber>_<stagename>.log`.

Once the job completes, `run_stages.py` (the script that `submit_to_condor.py` submits to
Condor) moves the output from the `WORK_DIR` to the `DATA_DIR` and `LOG_DIR`. From there,
`submit_to_condor.py` picks the output up and moves it to directories on the storage
device (`/data6` by default). If you look in
`/data6/<your username>/data/mytestjob/100000/` and
`/data6/<your username>/log/mytestjob/100000/` after the script completes, you should see
the output files from the job (a `.xgen` file in the `data` directory and two `.log`, a
`.root`, and a `.xml` file in the `log` directory).

### Using Templates
Templates are easy-to-edit, almost ready-to-go example scripts. They contain edit
points enclosed by `<<<<` `>>>>`. Simply copy the file to your directory, search for
`<<<<` or `>>>>` inside the file, make the appropriate edits, and you're ready to go.
(You'll know you've made all the necessary changes when `<<<<` and `>>>>` no longer
appear in the file.)

### Testing
Once you've written or selected a configfile (see below), you should test it before submitting to
condor. First, run `python run_stages.py <path/to/configfile>` and check the output.
Then, submit a small batch to Condor using
`python submit_to_condor.py <jobname> <path/to/configfile> --setlohi 100000 100010 --test`
, wait for it to finish, then check the output. If everything is as-expected, you can
go ahead and submit for real using `submit_to_condor.py`.

## Questions
If you have questions or feedback, open an Issue in the
[repository](https://github.com/goi42/SU-lhcb-MC-gen/issues).

## Contributing
See CONTRIBUTING.md.

## Conceptual Framework
What follows is an overview of the logic behind SU-lhcb-MC-gen:

### organization
The following organizational structure is ___fundamental___ to SU-lhcb-MC-gen:
```
WORK_DIR = <sys>/<user>/work/<jobname>/<jobnum>
DATA_DIR = <sys>/<user>/data/<jobname>/<jobnum>
LOG_DIR = <sys>/<user>/log/<jobname>/<jobnum>
```
`sys` is the path to the system the job should run on (usually `/data2`). `jobnum` is
the sub-job number for the `jobname`.

Scripts run in the work directory, data files are stored in the data directory, and
log files are stored in the log directory. The scripts in this suite rely on this
structure and ___will not work___ without it. Keep this in mind, particularly when
developing.

### run_stages.py
At the heart of SU-lhcb-MC-gen is `run_stages.py`. This does most of the leg-work to
run scripts. `run_stages.py` centers around a function in the configuration file
called `make_stage_list`, which describes the scripts to be run, how, and in what
order. If you do not want to submit in-batch, you can run `run_stages.py` on its own.

`run_stages.py` is script-agnostic. You can run whatever sort of code you like using
it, so long as the code fits in the `make_stage_list` framework.

#### make_stage_list()
This function _must_ appear in your configfile and return a list of dictionaries of
the following form:
```python
def make_stage_list(USER, BASE_NAME):  # DO NOT CHANGE THIS LINE; run_stages.py will pass its USER and BASE_NAME parameters--you may refer to them inside this function if you want to
    stage_list = [
        {
            'name': 'stagename',
            'scripts': {'desired/relative/path/to/script.ext': 'scriptcontent'},  # run_stages.py will create WORK_DIR/desired/relative/path/to/script.ext and write scriptcontent into it for every item in this dictionary
            'log': 'logfilename',  # stdout and stderr will be directed to this file while this stage runs
            'call_string': 'a tcsh command',  # run_stages.py will call this string with subprocess.call in a tsch shell; make sure to point it at your 'scripts' above if desired
            'to_remove': ['filenames_to_remove_after_stage_runs'],  # these files, if they exist, will be removed after the stage completes successfully
            'dataname': 'filename_to_be_put_in_data_directory',  # this file will be moved to DATA_DIR; all other generated (and not-removed) files and directories will be moved to LOG_DIR
            'run': True,  # if this is False, run_stages.py will skip this stage
            'scriptonly': False,  # if this is True (and 'run' is True), run_stages.py will write scripts but will not run the stage; cleanup still happens
        }
    ]
        
    return stage_list
```

#### arguments
A number of arguments are essential to `run_stages.py` and they must appear in your
configfile. There are, in theory, other ways to declare these parameters besides
using argparse, but this method is highly recommended. See the help string for each
argument to understand what it does.
```python
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
args = parser.parse_args() if basename(__main__.__file__) == 'run_stages.py' else parser.parse_known_args()[0]  # assume all arguments are for this script if 'run_stages.py' is the main file, else allow arguments to go to other scripts
for arg in vars(args):
    exec('{ARG} = args.{ARG}'.format(ARG=arg))  # eliminate need to reference things as arg.thing
# -- end mandatory section -- #
```

### moveFiles.py
This script contains helpful functions for moving completed jobs from the `run_sys`
to the `store_sys`. It has many useful options; see the in-file documentation.

### submit_to_condor.py
This script is built around `moveFiles.py`. It uses the same commandline arguments
but reappropriates them so that files can be moved around `run_stages.py`, which
`submit_to_condor.py` runs on Condor in batches. It is recommended to run this file
using `nohup` or `screen` or `tmux`.

This is the heart of SU-lhcb-MC-gen. Once you've tested your configfile, you
should only have to run this script (if nothing goes awry).
