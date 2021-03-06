def nojobsrunning(user):
    '''does the user have any jobs active on Condor?
    '''
    from subprocess import check_output
    check = check_output(['condor_q {}'.format(user)], shell=True).split('\n')[-2]
    return True if '0 jobs; 0 completed, 0 removed, 0 idle, 0 running, 0 held, 0 suspended' in check else False


def Njobs(user):
    '''returns the number of jobs running on Condor for the given user
    '''
    from subprocess import check_output
    check = check_output(['condor_q {}'.format(user)], shell=True).split('\n')[-2]
    return int(check.split(' jobs;')[0])


def cpr(src, dst):
    '''does copy or copytree depending on whether src is a directory
    '''
    if isdir(src):
        copytree(src, dst)
    else:
        copy(src, dst)


def makelohilist(listofnums, maxsize):
    '''take listofnums, sort it (not in place), and find sequential series
    returns list of tuples of length 2, representing the [lo, hi) boundaries of sequential series in listofnums, where len(range(lo, hi)) <= maxsize
    '''
    if len(listofnums) != len(set(listofnums)):
        raise ValueError('listofnums contains duplicates!')
    
    indivnums = sorted(listofnums)
    
    # -- group the jobs-to-be-submitted into coherent groups
    lo = indivnums[0]
    lohilist = []
    
    secn = 0
    for i, n in enumerate(indivnums):
        secn += 1
        if (indivnums[-1] is n) or (n + 1 != indivnums[i + 1]) or secn >= maxsize:  # if the next n isn't this n+1, we've found the end of a consecutive section
            lohilist.append(
                (lo, n + 1)
            )
            if n is not indivnums[-1]:
                lo = indivnums[i + 1]
            secn = 0
    
    return lohilist


def incfilename(filename, i_start=0, i=None):
    '''chooses a name for a file by appending numbers incrementally (from i_start) to filename
    '''
    from os.path import exists, splitext
    if exists(filename):
        basename = splitext(filename)[0]
        suffname = splitext(filename)[1]
        newname = basename + str(i_start) + suffname
        if exists(newname):
            return incfilename(filename, i_start + 1)
        else:
            return newname
    else:
        return filename


def makepercent(num, tot, exact=False):
    'returns an integer representing num/tot as a percentage'
    exactvalue = float(num) * 100 / float(tot)
    return exactvalue if exact else int(exactvalue)

    
class updateprogress(object):
    """docstring for updateprogress"""
    
    def __init__(self, maxval):
        super(updateprogress, self).__init__()
        self.maxval = maxval
        self.printevery = float(self.maxval) / 100
        import imp
        try:
            imp.find_module('progressbar')
            self.useprogressbar = True
        except ImportError:
            self.useprogressbar = False
    
    def _printupdate(self, addstring=''):
        print 'on {0} out of {1} ({2}%){3}'.format(self.counter, self.maxval, makepercent(self.counter, self.maxval), addstring)

    def start(self):
        self.counter = 0
        if self.useprogressbar:
            import progressbar
            self.progbar = progressbar.ProgressBar(maxval=self.maxval,
                                                   widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage() ]
                                                   )
            self.progbar.start()
        else:
            self._lastprintupdate = 0
            print 'tracking progress'
            self._printupdate()
    
    def update(self, i):
        self.counter = i
        if self.useprogressbar:
            self.progbar.update(i)
        else:
            if self.counter - self._lastprintupdate >= self.printevery or (self.counter < self._lastprintupdate):
                self._printupdate()
                self._lastprintupdate = self.counter
    
    def finish(self):
        if self.useprogressbar:
            self.progbar.finish()
        else:
            self._printupdate(' (finished)')


def incname(afile, suffix='_ConflictedCopy', i_start=1):
    '''if afile exists, returns afilesuffix<i>, where <i> is the first integer name unused
    else, returns afile
    '''
    from os.path import exists, splitext
    
    def incname_suffix(afile, suffix, i):
        befext, ext = splitext(afile)
        nfile = befext + suffix + str(i) + ext
        if exists(nfile):
            return incname_suffix(afile, suffix, i + 1)
        else:
            return nfile
    
    if exists(afile):
        return incname_suffix(afile, suffix, i_start)
    else:
        return afile
