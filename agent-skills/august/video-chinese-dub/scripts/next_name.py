"""Print a free output stem in <outdir> (bumps _NN so nothing is overwritten).

usage: python next_name.py <outdir> <Name_00>
"""
import sys

from common import unique_stem

print(unique_stem(sys.argv[1], sys.argv[2]))
