import pandas as pd
import ephem
import os
import wto3_tools as wtool

from WtoDataBase3 import WtoDatabase3
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
        'ALMA_RB_10': 230.0}}


# noinspection PyAttributeOutsideInit
class WtoAlgorithm3(WtoDatabase3):
    """
    Inherits from WtoDatabase, adds the methods for selection and scoring.
    It also sets the default parameters for these methods: pwv=1.2, date=now,
    array angular resolution, transmission=0.5, minha=-5, maxha=3, etc.

    :return: A WtoAlgorithm instance.

    Should run:
       .update_archive
       .crea_extrainfo
       .write_ephem
       .observable_param
       .aggregate_dfs
       .selector
       .scorere

       (in this order)
    """
    def __init__(self, refresh_apdm=True, path=None, allc2=False, loadp1=False):

        """

        :type loadp1: bool
        :type allc2: bool
        :type path: str
        :type refresh_apdm: bool
        """
        super(WtoAlgorithm3, self).__init__(
            refresh_apdm=refresh_apdm, path=path, allc2=allc2, loadp1=loadp1)
        self.tau = pd.read_csv(
            self._wto_path + 'conf/tau.csv', sep=',', header=0).set_index(
            'freq')
        self.tsky = pd.read_csv(
            self._wto_path + 'conf/tskyR.csv', sep=',', header=0).set_index(
                'freq')
        self.pwvdata = pd.read_pickle(
            self._wto_path + 'conf/pwvdata.pandas').set_index(
                'freq')
        self.pwvdata.index = pd.Float64Index(
            pd.np.round(self.pwvdata.index.values, decimals=1), name=u'freq')

        self._pwv = None
        self._array_res = []
        self._date = ephem.now()
        self._availableobs = False
        self._time_astropy = TIME
        self._ALMA_ephem = ALMA1

    def aggregate_dfs(self):

        self.master_wto_df = pd.merge(
            self.projects.query('phase == "II"')[
                ['OBSPROJECT_UID', 'CYCLE', 'CODE', 'DC_LETTER_GRADE',
                 'PRJ_SCIENTIFIC_RANK', 'PRJ_STATUS']],
            self.sciencegoals.query('hasSB == True')[
                ['OBSPROJECT_UID', 'SG_ID', 'OUS_ID', 'ARcor', 'LAScor',
                 'isTimeConstrained', 'isCalSpecial', 'isSpectralScan']],
            on='OBSPROJECT_UID', how='left')

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            self.sblocks[
                ['OBSPROJECT_UID', 'OUS_ID', 'GOUS_ID', 'MOUS_ID', 'SB_UID']],
            on=['OBSPROJECT_UID', 'OUS_ID'], how='left')

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            self.schedblocks[
                ['SB_UID', 'sbName', 'array', 'repfreq', 'band', 'RA', 'DEC',
                 'maxPWVC', 'minAR', 'maxAR', 'BestConf', 'two_12m',
                 'estimatedTime', 'isPolarization', 'ephem']],
            on=['SB_UID'], how='left')

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            self.sb_status[['SB_UID', 'SB_STATE', 'EXECOUNT']],
            on=['SB_UID'], how='left')

        sbs_uid_s = self.master_wto_df.SB_UID.unique()

        qastatus = self.aqua_execblock.query(
            'SB_UID in @sbs_uid_s').groupby(
            ['SB_UID', 'QA0STATUS']).QA0STATUS.count().unstack().fillna(0)

        if 'Pass' not in qastatus.columns.values:
            qastatus['Pass'] = 0
        if 'Unset' not in qastatus.columns.values:
            qastatus['Unset'] = 0

        qastatus['Observed'] = qastatus.Unset + qastatus.Pass

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            qastatus[
                ['Unset', 'Pass', 'Observed']],
            left_on='SB_UID', right_index=True, how='left')
        self.master_wto_df.Unset.fillna(0, inplace=True)
        self.master_wto_df.Pass.fillna(0, inplace=True)
        self.master_wto_df.Observed.fillna(0, inplace=True)

        self.master_wto_df = pd.merge(
            self.master_wto_df,
            self.obs_param[
                ['SB_UID', 'rise', 'set', 'note', 'C36_1', 'C36_2', 'C36_3',
                 'C36_4', 'C36_5', 'C36_6', 'C36_7', 'C36_8', 'twelve_good']],
            on=['SB_UID'], how='left')

    def set_time_now(self):
        self._time_astropy = Time.now()
        self._time_astropy.delta_ut1_utc = 0
        self._time_astropy.location = ALMA
        self._ALMA_ephem.date = ephem.now()

    def write_ephem_coords(self):

        """

        """
        self.schedblocks['ephem'] = 'N/A'

        ephem_sb = pd.merge(
            self.schedblocks.query('RA == 0 and DEC == 0'),
            self.target_tables.query('isQuery == False'),
            on='SB_UID',
            how='left',
            suffixes=["_sb", "_fs"]).set_index('SB_UID', drop=False)

        results = ephem_sb.apply(
            lambda x: wtool.calc_ephem_coords(
                x['solarSystem'], x['ephemeris'], x['SB_UID'],
                alma=self._ALMA_ephem),
            axis=1)

        for r in results.iteritems():
            self.schedblocks.ix[r[0], 'RA'] = r[1][0]
            self.schedblocks.ix[r[0], 'DEC'] = r[1][1]
            self.schedblocks.ix[r[0], 'ephem'] = r[1][2]

    def observable_param(self, horizon=20):

        self.obs_param = self.schedblocks.apply(
            lambda r: wtool.observable(
                r['RA'], r['DEC'], self._ALMA_ephem, r['RA'], r['minAR'],
                r['maxAR'], r['array'], r['SB_UID'], horizon=horizon), axis=1
        )

    def selector(self, array_kind='TWELVE-M',
                 prj_status=("Ready", "InProgress"),
                 sb_status=("Ready", "Suspended", "Running", "CalibratorCheck",
                            "Waiting"),
                 cycle=("2013.A", "2013.1", "2015.1", "2015.A"),
                 letterg=("A", "B", "C"),
                 bands=("ALMA_RB_03", "ALMA_RB_04", "ALMA_RB_06", "ALMA_RB_07",
                        "ALMA_RB_08", "ALMA_RB_09", "ALMA_RB_10"),
                 pads=(), elev=20., minha=-3., maxha=3., site=ALMA, time=None,
                 min_trans=(0.7, 0.5), pwv=0, conf=None, check_count=True):

        if time:
            pass
        time = self._time_astropy
        print time
        self.aggregate_dfs()

        # select array kind
        self.selection_df = self.master_wto_df[['SB_UID']].copy()

        self.selection_df['selArray'] = (
            self.master_wto_df['array'] == array_kind)
        self.selection_df['selPrjState'] = (
            self.master_wto_df.apply(
                lambda x: True if x['PRJ_STATUS'] in prj_status else False,
                axis=1))
        self.selection_df['selSBState'] = (
            self.master_wto_df.apply(
                lambda x: True if x['SB_STATE'] in sb_status else False,
                axis=1))
        self.selection_df['selCount'] = True

        self.selection_df['selPrj'] = (
            self.master_wto_df.apply(
                lambda x: True if
                x['CYCLE'] in cycle and x['DC_LETTER_GRADE'] in letterg else
                False, axis=1)
        )

        self.selection_df['selBand'] = (
            self.master_wto_df.apply(
                lambda x: True if x['band'] in bands else False,
                axis=1
            )
        )

        if check_count:
            self.selection_df['selCount'] = (
                self.master_wto_df.EXECOUNT > self.master_wto_df.Observed)

        self.selection_df['selConf'] = False
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

        # select observable: elev, ha, moon & sun distance

        try:
            c = SkyCoord(
                ra=self.master_wto_df.RA*u.degree,
                dec=self.master_wto_df.DEC*u.degree,
                location=site, obstime=time)
        except IndexError:
            print("Nothing to observe? %s" % len(self.master_wto_df))
            self._availableobs = False
            return

        ha = time.sidereal_time('apparent') - c.ra
        self.master_wto_df['HA'] = ha.wrap_at(180*u.degree).value
        self.master_wto_df['RAh'] = c.ra.hour
        self.master_wto_df['elev'] = c.transform_to(
            AltAz(obstime=time, location=site)).alt.value
        corr_el = ((self.master_wto_df.ephem != 'N/A') &
             (self.master_wto_df.ephem != 'True'))
        self.master_wto_df.ix[corr_el, 'elev'] = -90.
        self.master_wto_df.ix[corr_el, 'HA'] = -24.

        self.selection_df['selElev'] = (
            self.master_wto_df.elev >= elev)

        self.selection_df['selHA'] = (
            (self.master_wto_df.HA >= minha) &
            (self.master_wto_df.HA <= maxha)
        )

        ind1 = pd.np.around(self.master_wto_df.repfreq, decimals=1)
        ind2 = self.master_wto_df.apply(
            lambda x: str(
                int(x['maxPWVC'] / 0.05) * 0.05 +
                (0.05 if (x['maxPWVC'] % 0.05) > 0.02 else 0.)),
            axis=1)

        pwv_str = (str(int(pwv / 0.05) * 0.05 +
                   (0.05 if (pwv % 0.05) > 0.02 else 0.)))

        self.master_wto_df['transmission_org'] = self.pwvdata.lookup(
            ind1, ind2)
        self.master_wto_df['tau_org'] = self.tau.lookup(ind1, ind2)
        self.master_wto_df['tsky_org'] = self.tsky.lookup(ind1, ind2)
        self.master_wto_df['airmass_org'] = calc_airmass(
            self.master_wto_df.DEC, transit=True)

        self.master_wto_df['transmission'] = self.pwvdata.ix[
            ind1, pwv_str].values
        self.master_wto_df['tau'] = self.tau.ix[ind1, pwv_str].values
        self.master_wto_df['tsky'] = self.tsky.ix[ind1, pwv_str].values
        self.master_wto_df['airmass'] = calc_airmass(
            self.master_wto_df.elev, transit=False)

        self.master_wto_df['tsys_org'] = (
            self.master_wto_df.apply(
                lambda x: calc_tsys(x['band'], x['tsky_org'], x['tau_org'],
                                    x['airmass_org']), axis=1))

        self.master_wto_df['tsys'] = (
            self.master_wto_df.apply(
                lambda x: calc_tsys(x['band'], x['tsky'], x['tau'],
                                    x['airmass']), axis=1))

        self.master_wto_df['tsysfrac'] = (
            self.master_wto_df.tsys / self.master_wto_df.tsys_org)**2

        # select transmission

        # calculate frac

        # select frac


def calc_tsys(band, tsky, tau, airmass):

    g = RECEIVER['g'][band]
    trx = RECEIVER['trx'][band]

    tsys = ((1 + g) *
            (trx +
             tsky * (
                 (1 - pd.np.exp(-1 * airmass * tau)) /
                 (1 - pd.np.exp(-1. * tau))
             ) * 0.95 + 0.05 * 270.) /
            (0.95 * pd.np.exp(-1 * tau * airmass)))

    return tsys


def calc_airmass(dec_el, transit=True):
    if transit:
        airmass = 1 / pd.np.cos(pd.np.radians(-23.0262015 - dec_el))
    else:
        airmass = 1 / pd.np.cos(pd.np.radians(90. - dec_el))
    return airmass
