import numpy as np


def convert_deg(angle, unit):
    """

    :param angle:
    :param unit:
    :return:
    """
    value = angle
    if unit == 'mas':
        value /= 3600000.
    elif unit == 'arcsec':
        value /= 3600.
    elif unit == 'arcmin':
        value /= 60.
    elif unit == 'rad':
        value = value * np.pi / 180.
    elif unit == 'hours':
        value *= 15.
    return value


def convert_sec(angle, unit):
    """

    :param angle:
    :param unit:
    :return:
    """
    value = angle
    if unit == 'mas':
        value /= 1000.
    elif unit == 'arcsec':
        value /= 1.
    elif unit == 'arcmin':
        value *= 60.
    elif unit == 'rad':
        value = (value * np.pi / 180.) * 3600.
    elif unit == 'hours':
        value *= 15. * 3600.
    elif unit == 'deg':
        value *= 3600.
    else:
        return None
    return value


def convert_jy(flux, unit):
    """

    :param flux:
    :param unit:
    :return:
    """
    value = flux
    if unit == 'Jy':
        value = value
    elif unit == 'mJy':
        value /= 1000.
    else:
        return None
    return value


def convert_mjy(flux, unit):
    """

    :param flux:
    :param unit:
    :return:
    """
    value = flux
    if unit == 'Jy':
        value *= 1e3
    elif unit == 'mJy':
        value = value
    else:
        return None
    return value


def convert_ghz(freq, unit):
    """

    :param freq:
    :param unit:
    :return:
    """
    value = freq
    if unit == 'GHz':
        value = value
    elif unit == 'MHz':
        value *= 1e-3
    elif unit == 'kHz':
        value *= 1e-6
    elif unit == 'Hz':
        value *= 1e-9
    else:
        return None
    return value


def convert_tsec(time, unit):

    """

    :param time:
    :param unit:
    :return:
    """
    try:
        value = float(time)
    except ValueError:
        print time, unit
        value = 0
    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60.
    elif unit == 'h':
        return value * 3600.
    elif unit == 'd':
        return value * 24. * 3600.
    else:
        return 0


def convert_thour(time, unit):

    """

    :param time:
    :param unit:
    :return:
    """
    try:
        value = float(time)
    except ValueError:
        print time, unit
        value = 0
    if unit == 's':
        return value / 3660.
    elif unit == 'min':
        return value / 60.
    elif unit == 'h':
        return value
    elif unit == 'd':
        return value * 24.
    else:
        return 0
