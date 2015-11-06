import pandas as pd
import ephem
import os
import wto3_tools as wtool

from WtoDataBase3 import WtoDatabase3
# from astropy import units as u
# from astropy.coordinates import SkyCoord, EarthLocation, AltAz
# from astropy.time import Time


# noinspection PyUnresolvedReferences
# ALMA = EarthLocation(
#     lat=-23.0262015*u.deg, lon=-67.7551257*u.deg, height=5060*u.m)

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

    def sched_db(self):
        pass

    def write_ephem_coords(self):

        """

        """
        self.create_extrainfo()

        ephem_sb = pd.merge(
            self.schedblocks.query('RA == 0 and DEC == 0'),
            self.target_tables.query('isQuery == False'),
            on='SB_UID',
            how='left',
            suffixes=["_sb", "_fs"]).set_index('SB_UID')

        results = ephem_sb.apply(
            lambda x: wtool.calc_ephem_coords(x['solarSystem'], x['ephemeris']),
            axis=1)

        for r in results.iteritems():
            self.schedblocks.ix[r[0], 'RA'] = r[1][0]
            self.schedblocks.ix[r[0], 'DEC'] = r[1][1]

    def observable_param(self, horizon=20):

        self.obs_param = self.schedblocks.apply(
            lambda r: wtool.observable(
                r['RA'], r['DEC'], wtool.ALMA1, r['RA'], r['minAR'],
                r['maxAR'], r['array'], r['SB_UID'], horizon=horizon), axis=1
        )
