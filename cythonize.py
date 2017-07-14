import pysam
from Cython.Build import cythonize


if __name__ == '__main__':
    cythonize('pysamstats/opt.pyx',
              include_path=pysam.get_include())
