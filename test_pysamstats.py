"""
Tests for the pysamstats module.

The strategy here is to compare the outputs of the functions under test with
unoptimised, pure-python reference implementations of the same functions, over
an example dataset. 

"""


# TODO simplify reference implementations by building lists and using len()

from pysam import Samfile, Fastafile
from nose.tools import eq_, assert_almost_equal
import numpy as np
from math import sqrt
import pysamstats


def _test(impl, refimpl):
    kwargs = {'chrom': 'Pf3D7_01_v3',
              'start': 0,
              'end': 10000,
              'one_based': False}
    expected = refimpl(Samfile('fixture/test.bam'), **kwargs)
    actual = impl(Samfile('fixture/test.bam'), **kwargs)
    for e, a in zip(expected, actual):
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


def _test_withrefseq(impl, refimpl):
    kwargs = {'chrom': 'Pf3D7_01_v3',
              'start': 0,
              'end': 10000,
              'one_based': False}
    expected = refimpl(Samfile('fixture/test.bam'), Fastafile('fixture/ref.fa'), **kwargs)
    actual = impl(Samfile('fixture/test.bam'), Fastafile('fixture/ref.fa'), **kwargs)
    for e, a in zip(expected, actual):
        for k, v in e.items():
            try:
                eq_(v, a[k])
            except:
                print k
                print e, a
                raise


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
        yield {'chr': chrom, 'pos': pos, 'reads_all': len(reads), 'reads_pp': len(pp(reads))}
        

def test_stat_coverage():
    _test(pysamstats.stat_coverage, stat_coverage_refimpl)


def stat_coverage_strand_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        yield {'chr': chrom, 'pos': pos, 
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
        yield {'chr': chrom, 'pos': pos, 
               'reads_all': len(reads), 
               'reads_pp': len(pp(reads)),
               'reads_mate_unmapped': len(reads_mate_unmapped),
               'reads_mate_other_chr': len(reads_mate_other_chr),
               'reads_mate_same_strand': len(reads_mate_same_strand),
               'reads_faceaway': len(reads_faceaway),
               'reads_softclipped': len(reads_softclipped)}
        

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
        yield {'chr': chrom, 'pos': pos, 
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
               'reads_softclipped_rev': len(rev(reads_softclipped))}
        

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
        yield {'chr': chrom, 'pos': pos, 'ref': ref,
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
        yield {'chr': chrom, 'pos': pos, 'ref': ref,
               'reads_all': len(reads),
               'reads_pp':len(reads_pp), 'reads_pp_fwd': len(fwd(reads_pp)), 'reads_pp_rev': len(rev(reads_pp)),
               'matches':len(matches), 'matches_fwd': len(fwd(matches)), 'matches_rev': len(rev(matches)),
               'matches_pp':len(matches_pp), 'matches_pp_fwd': len(fwd(matches_pp)), 'matches_pp_rev': len(rev(matches_pp)),
               'mismatches':len(mismatches), 'mismatches_fwd': len(fwd(mismatches)), 'mismatches_rev': len(rev(mismatches)),
               'mismatches_pp':len(mismatches_pp), 'mismatches_pp_fwd': len(fwd(mismatches_pp)), 'mismatches_pp_rev': len(rev(mismatches_pp)),
               'deletions':len(deletions), 'deletions_fwd': len(fwd(deletions)), 'deletions_rev': len(rev(deletions)),
               'deletions_pp':len(deletions_pp), 'deletions_pp_fwd': len(fwd(deletions_pp)), 'deletions_pp_rev': len(rev(deletions_pp)),
               'insertions':len(insertions), 'insertions_fwd': len(fwd(insertions)), 'insertions_rev': len(rev(insertions)),
               'insertions_pp':len(insertions_pp), 'insertions_pp_fwd': len(fwd(insertions_pp)), 'insertions_pp_rev': len(rev(insertions_pp)),
               'A':len(A), 'A_fwd': len(fwd(A)), 'A_rev': len(rev(A)), 'A_pp':len(A_pp), 'A_pp_fwd': len(fwd(A_pp)), 'A_pp_rev': len(rev(A_pp)),
               'C':len(C), 'C_fwd': len(fwd(C)), 'C_rev': len(rev(C)), 'C_pp':len(C_pp), 'C_pp_fwd': len(fwd(C_pp)), 'C_pp_rev': len(rev(C_pp)),
               'T':len(T), 'T_fwd': len(fwd(T)), 'T_rev': len(rev(T)), 'T_pp':len(T_pp), 'T_pp_fwd': len(fwd(T_pp)), 'T_pp_rev': len(rev(T_pp)),
               'G':len(G), 'G_fwd': len(fwd(G)), 'G_rev': len(rev(G)), 'G_pp':len(G_pp), 'G_pp_fwd': len(fwd(G_pp)), 'G_pp_rev': len(rev(G_pp)),
               'N':len(N), 'N_fwd': len(fwd(N)), 'N_rev': len(rev(N)), 'N_pp':len(N_pp), 'N_pp_fwd': len(fwd(N_pp)), 'N_pp_rev': len(rev(N_pp))}


def test_stat_variation_strand():
    _test_withrefseq(pysamstats.stat_variation_strand, stat_variation_strand_refimpl)


def stat_tlen_refimpl(samfile, chrom=None, start=None, end=None, one_based=False):
    start, end = normalise_coords(one_based, start, end)
    for col in samfile.pileup(reference=chrom, start=start, end=end):
        chrom = samfile.getrname(col.tid)
        pos = col.pos + 1 if one_based else col.pos
        reads = col.pileups
        reads_paired = [read for read in reads if not read.alignment.mate_is_unmapped and read.alignment.rnext == col.tid]
        if reads_paired:
            tlen = [read.alignment.tlen for read in reads_paired]
            rms_tlen = int(round(sqrt(np.mean(np.power(tlen, 2)))))
            std_tlen = int(round(np.std(tlen)))
        else:
            rms_tlen = std_tlen = 'NA'
        reads_pp = pp(reads)
        if reads_pp:
            tlen_pp = [read.alignment.tlen for read in reads_pp]
            rms_tlen_pp = int(round(sqrt(np.mean(np.power(tlen_pp, 2))) ))
            std_tlen_pp = int(round(np.std(tlen_pp)))
        else:
            rms_tlen_pp = std_tlen_pp = 'NA'
        yield {'chr': chrom, 'pos': pos, 
               'reads_all': col.n, 
               'reads_pp': len(reads_pp),
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
        if reads_paired:
            tlen = [read.alignment.tlen for read in reads_paired]
            rms_tlen = int(round(sqrt(np.mean(np.power(tlen, 2)))))
            std_tlen = int(round(np.std(tlen)))
        else:
            rms_tlen = std_tlen = 'NA'
        reads_paired_fwd = fwd(reads_paired)
        if reads_paired_fwd:
            tlen_fwd = [read.alignment.tlen for read in reads_paired_fwd]
            rms_tlen_fwd = int(round(sqrt(np.mean(np.power(tlen_fwd, 2)))))
            std_tlen_fwd = int(round(np.std(tlen_fwd)))
        else:
            rms_tlen_fwd = std_tlen_fwd = 'NA'
        reads_paired_rev = rev(reads_paired)
        if reads_paired_rev:
            tlen_rev = [read.alignment.tlen for read in reads_paired_rev]
            rms_tlen_rev = int(round(sqrt(np.mean(np.power(tlen_rev, 2)))))
            std_tlen_rev = int(round(np.std(tlen_rev)))
        else:
            rms_tlen_rev = std_tlen_rev = 'NA'
        
        # properly paired reads
        reads_pp = pp(reads)
        if reads_pp:
            tlen_pp = [read.alignment.tlen for read in reads_pp]
            rms_tlen_pp = int(round(sqrt(np.mean(np.power(tlen_pp, 2))) ))
            std_tlen_pp = int(round(np.std(tlen_pp)))
        else:
            rms_tlen_pp = std_tlen_pp = 'NA'
        reads_pp_fwd = fwd(reads_pp)
        if reads_pp_fwd:
            tlen_pp_fwd = [read.alignment.tlen for read in reads_pp_fwd]
            rms_tlen_pp_fwd = int(round(sqrt(np.mean(np.power(tlen_pp_fwd, 2))) ))
            std_tlen_pp_fwd = int(round(np.std(tlen_pp_fwd)))
        else:
            rms_tlen_pp_fwd = std_tlen_pp_fwd = 'NA'
        reads_pp_rev = rev(reads_pp)
        if reads_pp_rev:
            tlen_pp_rev = [read.alignment.tlen for read in reads_pp_rev]
            rms_tlen_pp_rev = int(round(sqrt(np.mean(np.power(tlen_pp_rev, 2))) ))
            std_tlen_pp_rev = int(round(np.std(tlen_pp_rev)))
        else:
            rms_tlen_pp_rev = std_tlen_pp_rev = 'NA'

        # yield record
        yield {'chr': chrom, 'pos': pos, 
               'reads_all': col.n, 'reads_fwd': len(fwd(reads)), 'reads_rev': len(rev(reads)),
               'reads_pp': len(reads_pp), 'reads_pp_fwd': len(fwd(reads_pp)), 'reads_pp_rev': len(rev(reads_pp)),
               'rms_tlen': rms_tlen, 'rms_tlen_fwd': rms_tlen_fwd, 'rms_tlen_rev': rms_tlen_rev,
               'rms_tlen_pp': rms_tlen_pp, 'rms_tlen_pp_fwd': rms_tlen_pp_fwd, 'rms_tlen_pp_rev': rms_tlen_pp_rev,
               'std_tlen': std_tlen, 'std_tlen_fwd': std_tlen_fwd, 'std_tlen_rev': std_tlen_rev,
               'std_tlen_pp': std_tlen_pp, 'std_tlen_pp_fwd': std_tlen_pp_fwd, 'std_tlen_pp_rev': std_tlen_pp_rev}
        

def test_stat_tlen_strand():
    _test(pysamstats.stat_tlen_strand, stat_tlen_strand_refimpl)

        
