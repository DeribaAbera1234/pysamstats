# cython: profile=True


import sys
import numpy as np
cimport numpy as np
import time


def normalise_coords(start, end, one_based):
    if one_based:
        start = start - 1 if start is not None else None
        end = end - 1 if end is not None else None
    return start, end


#############################
# BASIC COVERAGE STATISTICS #
#############################


cpdef object construct_rec_coverage(object samfile, object col, bint one_based=False):

    # statically typed variables
    cdef int i # loop index
    cdef int n # total number of reads in column
    cdef bint b_is_proper_pair
    cdef np.ndarray[np.uint8_t, ndim=1] is_proper_pair # whether the read is mapped in a proper pair
    # N.B., cython doesn't explicitly support boolean arrays, so we use uint8 here

    # initialise variables
    n = col.n
    is_proper_pair = np.zeros((n,), dtype=np.uint8)

    # get chromosome name and position
    chrom = samfile.getrname(col.tid)
    pos = col.pos + 1 if one_based else col.pos
    
    # loop over reads
    reads = col.pileups
    for i in range(n):
        read = reads[i]
        aln = read.alignment
        b_is_proper_pair = aln.is_proper_pair
        is_proper_pair[i] = b_is_proper_pair

    # set up various boolean arrays
    is_proper_pair.dtype = np.bool

    # determine counts
    reads_all = n
    reads_pp = np.count_nonzero(is_proper_pair)

    return {'chr': chrom, 
            'pos': pos, 
            'reads_all': reads_all, 
            'reads_pp': reads_pp}


def stat_coverage(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(start, end, one_based)
    for col in samfile.pileup(chrom, start, end):
        yield construct_rec_coverage(samfile, col, one_based)
        
        
def print_stats(statfun, samfile, chrom=None, start=None, end=None, 
                one_based=False, delimiter='\t', header=None, 
                progress=None):
    cdef long long counter = 0
    cdef long long modulus
    if header is not None:
        print >>sys.stdout, delimiter.join(header)
    if progress is None:
        for rec in statfun(samfile, chrom=chrom, start=start, end=end, one_based=one_based):
            print >>sys.stdout, delimiter.join(str(v) for v in rec)        
    else:
        modulus = progress
        before = time.time()
        before_all = before
        for rec in statfun(samfile, chrom=chrom, start=start, end=end, one_based=one_based):
            counter += 1
            print >>sys.stdout, delimiter.join(str(v) for v in rec)
            if counter % modulus == 0:
                after = time.time()
                elapsed = after - before
                print >>sys.stderr, '%s rows in %.2fs (%d rows/s)' % (progress, elapsed, progress/elapsed)
                before = after
        after_all = time.time()
        elapsed_all = after_all - before_all
        print >>sys.stderr, '%s rows in %.2fs (%d rows/s)' % (counter, elapsed_all, counter/elapsed_all)
    
    
def print_coverage(samfile, chrom=None, start=None, end=None, one_based=False, 
                   delimiter='\t', omit_header=False, progress=None):
    if omit_header:
        header = None
    else:
        header = ('chr', 'pos', 'reads_all', 'reads_pp')
    print_stats(stat_coverage, samfile, chrom=chrom, start=start, end=end, 
                one_based=one_based, delimiter=delimiter, header=header, 
                progress=progress)
    
    
################################
# STRANDED COVERAGE STATISTICS #
################################


cpdef object construct_rec_coverage_strand(object samfile, object col, bint one_based=False):

    # statically typed variables
    cdef int i # loop index
    cdef int n # total number of reads in column
    cdef bint b_is_reverse, b_is_proper_pair
    cdef np.ndarray[np.uint8_t, ndim=1] is_reverse # whether read is mapped to reverse strand
    cdef np.ndarray[np.uint8_t, ndim=1] is_proper_pair # whether the read is mapped in a proper pair
    # N.B., cython doesn't explicitly support boolean arrays, so we use uint8 here

    # initialise variables
    n = col.n
    is_reverse = np.zeros((n,), dtype=np.uint8)
    is_proper_pair = np.zeros((n,), dtype=np.uint8)

    # get chromosome name and position
    chrom = samfile.getrname(col.tid)
    pos = col.pos + 1 if one_based else col.pos
    
    # loop over reads
    reads = col.pileups
    for i in range(n):
        read = reads[i]
        aln = read.alignment
        b_is_reverse = aln.is_reverse
        is_reverse[i] = b_is_reverse
        b_is_proper_pair = aln.is_proper_pair
        is_proper_pair[i] = b_is_proper_pair

    # set up various boolean arrays
    is_reverse.dtype = np.bool
    is_proper_pair.dtype = np.bool
    is_forward = ~is_reverse
    is_pp_fwd = is_forward & is_proper_pair
    is_pp_rev = is_reverse & is_proper_pair

    # determine counts
    reads_all = n
    reads_fwd = np.count_nonzero(is_forward)
    reads_rev = np.count_nonzero(is_reverse)
    reads_pp = np.count_nonzero(is_proper_pair)
    reads_pp_fwd = np.count_nonzero(is_pp_fwd)
    reads_pp_rev = np.count_nonzero(is_pp_rev)

    return {'chr': chrom, 
            'pos': pos, 
            'reads_all': reads_all, 
            'reads_fwd': reads_fwd, 
            'reads_rev': reads_rev, 
            'reads_pp': reads_pp,
            'reads_pp_fwd': reads_pp_fwd,
            'reads_pp_rev': reads_pp_rev}


def stat_coverage_strand(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(start, end, one_based)
    for col in samfile.pileup(chrom, start, end):
        yield construct_rec_coverage_strand(samfile, col, one_based)
        
        
def print_coverage_strand(samfile, chrom=None, start=None, end=None, 
                          one_based=False, delimiter='\t', omit_header=False, 
                          progress=None):
    if omit_header:
        header = None
    else:
        header = ('chr', 'pos', 
                  'reads_all', 'reads_fwd', 'reads_rev', 
                  'reads_pp', 'reads_pp_fwd', 'reads_pp_rev')
    print_stats(stat_coverage_strand, samfile, chrom=chrom, start=start, end=end, 
                one_based=one_based, delimiter=delimiter, header=header, 
                progress=progress)
    
    
################################
# EXTENDED COVERAGE STATISTICS #
################################


cpdef object construct_rec_coverage_ext(object samfile, object col, bint one_based=False):
    pass    # TODO


