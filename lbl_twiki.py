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

header = str(
    '*NOTE*: This page is regenerated at least once a day. Feel free to '
    'modify numbers of executions. If you need to add a comment, please use '
    'the link in the first column (SB UID): if only a \'?\' (question mark) '
    'is shown at the end of the SB UID, click on it and a new wiki page for '
    'comments will be generated; if the SB UID is underlined it means that '
    'the link is already created, and you should add comments there. '
    'The project code links with the project tracker. *The LST Range columns'
    ' gives the rising and setting times in LST hours, for a minimum '
    'altitude of 30 degrees*\n\nAlso, *and just for the use of the !AoD*, '
    'there is a link that shows what it currently observable, given that it is '
    'over 20 degrees, within -4 and 4 HA, and executable in C36-7:\n\n'
    '[[http://tableau.alma.cl/views/Available/Dashboard1?:embed=y&:'
    'showShareOptions=true&:display_count=no]'
    '[What is up?]]\n\n The user is \'tableuser\' and the password should be '
    'avalaible with the AoD Lead (or otherwise send email to itoledo@alma.cl). '
    'Please, only one user should be logged with that account at a '
    'time.\n\n%TABLE{tablerules="rows"}%\n| *SB UID / '
    'Link to comments (scheduling, problems)*  | *Project Code* | '
    '*SG Name*  | *SB Name*  | *Band*  | *Max. PWV* | *RA*  | *LST Range* |  '
    '*Exec. Count* |  *Pass Obs.* |  *Unset Obs.* |  *Total Obs.* | '
    '*SB Note / EB UID (link to Aqua) and LST Range*  | *SB / EB Status*  '
    '| *Prj. Status*  |  *Critical or Pol (See instructions in block wiki)*'
    '  ||\n')


def get_lst(datestr, observer):
    observer.date = ephem.Date(datestr)
    return str(observer.sidereal_time())


def color_states(state, execount, qunset, qpass):
    if state == "FullyObserved":
        return '<font color="mediumblue"><strong>FullyObs</strong></font>'
    elif int(qpass) >= int(execount):
        return '<font color="mediumblue"><strong>FullyObs?</strong></font>'
    elif (int(qunset) + int(qpass)) >= int(execount):
        return '<font color="orange"><strong>' + state \
               + ' (execount reached)</strong></font>'
    elif state == "Ready":
        return '<font color="green"><strong>Ready</strong></font>'
    else:
        return '<font color="orange"><strong>' + state + '</strong></font>'


# noinspection PyUnusedLocal
def print_twiki(conf):

    sched_conf = datas.schedblocks.query(
        'BestConf in ["C36-8", "C36-7"]')[
        ['SB_UID', 'SG_ID', 'OUS_ID', 'sbName', 'sbNote', 'band', 'RA', 'execount',
         'OBSPROJECT_UID', 'isPolarization', 'maxPWVC']]

    sched_conf_s = pd.merge(sched_conf, datas.sb_status[['SB_UID', 'SB_STATE']],
                            on='SB_UID', how='left')
    sched_conf_ss = pd.merge(
        datas.sciencegoals[['OBSPROJECT_UID', 'OUS_ID', 'isTimeConstrained']],
        sched_conf_s, on=['OBSPROJECT_UID', 'OUS_ID'])
    sched_conf_ssp = pd.merge(
        pd.merge(
            datas.projects[['OBSPROJECT_UID', 'CODE', 'PRJ_STATUS', 'CYCLE',
                            'DC_LETTER_GRADE']],
            datas.obsproject[['OBSPROJECT_UID', 'NOTE']], on='OBSPROJECT_UID'),
        sched_conf_ss, on='OBSPROJECT_UID', how='right')

    table = sched_conf_ssp.query(
        'CYCLE != "2013.A" and DC_LETTER_GRADE != "C"').sort('RA')[
        ['SB_UID', 'CODE', 'SG_ID', 'sbName', 'band', 'maxPWVC', 'RA', 'execount', 'sbNote',
         'SB_STATE', 'PRJ_STATUS', 'NOTE', 'isTimeConstrained', 'isPolarization',
         'OBSPROJECT_UID']].sort('RA')
    table['RA'] = table.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['RA'] / 15.),
                        int(60. * (ro1['RA'] / 15. - int(ro1['RA'] / 15.)))))
        , axis=1).astype(str).str.slice(0, 5)

    table = pd.merge(
        table,
        datas.obs_param.query('C36_7 == @conf')[['SB_UID', 'rise', 'set']],
        on='SB_UID', how='inner').set_index('SB_UID', drop=False)
    table['rise_lst'] = table.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['rise']),
                        int(60. * (ro1['rise'] - int(ro1['rise'])))))
        , axis=1)
    table['set_lst'] = table.apply(
        lambda ro1: pd.Timestamp.time(
            pd.datetime(2015, 1, 1, int(ro1['set']),
                        int(60. * (ro1['set'] - int(ro1['set'])))))
        , axis=1)
    table['rise_lst'] = table.rise_lst.astype(str).str.slice(0, 5)
    table['set_lst'] = table.set_lst.astype(str).str.slice(0, 5)
    table['range'] = table.rise_lst + '-' + table.set_lst

    h = ephem.Date(ephem.now() - 7.)
    hs = str(h)[:10].replace('/', '-')
    sbs = table.index.unique()
    qastatus = datas.aqua_execblock.query(
        'SB_UID in @sbs').query(
        'QA0STATUS in ["Unset", "Pass"] or ('
        'QA0STATUS == "SemiPass" and STARTTIME > @hs)').groupby(
        ['SB_UID', 'QA0STATUS']).QA0STATUS.count().unstack().fillna(0)

    table_b = pd.merge(
        table, qastatus.reset_index(),
        left_index=True, right_on='SB_UID', how='left').fillna(0)

    try:
        table_b['Observed'] = table_b.Unset + table_b.Pass + table_b.SemiPass
    except:
        table_b['Observed'] = table_b.Unset + table_b.Pass
        table_b['SemiPass'] = 0

    table_b['execount'] = table_b.apply(lambda x: str(int(x['execount'])), axis=1)
    table_b['Unset'] = table_b.apply(lambda x: str(int(x['Unset'])), axis=1)
    table_b['Pass'] = table_b.apply(lambda x: str(int(x['Pass'])), axis=1)
    table_b['SemiPass'] = table_b.apply(lambda x: str(int(x['SemiPass'])), axis=1)
    table_b['Observed'] = table_b.apply(lambda x: str(int(x['Observed'])), axis=1)
    table_b['NOTE'] = None
    table_b['sbNote'] = table_b.sbNote.str.replace('\n', ' ')
    table_b['sbNote'] = table_b.apply(
        lambda x: x['sbNote'] +
        ' <strong style="color: #ff0000">PENDING QA0 Status</strong>'
        if int(x['Unset']) + int(x['SemiPass']) > 0 else x['sbNote'], axis=1)
    table_b['SB_STATE'] = table_b.apply(
        lambda x: color_states(x['SB_STATE'], x['execount'], x['Unset'],
                               x['Pass']), axis=1)
    table_b['isTimeConstrained'] = table_b.apply(
        lambda x: '%Y%' if x['isTimeConstrained'] == True or
        x['isPolarization'] == True else '', axis=1)
    table_b['CODE'] = table_b.apply(
        lambda x: '[[https://asa.alma.cl/protrack/?projectUid=' +
        x['OBSPROJECT_UID'] + '][' + x['CODE'] + ']]', axis=1)
    table_b['PRJ_STATUS'] = table_b.apply(
        lambda x: '!' + x['PRJ_STATUS'], axis=1)
    table_b['sbName'] = table_b.apply(lambda x: '!' + x['sbName'], axis=1)

    table_b = table_b[
        [u'CODE', u'SG_ID', u'sbName', u'band', u'maxPWVC', u'RA', u'range', u'execount', u'Pass',
         u'Unset', u'SemiPass', u'Observed', u'sbNote', u'SB_STATE', u'PRJ_STATUS', u'SB_UID',
         u'isTimeConstrained']]

    table_b.columns = pd.Index(
        [u'Project Code', u'SG Name', u'SB Name', u'Band', u'max. PWV', u'RA', u'LST Range',
         u'Exec. Count', u'Pass Obs.', u'Unset Obs.', u'SemiPass Obs.', u'Total Obs.', u'SB Note',
         u'SB Status', u'Prj. Status', u'SB UID', u'Critical (See instructions)'],
        dtype='object')

    table_b.sort('RA', inplace=True)

    table_fin = pd.DataFrame(columns=table_b.columns)

    for r in table_b.iterrows():
        table_fin = table_fin.append(r[1], ignore_index=True)
        if r[1]['Pass Obs.'] > 0:
            sb_uid = r[1]['SB UID']
            df = datas.aqua_execblock.query(
                'SB_UID == @sb_uid and QA0STATUS == "Pass"')
            for d in df.iterrows():
                rarr = [('^', '^', '^', '^', '^', '^', '^', '^', '^', '^', '^', '^',
                         'EB:' + d[1]['EXECBLOCKUID'] +
                         ' [[https://asa.alma.cl/webaqua?ebuid=' +
                         d[1]['EXECBLOCKUID'] + '][(Aqua)]]' + ' LST: ' +
                         d[1]['LST_START'] + '-' + d[1]['LST_END'],
                         'Pass', '', '', '')]
                row_temp = pd.DataFrame(rarr, columns=table_b.columns)
                table_fin = table_fin.append(row_temp, ignore_index=True)
        if r[1]['Unset Obs.'] > 0:
            sb_uid = r[1]['SB UID']
            df = datas.aqua_execblock.query(
                'SB_UID == @sb_uid and QA0STATUS == "Unset"')
            for d in df.iterrows():
                rarr = [('^', '^', '^', '^', '^', '^', '^', '^', '^', '^', '^', '^',
                         'EB:' + d[1]['EXECBLOCKUID'] +
                         ' [[https://asa.alma.cl/webaqua?ebuid=' +
                         d[1]['EXECBLOCKUID'] + '][(Aqua)]]' + ' LST: ' +
                         d[1]['LST_START'] + '-' + d[1]['LST_END'],
                         'Unset', '', '', '')]
                row_temp = pd.DataFrame(rarr, columns=table_b.columns)
                table_fin = table_fin.append(row_temp, ignore_index=True)
        if r[1]['SemiPass Obs.'] > 0:
            sb_uid = r[1]['SB UID']
            df = datas.aqua_execblock.query(
                'SB_UID == @sb_uid and (QA0STATUS == "SemiPass" and '
                'STARTTIME > @hs)')
            for d in df.iterrows():
                rarr = [('^', '^', '^', '^', '^', '^', '^', '^', '^', '^', '^', '^',
                         'EB:' + d[1]['EXECBLOCKUID'] +
                         ' [[https://asa.alma.cl/webaqua?ebuid=' +
                         d[1]['EXECBLOCKUID'] + '][(Aqua)]]' + ' LST: ' +
                         d[1]['LST_START'] + '-' + d[1]['LST_END'],
                         '!SemiPass', '', '', '')]
                row_temp = pd.DataFrame(rarr, columns=table_b.columns)
                table_fin = table_fin.append(row_temp, ignore_index=True)

    table_fin['SB UID'] = table_fin.apply(
        lambda x: '[[' + x['SB UID'].replace('uid://', '').replace('/', '_') +
        '][' + x['SB UID'] + ']]' if len(x['SB UID']) > 0 else '^', axis=1)
    f = open('twiki.txt', 'w')
    s = tabulate(table_fin.set_index('SB UID'), tablefmt='orgtbl')
    f.write(header + s)
    f.close()


if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option(
        "--conf", type=str, default='c367',
        help="Configuration to check: c368 or c367")
    parser.add_option(
        "--noreload", action='store_false', dest='reload', default=True,
        help="Reload APDM data")

    opts, args = parser.parse_args()
    print "Twiki for %s" % opts.conf
    if opts.conf not in ['c368', 'c367']:
        print("Use either c368 or c367 as input for --conf")
        sys.exit(1)

    datas = Wto.WtoAlgorithm3(path=Wto.home + '/.twiki/',
                              refresh_apdm=opts.reload)
    datas.write_ephem_coords()

    datas.static_param(horizon=30)
    datas.aqua_execblock['LST_START'] = datas.aqua_execblock.apply(
        lambda x: get_lst(x['STARTTIME'], ALMA1), axis=1)
    datas.aqua_execblock['LST_END'] = datas.aqua_execblock.apply(
        lambda x: get_lst(x['ENDTIME'], ALMA1), axis=1)

    if opts.conf == 'c368':
        print_twiki('C36-8')
    elif opts.conf == 'c367':
        print_twiki('C36-7')
    else:
        print("Use --conf=c368 or --conf=c367")
