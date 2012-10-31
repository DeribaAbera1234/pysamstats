#!/usr/bin/env python

import pstats, cProfile

from pysamstats import TlenStatsTable
t = TlenStatsTable('fixture/test.bam',
                    'Pf3D7_01_v3', 0, 1000)

cProfile.runctx('sum(1 for r in t)', globals(), locals(), 'Profile.prof')

s = pstats.Stats('Profile.prof')
s.strip_dirs().sort_stats('time').print_stats()

