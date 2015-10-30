#!/usr/bin/env python
import WtoAlgorithm3 as Wto
import pandas as pd
import ephem
import sys
from optparse import OptionParser
from tabulate import tabulate

ALMA1 = ephem.Observer()
ALMA1.lat = '-23.0262015'
ALMA1.long = '-67.7551257'
ALMA1.elev = 5060
ALMA1.horizon = ephem.degrees(str('20'))


def get_lst(datestr, observer):
    observer.date = ephem.Date(datestr)
    return str(observer.sidereal_time())


def color_states(state):
    if state == "FullyObserved":
        return '<font color="mediumblue"><strong>FullyObs</strong></font>'
    elif state == "Ready":
        return '<font color="green"><strong>Ready</strong></font>'
    else:
        return '<font color="orange"><strong>' + state + '</strong></font>'


def print_c368():

    c368 = datas.schedblocks.query(
        'BestConf == "C36-8"')[
        ['SB_UID', 'SG_ID', 'OUS_ID', 'sbName', 'sbNote', 'band', 'RA',
         'execount', 'OBSPROJECT_UID', 'isPolarization']]

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
        'CYCLE != "2013.A" and DC_LETTER_GRADE != "C"').sort('RA')[
        ['SB_UID', 'CODE', 'SG_ID', 'sbName', 'band', 'RA', 'execount', 'sbNote',
         'SB_STATE', 'PRJ_STATUS', 'NOTE', 'isTimeConstrained', 'isPolarization',
         'OBSPROJECT_UID']].sort('RA')
    table_8['RA'] = table_8.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['RA'] / 15.),
                        int(4 * (ro1['RA'] - int(ro1['RA'])))))
        , axis=1).astype(str).str.slice(0, 5)

    table_8 = pd.merge(
        table_8,
        datas.obs_param[['SB_UID', 'rise', 'set']],
        on='SB_UID', how='left').set_index('SB_UID', drop=False)
    table_8['rise_lst'] = table_8.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['rise']),
                        int(60. * (ro1['rise'] - int(ro1['rise'])))))
        , axis=1)
    table_8['set_lst'] = table_8.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['set']),
                        int(60. * (ro1['set'] - int(ro1['set'])))))
        , axis=1)
    table_8['rise_lst'] = table_8.rise_lst.astype(str).str.slice(0, 5)
    table_8['set_lst'] = table_8.set_lst.astype(str).str.slice(0, 5)
    table_8['range'] = table_8.rise_lst + '-' + table_8.set_lst

    sbs = table_8.index.unique()
    qastatus = datas.aqua_execblock.query(
        'SB_UID in @sbs').groupby(
        ['SB_UID', 'QA0STATUS']).QA0STATUS.count().unstack().fillna(0)

    table_8b = pd.merge(
        table_8, qastatus.reset_index(),
        left_index=True, right_on='SB_UID', how='left').fillna(0)

    table_8b['Observed'] = table_8b.Unset + table_8b.Pass
    table_8b['execount'] = table_8b.apply(lambda x: str(int(x['execount'])), axis=1)
    table_8b['Unset'] = table_8b.apply(lambda x: str(int(x['Unset'])), axis=1)
    table_8b['Pass'] = table_8b.apply(lambda x: str(int(x['Pass'])), axis=1)
    table_8b['Observed'] = table_8b.apply(lambda x: str(int(x['Observed'])), axis=1)
    table_8b['NOTE'] = None
    table_8b['sbNote'] = table_8b.sbNote.str.replace('\n', ' ')
    table_8b['sbNote'] = table_8b.apply(
        lambda x: x['sbNote'] +
        ' <strong style="color: #ff0000">PENDING QA0 Status</strong>'
        if int(x['Unset']) > 0 else x['sbNote'], axis=1)
    table_8b['SB_STATE'] = table_8b.apply(
        lambda x: color_states(x['SB_STATE']), axis=1)
    table_8b['isTimeConstrained'] = table_8b.apply(
        lambda x: '%Y%' if x['isTimeConstrained'] == True or
        x['isPolarization'] == True else '', axis=1)
    table_8b['CODE'] = table_8b.apply(
        lambda x: '[[https://asa.alma.cl/protrack/?projectUid=' +
        x['OBSPROJECT_UID'] + '][' + x['CODE'] + ']]', axis=1)
    table_8b['PRJ_STATUS'] = table_8b.apply(
        lambda x: '!' + x['PRJ_STATUS'], axis=1)
    table_8b['sbName'] = table_8b.apply(lambda x: '!' + x['sbName'], axis=1)

    table_8b = table_8b[
        [u'CODE', u'SG_ID', u'sbName', u'band', u'RA', u'range', u'execount', u'Pass',
         u'Unset', u'Observed', u'sbNote', u'SB_STATE', u'PRJ_STATUS', u'SB_UID',
         u'isTimeConstrained']]

    table_8b.columns = pd.Index(
        [u'Project Code', u'SG Name', u'SB Name', u'Band', u'RA', u'LST Range',
         u'Exec. Count', u'Pass Obs.', u'Unset Obs.', u'Total Obs.', u'SB Note',
         u'SB Status', u'Prj. Status', u'SB UID', u'Critical (See instructions)'],
        dtype='object')

    table_8b.sort('RA', inplace=True)

    table_8fin = pd.DataFrame(columns=table_8b.columns)

    for r in table_8b.iterrows():
        table_8fin = table_8fin.append(r[1], ignore_index=True)
        if r[1]['Pass Obs.'] > 0:
            sb_uid = r[1]['SB UID']
            df = datas.aqua_execblock.query(
                'SB_UID == @sb_uid and QA0STATUS == "Pass"')
            for d in df.iterrows():
                rarr = [('^', '^', '^', '^', '^', '^', '^', '^', '^', '^',
                         'EB:' + d[1]['EXECBLOCKUID'] +
                         ' [[https://asa.alma.cl/webaqua?ebuid=' +
                         d[1]['EXECBLOCKUID'] + '][(Aqua)]]' + ' LST: ' +
                         d[1]['LST_START'] + '-' + d[1]['LST_END'],
                         'Pass', '', '', '')]
                row_temp = pd.DataFrame(rarr, columns=table_8b.columns)
                table_8fin = table_8fin.append(row_temp, ignore_index=True)
        if r[1]['Unset Obs.'] > 0:
            sb_uid = r[1]['SB UID']
            df = datas.aqua_execblock.query(
                'SB_UID == @sb_uid and QA0STATUS == "Unset"')
            for d in df.iterrows():
                rarr = [('^', '^', '^', '^', '^', '^', '^', '^', '^', '^',
                         'EB:' + d[1]['EXECBLOCKUID'] +
                         ' [[https://asa.alma.cl/webaqua?ebuid=' +
                         d[1]['EXECBLOCKUID'] + '][(Aqua)]]' + ' LST: ' +
                         d[1]['LST_START'] + '-' + d[1]['LST_END'],
                         'Unset', '', '', '')]
                row_temp = pd.DataFrame(rarr, columns=table_8b.columns)
                table_8fin = table_8fin.append(row_temp, ignore_index=True)

    table_8fin['SB UID'] = table_8fin.apply(
        lambda x: '[[' + x['SB UID'].replace('uid://', '').replace('/', '_') +
        '][' + x['SB UID'] + ']]' if len(x['SB UID']) > 0 else '^', axis=1)
    print(
        tabulate(table_8fin.set_index('SB UID'), tablefmt='orgtbl'))


def print_c367():

    c367 = datas.schedblocks.query(
        'BestConf == "C36-7"')[
        ['SB_UID', 'SG_ID', 'OUS_ID', 'sbName', 'sbNote', 'band', 'RA', 'execount',
         'OBSPROJECT_UID', 'isPolarization']]

    c367_s = pd.merge(c367, datas.sb_status[['SB_UID', 'SB_STATE']],
                      on='SB_UID', how='left')
    c367_ss = pd.merge(
        datas.sciencegoals[['OBSPROJECT_UID', 'OUS_ID', 'isTimeConstrained']],
        c367_s, on=['OBSPROJECT_UID', 'OUS_ID'])
    c367_ssp = pd.merge(
        pd.merge(
            datas.projects[['OBSPROJECT_UID', 'CODE', 'PRJ_STATUS', 'CYCLE',
                            'DC_LETTER_GRADE']],
            datas.obsproject[['OBSPROJECT_UID', 'NOTE']], on='OBSPROJECT_UID'),
        c367_ss, on='OBSPROJECT_UID', how='right')

    table_7 = c367_ssp.query(
        'CYCLE != "2013.A" and DC_LETTER_GRADE != "C"').sort('RA')[
        ['SB_UID', 'CODE', 'SG_ID', 'sbName', 'band', 'RA', 'execount', 'sbNote',
         'SB_STATE', 'PRJ_STATUS', 'NOTE', 'isTimeConstrained', 'isPolarization',
         'OBSPROJECT_UID']].sort('RA')
    table_7['RA'] = table_7.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['RA'] / 15.),
                        int(4 * (ro1['RA'] - int(ro1['RA'])))))
        , axis=1).astype(str).str.slice(0, 5)

    table_7 = pd.merge(
        table_7,
        datas.obs_param[['SB_UID', 'rise', 'set']],
        on='SB_UID', how='left').set_index('SB_UID', drop=False)
    table_7['rise_lst'] = table_7.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['rise']),
                        int(60. * (ro1['rise'] - int(ro1['rise'])))))
        , axis=1)
    table_7['set_lst'] = table_7.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['set']),
                        int(60. * (ro1['set'] - int(ro1['set'])))))
        , axis=1)
    table_7['rise_lst'] = table_7.rise_lst.astype(str).str.slice(0, 5)
    table_7['set_lst'] = table_7.set_lst.astype(str).str.slice(0, 5)
    table_7['range'] = table_7.rise_lst + '-' + table_7.set_lst

    sbs = table_7.index.unique()
    qastatus = datas.aqua_execblock.query(
        'SB_UID in @sbs').groupby(
        ['SB_UID', 'QA0STATUS']).QA0STATUS.count().unstack().fillna(0)

    table_7b = pd.merge(
        table_7, qastatus.reset_index(),
        left_index=True, right_on='SB_UID', how='left').fillna(0)

    try:
        table_7b['Observed'] = table_7b.Unset + table_7b.Pass
    except AttributeError:
        try:
            table_7b['Observed'] = table_7b.Unset
            table_7b['Pass'] = 0
        except AttributeError:
            table_7b['Observed'] = 0
            table_7b['Unset'] = 0

    table_7b['execount'] = table_7b.apply(lambda x: str(int(x['execount'])), axis=1)
    table_7b['Unset'] = table_7b.apply(lambda x: str(int(x['Unset'])), axis=1)
    table_7b['Pass'] = table_7b.apply(lambda x: str(int(x['Pass'])), axis=1)
    table_7b['Observed'] = table_7b.apply(lambda x: str(int(x['Observed'])), axis=1)
    table_7b['NOTE'] = None
    table_7b['sbNote'] = table_7b.sbNote.str.replace('\n', ' ')
    table_7b['sbNote'] = table_7b.apply(
        lambda x: x['sbNote'] +
        ' <strong style="color: #ff0000">PENDING QA0 Status</strong>'
        if int(x['Unset']) > 0 else x['sbNote'], axis=1)
    table_7b['SB_STATE'] = table_7b.apply(
        lambda x: color_states(x['SB_STATE']), axis=1)
    table_7b['isTimeConstrained'] = table_7b.apply(
        lambda x: '%Y%' if x['isTimeConstrained'] == True or
        x['isPolarization'] == True else '', axis=1)
    table_7b['CODE'] = table_7b.apply(
        lambda x: '[[https://asa.alma.cl/protrack/?projectUid=' +
        x['OBSPROJECT_UID'] + '][' + x['CODE'] + ']]', axis=1)
    table_7b['PRJ_STATUS'] = table_7b.apply(
        lambda x: '!' + x['PRJ_STATUS'], axis=1)
    table_7b['sbName'] = table_7b.apply(lambda x: '!' + x['sbName'], axis=1)

    table_7b = table_7b[
        [u'CODE', u'SG_ID', u'sbName', u'band', u'RA', u'range', u'execount', u'Pass',
         u'Unset', u'Observed', u'sbNote', u'SB_STATE', u'PRJ_STATUS', u'SB_UID',
         u'isTimeConstrained']]

    table_7b.columns = pd.Index(
        [u'Project Code', u'SG Name', u'SB Name', u'Band', u'RA', u'LST Range',
         u'Exec. Count', u'Pass Obs.', u'Unset Obs.', u'Total Obs.', u'SB Note',
         u'SB Status', u'Prj. Status', u'SB UID', u'Critical (See instructions)'],
        dtype='object')

    table_7b.sort('RA', inplace=True)

    table_7fin = pd.DataFrame(columns=table_7b.columns)

    for r in table_7b.iterrows():
        table_7fin = table_7fin.append(r[1], ignore_index=True)
        if r[1]['Pass Obs.'] > 0:
            sb_uid = r[1]['SB UID']
            df = datas.aqua_execblock.query(
                'SB_UID == @sb_uid and QA0STATUS == "Pass"')
            for d in df.iterrows():
                rarr = [('^', '^', '^', '^', '^', '^', '^', '^', '^', '^',
                         'EB:' + d[1]['EXECBLOCKUID'] +
                         ' [[https://asa.alma.cl/webaqua?ebuid=' +
                         d[1]['EXECBLOCKUID'] + '][(Aqua)]]' + ' LST: ' +
                         d[1]['LST_START'] + '-' + d[1]['LST_END'],
                         'Pass', '', '', '')]
                row_temp = pd.DataFrame(rarr, columns=table_7b.columns)
                table_7fin = table_7fin.append(row_temp, ignore_index=True)
        if r[1]['Unset Obs.'] > 0:
            sb_uid = r[1]['SB UID']
            df = datas.aqua_execblock.query(
                'SB_UID == @sb_uid and QA0STATUS == "Unset"')
            for d in df.iterrows():
                rarr = [('^', '^', '^', '^', '^', '^', '^', '^', '^', '^',
                         'EB:' + d[1]['EXECBLOCKUID'] +
                         ' [[https://asa.alma.cl/webaqua?ebuid=' +
                         d[1]['EXECBLOCKUID'] + '][(Aqua)]]' + ' LST: ' +
                         d[1]['LST_START'] + '-' + d[1]['LST_END'],
                         'Unset', '', '', '')]
                row_temp = pd.DataFrame(rarr, columns=table_7b.columns)
                table_7fin = table_7fin.append(row_temp, ignore_index=True)

    table_7fin['SB UID'] = table_7fin.apply(
        lambda x: '[[' + x['SB UID'].replace('uid://', '').replace('/', '_') +
        '][' + x['SB UID'] + ']]' if len(x['SB UID']) > 0 else '^', axis=1)
    print(
        tabulate(table_7fin.set_index('SB UID'), tablefmt='orgtbl'))


if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option(
        "--conf", type=str, default='c368',
        help="Configuration to check: c368 or c367")

    opts, args = parser.parse_args()
    print "Twiki for %s" % opts.conf
    if opts.conf not in ['c368', 'c367']:
        print("Use either c368 or c367 as input for --conf")
        sys.exit(1)

    datas = Wto.WtoAlgorithm3(path=Wto.home + '/.twiki/')
    datas.write_ephem_coords()

    datas.observable_param(horizon=30)
    datas.aqua_execblock['LST_START'] = datas.aqua_execblock.apply(
        lambda x: get_lst(x['STARTTIME'], ALMA1), axis=1)
    datas.aqua_execblock['LST_END'] = datas.aqua_execblock.apply(
        lambda x: get_lst(x['ENDTIME'], ALMA1), axis=1)

    if opts.conf == 'c368':
        print_c368()
    else:
        print_c367()
