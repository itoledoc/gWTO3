import WtoAlgorithm3 as Wto
import ephem
import numpy as np
import pylab as py
import pandas as pd


ALMA1 = ephem.Observer()
ALMA1.lat = '-23.0262015'
ALMA1.long = '-67.7551257'
ALMA1.elev = 5060
ALMA1.horizon = ephem.degrees(str('20'))


def add_band(
        ind, timet, band, use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8,
        use_ra_b9, use_ra_b10):

    if band == "ALMA_RB_03":
        if ind == "all":
            use_ra_b3 += timet
        else:
            use_ra_b3[ind] += timet
        return use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
            use_ra_b9, use_ra_b10
    if band == "ALMA_RB_04":
        if ind == "all":
            use_ra_b4 += timet
        else:
            use_ra_b4[ind] += timet
        return use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
            use_ra_b9, use_ra_b10
    if band == "ALMA_RB_06":
        if ind == "all":
            use_ra_b6 += timet
        else:
            use_ra_b6[ind] += timet
        return use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
            use_ra_b9, use_ra_b10
    if band == "ALMA_RB_07":
        if ind == "all":
            use_ra_b7 += timet
        else:
            use_ra_b7[ind] += timet
        return use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
            use_ra_b9, use_ra_b10
    if band == "ALMA_RB_08":
        if ind == "all":
            use_ra_b8 += timet
        else:
            use_ra_b8[ind] += timet
        return use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
            use_ra_b9, use_ra_b10
    if band == "ALMA_RB_09":
        if ind == "all":
            use_ra_b9 += timet
        else:
            use_ra_b9[ind] += timet
        return use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
            use_ra_b9, use_ra_b10
    if band == "ALMA_RB_10":
        if ind == "all":
            use_ra_b10 += timet
        else:
            use_ra_b10[ind] += timet
        return use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
            use_ra_b9, use_ra_b10


def av_arrays(sel, minlst=-2., maxlst=2.):

    map_ra = np.arange(0, 24, 24. / (24 * 60.))
    use_ra_b3 = np.zeros(1440)
    use_ra_b4 = np.zeros(1440)
    use_ra_b6 = np.zeros(1440)
    use_ra_b7 = np.zeros(1440)
    use_ra_b8 = np.zeros(1440)
    use_ra_b9 = np.zeros(1440)
    use_ra_b10 = np.zeros(1440)

    for r in sel.iterrows():
        data = r[1]

        if data.RA == 0 or data.up == 24:
            use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, use_ra_b9, \
                use_ra_b10 = add_band(
                    'all', data.estimatedTime_SB / 24., data.band, use_ra_b3,
                    use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, use_ra_b9,
                    use_ra_b10)
            continue

        if data.up > maxlst - minlst:
            if maxlst < (data.RA / 15.) < 24 + minlst:
                rise = (data.RA / 15.) + minlst
                set_lst = (data.RA / 15.) + maxlst
                up = maxlst - minlst
                use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
                    use_ra_b9, use_ra_b10 = add_band(
                        (map_ra > rise) & (map_ra < set_lst),
                        data.estimatedTime_SB / up, data.band, use_ra_b3,
                        use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, use_ra_b9,
                        use_ra_b10)
            else:
                if (data.RA / 15.) < maxlst:
                    rise = 24 + minlst + (data.RA / 15.)
                    set_lst = (data.RA / 15.) + maxlst
                    up = maxlst - minlst
                else:
                    rise = (data.RA / 15.) + minlst
                    set_lst = maxlst - (24 - (data.RA / 15.))
                    up = maxlst - minlst
                use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
                    use_ra_b9, use_ra_b10 = add_band(
                        map_ra < set_lst, data.estimatedTime_SB / up,
                        data.band,
                        use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8,
                        use_ra_b9, use_ra_b10)
                use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
                    use_ra_b9, use_ra_b10 = add_band(
                        map_ra > rise, data.estimatedTime_SB / up, data.band,
                        use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8,
                        use_ra_b9, use_ra_b10)
            continue

        if data.rise > data.set:
            rise = data.rise
            set_lst = data.set
            up = data.up
            if data.up > maxlst - minlst:
                if set_lst > maxlst:
                    set_lst = maxlst
                if rise < 24 + minlst:
                    rise = 24 + minlst
                up = maxlst - minlst
            use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, use_ra_b9,\
                use_ra_b10 = add_band(
                    map_ra < set_lst, data.estimatedTime_SB / up, data.band,
                    use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8,
                    use_ra_b9, use_ra_b10)
            use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, use_ra_b9, \
                use_ra_b10 = add_band(
                    map_ra > rise, data.estimatedTime_SB / up, data.band,
                    use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8,
                    use_ra_b9, use_ra_b10)
        else:
            rise = data.rise
            set_lst = data.set
            up = data.up
            if up > maxlst - minlst and data.ephem is False:
                if rise < data.RA / 15. + minlst:
                    rise = data.RA / 15. + minlst
                if set_lst > data.RA / 15. + maxlst:
                    set_lst = data.RA / 15. + maxlst
                up = maxlst - minlst
                use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, \
                    use_ra_b9, use_ra_b10 = add_band(
                        (map_ra > rise) & (map_ra < set_lst),
                        data.estimatedTime_SB / up, data.band, use_ra_b3,
                        use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8, use_ra_b9,
                        use_ra_b10)

    return map_ra, [use_ra_b3, use_ra_b4, use_ra_b6, use_ra_b7, use_ra_b8,
                    use_ra_b9, use_ra_b10]


# noinspection PyUnusedLocal
def do_pre_plots(ra, used, tot_t, filename, title, lab=False, xleg='', yleg='',
                 ymax=None):
    py.close()
    py.figure(figsize=(11.69, 8.27))
    # py.bar(ra, used[0] + used[1] + used[2] + used[3] + used[4] + used[5] +
    #        used[6],
    #        width=1.66666667e-02, ec='#4575b4', fc='#4575b4', label='Band 10')
    # py.bar(ra, used[0] + used[1] + used[2] + used[3] + used[4] + used[5],
    #        width=1.66666667e-02, ec='#91bfdb', fc='#91bfdb', label='Band 9')
    # py.bar(ra, used[0] + used[1] + used[2] + used[3] + used[4],
    #        width=1.66666667e-02, ec='#e0f3f8', fc='#e0f3f8', label='Band 8')
    py.bar(ra, used[0] + used[1] + used[2] + used[3],
           width=1.66666667e-02, ec='#ffffbf', fc='#ffffbf', label='Band 7')
    py.bar(ra, used[0] + used[1] + used[2],
           width=1.66666667e-02, ec='#fee090', fc='#fee090', label='Band 6')
    py.bar(ra, used[0] + used[1],
           width=1.66666667e-02, ec='#fc8d59', fc='#fc8d59', label='Band 4')
    py.bar(ra, used[0],
           width=1.66666667e-02, ec='#d73027', fc='#d73027', label='Band 3')
    py.xlim(0, 24)
    if ymax:
        py.ylim(0, ymax)
    py.xlabel(xleg)
    py.ylabel(yleg)
    py.title(title, fontsize='xx-large')
    # py.plot(np.arange(0, 24, 24. / (24 * 60.)), tot_t, 'k--',
    #         label='100% efficiency')
    # py.plot(np.arange(0, 24, 24. / (24 * 60.)), tot_t * 0.6, 'k-.',
    #         label='Exp. Efficiency [h]')
    if lab:
        py.legend(framealpha=0.5, ncol=2)
    py.savefig('/home/itoledo/Documents/' + filename, dpi=300,
               bbox_inches='tight')

    return py.ylim()[1]


def get_lst(datestr, observer):
    observer.date = ephem.Date(datestr)
    return str(observer.sidereal_time())


datas = Wto.WtoAlgorithm3()
datas.write_ephem_coords()

datas.unmut_param(horizon=30)
datas.aqua_execblock['LST_START'] = datas.aqua_execblock.apply(
    lambda x: get_lst(x['STARTTIME'], ALMA1), axis=1)
datas.aqua_execblock['LST_END'] = datas.aqua_execblock.apply(
    lambda x: get_lst(x['ENDTIME'], ALMA1), axis=1)


def plots_remaining(conf):

    c368 = datas.schedblocks.query(
        'BestConf == @conf')[
        ['SB_UID', 'SG_ID', 'OUS_ID', 'sbName', 'sbNote', 'band', 'RA',
         'execount', 'OBSPROJECT_UID', 'isPolarization', 'estimatedTime']]

    c368_s = pd.merge(c368, datas.sb_status[['SB_UID', 'SB_STATE']],
                      on='SB_UID', how='left')
    c368_ss = pd.merge(
        datas.sciencegoals[['OBSPROJECT_UID', 'OUS_ID', 'isTimeConstrained']],
        c368_s, on=['OBSPROJECT_UID', 'OUS_ID'])
    c368_ssp = pd.merge(
        pd.merge(
            datas.projects[['OBSPROJECT_UID', 'CODE', 'PRJ_STATUS', 'CYCLE',
                            'DC_LETTER_GRADE']],
            datas.obsproject[['OBSPROJECT_UID', 'NOTE']], on='OBSPROJECT_UID'),
        c368_ss, on='OBSPROJECT_UID', how='right')

    table_8 = c368_ssp.query(
        'CYCLE != "2013.A" and DC_LETTER_GRADE != "C"').sort('RA')

    table_8 = pd.merge(
        table_8,
        datas.obs_param,
        on='SB_UID', how='left').set_index('SB_UID', drop=False)

    table_8['rise_lst'] = table_8.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['rise']),
                        int(60. * (ro1['rise'] - int(ro1['rise']))))),
        axis=1)
    table_8['set_lst'] = table_8.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['set']),
                        int(60. * (ro1['set'] - int(ro1['set']))))),
        axis=1)
    table_8['rise_lst'] = table_8.rise_lst.astype(str).str.slice(0, 5)
    table_8['set_lst'] = table_8.set_lst.astype(str).str.slice(0, 5)
    table_8['range'] = table_8.rise_lst + '-' + table_8.set_lst

    # noinspection PyUnusedLocal
    sbs = table_8.index.unique()
    qastatus = datas.aqua_execblock.query(
        'SB_UID in @sbs').groupby(
        ['SB_UID', 'QA0STATUS']).QA0STATUS.count().unstack().fillna(0)

    table_8b = pd.merge(
        table_8, qastatus.reset_index(),
        left_index=True, right_on='SB_UID', how='left').fillna(0)
    t8 = table_8b.query('SB_STATE != "FullyObserved"').copy()

    t8['estimatedTime_SB'] = (t8.estimatedTime / t8.execount) * (
        t8.execount - t8.Pass)
    t8['estimatedTime_SB'] = t8.apply(
        lambda x: 0 if x['estimatedTime_SB'] < 0 else x['estimatedTime_SB'],
        axis=1)
    rab, usedb = av_arrays(t8, minlst=-3., maxlst=3.)
    ymax = do_pre_plots(
        rab, usedb, 0, '%s_pass.png' % conf,
        '%s Remaining Pressure (only with QA0 Pass)' % conf, lab=True,
        yleg='Time Needed [hours]', xleg='LST [h]')

    t8['estimatedTime_SB'] = (t8.estimatedTime / t8.execount) * (
        t8.execount - t8.Pass - t8.Unset)
    t8['estimatedTime_SB'] = t8.apply(
        lambda x: 0 if x['estimatedTime_SB'] < 0 else x['estimatedTime_SB'],
        axis=1)
    rab, usedb = av_arrays(t8, minlst=-3., maxlst=3.)
    do_pre_plots(rab, usedb, 0, '%s_pass_unset.png' % conf,
                 '%s Remaining Pressure (QA0 Pass + QA0 Unset)' % conf,
                 lab=True, ymax=ymax,
                 yleg='Time Needed [hours]', xleg='LST [h]')
