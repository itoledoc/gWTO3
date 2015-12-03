import numpy as np
import pandas as pd
import math


def calc_cond_score(pwv, maxpwvc, fraction):

    """

    :param pwv:
    :param maxpwvc:
    :param fraction:
    :return:
    """
    frac = 1. / fraction
    pwv_corr = 1 - (abs(pwv - maxpwvc) / 4.)

    if pwv_corr < 0.1:
        pwv_corr = 0.1

    if frac < 1:
        x = frac - 1.
        sb_cond_score = 10 * (1 - (x ** 10.)) * pwv_corr

    elif frac == 1:
        sb_cond_score = 10.

    else:
        x = frac - 1
        if frac <= 1.3:
            sb_cond_score = (1. - (x / 0.3) ** 3.) * 10. * pwv_corr
        else:
            sb_cond_score = 0.

    return sb_cond_score


def calc_array_score(name, array_kind, ar, dec, array_ar_sb, minar, maxar):

    c_bmax = (0.4001 /
              np.cos(math.radians(-23.0262015) - math.radians(dec)) +
              0.6103)
    corr = 1. / c_bmax

    if array_kind == 'SEVEN-M' or array_kind == 'TP-Array':
        sb_array_score = 10.
        corr = 0

    elif array_ar_sb == np.NaN or array_ar_sb <= 0:
        sb_array_score = 0.

    else:

        arcorr = ar * corr
        # if arcorr > maxar or arcorr < minar:
        #     print("WTF??? %s" % name)

        if name.endswith('_TC'):
            arcorr = minar / 0.8

        if arcorr > 3.35:
            arcorr = 3.35
        if arcorr < 0.075:
            arcorr = 0.075

        if 0.9 * arcorr <= array_ar_sb <= 1.1 * arcorr:
            sb_array_score = 10.

        elif 0.8 * arcorr < array_ar_sb <= 1.2 * arcorr:
            sb_array_score = 8.0

        elif array_ar_sb < 0.8 * arcorr:  # and not points:
            l = 0.8 * arcorr - minar
            sb_array_score = ((array_ar_sb - minar) / l) * 8.0

        elif array_ar_sb > 1.2 * arcorr:
            l = arcorr * 1.2 - maxar
            try:
                s = 8. / l
            except ZeroDivisionError:
                s = 8. / 1.e-5
            sb_array_score = (array_ar_sb - maxar) * s
        else:
            # print("What happened with %s?" % name)
            sb_array_score = -1.

    return sb_array_score, ar * corr


def calc_sb_completion(observed, execount):

    sb_completion = observed / execount
    return 6 * sb_completion + 4.


def calc_executive_score():

    return 10.


def calc_sciencerank_score(srank, max_scirank=1400.):

    sb_science_score = 10. * (max_scirank - srank) / max_scirank
    return sb_science_score


def calc_cycle_grade_score(grade, cycle):

    if grade == 'A' and str(cycle).startswith('2015'):
        sb_grade_score = 10.
    elif str(cycle).startswith('2013'):
        sb_grade_score = 8.
    elif grade == 'B':
        sb_grade_score = 4.
    else:
        sb_grade_score = -100.

    return sb_grade_score


def calc_ha_scorer(ha):

    sb_ha_scorer = ((math.cos(math.radians((ha + 1.) * 15.)) - 0.3) /
                    (1 - 0.3)) * 10.

    return sb_ha_scorer


def calc_total_score(scores, weights=None):

    if not weights:
        weights = {'cond': 0.35, 'array': 0.05, 'sbcompletion': 0.20,
                   'executive': 0.05, 'sciencerank': 0.05, 'cyclegrade': 0.20,
                   'ha': 0.10}
    score = 0.
    keys = weights.keys()
    for n, s in enumerate(scores):
        score += weights[keys[n]] * s

    return score


def calc_all_scores(pwv, maxpwvc, fraction, name, array_kind, ar, dec,
                    array_ar_sb, minar, maxar, observed, execount, srank,
                    grade, cycle, ha):

    try:
        cond_score = calc_cond_score(pwv, maxpwvc, fraction)
    except ZeroDivisionError:
        cond_score = -9999.0
    array_score = calc_array_score(name, array_kind, ar, dec, array_ar_sb,
                                   minar, maxar)
    sbcompletion_score = calc_sb_completion(observed, execount)
    executive_score = 10.
    sciencerank_score = calc_sciencerank_score(srank)
    cyclegrade_score = calc_cycle_grade_score(grade, cycle)
    ha_score = calc_ha_scorer(ha)

    score = calc_total_score(
        [cond_score, array_score[0], sbcompletion_score,
         executive_score, sciencerank_score, cyclegrade_score,
         ha_score])

    return pd.Series([cond_score, array_score[0], sbcompletion_score,
                      executive_score, sciencerank_score, cyclegrade_score,
                      ha_score, score, array_score[1]],
                     index=[
                         'conditon score', 'array score',
                         'sb completion score', 'executive score',
                         'science rank score', 'cycle grade score',
                         'ha score', 'Score', 'AR PI'])
