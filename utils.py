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
