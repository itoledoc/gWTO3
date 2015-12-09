import pandas as pd
import ephem
import os
import wto3_tools as wtool
import visibiltyTools as rUV
import datetime as dt

from astropy import units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time

# noinspection PyUnresolvedReferences
ALMA = EarthLocation(
    lat=-23.0262015*u.deg, lon=-67.7551257*u.deg, height=5060*u.m)
TIME = Time.now()
TIME.delta_ut1_utc = 0
TIME.location = ALMA

ALMA1 = ephem.Observer()
ALMA1.lat = '-23.0262015'
ALMA1.long = '-67.7551257'
ALMA1.elev = 5060
ALMA1.horizon = ephem.degrees(str('20'))

home = os.environ['HOME']

RECEIVER = {
    'g': {
        'ALMA_RB_03': 0.0,
        'ALMA_RB_04': 0.0,
        'ALMA_RB_06': 0.0,
        'ALMA_RB_07': 0.0,
        'ALMA_RB_08': 0.0,
        'ALMA_RB_09': 1.0,
        'ALMA_RB_10': 1.0},
    'trx': {
        'ALMA_RB_03': 45.0,
        'ALMA_RB_04': 51.0,
        'ALMA_RB_06': 55.0,
        'ALMA_RB_07': 75.0,
        'ALMA_RB_08': 150.0,
        'ALMA_RB_09': 110.0,
        'ALMA_RB_10': 230.0},
    'mintrans': {
        'ALMA_RB_03': 0.7,
        'ALMA_RB_04': 0.7,
        'ALMA_RB_06': 0.7,
        'ALMA_RB_07': 0.7,
        'ALMA_RB_08': 0.6,
        'ALMA_RB_09': 0.5,
        'ALMA_RB_10': 0.5}
}

CONF_LIM = {
    'minbase': {
        'C36-1': 14.7,
        'C36-2': 14.7,
        'C36-3': 14.7,
        'C36-4': 38.6,
        'C36-5': 47.9,
        'C36-6': 77.3,
        'C36-7': 248.3,
        'C36-8': 346.5
    },
    'maxbase': {
        'C36-1': 160.7,
        'C36-2': 376.9,
        'C36-3': 538.9,
        'C36-4': 969.4,
        'C36-5': 1396.4,
        'C36-6': 2299.6,
        'C36-7': 6074.2,
        'C36-8': 9743.7
    }
}

CONFRES = {
    'C36-1': 3.35,
    'C36-2': 1.8,
    'C36-3': 1.22,
    'C36-4': 0.7,
    'C36-5': 0.49,
    'C36-6': 0.27,
    'C36-7': 0.12,
    'C36-8': 0.075}

CYC_NA = {'2013.A': 34,
          '2013.1': 34,
          '2015.1': 36,
          '2015.A': 36}


# noinspection PyAttributeOutsideInit
class WtoAlgorithm3(object):
    """
    Inherits from WtoDatabase, adds the methods for selection and scoring.
    It also sets the default parameters for these methods: pwv=1.2, date=now,
    array angular resolution, transmission=0.5, minha=-5, maxha=3, etc.

    :return: A WtoAlgorithm instance.

    Should run:
       .update_archive
       .write_ephem
       .static_param
       .selector
       .calc_scores

       (in this order)
    """
    def __init__(self, data):

        """

        """

        self.data = data
        self.tau = pd.read_csv(
            self.data._wto_path + 'conf/tau.csv', sep=',', header=0).set_index(
            'freq')
        self.tsky = pd.read_csv(
            self.data._wto_path + 'conf/tskyR.csv', sep=',',
            header=0).set_index(
                'freq')
        self.pwvdata = pd.read_pickle(
            self.data._wto_path + 'conf/pwvdata2.pandas')  # .set_index('freq')
        # self.pwvdata.index = pd.Float64Index(
        #     pd.np.round(self.pwvdata.index.values, decimals=1), name=u'freq')

        self._pwv = None
        self._array_res = []
        self._date = ephem.now()
        self._availableobs = False
        self._time_astropy = TIME
        self._ALMA_ephem = ALMA1
        self._static_calculated = False
        self.schedblocks = self.data.schedblocks.copy()

    def set_time_now(self):
        """

        """
        self._time_astropy = Time.now()
        self._time_astropy.delta_ut1_utc = 0
        self._time_astropy.location = ALMA
        self._ALMA_ephem.date = ephem.now()

    def set_time(self, time_str):
        """

        :param time_str:
        """
        self._time_astropy = Time(time_str)
        self._time_astropy.delta_ut1_utc = 0
        self._time_astropy.location = ALMA
        self._ALMA_ephem.date = ephem.date(self._time_astropy.iso)

    def write_ephem_coords(self):

        """
        TODO: deal with multiple targets, which RA to take?
        TODO: make this table unique... by instance
        """
        self.schedblocks['ephem'] = 'N/A'

        ephem_sb = pd.merge(
            self.schedblocks,
            self.data.target_tables.query(
                'solarSystem != "Unspecified" and isQuery == False and '
                'RA == 0'),
            on='SB_UID').drop_duplicates(['SB_UID', 'ephemeris']).set_index(
            'SB_UID', drop=False)

        results = ephem_sb.apply(
            lambda x: wtool.calc_ephem_coords(
                x['solarSystem'], x['ephemeris'], x['SB_UID'],
                alma=self._ALMA_ephem),
            axis=1)

        for r in results.iteritems():
            self.schedblocks.ix[r[0], 'RA'] = r[1][0]
            self.schedblocks.ix[r[0], 'DEC'] = r[1][1]
            self.schedblocks.ix[r[0], 'ephem'] = r[1][2]

    def static_param(self, horizon=20):

        """

        :param horizon:
        """
        if self._static_calculated:
            idx = self.data.target_tables.query(
                'solarSystem != "Unspecified" and isQuery == False and '
                'RA == 0').SB_UID.unique()

            self.obs_param.ix[idx] = self.schedblocks.ix[idx].apply(
                lambda r: wtool.observable(
                    r['RA'], r['DEC'], self._ALMA_ephem, r['RA'], r['minAR'],
                    r['maxAR'], r['array'], r['SB_UID'], horizon=horizon),
                axis=1
            )

        else:
            self.obs_param = self.schedblocks.apply(
                lambda r: wtool.observable(
                    r['RA'], r['DEC'], self._ALMA_ephem, r['RA'], r['minAR'],
                    r['maxAR'], r['array'], r['SB_UID'], horizon=horizon),
                axis=1
            )

            ind1 = pd.np.around(self.schedblocks.repfreq, decimals=1)
            ind2 = self.schedblocks.apply(
                lambda x: str(
                    int(x['maxPWVC'] / 0.05) * 0.05 +
                    (0.05 if (x['maxPWVC'] % 0.05) > 0.02 else 0.)),
                axis=1)

            self.schedblocks['transmission_ot'] = self.pwvdata.lookup(
                ind1, ind2)
            self.schedblocks['tau_ot'] = self.tau.lookup(ind1, ind2)
            self.schedblocks['tsky_ot'] = self.tsky.lookup(ind1, ind2)
            self.schedblocks['airmass_ot'] = self.schedblocks.apply(
                lambda x: calc_airmass(x['DEC'], transit=True), axis=1)
            self.schedblocks['tsys_ot'] = (
                self.schedblocks.apply(
                    lambda x: calc_tsys(x['band'], x['tsky_ot'], x['tau_ot'],
                                        x['airmass_ot']), axis=1))

        self.obs_param.rise.fillna(0, inplace=True)
        self.obs_param['rise datetime'] = self.obs_param.apply(
            lambda x:
            dt.datetime.strptime(
                '2015-01-01 ' + str(int(x['rise'])) + ':' +
                str(int(60*(x['rise'] - int(x['rise'])))),
                '%Y-%m-%d %H:%M'),
            axis=1)

        self._static_calculated = True

    def update_apdm(self, obsproject_uid):

        """

        :param obsproject_uid:
        """
        self.data._update_apdm(obsproject_uid)
        self.schedblocks = self.data.schedblocks.copy()
        self._static_calculated = False

    def selector(self,
                 array_kind='TWELVE-M',
                 prj_status=("Ready", "InProgress"),
                 sb_status=("Ready", "Suspended", "Running", "CalibratorCheck",
                            "Waiting"),
                 cycle=("2013.A", "2013.1", "2015.1", "2015.A"),
                 letterg=("A", "B", "C"),
                 bands=("ALMA_RB_03", "ALMA_RB_04", "ALMA_RB_06", "ALMA_RB_07",
                        "ALMA_RB_08", "ALMA_RB_09", "ALMA_RB_10"),
                 check_count=True,
                 conf=None,
                 calc_blratio=False,
                 numant=None,
                 array_id=None,
                 horizon=20.,
                 minha=-3.,
                 maxha=3.,
                 pwv=0.):

        """

        :param array_kind:
        :param prj_status:
        :param sb_status:
        :param cycle:
        :param letterg:
        :param bands:
        :param check_count:
        :param conf:
        :param calc_blratio:
        :param numant:
        :param array_id:
        :param horizon:
        :param minha:
        :param maxha:
        :param pwv:
        :param mintrans:
        :return:
        """
        if float(pwv) > 8:
            pwv = 8.0
        print self._time_astropy

        self._aggregate_dfs()
        self.master_wto_df['array'] = self.master_wto_df.apply(
            lambda x: 'SEVEN-M' if x['array'] == "ACA" else
            x['array'], axis=1
        )
        self.selection_df = self.master_wto_df[['SB_UID']].copy()

        # select array kind

        self.selection_df['selArray'] = (
            self.master_wto_df['array'] == array_kind)

        # select valid Prj States
        self.selection_df['selPrjState'] = (
            self.master_wto_df.apply(
                lambda x: True if x['PRJ_STATUS'] in prj_status else False,
                axis=1))

        # select valid SB States
        self.selection_df['selSBState'] = (
            self.master_wto_df.apply(
                lambda x: True if x['SB_STATE'] in sb_status else False,
                axis=1))

        # select By grades
        self.selection_df['selGrade'] = (
            self.master_wto_df.apply(
                lambda x: True if
                x['CYCLE'] in cycle and x['DC_LETTER_GRADE'] in letterg else
                False, axis=1)
        )

        # select by band
        self.selection_df['selBand'] = (
            self.master_wto_df.apply(
                lambda x: True if x['band'] in bands else False,
                axis=1
            )
        )

        # select if still some observations are left

        self.selection_df['selCount'] = True

        if check_count:
            self.selection_df['selCount'] = (
                self.master_wto_df.EXECOUNT > self.master_wto_df.Observed)

        self.selection_df['selConf'] = True

        # Array Configuraton Selection (12m)

        if array_kind == "TWELVE-M":

            self.master_wto_df['blmax'] = self.master_wto_df.apply(
                lambda row: rUV.compute_bl(row['minAR'] / 0.8, 100.), axis=1)
            self.master_wto_df['blmin'] = self.master_wto_df.apply(
                lambda row: rUV.compute_bl(row['LAScor'], 100., las=True),
                axis=1)

            if conf:
                qstring = ''
                l = len(conf) - 1
                for i, c in enumerate(conf):
                    col = c.replace('-', '_')
                    if i == l:
                        qstring += '%s == "%s"' % (col, c)
                    else:
                        qstring += '%s == "%s" or ' % (col, c)
                sbs_sel = self.master_wto_df.query(qstring).SB_UID.unique()
                self.selection_df['selConf'] = self.selection_df.apply(
                    lambda x: True if x['SB_UID'] in sbs_sel else False,
                    axis=1
                )

                self.master_wto_df['bl_ratio'] = 1.
                self.master_wto_df['array_ar_cond'] = self.master_wto_df.apply(
                    lambda x: CONFRES[x['BestConf']] if x['BestConf'] in conf
                    else pd.np.NaN,
                    axis=1
                )
                self.master_wto_df['num_bl_use'] = 630.

                if calc_blratio:
                    try:
                        array_id = self.bl_arrays.iloc[0, 3]
                    except AttributeError:
                        self._query_array()
                        array_id = self.bl_arrays.iloc[0, 3]
                    array_ar, num_bl, num_ant, ruv = self._get_bl_prop(array_id)
                    self.master_wto_df[['array_ar_cond', 'num_bl_use']] = (
                        self.master_wto_df.apply(
                            lambda x: self._get_sbbased_bl_prop(
                                ruv, x['blmin'] * 0.9, x['blmax'] * 1.1),
                            axis=1)
                    )
                    self.master_wto_df['bl_ratio'] = self.master_wto_df.apply(
                        lambda x: calc_bl_ratio(
                            x['array'], x['CYCLE'], x['num_bl_use'],
                            self.selection_df.ix[x.name, 'selConf']),
                        axis=1
                    )

            else:
                if array_id == 'last':
                    self._query_array()
                    array_id = self.bl_arrays.iloc[0, 3]

                ar, numbl, numant, ruv = self._get_bl_prop(array_id)
                self.master_wto_df[['array_ar_cond', 'num_bl_use']] = (
                    self.master_wto_df.apply(
                        lambda x: self._get_sbbased_bl_prop(
                            ruv, x['blmin'] * 0.9, x['blmax'] * 1.1), axis=1)
                )

                self.selection_df['selConf'] = self.master_wto_df.apply(
                    lambda x: True if (x['array_ar_cond'] > x['minAR']) and
                                      (x['array_ar_cond'] < x['maxAR']) else
                    False, axis=1
                )

                self.master_wto_df['bl_ratio'] = self.master_wto_df.apply(
                    lambda x: calc_bl_ratio(
                        x['array'], x['CYCLE'], x['num_bl_use'],
                        self.selection_df.ix[x.name, 'selConf']),
                    axis=1
                )

        # Array Configuration Selection (7m or ACA)

        elif array_kind == "SEVEN-M":
            if numant is None:
                numant = 10.
            self.selection_df['selConf'] = self.master_wto_df.apply(
                lambda x: True if x['array'] == "SEVEN-M" else
                False, axis=1
            )
            self.master_wto_df['blmax'] = pd.np.NaN
            self.master_wto_df['blmin'] = pd.np.NaN
            self.master_wto_df['array_ar_cond'] = pd.np.NaN
            self.master_wto_df['num_bl_use'] = pd.np.NaN
            self.master_wto_df['bl_ratio'] = self.master_wto_df.apply(
                lambda x: calc_bl_ratio(
                    x['array'], x['CYCLE'], x['num_bl_use'],
                    self.selection_df.ix[x.name, 'selConf'], numant=numant),
                axis=1
            )

        # Array Configuration selection (TP)
        else:
            if numant is None:
                numant = 10.
            self.selection_df['selConf'] = self.master_wto_df.apply(
                lambda x: True if x['array'] == "TP-Array" else
                False, axis=1
            )
            self.master_wto_df['blmax'] = pd.np.NaN
            self.master_wto_df['blmin'] = pd.np.NaN
            self.master_wto_df['array_ar_cond'] = pd.np.NaN
            self.master_wto_df['num_bl_use'] = pd.np.NaN
            self.master_wto_df['bl_ratio'] = 1.

        # select observable: elev, ha, moon & sun distance

        try:
            c = SkyCoord(
                ra=self.master_wto_df.RA*u.degree,
                dec=self.master_wto_df.DEC*u.degree,
                location=ALMA, obstime=self._time_astropy)
        except IndexError:
            print("Nothing to observe? %s" % len(self.master_wto_df))
            self._availableobs = False
            return

        ha = self._time_astropy.sidereal_time('apparent') - c.ra
        self.master_wto_df['HA'] = ha.wrap_at(180*u.degree).value
        self.master_wto_df['RAh'] = c.ra.hour
        self.master_wto_df['elev'] = c.transform_to(
            AltAz(obstime=self._time_astropy, location=ALMA)).alt.value
        corr_el = ((self.master_wto_df.ephem != 'N/A') &
                   (self.master_wto_df.ephem != 'OK'))
        self.master_wto_df.ix[corr_el, 'elev'] = -90.
        self.master_wto_df.ix[corr_el, 'HA'] = -24.

        self.selection_df['selElev'] = (
            self.master_wto_df.elev >= horizon)

        self.selection_df['selHA'] = (
            (self.master_wto_df.HA >= minha) &
            (self.master_wto_df.HA <= maxha)
        )

        # Sel Conditions, exec. frac

        ind1 = pd.np.around(self.master_wto_df.repfreq, decimals=1)

        pwv_str = (str(int(pwv / 0.05) * 0.05 +
                   (0.05 if (pwv % 0.05) > 0.02 else 0.)))

        self.master_wto_df['transmission'] = self.pwvdata.ix[
            ind1, pwv_str].values
        self.master_wto_df['tau'] = self.tau.ix[ind1, pwv_str].values
        self.master_wto_df['tsky'] = self.tsky.ix[ind1, pwv_str].values
        self.master_wto_df['airmass'] = self.master_wto_df.apply(
            lambda x: calc_airmass(x['elev'], transit=False), axis=1)
        self.master_wto_df['tsys'] = (
            self.master_wto_df.apply(
                lambda x: calc_tsys(x['band'], x['tsky'], x['tau'],
                                    x['airmass']), axis=1))
        self.master_wto_df['tsys_ratio'] = self.master_wto_df.apply(
            lambda x: (x['tsys'] / x['tsys_ot'])**2. if x['tsys'] <= 25000. else
            pd.np.inf, axis=1)

        self.master_wto_df['Exec. Frac'] = self.master_wto_df.apply(
            lambda x: 1 / (x['bl_ratio'] * x['tsys_ratio']) if
            (x['bl_ratio'] * x['tsys_ratio']) <= 100. else 0., axis=1)

        self.master_wto_df.set_index('SB_UID', drop=False, inplace=True)
        self.selection_df.set_index('SB_UID', drop=False, inplace=True)

        savedate = ALMA1.date
        savehoriz = ALMA1.horizon
        ALMA1.horizon = 0.0
        lstdate = str(ALMA1.sidereal_time()).split(':')
        lstdate0 = dt.datetime.strptime(
            '2014-12-31 ' + str(lstdate[0]) + ':' +
            str(lstdate[1]), '%Y-%m-%d %H:%M')
        lstdate1 = dt.datetime.strptime(
            '2015-01-01 ' + str(lstdate[0]) + ':' +
            str(lstdate[1]), '%Y-%m-%d %H:%M')
        lstdate2 = dt.datetime.strptime(
            '2015-01-02 ' + str(lstdate[0]) + ':' +
            str(lstdate[1]), '%Y-%m-%d %H:%M')
        sunrisedate = ALMA1.previous_rising(ephem.Sun())
        ALMA1.date = sunrisedate
        sunriselst = str(ALMA1.sidereal_time()).split(':')
        sunriselst_h = dt.datetime.strptime(
            '2015-01-01 ' + str(sunriselst[0]) + ':' +
            str(sunriselst[1]), '%Y-%m-%d %H:%M')
        sunsetdate = ALMA1.next_setting(ephem.Sun())
        ALMA1.date = sunsetdate
        sunsetlst = str(ALMA1.sidereal_time()).split(':')
        sunsetlst_h = dt.datetime.strptime(
            '2015-01-01 ' + str(sunsetlst[0]) + ':' +
            str(sunriselst[1]), '%Y-%m-%d %H:%M')

        self.inputs = pd.DataFrame(
            pd.np.array([lstdate0, lstdate1, lstdate2,
                         sunsetlst_h - dt.timedelta(1), sunriselst_h,
                         sunsetlst_h, sunriselst_h + dt.timedelta(1)]),
            index=['lst0', 'lst1', 'lst2', 'set1', 'rise1', 'set2', 'rise2'],
            columns=['2013.A']).transpose()
        self.inputs.ix['2013.1', :] = self.inputs.ix['2013.A', :]
        self.inputs.ix['2015.A', :] = self.inputs.ix['2013.A', :]
        self.inputs.ix['2015.1', :] = self.inputs.ix['2013.A', :]
        ALMA1.date = savedate
        ALMA1.horizon = savehoriz

    def _aggregate_dfs(self):

        """

        """
        self.master_wto_df = pd.merge(
            self.data.projects.query('phase == "II"')[
                ['OBSPROJECT_UID', 'CYCLE', 'CODE', 'DC_LETTER_GRADE',
                 'PRJ_SCIENTIFIC_RANK', 'PRJ_STATUS']],
            self.data.sciencegoals.query('hasSB == True')[
                ['OBSPROJECT_UID', 'SG_ID', 'OUS_ID', 'ARcor', 'LAScor',
                 'isTimeConstrained', 'isCalSpecial', 'isSpectralScan']],
            on='OBSPROJECT_UID', how='left')

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            self.data.sblocks[
                ['OBSPROJECT_UID', 'OUS_ID', 'GOUS_ID', 'MOUS_ID', 'SB_UID']],
            on=['OBSPROJECT_UID', 'OUS_ID'], how='left')

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            self.schedblocks[
                ['SB_UID', 'sbName', 'array', 'repfreq', 'band', 'RA', 'DEC',
                 'maxPWVC', 'minAR', 'maxAR', 'OT_BestConf', 'BestConf',
                 'two_12m', 'estimatedTime', 'isPolarization', 'ephem',
                 'airmass_ot', 'transmission_ot', 'tau_ot', 'tsky_ot',
                 'tsys_ot']],
            on=['SB_UID'], how='left')

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            self.data.sb_status[['SB_UID', 'SB_STATE', 'EXECOUNT']],
            on=['SB_UID'], how='left')

        # noinspection PyUnusedLocal
        sbs_uid_s = self.master_wto_df.SB_UID.unique()
        h = ephem.Date(ephem.now() - 7.)
        # noinspection PyUnusedLocal
        hs = str(h)[:10].replace('/', '-')
        qastatus = self.data.aqua_execblock.query(
            'SB_UID in @sbs_uid_s').query(
            'QA0STATUS in ["Unset", "Pass"] or '
            '(QA0STATUS == "SemiPass" and STARTTIME > @hs)').groupby(
            ['SB_UID', 'QA0STATUS']).QA0STATUS.count().unstack().fillna(0)

        if 'Pass' not in qastatus.columns.values:
            qastatus['Pass'] = 0
        if 'Unset' not in qastatus.columns.values:
            qastatus['Unset'] = 0
        if 'SemiPass' not in qastatus.columns.values:
            qastatus['SemiPass'] = 0

        qastatus['Observed'] = qastatus.Unset + qastatus.Pass

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            qastatus[
                ['Unset', 'Pass', 'Observed', 'SemiPass']],
            left_on='SB_UID', right_index=True, how='left')
        self.master_wto_df.Unset.fillna(0, inplace=True)
        self.master_wto_df.Pass.fillna(0, inplace=True)
        self.master_wto_df.Observed.fillna(0, inplace=True)
        self.master_wto_df.SemiPass.fillna(0, inplace=True)

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            self.obs_param[
                ['SB_UID', 'rise', 'set', 'note', 'C36_1', 'C36_2', 'C36_3',
                 'C36_4', 'C36_5', 'C36_6', 'C36_7', 'C36_8', 'twelve_good']],
            on=['SB_UID'], how='left')

    def _query_array(self):
        """

        """
        bl = str(
            "select se.SE_TIMESTAMP ts1, sa.SLOG_ATTR_VALUE av1, "
            "se.SE_ARRAYNAME, se.SE_ID se1 from ALMA.SHIFTLOG_ENTRIES se, "
            "ALMA.SLOG_ENTRY_ATTR sa "
            "WHERE se.SE_TYPE=7 and se.SE_TIMESTAMP > SYSDATE - 1/1. "
            "and sa.SLOG_SE_ID = se.SE_ID and sa.SLOG_ATTR_TYPE = 31 "
            "and se.SE_LOCATION='OSF-AOS' and se.SE_CORRELATORTYPE = 'BL'")
        # aca = str(
        #     "select se.SE_TIMESTAMP ts1, sa.SLOG_ATTR_VALUE av1, "
        #     "se.SE_ARRAYNAME, se.SE_ID se1, se.SE_ARRAYFAMILY, "
        #     "se.SE_CORRELATORTYPE from ALMA.SHIFTLOG_ENTRIES se, "
        #     "ALMA.SLOG_ENTRY_ATTR sa "
        #     "WHERE se.SE_TYPE=7 and se.SE_TIMESTAMP > SYSDATE - 1/1. "
        #     "and sa.SLOG_SE_ID = se.SE_ID and sa.SLOG_ATTR_TYPE = 31 "
        #     "and se.SE_LOCATION='OSF-AOS'")
        try:
            self.data._cursor.execute(bl)
            self._bl_arrays_info = pd.DataFrame(
                self.data._cursor.fetchall(),
                columns=[rec[0] for rec in self.data._cursor.description]
            ).sort_values(by='TS1', ascending=False)
        except ValueError:
            self._bl_arrays_info = pd.DataFrame(
                columns=pd.Index(
                    [u'TS1', u'AV1', u'SE_ARRAYNAME', u'SE1'], dtype='object'))
            print("No BL arrays have been created in the last 6 hours.")

        self._group_bl_arrays = self._bl_arrays_info[
            self._bl_arrays_info.AV1.str.startswith('CM') == False].copy()

        self.bl_arrays = self._group_bl_arrays.groupby(
            'TS1').aggregate(
            {'SE_ARRAYNAME': max, 'SE1': max,
             'AV1': pd.np.count_nonzero}).query(
            'AV1 > 30').reset_index().sort_values(by='TS1', ascending=False)

        # get latest pad info

        b = str(
            "select se.SE_TIMESTAMP ts1, se.SE_SUBJECT, "
            "sa.SLOG_ATTR_VALUE av1, se.SE_ID se1, se.SE_SHIFTACTIVITY "
            "from alma.SHIFTLOG_ENTRIES se, alma.SLOG_ENTRY_ATTR sa "
            "WHERE se.SE_TYPE=1 and se.SE_TIMESTAMP > SYSDATE - 2. "
            "and sa.SLOG_SE_ID = se.SE_ID and sa.SLOG_ATTR_TYPE = 12 "
            "and se.SE_LOCATION='OSF-AOS'"
        )

        try:
            self.data._cursor.execute(b)
            self._shifts = pd.DataFrame(
                self.data._cursor.fetchall(),
                columns=[rec[0] for rec in self.data._cursor.description]
            ).sort_values(by='TS1', ascending=False)
        except ValueError:
            self._shifts = pd.DataFrame(
                columns=pd.Index(
                    [u'TS1', u'AV1', u'SE_ARRAYNAME', u'SE1'], dtype='object'))
            print("No shiftlogs have been created in the last 6 hours.")

        last_shift = self._shifts[
            self._shifts.SE1 == self._shifts.iloc[0].SE1].copy()
        last_shift['AV1'] = last_shift.AV1.str.split(':')
        ante = last_shift.apply(lambda x: x['AV1'][0], axis=1)
        pads = last_shift.apply(lambda x: x['AV1'][1], axis=1)
        self._ante_pad = pd.DataFrame({'antenna': ante, 'pad': pads})

    def _get_bl_prop(self, array_name):

        """

        :return:
        :param array_name:
        """
        # In case a bl_array is selected
        if array_name not in CONF_LIM['minbase'].keys():
            id1 = self._bl_arrays_info.query(
                'SE_ARRAYNAME == "%s"' % array_name).iloc[0].SE1
            ap = self._bl_arrays_info.query(
                'SE_ARRAYNAME == "%s" and SE1 == %d' % (array_name, id1)
            )[['AV1']]

            ap.rename(columns={'AV1': 'antenna'}, inplace=True)
            ap = ap[ap.antenna.str.contains('CM') == False]
            conf = pd.merge(ap, self._ante_pad,
                            left_on='antenna', right_on='antenna')[
                ['pad', 'antenna']]
            conf_file = self.data._data_path + '%s.txt' % array_name
            conf.to_csv(conf_file, header=False,
                        index=False, sep=' ')
            ac = rUV.ac.ArrayConfigurationCasaFile()
            ac.createCasaConfig(conf_file)
            ruv = rUV.compute_radialuv(conf_file + ".cfg")
            num_bl = len(ruv)
            num_ant = len(ap)
            array_ar = rUV.compute_array_ar(ruv)

        # If C36 is selected
        else:
            conf_file = (self.data._wto_path +
                         'conf/%s.cfg' % array_name)
            ruv = rUV.compute_radialuv(conf_file)
            # noinspection PyTypeChecker
            array_ar = CONFRES[array_name]
            num_bl = 36 * 35. / 2.
            num_ant = 36

        return array_ar, num_bl, num_ant, ruv

    @staticmethod
    def _get_sbbased_bl_prop(ruv, blmin, blmax):

        """

        :param ruv:
        :param blmin:
        :param blmax:
        :return:
        """
        ruv = ruv[(ruv >= blmin) & (ruv <= blmax)]
        if len(ruv) < 300.:
            return pd.Series(
                [pd.np.NaN, 0],
                index=['array_ar_cond', 'num_bl_use'])
        num_bl = len(ruv)
        array_ar = rUV.compute_array_ar(ruv)

        return pd.Series([array_ar, num_bl],
                         index=['array_ar_cond', 'num_bl_use'])


def calc_bl_ratio(arrayk, cycle, numbl, selconf, numant=None):

    """

    :param arrayk:
    :param cycle:
    :param numbl:
    :param selconf:
    :param numant:
    :return:
    """
    if arrayk == "TWELVE-M" and selconf:
        bl_or = CYC_NA[cycle] * (CYC_NA[cycle] - 1.) / 2.
        try:
            bl_frac = bl_or / numbl
        except ZeroDivisionError:
            bl_frac = pd.np.Inf
        return bl_frac
    elif arrayk in ["ACA", "SEVEN-M"] and selconf:
        return 5 * 9. / (numant * (numant - 1) / 2.)
    elif arrayk in ["TP-Array"] and selconf:
        return 1.
    else:
        return pd.np.Inf


def calc_tsys(band, tsky, tau, airmass):

    """

    :param band:
    :param tsky:
    :param tau:
    :param airmass:
    :return:
    """
    if airmass:

        g = RECEIVER['g'][band]
        trx = RECEIVER['trx'][band]

        tsys = ((1 + g) *
                (trx +
                 tsky * (
                     (1 - pd.np.exp(-1 * airmass * tau)) /
                     (1 - pd.np.exp(-1. * tau))
                 ) * 0.95 + 0.05 * 270.) /
                (0.95 * pd.np.exp(-1 * tau * airmass)))

    else:
        tsys = pd.np.Inf

    return tsys


# noinspection PyTypeChecker
def calc_airmass(dec_el, transit=True):
    """

    :param dec_el:
    :param transit:
    :return:
    """
    if transit:
        airmass = 1 / pd.np.cos(pd.np.radians(-23.0262015 - dec_el))
    else:
        if dec_el > 0:
            airmass = 1 / pd.np.cos(pd.np.radians(90. - dec_el))
        else:
            airmass = None
    return airmass

