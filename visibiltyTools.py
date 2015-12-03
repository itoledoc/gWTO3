import arrayConfigurationTools as ac
from lxml import objectify
from scipy.stats import rayleigh

import numpy as np
import math


def computeRuv(fileCasa):
    """
    Compute the radial distance in the uv plane
    """

    f = open(fileCasa, 'r')

    xx = []
    yy = []

    for line in f:
        if line[0] != "#":
            dat = line.split()

            xx.append(float(dat[0]))
            yy.append(float(dat[1]))

    f.close()

    nant = len(xx)
    nbl = nant * (nant - 1) / 2
    Ruv = np.zeros(nbl)

    index = 0
    for i in range(nant):
        for j in range(0, i):
            r2 = (xx[i] - xx[j]) * (xx[i] - xx[j]) + (yy[i] - yy[j]) * (
                yy[i] - yy[j])
            Ruv[index] = math.sqrt(r2)
            index += 1

    return (Ruv)


def computeBL(AR, freq, las=False):
    """
    compute the BL in meter for a resolution AR (applying a Briggs correction
    """

    try:
        BLmax = 61800 / (freq * AR)
    except ZeroDivisionError:
        BLmax = 0.

    if BLmax < 165.6 and not las:
        BLmax = 165.6

    if las:
        if BLmax > 248.3:
            BLmax = 248.3

    return (BLmax)


def compute_array_ar(ruv):
    x = np.linspace(0, ruv.max() + 100., 1000)
    param = rayleigh.fit(ruv)
    pdf_fitted = rayleigh.pdf(x, loc=param[0], scale=param[1])
    interval = rayleigh.interval(0.992, loc=param[0], scale=param[1])
    linea = min(interval[1], ruv.max())
    return 61800 / (100. * linea)



