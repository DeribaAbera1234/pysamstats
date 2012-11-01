# cython: profile=True

"""
TODO doc me

"""

# standard library imports
import math
import itertools

# 3rd party imports
from csamtools cimport Samfile, PileupRead, AlignedRead, PileupProxy, Fastafile
import numpy as np
cimport numpy as np
from libc.math cimport sqrt


cdef class AggStrnd:
    cdef int n
    cdef int all
    cdef int fwd
    cdef int rev
    
    def __cinit__(self, n):
        self.n = n
        self.all = 0
        self.fwd = 0
        self.rev = 0
    
    # to be overridden in subclasses    
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse):
        return 0

    cdef add(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse):
        if self.test(read, aln, is_proper_pair, is_reverse):
            self.all += 1
            if is_reverse:
                self.rev += 1
            else:
                self.fwd += 1
                

cdef class AggStrndUnmp:
    cdef int n
    cdef int all
    cdef int fwd
    cdef int rev
    
    def __cinit__(self, n):
        self.n = n
        self.all = 0
        self.fwd = 0
        self.rev = 0
    
    # to be overridden in subclasses    
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse, bint mate_is_unmapped):
        return 0

    cdef add(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse, bint mate_is_unmapped):
        if self.test(read, aln, is_proper_pair, is_reverse, mate_is_unmapped):
            self.all += 1
            if is_reverse:
                self.rev += 1
            else:
                self.fwd += 1
        

cdef class AggPpStrnd:
    cdef int n
    cdef int all
    cdef int fwd
    cdef int rev
    cdef int pp
    cdef int pp_fwd
    cdef int pp_rev
    
    def __cinit__(self, n):
        self.n = n
        self.all = 0
        self.fwd = 0
        self.rev = 0
        self.pp = 0
        self.pp_fwd = 0
        self.pp_rev = 0
    
    # to be overridden in subclasses    
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse):
        return 0

    cdef add(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse):
        if self.test(read, aln, is_proper_pair, is_reverse):
            self.all += 1
            if is_reverse:
                self.rev += 1
                if is_proper_pair:
                    self.pp += 1
                    self.pp_rev += 1
            else:
                self.fwd += 1
                if is_proper_pair:
                    self.pp += 1
                    self.pp_fwd += 1
        

cdef class AggReads(AggPpStrnd):
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse):
        return 1


cdef class AggReadsMateUnmapped(AggStrndUnmp):
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse, bint mate_is_unmapped):
        return mate_is_unmapped
    
    
cdef class AggReadsMateOtherChr(AggStrndUnmp):
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse, bint mate_is_unmapped):
        return not mate_is_unmapped and aln.rnext != aln.tid 
        
    
cdef class AggReadsMateSameStrand(AggStrndUnmp):
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse, bint mate_is_unmapped):
        cdef bint mate_is_reverse
        if not mate_is_unmapped:
            mate_is_reverse = aln.mate_is_reverse
            return (is_reverse and mate_is_reverse) or (not is_reverse and not mate_is_reverse)
        else:
            return 0
    
    
cdef class AggReadsFaceaway(AggStrndUnmp):
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse, bint mate_is_unmapped):
        cdef int tlen
        if not mate_is_unmapped:
            tlen = aln.tlen
            return ((is_reverse and tlen > 0) # mapped to reverse strand but leftmost
                    or (not is_reverse and tlen < 0)) # mapped to fwd strand but rightmost
        else:
            return 0
    
    
cdef class AggReadsEdit0(AggPpStrnd):
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse):
        return aln.opt('NM') == 0
    
    
cdef class AggReadsSoftClipped(AggPpStrnd):
    cdef bint test(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse):
        cigar = aln.cigar
        cdef int i = 0
        for i in range(len(cigar)):
            op = cigar[i]
            if op[0] == 4: # softclip code
                return 1
        return 0
    

cdef struct PpStrndCounts:
    int all
    int fwd
    int rev
    int pp
    int pp_fwd
    int pp_rev
    
    
cdef class AggVariation:
    cdef int n
    cdef PpStrndCounts A
    cdef PpStrndCounts C
    cdef PpStrndCounts T
    cdef PpStrndCounts G
    cdef PpStrndCounts N
    cdef PpStrndCounts deletions
    cdef PpStrndCounts insertions
    
    def __cinit__(self, n):
        self.n = n
        self.A = PpStrndCounts(all=0, fwd=0, rev=0, pp=0, pp_fwd=0, pp_rev=0)
        self.C = PpStrndCounts(all=0, fwd=0, rev=0, pp=0, pp_fwd=0, pp_rev=0)
        self.T = PpStrndCounts(all=0, fwd=0, rev=0, pp=0, pp_fwd=0, pp_rev=0)
        self.G = PpStrndCounts(all=0, fwd=0, rev=0, pp=0, pp_fwd=0, pp_rev=0)
        self.N = PpStrndCounts(all=0, fwd=0, rev=0, pp=0, pp_fwd=0, pp_rev=0)
        self.deletions = PpStrndCounts(all=0, fwd=0, rev=0, pp=0, pp_fwd=0, pp_rev=0)
        self.insertions = PpStrndCounts(all=0, fwd=0, rev=0, pp=0, pp_fwd=0, pp_rev=0)
    
    cdef add(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse):
        cdef int indel = read.indel
#        cdef char base
        cdef int qpos
        if indel < 0:
            self.deletions = increment_pp_strnd_counts(self.deletions, is_proper_pair, is_reverse)
        elif indel > 0:
            self.insertions = increment_pp_strnd_counts(self.insertions, is_proper_pair, is_reverse)
        else:
            qpos = read.qpos
            base = aln.seq[qpos]
            if base == 'A':
                self.A = increment_pp_strnd_counts(self.A, is_proper_pair, is_reverse)
            elif base == 'C':
                self.C = increment_pp_strnd_counts(self.C, is_proper_pair, is_reverse)
            elif base == 'T':
                self.T = increment_pp_strnd_counts(self.T, is_proper_pair, is_reverse)
            elif base == 'G':
                self.G = increment_pp_strnd_counts(self.G, is_proper_pair, is_reverse)
            elif base == 'N':
                self.N = increment_pp_strnd_counts(self.N, is_proper_pair, is_reverse)

cdef PpStrndCounts increment_pp_strnd_counts(PpStrndCounts c, bint is_proper_pair, bint is_reverse):
    c.all += 1
    if is_reverse:
        c.rev += 1
        if is_proper_pair:
            c.pp += 1
            c.pp_rev += 1
    else:
        c.fwd += 1
        if is_proper_pair:
            c.pp += 1
            c.pp_fwd += 1
    return c
    
    
cpdef build_coverage_stats(PileupProxy col):
    cdef int n = col.n
    cdef int ri
    cdef bint is_proper_pair
    cdef bint is_reverse
    cdef bint mate_is_unmapped
    cdef PileupRead read
    cdef AlignedRead aln

    # create aggregators
    agg_reads = AggReads(n)
    agg_reads_mate_unmapped = AggReadsMateUnmapped(n)
    agg_reads_mate_other_chr = AggReadsMateOtherChr(n)
    agg_reads_mate_same_strand = AggReadsMateSameStrand(n)
    agg_reads_faceaway = AggReadsFaceaway(n)
    agg_reads_edit0 = AggReadsEdit0(n)
    agg_reads_softclipped = AggReadsSoftClipped(n)
    
    # access reads
    reads = col.pileups

    # iterate over reads in the column
    for ri in range(n):
        read = reads[ri]
        aln = read.alignment
        
        # optimisation - access these now so done only once
        is_proper_pair = aln.is_proper_pair
        is_reverse = aln.is_reverse
        mate_is_unmapped = aln.mate_is_unmapped
        
        # pass reads to aggregators
        agg_reads.add(read, aln, is_proper_pair, is_reverse)
        agg_reads_mate_unmapped.add(read, aln, is_proper_pair, is_reverse, mate_is_unmapped)
        agg_reads_mate_other_chr.add(read, aln, is_proper_pair, is_reverse, mate_is_unmapped)
        agg_reads_mate_same_strand.add(read, aln, is_proper_pair, is_reverse, mate_is_unmapped)
        agg_reads_faceaway.add(read, aln, is_proper_pair, is_reverse, mate_is_unmapped)
        agg_reads_edit0.add(read, aln, is_proper_pair, is_reverse)
        agg_reads_softclipped.add(read, aln, is_proper_pair, is_reverse)
            
    # construct output row
    data = {
            'reads': agg_reads.all,
            'reads_fwd': agg_reads.fwd,
            'reads_rev': agg_reads.rev,
            'reads_pp': agg_reads.pp,
            'reads_pp_fwd': agg_reads.pp_fwd,
            'reads_pp_rev': agg_reads.pp_rev,
            'reads_mate_unmapped': agg_reads_mate_unmapped.all,
            'reads_mate_unmapped_fwd': agg_reads_mate_unmapped.fwd,
            'reads_mate_unmapped_rev': agg_reads_mate_unmapped.rev,
            'reads_mate_other_chr': agg_reads_mate_other_chr.all,
            'reads_mate_other_chr_fwd': agg_reads_mate_other_chr.fwd,
            'reads_mate_other_chr_rev': agg_reads_mate_other_chr.rev,
            'reads_mate_same_strand': agg_reads_mate_same_strand.all,
            'reads_mate_same_strand_fwd': agg_reads_mate_same_strand.fwd,
            'reads_mate_same_strand_rev': agg_reads_mate_same_strand.rev,
            'reads_faceaway': agg_reads_faceaway.all,
            'reads_faceaway_fwd': agg_reads_faceaway.fwd,
            'reads_faceaway_rev': agg_reads_faceaway.rev,
            'reads_edit0': agg_reads_edit0.all,
            'reads_edit0_fwd': agg_reads_edit0.fwd,
            'reads_edit0_rev': agg_reads_edit0.rev,
            'reads_edit0_pp': agg_reads_edit0.pp,
            'reads_edit0_pp_fwd': agg_reads_edit0.pp_fwd,
            'reads_edit0_pp_rev': agg_reads_edit0.pp_rev,
            'reads_softclipped': agg_reads_softclipped.all,
            'reads_softclipped_fwd': agg_reads_softclipped.fwd,
            'reads_softclipped_rev': agg_reads_softclipped.rev,
            'reads_softclipped_pp': agg_reads_softclipped.pp,
            'reads_softclipped_pp_fwd': agg_reads_softclipped.pp_fwd,
            'reads_softclipped_pp_rev': agg_reads_softclipped.pp_rev,
            }
    return data

    
class CoverageStatsTable(object):
    
    def __init__(self, samfn, chr=None, start=None, end=None):
        self.samfn = samfn
        self.chr = chr
        self.start = start
        self.end = end
        
    def __iter__(self):

        # define header
        fixed_variables = ['chr', 'pos', 'reads']
        computed_variables = [
                              'reads_fwd', 
                              'reads_rev',
                              'reads_pp',
                              'reads_pp_fwd',
                              'reads_pp_rev',
                              'reads_mate_unmapped',
                              'reads_mate_unmapped_fwd',
                              'reads_mate_unmapped_rev',
                              'reads_mate_other_chr',
                              'reads_mate_other_chr_fwd',
                              'reads_mate_other_chr_rev',
                              'reads_mate_same_strand',
                              'reads_mate_same_strand_fwd',
                              'reads_mate_same_strand_rev',
                              'reads_faceaway',
                              'reads_faceaway_fwd',
                              'reads_faceaway_rev',
                              'reads_edit0',                            
                              'reads_edit0_fwd',
                              'reads_edit0_rev',                            
                              'reads_edit0_pp',                            
                              'reads_edit0_pp_fwd',
                              'reads_edit0_pp_rev',
                              'reads_softclipped',                         
                              'reads_softclipped_fwd',                         
                              'reads_softclipped_rev',                         
                              'reads_softclipped_pp',
                              'reads_softclipped_pp_fwd',                         
                              'reads_softclipped_pp_rev',                         
                              ]
        header = fixed_variables + computed_variables
        yield header
        
        # open sam file
        sam = Samfile(self.samfn)
        
        # run pileup
        for col in sam.pileup(self.chr, self.start, self.end):
            
            # fixed variables            
            chr = sam.getrname(col.tid)
            pos = col.pos + 1 # 1-based
            row = [chr, pos, col.n] 
            
            # computed variables
            data = build_coverage_stats(col)
            row.extend(data[v] for v in computed_variables) 
            yield row


cpdef build_minimal_coverage_stats(PileupProxy col):
    cdef int n
    cdef int ri
    cdef int reads_pp = 0
    cdef PileupRead read
    cdef AlignedRead aln

    n = col.n
    
    # access reads
    reads = col.pileups

    # iterate over reads in the column
    for ri in range(n):
        read = reads[ri]
        aln = read.alignment
        if aln.is_proper_pair:
            reads_pp += 1
            
    return reads_pp

    
class MinimalCoverageStatsTable(object):
    
    def __init__(self, samfn, chr=None, start=None, end=None):
        self.samfn = samfn
        self.chr = chr
        self.start = start
        self.end = end
        
    def __iter__(self):

        # define header
        header = ['chr', 'pos', 'reads', 'reads_pp']
        yield header
        
        # open sam file
        sam = Samfile(self.samfn)
        
        # run pileup
        for col in sam.pileup(self.chr, self.start, self.end):
            
            # fixed variables            
            chr = sam.getrname(col.tid)
            pos = col.pos + 1 # 1-based
            reads_pp = build_minimal_coverage_stats(col)
            row = [chr, pos, col.n, reads_pp] 
            yield row


class VariationStatsTable(object):
    
    def __init__(self, samfn, fafn, chr=None, start=None, end=None):
        self.samfn = samfn
        self.fafn = fafn
        self.chr = chr
        self.start = start
        self.end = end
        
    def __iter__(self):

        # define header
        fixed_variables = ['chr', 'pos', 'reads']
        computed_variables = [
                              'reads_fwd', 
                              'reads_rev',
                              'reads_pp',
                              'reads_pp_fwd',
                              'reads_pp_rev',
                              'matches',
                              'matches_fwd',
                              'matches_rev',
                              'matches_pp',
                              'matches_pp_fwd',
                              'matches_pp_rev',
                              'mismatches',
                              'mismatches_fwd',
                              'mismatches_rev',
                              'mismatches_pp',
                              'mismatches_pp_fwd',
                              'mismatches_pp_rev',
                              'deletions',
                              'deletions_fwd',
                              'deletions_rev',
                              'deletions_pp',
                              'deletions_pp_fwd',
                              'deletions_pp_rev',
                              'insertions',
                              'insertions_fwd',
                              'insertions_rev',
                              'insertions_pp',
                              'insertions_pp_fwd',
                              'insertions_pp_rev',
                              'A',
                              'A_fwd',
                              'A_rev',
                              'A_pp',
                              'A_pp_fwd',
                              'A_pp_rev',
                              'C',
                              'C_fwd',
                              'C_rev',
                              'C_pp',
                              'C_pp_fwd',
                              'C_pp_rev',
                              'T',
                              'T_fwd',
                              'T_rev',
                              'T_pp',
                              'T_pp_fwd',
                              'T_pp_rev',
                              'G',
                              'G_fwd',
                              'G_rev',
                              'G_pp',
                              'G_pp_fwd',
                              'G_pp_rev',
                              'N',
                              'N_fwd',
                              'N_rev',
                              'N_pp',
                              'N_pp_fwd',
                              'N_pp_rev',
                              ]
        header = fixed_variables + computed_variables
        yield header
        
        # open sam file
        sam = Samfile(self.samfn)
        fa = Fastafile(self.fafn)
        
        # run pileup
        for col in sam.pileup(self.chr, self.start, self.end):
            
            # fixed variables            
            chr = sam.getrname(col.tid)
            pos = col.pos 
            row = [chr, pos + 1, col.n] # 1-based
            
            # reference base
            ref = fa.fetch(chr, pos, pos+1).upper()
            
            # computed variables
            data = build_variation_stats(col, ref)
            row.extend(data[v] for v in computed_variables) 
            yield row


cdef dict_pp_strnd_counts(PpStrndCounts c, prefix):
    return {
            prefix: c.all,
            prefix+'_fwd': c.fwd,
            prefix+'_rev': c.rev,
            prefix+'_pp': c.pp,
            prefix+'_pp_fwd': c.pp_fwd,
            prefix+'_pp_rev': c.pp_rev,
            }


cdef dict_pp_strnd_counts_sum(PpStrndCounts a, PpStrndCounts b, PpStrndCounts c, prefix):
    return {
            prefix: a.all + b.all + c.all,
            prefix+'_fwd': a.fwd + b.fwd + c.fwd,
            prefix+'_rev': a.rev + b.rev + c.rev,
            prefix+'_pp': a.pp + b.pp + c.pp,
            prefix+'_pp_fwd': a.pp_fwd + b.pp_fwd + c.pp_fwd,
            prefix+'_pp_rev': a.pp_rev + b.pp_rev + c.pp_rev,
            }


cpdef build_variation_stats(PileupProxy col, ref):
    cdef int n = col.n
    cdef int ri
    cdef bint is_proper_pair
    cdef bint is_reverse
    cdef PileupRead read
    cdef AlignedRead aln
    cdef PpStrndCounts empty

    # create aggregators
    agg_reads = AggReads(n)
    agg_variation = AggVariation(n)
    
    # access reads
    reads = col.pileups

    # iterate over reads in the column
    for ri in range(n):
        read = reads[ri]
        aln = read.alignment
        
        # optimisation - access these now so done only once
        is_proper_pair = aln.is_proper_pair
        is_reverse = aln.is_reverse
        
        # pass reads to aggregators
        agg_reads.add(read, aln, is_proper_pair, is_reverse)
        agg_variation.add(read, aln, is_proper_pair, is_reverse)
            
    data = {
            'reads': agg_reads.all,
            'reads_fwd': agg_reads.fwd,
            'reads_rev': agg_reads.rev,
            'reads_pp': agg_reads.pp,
            'reads_pp_fwd': agg_reads.pp_fwd,
            'reads_pp_rev': agg_reads.pp_rev,
            }
    data.update(dict_pp_strnd_counts(agg_variation.A, 'A'))
    data.update(dict_pp_strnd_counts(agg_variation.C, 'C'))
    data.update(dict_pp_strnd_counts(agg_variation.T, 'T'))
    data.update(dict_pp_strnd_counts(agg_variation.G, 'G'))
    data.update(dict_pp_strnd_counts(agg_variation.N, 'N'))
    data.update(dict_pp_strnd_counts(agg_variation.deletions, 'deletions'))
    data.update(dict_pp_strnd_counts(agg_variation.insertions, 'insertions'))
    if ref == 'A':
        data.update(dict_pp_strnd_counts(agg_variation.A, 'matches'))
        data.update(dict_pp_strnd_counts_sum(agg_variation.C, agg_variation.T, agg_variation.G, 'mismatches'))
    elif ref == 'C':
        data.update(dict_pp_strnd_counts(agg_variation.C, 'matches'))
        data.update(dict_pp_strnd_counts_sum(agg_variation.A, agg_variation.T, agg_variation.G, 'mismatches'))
    elif ref == 'T':
        data.update(dict_pp_strnd_counts(agg_variation.T, 'matches'))
        data.update(dict_pp_strnd_counts_sum(agg_variation.A, agg_variation.C, agg_variation.G, 'mismatches'))
    elif ref == 'G':
        data.update(dict_pp_strnd_counts(agg_variation.G, 'matches'))
        data.update(dict_pp_strnd_counts_sum(agg_variation.A, agg_variation.C, agg_variation.T, 'mismatches'))
    else:
        empty = PpStrndCounts(all=0, fwd=0, rev=0, pp=0, pp_fwd=0, pp_rev=0)
        data.update(dict_pp_strnd_counts(empty, 'matches'))
        data.update(dict_pp_strnd_counts(empty, 'mismatches'))
    return data 
    

class TlenStatsTable(object):
    
    def __init__(self, samfn, chr=None, start=None, end=None):
        self.samfn = samfn
        self.chr = chr
        self.start = start
        self.end = end
        
    def __iter__(self):

        # define header
        fixed_variables = ['chr', 'pos', 'reads']
        computed_variables = [
                              'reads_fwd', 
                              'reads_rev',
                              'reads_pp',
                              'reads_pp_fwd',
                              'reads_pp_rev',
                              'rms_tlen',
                              'rms_tlen_fwd',
                              'rms_tlen_rev',
                              'rms_tlen_pp',
                              'rms_tlen_pp_fwd',
                              'rms_tlen_pp_rev',
                              'std_tlen',
                              'std_tlen_fwd',
                              'std_tlen_rev',
                              'std_tlen_pp',
                              'std_tlen_pp_fwd',
                              'std_tlen_pp_rev',
                              ]
        header = fixed_variables + computed_variables
        yield header
        
        # open sam file
        sam = Samfile(self.samfn)
        
        # run pileup
        for col in sam.pileup(self.chr, self.start, self.end):
            
            # fixed variables            
            chr = sam.getrname(col.tid)
            pos = col.pos + 1 # 1-based
            row = [chr, pos, col.n] 
            
            # computed variables
            data = build_tlen_stats(col)
            row.extend(data[v] for v in computed_variables) 
            yield row


cpdef build_tlen_stats(PileupProxy col):
    cdef int n = col.n
    cdef int ri
    cdef bint is_proper_pair
    cdef bint is_reverse
    cdef bint mate_is_unmapped
    cdef PileupRead read
    cdef AlignedRead aln

    # create aggregators
    agg_reads = AggReads(n)
    
    # access reads
    reads = col.pileups

    arr = np.empty((n,), dtype=[('tlen', np.int32), ('is_proper_pair', np.bool), ('is_reverse', np.bool), ('mate_is_unmapped', np.bool)]).view(np.recarray)
    
    # iterate over reads in the column
    for ri in range(n):
        read = reads[ri]
        aln = read.alignment
        
        # optimisation - access these now so done only once
        tlen = aln.tlen
        is_proper_pair = aln.is_proper_pair
        is_reverse = aln.is_reverse
        mate_is_unmapped = aln.mate_is_unmapped
        
        # store for computation
        arr[ri] = (tlen, is_proper_pair, is_reverse, mate_is_unmapped)
        
        # pass reads to other aggregators
        agg_reads.add(read, aln, is_proper_pair, is_reverse)
        
    sqtlen = arr.tlen**2
    # ignore values where tlen is so ridiculously large that won't fit in 4 bytes
    arr = arr[sqtlen >= 0]
    sqtlen = sqtlen[sqtlen >= 0]
    tlen = arr.tlen
    
    filter_mate_is_mapped = arr.mate_is_unmapped != True
    filter_mate_is_mapped_fwd = filter_mate_is_mapped & (arr.is_reverse != True)
    filter_mate_is_mapped_rev = filter_mate_is_mapped & arr.is_reverse
    filter_mate_is_mapped_pp = filter_mate_is_mapped & arr.is_proper_pair
    filter_mate_is_mapped_pp_rev = filter_mate_is_mapped_pp & arr.is_reverse
    filter_mate_is_mapped_pp_fwd = filter_mate_is_mapped_pp & (arr.is_reverse != True)
    
    rms_tlen = sqrt(np.mean(sqtlen[filter_mate_is_mapped]))
    rms_tlen_fwd = sqrt(np.mean(sqtlen[filter_mate_is_mapped_fwd]))
    rms_tlen_rev = sqrt(np.mean(sqtlen[filter_mate_is_mapped_rev]))
    rms_tlen_pp = sqrt(np.mean(sqtlen[filter_mate_is_mapped_pp]))
    rms_tlen_pp_fwd = sqrt(np.mean(sqtlen[filter_mate_is_mapped_pp_fwd]))
    rms_tlen_pp_rev = sqrt(np.mean(sqtlen[filter_mate_is_mapped_pp_rev]))

    std_tlen = np.std(tlen[filter_mate_is_mapped])
    std_tlen_fwd = np.std(tlen[filter_mate_is_mapped_fwd])
    std_tlen_rev = np.std(tlen[filter_mate_is_mapped_rev])
    std_tlen_pp = np.std(tlen[filter_mate_is_mapped_pp])
    std_tlen_pp_fwd = np.std(tlen[filter_mate_is_mapped_pp_fwd])
    std_tlen_pp_rev = np.std(tlen[filter_mate_is_mapped_pp_rev])
                
    # construct output row
    data = {
            'reads': agg_reads.all,
            'reads_fwd': agg_reads.fwd,
            'reads_rev': agg_reads.rev,
            'reads_pp': agg_reads.pp,
            'reads_pp_fwd': agg_reads.pp_fwd,
            'reads_pp_rev': agg_reads.pp_rev,
            'rms_tlen': rms_tlen,
            'rms_tlen_fwd': rms_tlen_fwd,
            'rms_tlen_rev': rms_tlen_rev,
            'rms_tlen_pp': rms_tlen_pp,
            'rms_tlen_pp_fwd': rms_tlen_pp_fwd,
            'rms_tlen_pp_rev': rms_tlen_pp_rev,
            'std_tlen': std_tlen,
            'std_tlen_fwd': std_tlen_fwd,
            'std_tlen_rev': std_tlen_rev,
            'std_tlen_pp': std_tlen_pp,
            'std_tlen_pp_fwd': std_tlen_pp_fwd,
            'std_tlen_pp_rev': std_tlen_pp_rev,
            }
    return data


class MapqStatsTable(object):
    
    def __init__(self, samfn, chr=None, start=None, end=None):
        self.samfn = samfn
        self.chr = chr
        self.start = start
        self.end = end
        
    def __iter__(self):

        # define header
        fixed_variables = ['chr', 'pos', 'reads']
        computed_variables = [
                              'reads_fwd', 
                              'reads_rev',
                              'reads_pp',
                              'reads_pp_fwd',
                              'reads_pp_rev',
                              'rms_mapq',
                              'rms_mapq_fwd',
                              'rms_mapq_rev',
                              'rms_mapq_pp',
                              'rms_mapq_pp_fwd',
                              'rms_mapq_pp_rev',
                              'median_mapq',
                              'median_mapq_fwd',
                              'median_mapq_rev',
                              'median_mapq_pp',
                              'median_mapq_pp_fwd',
                              'median_mapq_pp_rev',
                              'max_mapq',
                              'max_mapq_fwd',
                              'max_mapq_rev',
                              'max_mapq_pp',
                              'max_mapq_pp_fwd',
                              'max_mapq_pp_rev',
                              'reads_mapq0',
                              'reads_mapq0_fwd',
                              'reads_mapq0_rev',
                              'reads_mapq0_pp',
                              'reads_mapq0_pp_fwd',
                              'reads_mapq0_pp_rev',
                              ]
        header = fixed_variables + computed_variables
        yield header
        
        # open sam file
        sam = Samfile(self.samfn)
        
        # run pileup
        for col in sam.pileup(self.chr, self.start, self.end):
            
            # fixed variables            
            chr = sam.getrname(col.tid)
            pos = col.pos + 1 # 1-based
            row = [chr, pos, col.n] 
            
            # computed variables
            data = build_mapq_stats(col)
            row.extend(data[v] for v in computed_variables) 
            yield row


cdef int amax(a):
    cdef int n = len(a)
    if n > 0:
        return np.amax(a)
    else:
        return 0


cdef class AggReadsMapq0:
    cdef int n
    cdef int all
    cdef int fwd
    cdef int rev
    cdef int pp
    cdef int pp_fwd
    cdef int pp_rev
    
    def __cinit__(self, n):
        self.n = n
        self.all = 0
        self.fwd = 0
        self.rev = 0
        self.pp = 0
        self.pp_fwd = 0
        self.pp_rev = 0
    
    cdef add(self, PileupRead read, AlignedRead aln, bint is_proper_pair, bint is_reverse, int mapq):
        if mapq == 0:
            self.all += 1
            if is_reverse:
                self.rev += 1
                if is_proper_pair:
                    self.pp += 1
                    self.pp_rev += 1
            else:
                self.fwd += 1
                if is_proper_pair:
                    self.pp += 1
                    self.pp_fwd += 1
        

cpdef build_mapq_stats(PileupProxy col):
    cdef int n = col.n
    cdef int ri
    cdef int mapq
    cdef bint is_proper_pair
    cdef bint is_reverse
    cdef PileupRead read
    cdef AlignedRead aln

    # create aggregators
    agg_reads = AggReads(n)
    agg_reads_mapq0 = AggReadsMapq0(n)
    
    # access reads
    reads = col.pileups

    arr = np.empty((n,), 
                   dtype=[('mapq', np.uint32), 
                          ('is_proper_pair', np.bool), 
                          ('is_reverse', np.bool)])
    arr = arr.view(np.recarray)
    
    # iterate over reads in the column
    for ri in range(n):
        read = reads[ri]
        aln = read.alignment
        
        # optimisation - access these now so done only once
        mapq = aln.mapq
        is_proper_pair = aln.is_proper_pair
        is_reverse = aln.is_reverse
        
        # store for computation
        arr[ri] = (mapq, is_proper_pair, is_reverse)
        
        # pass reads to other aggregators
        agg_reads.add(read, aln, is_proper_pair, is_reverse)
        agg_reads_mapq0.add(read, aln, is_proper_pair, is_reverse, mapq)
        
    sqmapq = arr.mapq**2
    
    filter_fwd = arr.is_reverse != True
    filter_rev = arr.is_reverse
    filter_pp = arr.is_proper_pair
    filter_pp_rev = filter_pp & filter_rev
    filter_pp_fwd = filter_pp & filter_fwd

    rms_mapq = sqrt(np.mean(sqmapq))
    rms_mapq_fwd = sqrt(np.mean(sqmapq[filter_fwd]))
    rms_mapq_rev = sqrt(np.mean(sqmapq[filter_rev]))
    rms_mapq_pp = sqrt(np.mean(sqmapq[filter_pp]))
    rms_mapq_pp_fwd = sqrt(np.mean(sqmapq[filter_pp_fwd]))
    rms_mapq_pp_rev = sqrt(np.mean(sqmapq[filter_pp_rev]))

    max_mapq = amax(arr.mapq)
    max_mapq_fwd = amax(arr.mapq[filter_fwd])
    max_mapq_rev = amax(arr.mapq[filter_rev])
    max_mapq_pp = amax(arr.mapq[filter_pp])
    max_mapq_pp_fwd = amax(arr.mapq[filter_pp_fwd])
    max_mapq_pp_rev = amax(arr.mapq[filter_pp_rev])
    
    median_mapq = np.median(arr.mapq)
    median_mapq_fwd = np.median(arr.mapq[filter_fwd])
    median_mapq_rev = np.median(arr.mapq[filter_rev])
    median_mapq_pp = np.median(arr.mapq[filter_pp])
    median_mapq_pp_fwd = np.median(arr.mapq[filter_pp_fwd])
    median_mapq_pp_rev = np.median(arr.mapq[filter_pp_rev])
    
    # construct output row
    data = {
            'reads_fwd': agg_reads.fwd,
            'reads_rev': agg_reads.rev,
            'reads_pp': agg_reads.pp,
            'reads_pp_fwd': agg_reads.pp_fwd,
            'reads_pp_rev': agg_reads.pp_rev,
            'rms_mapq': rms_mapq,
            'rms_mapq_fwd': rms_mapq_fwd,
            'rms_mapq_rev': rms_mapq_rev,
            'rms_mapq_pp': rms_mapq_pp,
            'rms_mapq_pp_fwd': rms_mapq_pp_fwd,
            'rms_mapq_pp_rev': rms_mapq_pp_rev,
            'median_mapq': median_mapq,
            'median_mapq_fwd': median_mapq_fwd,
            'median_mapq_rev': median_mapq_rev,
            'median_mapq_pp': median_mapq_pp,
            'median_mapq_pp_fwd': median_mapq_pp_fwd,
            'median_mapq_pp_rev': median_mapq_pp_rev,
            'max_mapq': max_mapq,
            'max_mapq_fwd': max_mapq_fwd,
            'max_mapq_rev': max_mapq_rev,
            'max_mapq_pp': max_mapq_pp,
            'max_mapq_pp_fwd': max_mapq_pp_fwd,
            'max_mapq_pp_rev': max_mapq_pp_rev,
            'reads_mapq0': agg_reads_mapq0.all,
            'reads_mapq0_fwd': agg_reads_mapq0.fwd,
            'reads_mapq0_rev': agg_reads_mapq0.rev,
            'reads_mapq0_pp': agg_reads_mapq0.pp,
            'reads_mapq0_pp_fwd': agg_reads_mapq0.pp_fwd,
            'reads_mapq0_pp_rev': agg_reads_mapq0.pp_rev,
            }
    return data


class BaseqStatsTable(object):
    
    def __init__(self, samfn, fafn, chr=None, start=None, end=None):
        self.samfn = samfn
        self.fafn = fafn
        self.chr = chr
        self.start = start
        self.end = end
        
    def __iter__(self):

        # define header
        fixed_variables = ['chr', 'pos', 'reads']
        computed_variables = [
                              'reads_fwd', 
                              'reads_rev',
                              'reads_pp',
                              'reads_pp_fwd',
                              'reads_pp_rev',
                              'rms_baseq',
                              'rms_baseq_fwd',
                              'rms_baseq_rev',
                              'rms_baseq_pp',
                              'rms_baseq_pp_fwd',
                              'rms_baseq_pp_rev',
                              'median_baseq',
                              'median_baseq_fwd',
                              'median_baseq_rev',
                              'median_baseq_pp',
                              'median_baseq_pp_fwd',
                              'median_baseq_pp_rev',
                              'rms_baseq_matches',
                              'rms_baseq_matches_fwd',
                              'rms_baseq_matches_rev',
                              'rms_baseq_matches_pp',
                              'rms_baseq_matches_pp_fwd',
                              'rms_baseq_matches_pp_rev',
                              'rms_baseq_mismatches',
                              'rms_baseq_mismatches_fwd',
                              'rms_baseq_mismatches_rev',
                              'rms_baseq_mismatches_pp',
                              'rms_baseq_mismatches_pp_fwd',
                              'rms_baseq_mismatches_pp_rev',
                              ]
        header = fixed_variables + computed_variables
        yield header
        
        # open sam file
        sam = Samfile(self.samfn)
        fa = Fastafile(self.fafn)
        
        # run pileup
        for col in sam.pileup(self.chr, self.start, self.end):
            
            # fixed variables            
            chr = sam.getrname(col.tid)
            pos = col.pos 
            row = [chr, pos+1, col.n] # 1-based 

            # reference base
            ref = fa.fetch(chr, pos, pos+1).upper()
            
            # computed variables
            data = build_baseq_stats(col, ref)
            row.extend(data[v] for v in computed_variables) 
            yield row


cpdef build_baseq_stats(PileupProxy col, ref):
    cdef int n = col.n
    cdef int ri
    cdef int baseq
    cdef bint is_proper_pair
    cdef bint is_reverse
    cdef PileupRead read
    cdef AlignedRead aln

    # access reads
    reads = col.pileups

    # create aggregators
    agg_reads = AggReads(n)

    # setup array to store data in
    arr = np.empty((n,), 
                   dtype=[('baseq', np.uint32), 
                          ('is_proper_pair', np.bool), 
                          ('is_reverse', np.bool),
                          ('is_del', np.bool),
                          ('basecall', 'a1')])
    arr = arr.view(np.recarray)
    
    # iterate over reads in the column
    for ri in range(n):
        read = reads[ri]
        aln = read.alignment
        
        # optimisation - access these now so done only once
        qpos = read.qpos
        baseq = ord(aln.qual[qpos])-33
        is_proper_pair = aln.is_proper_pair
        is_reverse = aln.is_reverse
        is_del = read.is_del
        basecall = aln.seq[qpos]
        
        # pass to aggregators
        agg_reads.add(read, aln, is_proper_pair, is_reverse)

        # store for computation
        arr[ri] = (baseq, is_proper_pair, is_reverse, is_del, basecall)
        
    # ignore deletions
    arr = arr[arr.is_del != True]

    # square base qualities    
    sqbaseq = arr.baseq**2
    
    filter_fwd = arr.is_reverse != True
    filter_rev = arr.is_reverse
    filter_pp = arr.is_proper_pair
    filter_pp_rev = filter_pp & filter_rev
    filter_pp_fwd = filter_pp & filter_fwd
    
    rms_baseq = sqrt(np.mean(sqbaseq))
    rms_baseq_fwd = sqrt(np.mean(sqbaseq[filter_fwd]))
    rms_baseq_rev = sqrt(np.mean(sqbaseq[filter_rev]))
    rms_baseq_pp = sqrt(np.mean(sqbaseq[filter_pp]))
    rms_baseq_pp_fwd = sqrt(np.mean(sqbaseq[filter_pp_fwd]))
    rms_baseq_pp_rev = sqrt(np.mean(sqbaseq[filter_pp_rev]))

    median_baseq = np.median(arr.baseq)
    median_baseq_fwd = np.median(arr.baseq[filter_fwd])
    median_baseq_rev = np.median(arr.baseq[filter_rev])
    median_baseq_pp = np.median(arr.baseq[filter_pp])
    median_baseq_pp_fwd = np.median(arr.baseq[filter_pp_fwd])
    median_baseq_pp_rev = np.median(arr.baseq[filter_pp_rev])

    filter_matches = (arr.basecall == ref)
    rms_baseq_matches = sqrt(np.mean(sqbaseq[filter_matches]))
    rms_baseq_matches_fwd = sqrt(np.mean(sqbaseq[filter_fwd & filter_matches]))
    rms_baseq_matches_rev = sqrt(np.mean(sqbaseq[filter_rev & filter_matches]))
    rms_baseq_matches_pp = sqrt(np.mean(sqbaseq[filter_pp & filter_matches]))
    rms_baseq_matches_pp_fwd = sqrt(np.mean(sqbaseq[filter_pp_fwd & filter_matches]))
    rms_baseq_matches_pp_rev = sqrt(np.mean(sqbaseq[filter_pp_rev & filter_matches]))
    
    filter_mismatches = ((arr.basecall != ref) & (arr.basecall != 'N'))
    rms_baseq_mismatches = sqrt(np.mean(sqbaseq[filter_mismatches]))
    rms_baseq_mismatches_fwd = sqrt(np.mean(sqbaseq[filter_fwd & filter_mismatches]))
    rms_baseq_mismatches_rev = sqrt(np.mean(sqbaseq[filter_rev & filter_mismatches]))
    rms_baseq_mismatches_pp = sqrt(np.mean(sqbaseq[filter_pp & filter_mismatches]))
    rms_baseq_mismatches_pp_fwd = sqrt(np.mean(sqbaseq[filter_pp_fwd & filter_mismatches]))
    rms_baseq_mismatches_pp_rev = sqrt(np.mean(sqbaseq[filter_pp_rev & filter_mismatches]))
    
    # construct output row
    data = {
            'reads_fwd': agg_reads.fwd,
            'reads_rev': agg_reads.rev,
            'reads_pp': agg_reads.pp,
            'reads_pp_fwd': agg_reads.pp_fwd,
            'reads_pp_rev': agg_reads.pp_rev,
            'rms_baseq': rms_baseq,
            'rms_baseq_fwd': rms_baseq_fwd,
            'rms_baseq_rev': rms_baseq_rev,
            'rms_baseq_pp': rms_baseq_pp,
            'rms_baseq_pp_fwd': rms_baseq_pp_fwd,
            'rms_baseq_pp_rev': rms_baseq_pp_rev,
            'median_baseq': median_baseq,
            'median_baseq_fwd': median_baseq_fwd,
            'median_baseq_rev': median_baseq_rev,
            'median_baseq_pp': median_baseq_pp,
            'median_baseq_pp_fwd': median_baseq_pp_fwd,
            'median_baseq_pp_rev': median_baseq_pp_rev,
            'rms_baseq_matches': rms_baseq_matches,
            'rms_baseq_matches_fwd': rms_baseq_matches_fwd,
            'rms_baseq_matches_rev': rms_baseq_matches_rev,
            'rms_baseq_matches_pp': rms_baseq_matches_pp,
            'rms_baseq_matches_pp_fwd': rms_baseq_matches_pp_fwd,
            'rms_baseq_matches_pp_rev': rms_baseq_matches_pp_rev,
            'rms_baseq_mismatches': rms_baseq_mismatches,
            'rms_baseq_mismatches_fwd': rms_baseq_mismatches_fwd,
            'rms_baseq_mismatches_rev': rms_baseq_mismatches_rev,
            'rms_baseq_mismatches_pp': rms_baseq_mismatches_pp,
            'rms_baseq_mismatches_pp_fwd': rms_baseq_mismatches_pp_fwd,
            'rms_baseq_mismatches_pp_rev': rms_baseq_mismatches_pp_rev,
            }
    return data


class NormedCoverageStatsTable(object):
    
    def __init__(self, samfn, chr=None, start=None, end=None):
        self.samfn = samfn
        self.chr = chr
        self.start = start
        self.end = end
        
    def __iter__(self):
        cdef int i, n
        
        raw = MinimalCoverageStatsTable(self.samfn, self.chr, self.start, self.end)
        dtype = [('chr', 'a20'), ('pos', 'u4'), ('reads', 'u2'), ('reads_pp', 'u2')]
        it = (tuple(row) for row in itertools.islice(raw, 1, None))
        arr = np.fromiter(it, dtype=dtype).view(np.recarray)
        median_reads = np.median(arr.reads)
        median_reads_pp = np.median(arr.reads_pp)
        normed_coverage = (arr.reads * 1.) / median_reads
        normed_coverage_pp = (arr.reads_pp * 1.) / median_reads_pp
        
        header = ['chr', 'pos', 'reads', 'reads_pp', 'normed_coverage', 'normed_coverage_pp']
        yield header
        
        n = len(arr)
        
        for i in range(n):
            yield arr.chr[i], arr.pos[i], arr.reads[i], arr.reads_pp[i], normed_coverage[i], normed_coverage_pp[i]
            
