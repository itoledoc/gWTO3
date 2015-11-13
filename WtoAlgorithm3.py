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


# noinspection PyAttributeOutsideInit
class WtoAlgorithm3(WtoDatabase3):
    """
    Inherits from WtoDatabase, adds the methods for selection and scoring.
    It also sets the default parameters for these methods: pwv=1.2, date=now,
    array angular resolution, transmission=0.5, minha=-5, maxha=3, etc.

    :return: A WtoAlgorithm instance.
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
        self.reciever = pd.DataFrame(
            [55., 45., 75., 110., 51., 150., 230.],
            columns=['trx'],
            index=['ALMA_RB_06', 'ALMA_RB_03', 'ALMA_RB_07', 'ALMA_RB_09',
                   'ALMA_RB_04', 'ALMA_RB_08', 'ALMA_RB_10'])
        self.reciever['g'] = [0., 0., 0., 1., 0., 0., 1.]
        self._pwv = None
        self._array_res = []
        self._date = ephem.now()
        self._availableobs = False
        self._time_astropy = TIME
        self._ALMA_ephem = ALMA1

    def set_time_now(self):
        self._time_astropy = Time.now()
        self._time_astropy.delta_ut1_utc = 0
        self._time_astropy.location = ALMA
        self._ALMA_ephem.date = ephem.now()

    def write_ephem_coords(self):

        """

        """
        self.create_extrainfo()

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


        # select array kind
        self.selected = self.schedblocks.query('array == @array_kind').copy()

        # select status
        # select Cycle, Letter

        prj_uid_s = self.projects.query(
            'PRJ_STATUS in @prj_status and CYCLE in @cycle and '
            'PRJ_LETTER_GRADE in @letterg').OBSPROJECT_UID.unique()
        sbs_uid_s = self.sb_status.query(
            'SB_STATE in @sb_status').SB_UID.unique()

        self.selected = self.selected.query(
            'OBSPROJECT_UID in @prj_uid_s and SB_UID in @sbs_uid_s').copy()

        # select band
        self.selected = self.selected.query(
            'band in @bands'
        ).copy()

        qastatus = self.aqua_execblock.query(
            'SB_UID in @sbs_uid_s').groupby(
            ['SB_UID', 'QA0STATUS']).QA0STATUS.count().unstack().fillna(0)
        self.selected = pd.merge(
            self.selected, qastatus.reset_index(),
            left_index=True, right_on='SB_UID', how='left'
        ).fillna(0).set_index('SB_UID', drop=False)
        self.selected = pd.merge(self.selected, self.sb_status, on='SB_UID')
        if 'Pass' not in self.selected.columns.values:
            self.selected['Pass'] = 0
        if 'Unset' not in self.selected.columns.values:
            self.selected['Unset'] = 0

        self.selected['Observed'] = self.selected.Unset + self.selected.Pass

        # select still needs observations
        if check_count:
            self.selected = self.selected.query('EXECOUNT > Pass')

        # select array resolution
        self.selected = pd.merge(
            self.selected, self.obs_param, on='SB_UID').set_index('SB_UID',
                                                                  drop=False)
        if conf:
            qstring = ''
            l = len(conf) - 1
            for i, c in enumerate(conf):
                col = c.replace('-', '_')
                if i == l:
                    qstring += '%s == "%s"' % (col, c)
                else:
                    qstring += '%s == "%s" or ' % (col, c)
            self.selected = self.selected.query(qstring)

        # select observable: elev, ha, moon & sun distance
        try:
            c = SkyCoord(
                ra=self.selected.RA*u.degree,
                dec=self.selected.DEC*u.degree,
                location=site, obstime=time)
        except IndexError:
            print("Nothing to observe? %s") % len(self.selected)
            self._availableobs = False
            return

        ha = time.sidereal_time('apparent') - c.ra
        self.selected['HA'] = ha.wrap_at(180*u.degree).value
        self.selected['RAh'] = c.ra.hour
        self.selected['elev'] = c.transform_to(
            AltAz(obstime=time, location=site)).alt.value
        self.selected = self.selected.query(
            'elev >= @elev and (@minha <= HA <= @maxha)').copy()
        self._availableobs = True

        # select transmission

        # calculate frac

        # select frac

