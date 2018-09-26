# SU-lhcb-MC-gen
A suite of scripts for generating MC on lhcb-dev

## About
This is a suite of scripts designed to make life easier for people submitting
MC jobs (or any jobs) to Condor on lhcb-dev. It revolves around the use of
configuration files and the script run_stages.py.

In order to use this suite, simply clone the git repo, create a configuration
file, and off you go! There are sample configuration files and templates in the
`samples/` and `templates/` directories. You should be able to find what you
need there.

Don't be shy about contributing! If you have a configuration file you're proud
of, add it to the samples! See CONTRIBUTING.md.

## Requirements
This suite is designed to work with python 2.7 on lhcb-dev.

It is recommended, but not required, that users install the
[`progressbar`](https://progressbar-2.readthedocs.io/en/latest/) package.

## Getting Started
To get a feel for the suite, try running a sample configuration file. Just do
(preferably in a `screen` or `tmux` session):
```bash
python submit_to_condor.py mytestjob samples/configuration_files/GeneratorLevelMC_2016.py --setlohi 100000 100010
```
(<kbd>^C</kbd> will cancel and <kbd>^Z</kbd> will pause. \[This won't affect
any jobs submitted to Condor.\])

`submit_to_condor.py` is your primary interaction point with this suite. It
takes a name for your job, a configuration file, and the runnumbers you want to
use and submits them in batches to Condor. (It's best to run it in a `tmux` or
`screen` session.) It will wait while your jobs run and periodically check on
their progress, submitting more jobs as they complete. This helps you be a good
citizen in your use of Condor by avoiding having too many jobs running at once.
It will even move your jobs from their running device (usually `/data2`) to a
storage device inaccessible to Condor (e.g., `/data6`)!

### Exploring the Jobs
Leave `submit_to_condor.py` running for now. In another shell, do
```bash
condor_q <your username>
```
You should see (100010 - 100000 = ) 10 jobs listed, either running or idle.
These are the 10 jobs you submitted to Condor! They will handle whatever script
you submitted while you wait, whether you are logged in or not.

Once all your jobs have started running, if you look in
`/data2/<your username>/work/mytestjob/`, you should see directories named
`[100000, 100009]`. These are the so-called `WORK_DIR` for each of the 10 jobs
you submitted and all your job's output should be stored here while it runs.

In each job's `WORK_DIR`, you should see a file called
`mytestjob_*_general.log`, which summarizes the job progress. Each stage of the
job generates an additional log file, usually called
`<jobname>_<jobnumber>_<stagename>.log`. As each job progresses, you should see
more and more files stored in this directory.

> If a job fails to complete for whatever reason, all files will remain in the
> `WORK_DIR`. This allows you to easily see which of your jobs had problems and
> prevents them from being moved to storage before they are ready.
>
> __NB:__ If the `WORK_DIR` already exists, your job __will not run__ by
> default; this is to prevent accidental overwrites. Best practice is to remove
> the numbered directories manually, but if you're very sure you want to
> overwrite any existing data, you can use `--WORK_DIR_EXISTS` when you run.
>
> > `WORK_DIR` refers to the numbered directory, e.g.,
> > `/data2/<your username>/work/mytestjob/100000/`, not
> > `/data2/<your username>/work/mytestjob/`, which just helps organize the many
> > `WORK_DIR` and will not prevent the job from running.

Once the job completes, `run_stages.py` (the script that `submit_to_condor.py`
submits to Condor) moves the output from the `WORK_DIR` to the `DATA_DIR` and
`LOG_DIR`. From there, `submit_to_condor.py` picks the output up and moves it
to directories on the storage device (`/data6` by default). If you look in
`/data6/<your username>/data/mytestjob/100000/` and
`/data6/<your username>/log/mytestjob/100000/` after the job completes, you
should see the output files from the job.

Congratulations, you've successfully submitted your first jobs!

### Submission and Configuration Files
Running jobs revolves around the use of configuration files. These tell
`run_stages.py` what to do. The easiest way to write them is to use a template
(see __Using Templates__ below). Once you are confident your configuration file
works the way you want it to (see __Testing__ below), you pass it as an
argument to either `run_stages.py` or `submit_to_condor.py` (which passes it to
`run_scripts.py`).

You are encouraged to write add your own command-line arguments to your
configuration file using the `argparse` module in python.

> If you add your own command-line arguments, ___make sure they are optional___
> (e.g., have `--` in front of their names) to help avoid potential conflicts
> with other scripts.

You can pass your configuration-file arguments to both `run_stages.py` and
`submit_to_condor.py`. They know how to handle them.

You can read more about `run_stages.py` and `submit_to_condor.py` in the
__Conceptual Framework__ section below.

### Using Templates
Templates are easy-to-edit, almost ready-to-go configuration files. They
contain edit points enclosed by `<<<<` `>>>>`. Simply copy the file to your
directory, search for `<<<<` or `>>>>` inside the file, make the appropriate
edits, and you're ready to go. (Note you will need to overwrite the `<<<<` and
`>>>>`&mdash;do not leave them in the file! You'll know you've made all the
necessary changes when `<<<<` and `>>>>` no longer appear in the file.)

### Testing
Once you've written or selected a configuration file, you should test it before
submitting to condor. First, run `python run_stages.py <path/to/configfile>`
and check the output. Then, submit a small batch to Condor using `python
submit_to_condor.py <jobname> <path/to/configfile> --setlohi 100000 100010
--test` , wait for it to finish, then check the output. If everything is
as-expected, you can go ahead and submit for real using `submit_to_condor.py`.

> Remember that `run_stages.py` does not know what you are trying to do. It's
> up to you to make sure your scripts actually work and that any environments
> you use (e.g., a local Gauss build) are built properly

## Questions
If you have questions or feedback, open an Issue in the
[repository](https://github.com/goi42/SU-lhcb-MC-gen/issues).

## Contributing
See CONTRIBUTING.md.

## Detailed Description
What follows is an explanation of how to use SU-lhcb-MC-gen:

### organization
The following organizational structure is ___fundamental___ to SU-lhcb-MC-gen:
```
WORK_DIR = <sys>/<user>/work/<jobname>/<jobnum>
DATA_DIR = <sys>/<user>/data/<jobname>/<jobnum>
LOG_DIR = <sys>/<user>/log/<jobname>/<jobnum>
```
`sys` is the path to the system the job should run on (usually `/data2`).
`jobnum` is the sub-job number for the `jobname`.

Scripts run in the work directory, data files are stored in the data directory,
and log files are stored in the log directory. The scripts in this suite rely on
this structure and ___will not work___ without it. Keep this in mind,
particularly when developing.

### run_stages.py
At the heart of SU-lhcb-MC-gen is `run_stages.py`. This does most of the
leg-work to run scripts. `run_stages.py` centers around a function in the
configuration file called `make_stage_list`, which describes the scripts to be
run, how, and in what order. If you do not want to submit in-batch, you can run
`run_stages.py` on its own.

`run_stages.py` is script-agnostic. You can run whatever sort of code you like
using it, so long as the code fits in the `make_stage_list` framework.

#### make_stage_list()
This function _must_ appear in your configfile and return a list of
dictionaries of the following form:
```python
def make_stage_list(USER, BASE_NAME):  # DO NOT CHANGE THIS LINE; run_stages.py will pass its USER and BASE_NAME parameters--you may refer to them inside this function if you want to
    stage_list = [
        {
            'name': 'stagename',  # what run_stages.py should call this stage
            'scripts': {'desired/relative/path/to/script.ext': 'scriptcontent'},  # run_stages.py will create WORK_DIR/desired/relative/path/to/script.ext and write scriptcontent into it for every item in this dictionary
            'log': 'logfilename',  # stdout and stderr will be directed to this file while this stage runs
            'call_string': 'a tcsh command',  # run_stages.py will call this string with subprocess.call in a tsch shell; make sure to point it at your 'scripts' above if desired
            'to_remove': ['filenames_to_remove_after_stage_runs'],  # these files, if they exist, will be removed after the stage completes successfully
            'dataname': 'filename_to_be_put_in_data_directory',  # the file with this name will be moved to DATA_DIR; all other generated, non-removed files and directories will be moved to LOG_DIR
            'run': True,  # if this is False, run_stages.py will skip this stage
            'scriptonly': False,  # if this is True (and 'run' is True), run_stages.py will write scripts but will not run the stage; cleanup still happens
        }
    ]
        
    return stage_list
```

This function determines everything that happens in your job. `run_stages.py`
will run the `'call_string'` (along with some environment-setting parameters)
inside a fresh `tcsh` shell for each stage sequentially. This means that each
stage can refer to and use the output of previous stages.

> `run_stages.py` is script agnostic, meaning it does not care what sort of
> thing you tell it to run. This means it's your responsibility to make sure
> the script run in each stage picks up the output from the previous stage if
> you want it to.
> > Relative file paths are essential for this. The `WORK_DIR` is the current
> > working directory while your job runs, so all output files are created
> > there and can be referred to by name by other stages in your script.

#### arguments
A number of arguments are essential to `run_stages.py` and they must appear in
your configfile. There are, in theory, other ways to declare these parameters
besides using argparse, but this method is highly recommended. See the help
string for each argument to understand what it does.
```python
# -- essential parameters -- #
parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='set parameters to be used in run_stages.py')

parser.add_argument('configfile', type=os.path.abspath,
                    help='this argument must be here to ensure integration with run_stages.py')
parser.add_argument('--SIGNAL_NAME', default='TestProduction',
                    help='what you want the organizing directory for your job to be named. submit_to_condor.py sets this parameter when it submits jobs.')
parser.add_argument('--RUN_NUMBER', type=int, default=300000,
                    help='set equal to the job number by submit_to_condor.py, which allows the user to change script behavior for each job, e.g., set a different random seed.')
parser.add_argument('--RUN_SYS', default='/data2', type=os.path.abspath,
                    help='system to run on')
cleangroup = parser.add_argument_group('cleaning options')
cleangroup.add_argument('--noCLEANSTAGES', dest='CLEANSTAGES', action='store_false',
                        help='deletes data from earlier stages as it goes.')
cleangroup.add_argument('--noCLEANWORK', dest='CLEANWORK', action='store_false',
                        help='moves files out of work directory.')
cleangroup.add_argument('--PRECLEANED', action='store_true',
                        help='if this script has already been run with CLEANWORK active, you can specify this argument so that it moves appropriate files to the work directory first. Used automatically by submit_to_condor.py')
cleangroup.add_argument('--SOME_MISSING', action='store_true',
                        help='if running a later stage, you may specify this argument to let the script terminate without errors if the input files are missing. Used automatically by submit_to_condor.py')
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
You can also add your own custom arguments inside your configfile!
`run_stages.py` won't care about them, but your configfile will still see them.
`submit_to_condor.py` is even written with this in
mind&mdash;`submit_to_condor.py <jobname> <path/to/configfile> <your
arguments>` should work just fine, as long as your arguments don't conflict
with the ones used by this suite.

> If you add your own command-line arguments, ___make sure they are optional___
> (e.g., have `--` in front of their names) to help avoid potential conflicts
> with other scripts.


### moveFiles.py
This script contains helpful functions for moving completed jobs from the
`run_sys` to the `store_sys`. It has many useful options; see the in-file
documentation. If your job submission goes smoothly, you probably will not have
to interact with this file directly.

### submit_to_condor.py
This script is built around `moveFiles.py`. It uses the same commandline
arguments (plus some others) but reappropriates them so that files can be moved
around `run_stages.py`, which `submit_to_condor.py` runs on Condor in batches.
You can also pass it any arguments declared in your configfile. It is
recommended to run this file using `screen` or `tmux`. (See the man files for
each of these if you're not familiar.)

This is the heart of SU-lhcb-MC-gen. Once you've tested your configfile, you
should only have to run this script (if nothing goes awry).

#### `--chunks_of`
This is the main parameter that allows you to be a good citizen on Condor. This
parameter specifies the maximum number of jobs you want to have on Condor and
`run_sys` at once. The default value should be fine most of the time, but if
you have particularly slow jobs (that take more than two hours to run, say),
you should consider reducing it. If your jobs are particularly fast (say, less
than 10 minutes), you can use a larger value.

#### `--setlohi` and `--runfromstorage`
When you use `submit_to_condor.py`, you must use one of these two options.

##### `--setlohi`
sets the low (inclusive) and high (exclusive) `RUN_NUMBER` you want to use. So
`--setlohi 100000 101234` will submit 1234 jobs with `RUN_NUMBER` equal to
[100000, 101233).

> __NB:__ If you are using `submit_to_condor.py` to submit Monte Carlo, this is
> _not_ equal to the number of events. You will end up with a number of events
> equal to (hi - lo) * `NUM_EVENT`, where `NUM_EVENT` is the number of events
> generated in each job

##### `--runfromstorage`
Use this option if you want to run over pre-existing runs. It will find all the
run numbers in the `DATA_DIR` on `store_sys` for this `SIGNAL_NAME`, and move
this data to the `run_sys`. Since `submit_to_condor.py` always uses the
`--PRECLEANED` option (see argument documentation for `run_stages.py` above),
this data will be available for whatever stages you submit now.

This is a powerful utility that means you do not have to run all of your stages
at once. For example, suppose you want to generate MC using
`samples/configuration_files/basic_MCGen_2016_s28r1_WithArguments.py`. You
could generate just through the `Brunel` stage by doing:
```bash
python submit_to_condor.py myMCgen samples/configuration_files/basic_MCGen_2016_s28r1_WithArguments.py --GEN_LEVEL "gauss boole moorel0 moorehlt1 moorehlt2 brunel" --setlohi 100000 100100
```
Once these jobs finish, if you decide you _do_ want to run the DaVinci stage to
get stripped data, you could do:
```bash
python submit_to_condor.py myMCgen samples/configuration_files/basic_MCGen_2016_s28r1_WithArguments.py --GEN_LEVEL "davinci" --runfromstorage
```
This will take all the MC that you successfully generated before and move the
data files to where DaVinci can get them on the `run_sys` instead of leaving
them on the `store_sys`. If some of your jobs failed, they will be skipped.

You can still specify a specific job range with `--setlohi` if you use
`--runfromstorage`. Suppose you only wanted to run the DaVinci stage over the
first 50 jobs (for whatever reason). Just add `--setlohi 100000 100050`:
```bash
python submit_to_condor.py myMCgen samples/configuration_files/basic_MCGen_2016_s28r1_WithArguments.py --GEN_LEVEL "davinci" --runfromstorage --setlohi 100000 100050
```
Note that using `--setlohi 0 100050` would have had the same effect: When
`--runfromstorage` is specified, `--setlohi` just ensures the run numbers fall
within the specified range.


#### What if `submit_to_condor.py` quits?
Check the output on screen to see how far it got. If there's nothing wrong with
your jobs, you can just run it again with `--setlohi <lo> <hi>`, where `<lo>`
is the top end of the last successfully submitted range and `<hi>` is the
highest run number desired. For instance, if it quit while the range [100100,
100200) out of [100000, 105000) was running, you would use
`--setlohi 100200 105000`.

> Remember that Condor is a separate system, and it's where your jobs actually run.
> `submit_to_condor.py` just handles the submission process.
