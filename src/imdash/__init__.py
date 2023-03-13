# This is here to prevent BLAS libraries from going haywire.
# Sometimes ALL cores will be used, which (ironically) increases computation
# time and results in excessively high load on the system. Using just one
# thread still results in a 2x speed up compared to e.g. einsum(...).
from os import environ
N_THREADS = '1'
environ['OMP_NUM_THREADS'] = N_THREADS
environ['OPENBLAS_NUM_THREADS'] = N_THREADS
environ['MKL_NUM_THREADS'] = N_THREADS
environ['VECLIB_MAXIMUM_THREADS'] = N_THREADS
environ['NUMEXPR_NUM_THREADS'] = N_THREADS


from imdash.components import *
