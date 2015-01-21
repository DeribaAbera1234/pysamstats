#!/usr/bin/env python

from __future__ import print_function, division, absolute_import

import sys
import pstats
import cProfile as profile
import timeit


from pysam import Samfile, Fastafile


sys.path.append('.')
import pysamstats


def do_profiling(fun, end=1000):
    samfile = Samfile('fixture/test.bam')
    count = 0
    f = getattr(pysamstats, fun)
    for _ in f(samfile, chrom='Pf3D7_01_v3', start=0, end=end):
        count += 1


def do_profiling_withrefseq(fun, end=1000):
    samfile = Samfile('fixture/test.bam')
    fafile = Fastafile('fixture/ref.fa')
    count = 0
    f = getattr(pysamstats, fun)
    for _ in f(samfile, fafile, chrom='Pf3D7_01_v3', start=0, end=end):
        count += 1


stats_types_requiring_fasta = ('variation', 
                               'variation_strand', 
                               'baseq_ext', 
                               'baseq_ext_strand', 
                               'coverage_gc',
                               'coverage_normed_gc',
                               'coverage_binned',
                               'coverage_ext_binned')

fun = sys.argv[1]
if len(sys.argv) > 2:
    end = sys.argv[2]
else:
    end = 1000
if len(sys.argv) > 3:
    number = int(sys.argv[3])
else:
    number = 1
if len(sys.argv) > 4:
    repeat = int(sys.argv[4])
else:
    repeat = 3

if fun in stats_types_requiring_fasta:
    cmd = 'do_profiling_withrefseq("stat_%s", %s)' % (fun, end)
else:
    cmd = 'do_profiling("stat_%s", %s)' % (fun, end)
    
prof_fn = '%s.prof' % fun
profile.runctx(cmd, globals(), locals(), prof_fn)
s = pstats.Stats(prof_fn)
s.strip_dirs().sort_stats('time').print_stats()
print(timeit.repeat(cmd,
                    number=number,
                    repeat=repeat,
                    setup='from __main__ import do_profiling, '
                          'do_profiling_withrefseq'))


