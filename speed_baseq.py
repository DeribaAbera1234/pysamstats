#!/usr/bin/env python

from pysamstats import BaseqStatsTable
t = BaseqStatsTable('fixture/test.bam', 'fixture/ref.fa',
                    'Pf3D7_01_v3', 0, 10000)

from petl import *
nrows(progress(t, 1000))
