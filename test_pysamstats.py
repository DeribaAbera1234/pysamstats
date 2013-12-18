"""
Tests for the pysamstats module.

The strategy here is to compare the outputs of the functions under test with
unoptimised, pure-python reference implementations of the same functions, over
an example dataset. 

"""


from pysam import Samfile, Fastafile
from nose.tools import eq_, assert_almost_equal
import numpy as np
from math import sqrt
import pysamstats
from itertools import izip_longest


def _compare_iterators(expected, actual):
    for e, a in izip_longest(expected, actual, fillvalue=None):
        assert e is not None, ('expected value is None', e, a)
        assert a is not None, ('actual value is None', e, a)
        for k, v in e.items():
            try:
                if isinstance(v, float):
                    assert_almost_equal(v, a[k])
                else:
                    eq_(v, a[k])
            except:
                print k
                print e
                print a
                raise
        for k in a:  # check no unexpected fields
            try:
                assert k in e
            except:
                print k
                print e
                print a
                raise


def _test(impl, refimpl):
    kwargs = {'chrom': 'Pf3D7_01_v3',
              'start': 0,
              'end': 2000,
              'one_based': False}
    expected = refimpl(Samfile('fixture/test.bam'), **kwargs)
    actual = impl(Samfile('fixture/test.bam'), **kwargs)
    _compare_iterators(expected, actual)


def _test_withrefseq(impl, refimpl, bam_fn='fixture/test.bam', fasta_fn='fixture/ref.fa'):
    kwargs = {'chrom': 'Pf3D7_01_v3',
              'start': 0,
              'end': 2000,
              'one_based': False}
    expected = refimpl(Samfile(bam_fn), Fastafile(fasta_fn), **kwargs)
    actual = impl(Samfile(bam_fn), Fastafile(fasta_fn), **kwargs)
    _compare_iterators(expected, actual)


def normalise_coords(one_based, start, end):
    if one_based:
        start = start - 1 if start is not None else None
        end = end - 1 if end is not None else None
    return start, end


def fwd(reads):
    return [read for read in reads if not read.alignment.is_reverse]


def rev(reads):
    return [read for read in reads if read.alignment.is_reverse]


def pp(reads):
    return [read for read in reads if read.alignment.is_proper_pair]
        
        
def stat_coverage_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        yield {'chrom': chrom, 'pos': pos, 'reads_all': len(reads), 'reads_pp': len(pp(reads))}
        

def test_stat_coverage():
    _test(pysamstats.stat_coverage, stat_coverage_refimpl)


def stat_coverage_strand_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': len(reads), 'reads_fwd': len(fwd(reads)), 'reads_rev': len(rev(reads)),
               'reads_pp': len(pp(reads)), 'reads_pp_fwd': len(fwd(pp(reads))), 'reads_pp_rev': len(rev(pp(reads)))}
        

def test_stat_coverage_strand():
    _test(pysamstats.stat_coverage_strand, stat_coverage_strand_refimpl)


def stat_coverage_ext_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_mate_unmapped = [read for read in reads if read.alignment.mate_is_unmapped]
        reads_mate_mapped = [read for read in reads if not read.alignment.mate_is_unmapped]
        reads_mate_other_chr = [read for read in reads_mate_mapped
                                if col.tid != read.alignment.rnext]
        reads_mate_same_strand = [read for read in reads_mate_mapped
                                  if col.tid == read.alignment.rnext
                                  and (read.alignment.is_reverse == read.alignment.mate_is_reverse)]
        reads_faceaway = [read for read in reads_mate_mapped
                          if read.alignment.is_reverse != read.alignment.mate_is_reverse
                          and ((read.alignment.is_reverse and read.alignment.tlen > 0) # mapped to reverse strand but leftmost
                               or (not read.alignment.is_reverse and read.alignment.tlen < 0)) # mapped to fwd strand but rightmost
                          ]
        reads_softclipped = [read for read in reads
                             if any((op[0] == 4) for op in read.alignment.cigar)]
        reads_duplicate = [read for read in reads if read.alignment.is_duplicate]
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': len(reads), 
               'reads_pp': len(pp(reads)),
               'reads_mate_unmapped': len(reads_mate_unmapped),
               'reads_mate_other_chr': len(reads_mate_other_chr),
               'reads_mate_same_strand': len(reads_mate_same_strand),
               'reads_faceaway': len(reads_faceaway),
               'reads_softclipped': len(reads_softclipped),
               'reads_duplicate': len(reads_duplicate)}
        

def test_stat_coverage_ext():
    _test(pysamstats.stat_coverage_ext, stat_coverage_ext_refimpl)


def stat_coverage_ext_strand_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_pp = pp(reads)
        reads_mate_unmapped = [read for read in reads if read.alignment.mate_is_unmapped]
        reads_mate_mapped = [read for read in reads if not read.alignment.mate_is_unmapped]
        reads_mate_other_chr = [read for read in reads_mate_mapped
                                if col.tid != read.alignment.rnext]
        reads_mate_same_strand = [read for read in reads_mate_mapped
                                  if col.tid == read.alignment.rnext
                                  and (read.alignment.is_reverse == read.alignment.mate_is_reverse)]
        reads_faceaway = [read for read in reads_mate_mapped
                          if read.alignment.is_reverse != read.alignment.mate_is_reverse
                          and ((read.alignment.is_reverse and read.alignment.tlen > 0) # mapped to reverse strand but leftmost
                               or (not read.alignment.is_reverse and read.alignment.tlen < 0)) # mapped to fwd strand but rightmost
                          ]
        reads_softclipped = [read for read in reads
                             if any((op[0] == 4) for op in read.alignment.cigar)]
        reads_duplicate = [read for read in reads if read.alignment.is_duplicate]
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': len(reads), 
               'reads_fwd': len(fwd(reads)),
               'reads_rev': len(rev(reads)),
               'reads_pp': len(reads_pp),
               'reads_pp_fwd': len(fwd(reads_pp)),
               'reads_pp_rev': len(rev(reads_pp)),
               'reads_mate_unmapped': len(reads_mate_unmapped),
               'reads_mate_unmapped_fwd': len(fwd(reads_mate_unmapped)),
               'reads_mate_unmapped_rev': len(rev(reads_mate_unmapped)),
               'reads_mate_other_chr': len(reads_mate_other_chr),
               'reads_mate_other_chr_fwd': len(fwd(reads_mate_other_chr)),
               'reads_mate_other_chr_rev': len(rev(reads_mate_other_chr)),
               'reads_mate_same_strand': len(reads_mate_same_strand),
               'reads_mate_same_strand_fwd': len(fwd(reads_mate_same_strand)),
               'reads_mate_same_strand_rev': len(rev(reads_mate_same_strand)),
               'reads_faceaway': len(reads_faceaway),
               'reads_faceaway_fwd': len(fwd(reads_faceaway)),
               'reads_faceaway_rev': len(rev(reads_faceaway)),
               'reads_softclipped': len(reads_softclipped),
               'reads_softclipped_fwd': len(fwd(reads_softclipped)),
               'reads_softclipped_rev': len(rev(reads_softclipped)),
               'reads_duplicate': len(reads_duplicate),
               'reads_duplicate_fwd': len(fwd(reads_duplicate)),
               'reads_duplicate_rev': len(rev(reads_duplicate)),
               }
        

def test_stat_coverage_ext_strand():
    _test(pysamstats.stat_coverage_ext_strand, stat_coverage_ext_strand_refimpl)


def stat_variation_refimpl(samfile, fafile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_nodel = [read for read in reads if not read.is_del]
        reads_pp = pp(reads)
        reads_pp_nodel = [read for read in reads_pp if not read.is_del]
        ref = fafile.fetch(chrom, col.pos, col.pos+1).upper()
        matches = [read for read in reads_nodel
                      if read.alignment.seq[read.qpos] == ref]
        matches_pp = [read for read in reads_pp_nodel
                         if read.alignment.seq[read.qpos] == ref]
        mismatches = [read for read in reads_nodel
                         if read.alignment.seq[read.qpos] != ref]
        mismatches_pp = [read for read in reads_pp_nodel
                            if read.alignment.seq[read.qpos] != ref]
        deletions = [read for read in reads
                        if read.is_del]
        deletions_pp = [read for read in reads_pp
                           if read.is_del]
        insertions = [read for read in reads
                         if read.indel > 0]
        insertions_pp = [read for read in reads_pp
                            if read.indel > 0]
        A = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'A']
        A_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'A']
        C = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'C']
        C_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'C']
        T = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'T']
        T_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'T']
        G = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'G']
        G_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'G']
        N = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'N']
        N_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'N']
        yield {'chrom': chrom, 'pos': pos, 'ref': ref,
               'reads_all': len(reads), 
               'reads_pp': len(reads_pp),
               'matches': len(matches),
               'matches_pp': len(matches_pp),
               'mismatches': len(mismatches),
               'mismatches_pp': len(mismatches_pp),
               'deletions': len(deletions),
               'deletions_pp': len(deletions_pp),
               'insertions': len(insertions),
               'insertions_pp': len(insertions_pp),
               'A': len(A), 'A_pp': len(A_pp),
               'C': len(C), 'C_pp': len(C_pp),
               'T': len(T), 'T_pp': len(T_pp),
               'G': len(G), 'G_pp': len(G_pp),
               'N': len(N), 'N_pp': len(N_pp)}
        

def test_stat_variation():
    _test_withrefseq(pysamstats.stat_variation, stat_variation_refimpl)

        
def stat_variation_strand_refimpl(samfile, fafile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_nodel = [read for read in reads if not read.is_del]
        reads_pp = [read for read in reads if read.alignment.is_proper_pair]
        reads_pp_nodel = [read for read in reads if read.alignment.is_proper_pair and not read.is_del]
        ref = fafile.fetch(chrom, col.pos, col.pos+1).upper()
        matches = [read for read in reads_nodel
                      if read.alignment.seq[read.qpos] == ref]
        matches_pp = [read for read in reads_pp_nodel
                         if read.alignment.seq[read.qpos] == ref]
        mismatches = [read for read in reads_nodel
                         if read.alignment.seq[read.qpos] != ref]
        mismatches_pp = [read for read in reads_pp_nodel
                            if read.alignment.seq[read.qpos] != ref]
        deletions = [read for read in reads
                        if read.is_del]
        deletions_pp = [read for read in reads_pp
                           if read.is_del]
        insertions = [read for read in reads
                         if read.indel > 0]
        insertions_pp = [read for read in reads_pp
                            if read.indel > 0]
        A = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'A']
        A_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'A']
        C = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'C']
        C_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'C']
        T = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'T']
        T_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'T']
        G = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'G']
        G_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'G']
        N = [read for read in reads_nodel
                if read.alignment.seq[read.qpos] == 'N']
        N_pp = [read for read in reads_pp_nodel
                   if read.alignment.seq[read.qpos] == 'N']
        yield {'chrom': chrom, 'pos': pos, 'ref': ref,
               'reads_all': len(reads), 'reads_fwd': len(fwd(reads)), 'reads_rev': len(rev(reads)),
               'reads_pp': len(reads_pp), 'reads_pp_fwd': len(fwd(reads_pp)), 'reads_pp_rev': len(rev(reads_pp)),
               'matches': len(matches), 'matches_fwd': len(fwd(matches)), 'matches_rev': len(rev(matches)),
               'matches_pp': len(matches_pp), 'matches_pp_fwd': len(fwd(matches_pp)), 'matches_pp_rev': len(rev(matches_pp)),
               'mismatches': len(mismatches), 'mismatches_fwd': len(fwd(mismatches)), 'mismatches_rev': len(rev(mismatches)),
               'mismatches_pp': len(mismatches_pp), 'mismatches_pp_fwd': len(fwd(mismatches_pp)), 'mismatches_pp_rev': len(rev(mismatches_pp)),
               'deletions': len(deletions), 'deletions_fwd': len(fwd(deletions)), 'deletions_rev': len(rev(deletions)),
               'deletions_pp': len(deletions_pp), 'deletions_pp_fwd': len(fwd(deletions_pp)), 'deletions_pp_rev': len(rev(deletions_pp)),
               'insertions': len(insertions), 'insertions_fwd': len(fwd(insertions)), 'insertions_rev': len(rev(insertions)),
               'insertions_pp': len(insertions_pp), 'insertions_pp_fwd': len(fwd(insertions_pp)), 'insertions_pp_rev': len(rev(insertions_pp)),
               'A': len(A), 'A_fwd': len(fwd(A)), 'A_rev': len(rev(A)), 'A_pp':len(A_pp), 'A_pp_fwd': len(fwd(A_pp)), 'A_pp_rev': len(rev(A_pp)),
               'C': len(C), 'C_fwd': len(fwd(C)), 'C_rev': len(rev(C)), 'C_pp':len(C_pp), 'C_pp_fwd': len(fwd(C_pp)), 'C_pp_rev': len(rev(C_pp)),
               'T': len(T), 'T_fwd': len(fwd(T)), 'T_rev': len(rev(T)), 'T_pp':len(T_pp), 'T_pp_fwd': len(fwd(T_pp)), 'T_pp_rev': len(rev(T_pp)),
               'G': len(G), 'G_fwd': len(fwd(G)), 'G_rev': len(rev(G)), 'G_pp':len(G_pp), 'G_pp_fwd': len(fwd(G_pp)), 'G_pp_rev': len(rev(G_pp)),
               'N': len(N), 'N_fwd': len(fwd(N)), 'N_rev': len(rev(N)), 'N_pp':len(N_pp), 'N_pp_fwd': len(fwd(N_pp)), 'N_pp_rev': len(rev(N_pp))}


def test_stat_variation_strand():
    _test_withrefseq(pysamstats.stat_variation_strand, stat_variation_strand_refimpl)


def rms(a):
    if a:
        return int(round(sqrt(np.mean(np.power(a, 2)))))
    else:
        return 0


def mean(a):
    if a:
        return int(round(np.mean(a)))
    else:
        return 0


def std(a):
    if a:
        return int(round(np.std(a)))
    else:
        return 0
    
    
def vmax(a):
    if a:
        return max(a)
    else:
        return 0
    
    
def stat_tlen_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        # N.B., tlen only means something if mate is mapped to same chromosome
        reads_paired = [read for read in reads if not read.alignment.mate_is_unmapped and read.alignment.rnext == col.tid]
        tlen = [read.alignment.tlen for read in reads_paired]
        mean_tlen, rms_tlen, std_tlen = mean(tlen), rms(tlen), std(tlen)
        reads_pp = pp(reads)
        tlen_pp = [read.alignment.tlen for read in reads_pp]
        mean_tlen_pp, rms_tlen_pp, std_tlen_pp = mean(tlen_pp), rms(tlen_pp), std(tlen_pp)
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': col.n,
               'reads_paired': len(reads_paired),
               'reads_pp': len(reads_pp),
               'mean_tlen': mean_tlen,
               'mean_tlen_pp': mean_tlen_pp,
               'rms_tlen': rms_tlen,
               'rms_tlen_pp': rms_tlen_pp,
               'std_tlen': std_tlen,
               'std_tlen_pp': std_tlen_pp}
        

def test_stat_tlen():
    _test(pysamstats.stat_tlen, stat_tlen_refimpl)


def stat_tlen_strand_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups

        # all "paired" reads
        reads_paired = [read for read in reads if not read.alignment.mate_is_unmapped and read.alignment.rnext == col.tid]
        tlen = [read.alignment.tlen for read in reads_paired]
        mean_tlen, rms_tlen, std_tlen = mean(tlen), rms(tlen), std(tlen)
        reads_paired_fwd = fwd(reads_paired)
        tlen_fwd = [read.alignment.tlen for read in reads_paired_fwd]
        mean_tlen_fwd, rms_tlen_fwd, std_tlen_fwd = mean(tlen_fwd), rms(tlen_fwd), std(tlen_fwd)
        reads_paired_rev = rev(reads_paired)
        tlen_rev = [read.alignment.tlen for read in reads_paired_rev]
        mean_tlen_rev, rms_tlen_rev, std_tlen_rev = mean(tlen_rev), rms(tlen_rev), std(tlen_rev)
        
        # properly paired reads
        reads_pp = pp(reads)
        tlen_pp = [read.alignment.tlen for read in reads_pp]
        mean_tlen_pp, rms_tlen_pp, std_tlen_pp = mean(tlen_pp), rms(tlen_pp), std(tlen_pp)
        reads_pp_fwd = fwd(reads_pp)
        tlen_pp_fwd = [read.alignment.tlen for read in reads_pp_fwd]
        mean_tlen_pp_fwd, rms_tlen_pp_fwd, std_tlen_pp_fwd = mean(tlen_pp_fwd), rms(tlen_pp_fwd), std(tlen_pp_fwd)
        reads_pp_rev = rev(reads_pp)
        tlen_pp_rev = [read.alignment.tlen for read in reads_pp_rev]
        mean_tlen_pp_rev, rms_tlen_pp_rev, std_tlen_pp_rev = mean(tlen_pp_rev), rms(tlen_pp_rev), std(tlen_pp_rev)

        # yield record
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': col.n, 'reads_fwd': len(fwd(reads)), 'reads_rev': len(rev(reads)),
               'reads_paired': len(reads_paired), 'reads_paired_fwd': len(fwd(reads_paired)), 'reads_paired_rev': len(rev(reads_paired)),
               'reads_pp': len(reads_pp), 'reads_pp_fwd': len(fwd(reads_pp)), 'reads_pp_rev': len(rev(reads_pp)),
               'mean_tlen': mean_tlen, 'mean_tlen_fwd': mean_tlen_fwd, 'mean_tlen_rev': mean_tlen_rev,
               'mean_tlen_pp': mean_tlen_pp, 'mean_tlen_pp_fwd': mean_tlen_pp_fwd, 'mean_tlen_pp_rev': mean_tlen_pp_rev,
               'rms_tlen': rms_tlen, 'rms_tlen_fwd': rms_tlen_fwd, 'rms_tlen_rev': rms_tlen_rev,
               'rms_tlen_pp': rms_tlen_pp, 'rms_tlen_pp_fwd': rms_tlen_pp_fwd, 'rms_tlen_pp_rev': rms_tlen_pp_rev,
               'std_tlen': std_tlen, 'std_tlen_fwd': std_tlen_fwd, 'std_tlen_rev': std_tlen_rev,
               'std_tlen_pp': std_tlen_pp, 'std_tlen_pp_fwd': std_tlen_pp_fwd, 'std_tlen_pp_rev': std_tlen_pp_rev}
        

def test_stat_tlen_strand():
    _test(pysamstats.stat_tlen_strand, stat_tlen_strand_refimpl)


def mapq0(reads):
    return [read for read in reads if read.alignment.mapq == 0]


def mapq(reads):
    return [read.alignment.mapq for read in reads]        
    

def stat_mapq_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_pp = pp(reads)
        reads_mapq0 = mapq0(reads)
        reads_mapq0_pp = mapq0(reads_pp)
        mapq_all = mapq(reads)
        rms_mapq, max_mapq = rms(mapq_all), vmax(mapq_all)
        mapq_pp = mapq(reads_pp)
        rms_mapq_pp, max_mapq_pp = rms(mapq_pp), vmax(mapq_pp)
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': col.n, 
               'reads_pp': len(reads_pp),
               'reads_mapq0': len(reads_mapq0),
               'reads_mapq0_pp': len(reads_mapq0_pp),
               'rms_mapq': rms_mapq,
               'rms_mapq_pp': rms_mapq_pp,
               'max_mapq': max_mapq,
               'max_mapq_pp': max_mapq_pp,
               }
        

def test_stat_mapq():
    _test(pysamstats.stat_mapq, stat_mapq_refimpl)

        
def stat_mapq_strand_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_fwd = fwd(reads)
        reads_rev = rev(reads)
        reads_pp = pp(reads)
        reads_pp_fwd = fwd(reads_pp)
        reads_pp_rev = rev(reads_pp)
        reads_mapq0 = mapq0(reads)
        reads_mapq0_fwd = mapq0(reads_fwd)
        reads_mapq0_rev = mapq0(reads_rev)
        reads_mapq0_pp = mapq0(reads_pp)
        reads_mapq0_pp_fwd = mapq0(reads_pp_fwd)
        reads_mapq0_pp_rev = mapq0(reads_pp_rev)
        mapq_all = mapq(reads)
        rms_mapq, max_mapq = rms(mapq_all), vmax(mapq_all)
        mapq_fwd = mapq(reads_fwd)
        rms_mapq_fwd, max_mapq_fwd = rms(mapq_fwd), vmax(mapq_fwd)
        mapq_rev = mapq(reads_rev)
        rms_mapq_rev, max_mapq_rev = rms(mapq_rev), vmax(mapq_rev)
        mapq_pp = mapq(reads_pp)
        rms_mapq_pp, max_mapq_pp = rms(mapq_pp), vmax(mapq_pp)
        mapq_pp_fwd = mapq(reads_pp_fwd)
        rms_mapq_pp_fwd, max_mapq_pp_fwd = rms(mapq_pp_fwd), vmax(mapq_pp_fwd)
        mapq_pp_rev = mapq(reads_pp_rev)
        rms_mapq_pp_rev, max_mapq_pp_rev = rms(mapq_pp_rev), vmax(mapq_pp_rev)
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': col.n, 
               'reads_fwd': len(reads_fwd),
               'reads_rev': len(reads_rev),
               'reads_pp': len(reads_pp),
               'reads_pp_fwd': len(reads_pp_fwd),
               'reads_pp_rev': len(reads_pp_rev),
               'reads_mapq0': len(reads_mapq0),
               'reads_mapq0_fwd': len(reads_mapq0_fwd),
               'reads_mapq0_rev': len(reads_mapq0_rev),
               'reads_mapq0_pp': len(reads_mapq0_pp),
               'reads_mapq0_pp_fwd': len(reads_mapq0_pp_fwd),
               'reads_mapq0_pp_rev': len(reads_mapq0_pp_rev),
               'rms_mapq': rms_mapq,
               'rms_mapq_fwd': rms_mapq_fwd,
               'rms_mapq_rev': rms_mapq_rev,
               'rms_mapq_pp': rms_mapq_pp,
               'rms_mapq_pp_fwd': rms_mapq_pp_fwd,
               'rms_mapq_pp_rev': rms_mapq_pp_rev,
               'max_mapq': max_mapq,
               'max_mapq_fwd': max_mapq_fwd,
               'max_mapq_rev': max_mapq_rev,
               'max_mapq_pp': max_mapq_pp,
               'max_mapq_pp_fwd': max_mapq_pp_fwd,
               'max_mapq_pp_rev': max_mapq_pp_rev,
               }
        

def test_stat_mapq_strand():
    _test(pysamstats.stat_mapq_strand, stat_mapq_strand_refimpl)


def baseq(reads):
    return [ord(read.alignment.qual[read.qpos])-33 for read in reads]
        
        
def nodel(reads):
    return [read for read in reads if not read.is_del]
        
        
def stat_baseq_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        # N.B., make sure aligned base is not a deletion
        reads_nodel = nodel(reads)
        reads_pp = pp(reads)
        reads_pp_nodel = nodel(reads_pp)
        rms_baseq = rms(baseq(reads_nodel))
        rms_baseq_pp = rms(baseq(reads_pp_nodel))
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': len(reads),
               'reads_pp': len(reads_pp),
               'rms_baseq': rms_baseq,
               'rms_baseq_pp': rms_baseq_pp}
        

def test_stat_baseq():
    _test(pysamstats.stat_baseq, stat_baseq_refimpl)


def stat_baseq_strand_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_fwd = fwd(reads)
        reads_rev = rev(reads)
        reads_pp = pp(reads)
        reads_pp_fwd = fwd(reads_pp)
        reads_pp_rev = rev(reads_pp)
        reads_nodel = nodel(reads)
        reads_fwd_nodel = nodel(reads_fwd)
        reads_rev_nodel = nodel(reads_rev)
        reads_pp_nodel = nodel(reads_pp)
        reads_pp_fwd_nodel = nodel(reads_pp_fwd)
        reads_pp_rev_nodel = nodel(reads_pp_rev)
        rms_baseq = rms(baseq(reads_nodel))
        rms_baseq_fwd = rms(baseq(reads_fwd_nodel))
        rms_baseq_rev = rms(baseq(reads_rev_nodel))
        rms_baseq_pp = rms(baseq(reads_pp_nodel))
        rms_baseq_pp_fwd = rms(baseq(reads_pp_fwd_nodel))
        rms_baseq_pp_rev = rms(baseq(reads_pp_rev_nodel))
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': len(reads), 'reads_fwd': len(reads_fwd), 'reads_rev': len(reads_rev),
               'reads_pp': len(reads_pp), 'reads_pp_fwd': len(reads_pp_fwd), 'reads_pp_rev': len(reads_pp_rev),
               'rms_baseq': rms_baseq, 'rms_baseq_fwd': rms_baseq_fwd, 'rms_baseq_rev': rms_baseq_rev,
               'rms_baseq_pp': rms_baseq_pp, 'rms_baseq_pp_fwd': rms_baseq_pp_fwd, 'rms_baseq_pp_rev': rms_baseq_pp_rev,
               }

def test_stat_baseq_strand():
    _test(pysamstats.stat_baseq_strand, stat_baseq_strand_refimpl)


def stat_baseq_ext_refimpl(samfile, fafile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_nodel = [read for read in reads if not read.is_del]
        reads_pp = pp(reads)
        reads_pp_nodel = [read for read in reads_pp if not read.is_del]
        ref = fafile.fetch(chrom, col.pos, col.pos+1).upper()
        matches = [read for read in reads_nodel
                      if read.alignment.seq[read.qpos] == ref]
        matches_pp = [read for read in reads_pp_nodel
                         if read.alignment.seq[read.qpos] == ref]
        mismatches = [read for read in reads_nodel
                         if read.alignment.seq[read.qpos] != ref]
        mismatches_pp = [read for read in reads_pp_nodel
                            if read.alignment.seq[read.qpos] != ref]

        rms_baseq = rms(baseq(reads_nodel))
        rms_baseq_pp = rms(baseq(reads_pp_nodel))
        rms_baseq_matches = rms(baseq(matches))
        rms_baseq_matches_pp = rms(baseq(matches_pp))
        rms_baseq_mismatches = rms(baseq(mismatches))
        rms_baseq_mismatches_pp = rms(baseq(mismatches_pp))
        yield {'chrom': chrom, 'pos': pos, 'ref': ref,
               'reads_all': len(reads),
               'reads_pp': len(reads_pp),
               'matches': len(matches),
               'matches_pp': len(matches_pp),
               'mismatches': len(mismatches),
               'mismatches_pp': len(mismatches_pp),
               'rms_baseq': rms_baseq, 
               'rms_baseq_pp': rms_baseq_pp, 
               'rms_baseq_matches': rms_baseq_matches, 
               'rms_baseq_matches_pp': rms_baseq_matches_pp, 
               'rms_baseq_mismatches': rms_baseq_mismatches, 
               'rms_baseq_mismatches_pp': rms_baseq_mismatches_pp, 
               }
        

def test_stat_baseq_ext():
    _test_withrefseq(pysamstats.stat_baseq_ext, stat_baseq_ext_refimpl)


def stat_baseq_ext_strand_refimpl(samfile, fafile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_pp = pp(reads)
        reads_nodel = [read for read in reads if not read.is_del]
        reads_nodel_fwd = fwd(reads_nodel)
        reads_nodel_rev = rev(reads_nodel)
        reads_nodel_pp = pp(reads_nodel)
        reads_nodel_pp_fwd = fwd(reads_nodel_pp)
        reads_nodel_pp_rev = rev(reads_nodel_pp)
        reads_pp_nodel = [read for read in reads_pp if not read.is_del]
        ref = fafile.fetch(chrom, col.pos, col.pos+1).upper()
        matches = [read for read in reads_nodel
                      if read.alignment.seq[read.qpos] == ref]
        matches_fwd = fwd(matches)
        matches_rev = rev(matches)
        matches_pp = pp(matches)
        matches_pp_fwd = fwd(matches_pp)
        matches_pp_rev = rev(matches_pp)
        mismatches = [read for read in reads_nodel
                         if read.alignment.seq[read.qpos] != ref]
        mismatches_fwd = fwd(mismatches)
        mismatches_rev = rev(mismatches)
        mismatches_pp = pp(mismatches)
        mismatches_pp_fwd = fwd(mismatches_pp)
        mismatches_pp_rev = rev(mismatches_pp)

        rms_baseq = rms(baseq(reads_nodel))
        rms_baseq_fwd = rms(baseq(reads_nodel_fwd))
        rms_baseq_rev = rms(baseq(reads_nodel_rev))
        rms_baseq_pp = rms(baseq(reads_pp_nodel))
        rms_baseq_pp_fwd = rms(baseq(reads_nodel_pp_fwd))
        rms_baseq_pp_rev = rms(baseq(reads_nodel_pp_rev))
        rms_baseq_matches = rms(baseq(matches))
        rms_baseq_matches_fwd = rms(baseq(matches_fwd))
        rms_baseq_matches_rev = rms(baseq(matches_rev))
        rms_baseq_matches_pp = rms(baseq(matches_pp))
        rms_baseq_matches_pp_fwd = rms(baseq(matches_pp_fwd))
        rms_baseq_matches_pp_rev = rms(baseq(matches_pp_rev))
        rms_baseq_mismatches = rms(baseq(mismatches))
        rms_baseq_mismatches_fwd = rms(baseq(mismatches_fwd))
        rms_baseq_mismatches_rev = rms(baseq(mismatches_rev))
        rms_baseq_mismatches_pp = rms(baseq(mismatches_pp))
        rms_baseq_mismatches_pp_fwd = rms(baseq(mismatches_pp_fwd))
        rms_baseq_mismatches_pp_rev = rms(baseq(mismatches_pp_rev))
        yield {'chrom': chrom, 'pos': pos, 'ref': ref,
               'reads_all': len(reads), 'reads_fwd': len(fwd(reads)), 'reads_rev': len(rev(reads)),
               'reads_pp': len(reads_pp), 'reads_pp_fwd': len(fwd(reads_pp)), 'reads_pp_rev': len(rev(reads_pp)),
               'matches': len(matches),
               'matches_fwd': len(matches_fwd),
               'matches_rev': len(matches_rev),
               'matches_pp': len(matches_pp),
               'matches_pp_fwd': len(matches_pp_fwd),
               'matches_pp_rev': len(matches_pp_rev),
               'mismatches': len(mismatches),
               'mismatches_fwd': len(mismatches_fwd),
               'mismatches_rev': len(mismatches_rev),
               'mismatches_pp': len(mismatches_pp),
               'mismatches_pp_fwd': len(mismatches_pp_fwd),
               'mismatches_pp_rev': len(mismatches_pp_rev),
               'rms_baseq': rms_baseq, 
               'rms_baseq_fwd': rms_baseq_fwd, 
               'rms_baseq_rev': rms_baseq_rev, 
               'rms_baseq_pp': rms_baseq_pp, 
               'rms_baseq_pp_fwd': rms_baseq_pp_fwd, 
               'rms_baseq_pp_rev': rms_baseq_pp_rev, 
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
        

def test_stat_baseq_ext_strand():
    _test_withrefseq(pysamstats.stat_baseq_ext_strand, stat_baseq_ext_strand_refimpl)


from bisect import bisect_left


def stat_coverage_normed_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    
    # first need to load the coverage data into an array, to calculate the median
    it = (col.n for col in samfile.pileup(reference=chrom, start=start, end=end))
    a = np.fromiter(it, dtype='u4')
    dp_mean = np.mean(a)
    dp_median = np.median(a)
    dp_percentiles = [np.percentile(a, q) for q in range(101)]
    
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        dp = col.n
        dp_normed_median = dp * 1. / dp_median
        dp_normed_mean = dp * 1. / dp_mean
        dp_percentile = bisect_left(dp_percentiles, dp)
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': col.n, 
               'dp_normed_median': dp_normed_median,
               'dp_normed_mean': dp_normed_mean,
               'dp_percentile': dp_percentile}
        

def test_stat_coverage_normed():
    _test(pysamstats.stat_coverage_normed, stat_coverage_normed_refimpl)


from collections import Counter


def stat_coverage_gc_refimpl(samfile, fafile, 
                             chrom=None, start=None, end=None, one_based=False,
                             window_size=300, window_offset=150):
    start, end = normalise_coords(one_based, start, end)
    
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        
        if col.pos <= window_offset:
            continue # until we get a bit further into the chromosome
        
        ref_window_start = col.pos - window_offset
        ref_window_end = ref_window_start + window_size
        ref_window = fafile.fetch(chrom, ref_window_start, ref_window_end).lower()
        
        if len(ref_window) == 0:
            break # because we've hit the end of the chromosome
        
        base_counter = Counter(ref_window)
        gc_count = base_counter['g'] + base_counter['c']
        gc_percent = int(round(gc_count * 100. / window_size))
        yield {'chrom': chrom, 'pos': pos, 
               'reads_all': len(reads), 
               'reads_pp': len(pp(reads)),
               'gc': gc_percent}
        

def test_stat_coverage_gc():
    _test_withrefseq(pysamstats.stat_coverage_gc, stat_coverage_gc_refimpl)


def test_stat_coverage_gc_uppercase_fasta():
    _test_withrefseq(pysamstats.stat_coverage_gc, stat_coverage_gc_refimpl, fasta_fn='fixture/ref.upper.fa')


def stat_coverage_normed_gc_refimpl(samfile, fafile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    
    # first need to load the coverage data into an array, to calculate the median
    recs = stat_coverage_gc_refimpl(samfile, fafile, chrom=chrom, start=start, end=end, one_based=one_based)
    it = ((rec['reads_all'], rec['gc']) for rec in recs)
    a = np.fromiter(it, dtype=[('dp', 'u4'), ('gc', 'u1')]).view(np.recarray)
    dp_mean = np.mean(a.dp)
    dp_median = np.median(a.dp)
    dp_percentiles = [np.percentile(a.dp, q) for q in range(101)]    
    dp_mean_bygc = dict()
    dp_median_bygc = dict()
    dp_percentiles_bygc = dict()
    for gc in range(101):
        flt = a.gc == gc
        if np.count_nonzero(flt) > 0:
            b = a[flt].dp
            dp_mean_bygc[gc] = np.mean(b)
            dp_median_bygc[gc] = np.median(b)
            dp_percentiles_bygc[gc] = [np.percentile(b, q) for q in range(101)]
    
    # second pass
    recs = stat_coverage_gc_refimpl(samfile, fafile, chrom=chrom, start=start, end=end, one_based=one_based)
    for rec in recs:
        dp = rec['reads_all']
        gc = rec['gc']
        dp_normed_median = dp * 1. / dp_median
        dp_normed_mean = dp * 1. / dp_mean
        dp_percentile = bisect_left(dp_percentiles, dp)
        dp_normed_median_bygc = dp * 1. / dp_median_bygc[gc]
        dp_normed_mean_bygc = dp * 1. / dp_mean_bygc[gc]
        dp_percentile_bygc = bisect_left(dp_percentiles_bygc[gc], dp)
        rec['dp_normed_median'] = dp_normed_median
        rec['dp_normed_mean'] = dp_normed_mean
        rec['dp_percentile'] = dp_percentile
        rec['dp_normed_median_gc'] = dp_normed_median_bygc
        rec['dp_normed_mean_gc'] = dp_normed_mean_bygc
        rec['dp_percentile_gc'] = dp_percentile_bygc
        del rec['reads_pp']
        yield rec
        

def test_stat_coverage_normed_gc():
    _test_withrefseq(pysamstats.stat_coverage_normed_gc, stat_coverage_normed_gc_refimpl)


from itertools import chain


def stat_coverage_binned_refimpl(samfile, fastafile, 
                                 chrom=None, start=None, end=None, one_based=False,
                                 window_size=300, window_offset=150):
    if chrom is None:
        it = chain(*[_iter_coverage_binned(samfile, fastafile, chrom, None, None, one_based, window_size, window_offset) 
                     for chrom in samfile.references])
    else:
        it = _iter_coverage_binned(samfile, fastafile, chrom, start, end, one_based, window_size, window_offset)   
    return it   
        
        
def _iter_coverage_binned(samfile, fastafile, chrom, start, end, one_based, window_size, window_offset):
    assert chrom is not None
    start, end = normalise_coords(one_based, start, end)
    if start is None:
        start = 0
    # setup first bin
    bin_start = start
    bin_end = bin_start + window_size
    reads_all = reads_pp = 0

    # iterate over reads
    for aln in samfile.fetch(chrom, start, end):
        while aln.pos > bin_end:  # end of bin
            nc = Counter(fastafile.fetch(chrom, bin_start, bin_end).lower())
            gc_percent = int(round((nc['g'] + nc['c']) * 100. / window_size))
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos, 
                   'gc': gc_percent, 'reads_all': reads_all, 'reads_pp': reads_pp}
            yield rec
            reads_all = reads_pp = 0
            bin_start = bin_end
            bin_end = bin_start + window_size
        if not aln.is_unmapped:
            reads_all += 1
            if aln.is_proper_pair:
                reads_pp += 1

    # deal with last non-empty bin
    nc = Counter(fastafile.fetch(chrom, bin_start, bin_end).lower())
    gc_percent = int(round((nc['g'] + nc['c']) * 100. / window_size))
    pos = bin_start + window_offset
    if one_based:
        pos += 1
    rec = {'chrom': chrom, 'pos': pos,
           'gc': gc_percent, 'reads_all': reads_all, 'reads_pp': reads_pp}
    yield rec

    # deal with empty bins up to explicit end
    if end is not None:
        while bin_end < end:
            reads_all = reads_pp = 0
            bin_start = bin_end
            bin_end = bin_start + window_size
            nc = Counter(fastafile.fetch(chrom, bin_start, bin_end).lower())
            gc_percent = int(round((nc['g'] + nc['c']) * 100. / window_size))
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos,
                   'gc': gc_percent, 'reads_all': reads_all, 'reads_pp': reads_pp}
            yield rec


def test_stat_coverage_binned():
    _test_withrefseq(pysamstats.stat_coverage_binned, stat_coverage_binned_refimpl)


def test_stat_coverage_binned_uppercase_fasta():
    _test_withrefseq(pysamstats.stat_coverage_binned, stat_coverage_binned_refimpl, fasta_fn='fixture/ref.upper.fa')


def stat_coverage_ext_binned_refimpl(samfile, fastafile, 
                                 chrom=None, start=None, end=None, one_based=False,
                                 window_size=300, window_offset=150):
    if chrom is None:
        it = chain(*[_iter_coverage_ext_binned(samfile, fastafile, chrom, None, None, one_based, window_size, window_offset) 
                     for chrom in samfile.references])
    else:
        it = _iter_coverage_ext_binned(samfile, fastafile, chrom, start, end, one_based, window_size, window_offset)   
    return it   
        
        
def _iter_coverage_ext_binned(samfile, fastafile, chrom, start, end, one_based, window_size, window_offset):
    assert chrom is not None
    start, end = normalise_coords(one_based, start, end)
    if start is None:
        start = 0
    # setup first bin
    bin_start = start
    bin_end = bin_start + window_size
    reads_all = reads_pp = reads_mate_unmapped = reads_mate_other_chr = reads_mate_same_strand = reads_faceaway = reads_softclipped = reads_duplicate = 0

    # iterate over reads
    for aln in samfile.fetch(chrom, start, end):
        while aln.pos > bin_end:  # end of bin
            nc = Counter(fastafile.fetch(chrom, bin_start, bin_end).lower())
            gc_percent = int(round((nc['g'] + nc['c']) * 100. / window_size))
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos, 
                   'gc': gc_percent, 
                   'reads_all': reads_all, 
                   'reads_pp': reads_pp,
                   'reads_mate_unmapped': reads_mate_unmapped,
                   'reads_mate_other_chr': reads_mate_other_chr,
                   'reads_mate_same_strand': reads_mate_same_strand,
                   'reads_faceaway': reads_faceaway,
                   'reads_softclipped': reads_softclipped,
                   'reads_duplicate': reads_duplicate}
            yield rec
            reads_all = reads_pp = reads_mate_unmapped = reads_mate_other_chr = reads_mate_same_strand = reads_faceaway = reads_softclipped = reads_duplicate = 0
            bin_start = bin_end
            bin_end = bin_start + window_size
#        print aln, aln.cigar, repr(aln.cigarstring)
        if not aln.is_unmapped:
            reads_all += 1
            if aln.is_proper_pair:
                reads_pp += 1
            if aln.is_duplicate:
                reads_duplicate += 1
            if aln.cigar is not None and any((op[0] == 4) for op in aln.cigar):
                reads_softclipped += 1
            # should be mutually exclusive
            if aln.mate_is_unmapped:
                reads_mate_unmapped += 1
            elif aln.tid != aln.rnext:
                reads_mate_other_chr += 1
            elif aln.is_reverse == aln.mate_is_reverse:
                reads_mate_same_strand += 1
            elif ((aln.is_reverse and aln.tlen > 0) # mapped to reverse strand but leftmost
                  or (not aln.is_reverse and aln.tlen < 0)): # mapped to fwd strand but rightmost
                reads_faceaway += 1

    # deal with last non-empty bin
    nc = Counter(fastafile.fetch(chrom, bin_start, bin_end).lower())
    gc_percent = int(round((nc['g'] + nc['c']) * 100. / window_size))
    pos = bin_start + window_offset
    if one_based:
        pos += 1
    rec = {'chrom': chrom, 'pos': pos,
           'gc': gc_percent,
           'reads_all': reads_all,
           'reads_pp': reads_pp,
           'reads_mate_unmapped': reads_mate_unmapped,
           'reads_mate_other_chr': reads_mate_other_chr,
           'reads_mate_same_strand': reads_mate_same_strand,
           'reads_faceaway': reads_faceaway,
           'reads_softclipped': reads_softclipped,
           'reads_duplicate': reads_duplicate}
    yield rec

    # deal with empty bins up to explicit end
    if end is not None:
        while bin_end < end:
            reads_all = reads_pp = reads_mate_unmapped = reads_mate_other_chr = reads_mate_same_strand = reads_faceaway = reads_softclipped = reads_duplicate = 0
            bin_start = bin_end
            bin_end = bin_start + window_size
            nc = Counter(fastafile.fetch(chrom, bin_start, bin_end).lower())
            gc_percent = int(round((nc['g'] + nc['c']) * 100. / window_size))
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos,
                   'gc': gc_percent,
                   'reads_all': reads_all,
                   'reads_pp': reads_pp,
                   'reads_mate_unmapped': reads_mate_unmapped,
                   'reads_mate_other_chr': reads_mate_other_chr,
                   'reads_mate_same_strand': reads_mate_same_strand,
                   'reads_faceaway': reads_faceaway,
                   'reads_softclipped': reads_softclipped,
                   'reads_duplicate': reads_duplicate}
            yield rec
            
        
def test_stat_coverage_ext_binned():
    _test_withrefseq(pysamstats.stat_coverage_ext_binned, stat_coverage_ext_binned_refimpl)


def test_stat_coverage_ext_binned_uppercase_fasta():
    _test_withrefseq(pysamstats.stat_coverage_ext_binned, stat_coverage_ext_binned_refimpl, fasta_fn='fixture/ref.upper.fa')


def stat_mapq_binned_refimpl(samfile,  
                             chrom=None, start=None, end=None, one_based=False,
                             window_size=300, window_offset=150):
    if chrom is None:
        it = chain(*[_iter_mapq_binned(samfile, chrom, None, None, one_based, window_size, window_offset) 
                     for chrom in samfile.references])
    else:
        it = _iter_mapq_binned(samfile, chrom, start, end, one_based, window_size, window_offset)   
    return it   
        
        
def _iter_mapq_binned(samfile, chrom, start, end, one_based, window_size, window_offset):
    assert chrom is not None
    start, end = normalise_coords(one_based, start, end)
    if start is None:
        start = 0
    # setup first bin
    bin_start = start
    bin_end = bin_start + window_size
    reads_all = reads_mapq0 = mapq_square_sum = 0

    # iterate over reads
    for aln in samfile.fetch(chrom, start, end):
        while aln.pos > bin_end:  # end of bin
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos, 
                   'reads_all': reads_all, 
                   'reads_mapq0': reads_mapq0,
                   'rms_mapq': rootmean(mapq_square_sum, reads_all)}
            yield rec
            reads_all = reads_mapq0 = mapq_square_sum = 0
            bin_start = bin_end
            bin_end = bin_start + window_size
        if not aln.is_unmapped:
            reads_all += 1
            mapq_square_sum += aln.mapq**2
            if aln.mapq == 0:
                reads_mapq0 += 1

    # deal with last non-empty bin
    pos = bin_start + window_offset
    if one_based:
        pos += 1
    rec = {'chrom': chrom, 'pos': pos,
           'reads_all': reads_all,
           'reads_mapq0': reads_mapq0,
           'rms_mapq': rootmean(mapq_square_sum, reads_all)}
    yield rec

    # deal with empty bins up to explicit end
    if end is not None:
        while bin_end < end:
            reads_all = reads_mapq0 = mapq_square_sum = 0
            bin_start = bin_end
            bin_end = bin_start + window_size
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos,
                   'reads_all': reads_all,
                   'reads_mapq0': reads_mapq0,
                   'rms_mapq': rootmean(mapq_square_sum, reads_all)}
            yield rec

        
def test_stat_mapq_binned():
    _test(pysamstats.stat_mapq_binned, stat_mapq_binned_refimpl)


def stat_alignment_binned_refimpl(samfile,  
                             chrom=None, start=None, end=None, one_based=False,
                             window_size=300, window_offset=150):
    if chrom is None:
        it = chain(*[_iter_alignment_binned(samfile, chrom, None, None, one_based, window_size, window_offset) 
                     for chrom in samfile.references])
    else:
        it = _iter_alignment_binned(samfile, chrom, start, end, one_based, window_size, window_offset)   
    return it   
        
        
CIGAR = 'MIDNSHP=X'
        
        
def _iter_alignment_binned(samfile, chrom, start, end, one_based, window_size, window_offset):
    assert chrom is not None
    start, end = normalise_coords(one_based, start, end)
    if start is None:
        start = 0
    # setup first bin
    bin_start = start
    bin_end = bin_start + window_size
    c = Counter()
    reads_all = 0

    # iterate over reads
    for aln in samfile.fetch(chrom, start, end):
        while aln.pos > bin_end:  # end of bin
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos, 'reads_all': reads_all}
            for i in range(len(CIGAR)):
                rec[CIGAR[i]] = c[i]
#            rec['NM'] = c['NM']
            rec['bases_all'] = c[0] + c[1] + c[4] + c[7] + c[8]
            yield rec
            c = Counter()
            reads_all = 0
            bin_start = bin_end
            bin_end = bin_start + window_size
#        print aln.cigar
        if not aln.is_unmapped:
            reads_all += 1
            if aln.cigar is not None:
                for op, l in aln.cigar:
                    c[op] += l
            # add edit distance
    #        tags = dict(aln.tags)
    #        if 'NM' in tags:
    #            c['NM'] += tags['NM']

    # deal with last non-empty bin
    pos = bin_start + window_offset
    if one_based:
        pos += 1
    rec = {'chrom': chrom, 'pos': pos, 'reads_all': reads_all}
    for i in range(len(CIGAR)):
        rec[CIGAR[i]] = c[i]
#            rec['NM'] = c['NM']
    rec['bases_all'] = c[0] + c[1] + c[4] + c[7] + c[8]
    yield rec

    # deal with empty bins up to explicit end
    if end is not None:
        while bin_end < end:
            c = Counter()
            reads_all = 0
            bin_start = bin_end
            bin_end = bin_start + window_size
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos, 'reads_all': reads_all}
            for i in range(len(CIGAR)):
                rec[CIGAR[i]] = c[i]
        #            rec['NM'] = c['NM']
            rec['bases_all'] = c[0] + c[1] + c[4] + c[7] + c[8]
            yield rec

        
def test_stat_alignment_binned():
    _test(pysamstats.stat_alignment_binned, stat_alignment_binned_refimpl)


def stat_tlen_binned_refimpl(samfile,
                             chrom=None, start=None, end=None, one_based=False,
                             window_size=300, window_offset=150):
    if chrom is None:
        it = chain(*[_iter_tlen_binned(samfile, chrom, None, None, one_based, window_size, window_offset)
                     for chrom in samfile.references])
    else:
        it = _iter_tlen_binned(samfile, chrom, start, end, one_based, window_size, window_offset)
    return it


def _iter_tlen_binned(samfile, chrom, start, end, one_based, window_size, window_offset):
    assert chrom is not None
    start, end = normalise_coords(one_based, start, end)
    if start is None:
        start = 0
    # setup first bin
    bin_start = start
    bin_end = bin_start + window_size
    reads_all = reads_pp = 0
    tlens = []
    tlens_pp = []

    # iterate over reads
    for aln in samfile.fetch(chrom, start, end):
        while aln.pos > bin_end:  # end of bin
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos,
                   'reads_all': reads_all,
                   'reads_pp': reads_pp,
                   'mean_tlen': mean(tlens),
                   'rms_tlen': rms(tlens),
                   'mean_tlen_pp': mean(tlens_pp),
                   'rms_tlen_pp': rms(tlens_pp),
                   }
            yield rec
            reads_all = reads_pp = 0
            tlens = []
            tlens_pp = []
            bin_start = bin_end
            bin_end = bin_start + window_size
        if not aln.is_unmapped:
            reads_all += 1
            tlens.append(aln.tlen)
            if aln.is_proper_pair:
                reads_pp += 1
                tlens_pp.append(aln.tlen)

    # deal with last non-empty bin
    pos = bin_start + window_offset
    if one_based:
        pos += 1
    rec = {'chrom': chrom, 'pos': pos,
           'reads_all': reads_all,
           'reads_pp': reads_pp,
           'mean_tlen': mean(tlens),
           'rms_tlen': rms(tlens),
           'mean_tlen_pp': mean(tlens_pp),
           'rms_tlen_pp': rms(tlens_pp),
           }
    yield rec

    # deal with empty bins up to explicit end
    if end is not None:
        while bin_end < end:
            reads_all = reads_pp = 0
            tlens = []
            tlens_pp = []
            bin_start = bin_end
            bin_end = bin_start + window_size
            pos = bin_start + window_offset
            if one_based:
                pos += 1
            rec = {'chrom': chrom, 'pos': pos,
                   'reads_all': reads_all,
                   'reads_pp': reads_pp,
                   'mean_tlen': mean(tlens),
                   'rms_tlen': rms(tlens),
                   'mean_tlen_pp': mean(tlens_pp),
                   'rms_tlen_pp': rms(tlens_pp),
                   }
            yield rec


def test_stat_tlen_binned():
    _test(pysamstats.stat_tlen_binned, stat_tlen_binned_refimpl)


def rootmean(sqsum, count):
    if count > 0:
        return int(round(sqrt(sqsum * 1. / count)))
    else:
        return 0


def _mean(sum, count):
    if count > 0:
        return int(round(sum * 1. / count))
    else:
        return 0


pileup_functions = [
    (pysamstats.load_coverage, 0),
    (pysamstats.load_coverage_strand, 0),
    (pysamstats.load_coverage_ext, 0),
    (pysamstats.load_coverage_ext_strand, 0),
    (pysamstats.load_variation, 1),
    (pysamstats.load_variation_strand, 1),
    (pysamstats.load_tlen, 0),
    (pysamstats.load_tlen_strand, 0),
    (pysamstats.load_mapq, 0),
    (pysamstats.load_mapq_strand, 0),
    (pysamstats.load_baseq, 0),
    (pysamstats.load_baseq_strand, 0),
    (pysamstats.load_baseq_ext, 1),
    (pysamstats.load_baseq_ext_strand, 1),
    (pysamstats.load_coverage_gc, 1),
    (pysamstats.load_coverage_normed, 0),
    (pysamstats.load_coverage_normed_gc, 1),
]


def test_pileup_truncate():
    kwargs_notrunc = {'chrom': 'Pf3D7_01_v3',
                      'start': 2000,
                      'end': 2100,
                      'one_based': False,
                      'truncate': False}
    kwargs_trunc = {'chrom': 'Pf3D7_01_v3',
                    'start': 2000,
                    'end': 2100,
                    'one_based': False,
                    'truncate': True}
    for f, needs_ref in pileup_functions:
        print f.__name__
        # test no truncate
        if needs_ref:
            a = f(Samfile('fixture/test.bam'), Fastafile('fixture/ref.fa'), **kwargs_notrunc)
        else:
            a = f(Samfile('fixture/test.bam'), **kwargs_notrunc)
        eq_(1925, a['pos'][0])
        eq_(2174, a['pos'][-1])
        # test truncate
        if needs_ref:
            a = f(Samfile('fixture/test.bam'), Fastafile('fixture/ref.fa'), **kwargs_trunc)
        else:
            a = f(Samfile('fixture/test.bam'), **kwargs_trunc)
        eq_(2000, a['pos'][0])
        eq_(2099, a['pos'][-1])


def test_pileup_pad():
    kwargs_nopad = {'chrom': 'Pf3D7_01_v3',
                    'start': 0,
                    'end': 20000,
                    'one_based': False,
                    'pad': False}
    kwargs_pad = {'chrom': 'Pf3D7_01_v3',
                  'start': 0,
                  'end': 20000,
                  'one_based': False,
                  'pad': True}
    for f, needs_ref in pileup_functions:
        print f.__name__
        # test no pad
        if needs_ref:
            a = f(Samfile('fixture/test.bam'), Fastafile('fixture/ref.fa'), **kwargs_nopad)
        else:
            a = f(Samfile('fixture/test.bam'), **kwargs_nopad)
        eq_(924, a['pos'][0])
        eq_(10074, a['pos'][-1])
        # test pad
        if needs_ref:
            a = f(Samfile('fixture/test.bam'), Fastafile('fixture/ref.fa'), **kwargs_pad)
        else:
            a = f(Samfile('fixture/test.bam'), **kwargs_pad)
        eq_(0, a['pos'][0])
        eq_(19999, a['pos'][-1])
