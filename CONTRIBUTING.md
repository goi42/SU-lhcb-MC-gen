# CONTRIBUTING
Once you've made your changes, do:
```bash
git checkout -b <username>/<descriptive-moniker>
git add <path(s)/to/your/changes>
git commit  # enter a short description of your changes
git push -u origin <username>/<descriptive-moniker>
```
Open a [pull-request](https://github.com/goi42/SU-lhcb-MC-gen/pulls) in the GitHub
[repository](https://github.com/goi42/SU-lhcb-MC-gen).

Contriubtions are encouraged, particularly to the documentation, samples, and
templates. Don't be shy!

Open an [issue](https://github.com/goi42/SU-lhcb-MC-gen/issues) if you have problems
or a question.

## Templates
Templates are designed to be easy-to-fill-in samples. A user should only have to edit a
few lines to get them to work. Wherever you want a user to make an edit, enclose it
between four less-than and greater-than symbols, `<<<<` `>>>>`, with a simple
description of what belongs there.

For example:
```python
evtnum = int('<<<<EVENTTYPE from DecFile (e.g., 15264011)>>>>')
```
should be replaced with, e.g.,
```python
evtnum = int('15264011')
```
Remember, keep it easy to understand.

Optional parameters should be specified using `<<<<[optional thing <<<<text to replace>>>>][description of optional thing]>>>>`
, e.g.,
```python
'call_string': 'lb-run -c best <<<<[--user-area <<<</path/to/your/Gauss/Build>>>>][this section only necessary if you are using a DecFile not included in the official release]>>>> Gauss/<<<<Gauss Version>>>> gaudirun.py $GAUSSOPTS/Gauss-Job.py $GAUSSOPTS/Gauss-2016.py $GAUSSOPTS/GenStandAlone.py $DECFILESROOT/options/{0}.py $LBPYTHIA8ROOT/options/Pythia8.py'.format(evtnum),
```
which would be replaced by, e.g.,
```python
'call_string': 'lb-run -c best --user-area ~/cmtuser Gauss/v49r10 gaudirun.py $GAUSSOPTS/Gauss-Job.py $GAUSSOPTS/Gauss-2016.py $GAUSSOPTS/GenStandAlone.py $DECFILESROOT/options/{0}.py $LBPYTHIA8ROOT/options/Pythia8.py'.format(evtnum),
```
