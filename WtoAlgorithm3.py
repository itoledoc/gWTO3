import numpy as np
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

SSO = ['Moon', 'Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn',
       'Uranus', 'Neptune', 'Pluto']
MOON = ['Ganymede', 'Europa', 'Callisto', 'Io', 'Titan']

ASTEROIDS = {
    'Ceres': '1 Ceres,e,10.5934,80.3293,72.5220,2.767506,0.2140776,0.07582276,'
             '95.9892,12/09.0/2014,2000,H 3.34,0.12',
    'Pallas': '2 Pallas,e,34.8410,173.0962,309.9303,2.771606,0.2136027,'
              '0.23127367,78.2287,12/09.0/2014,2000,H 4.13,0.11',
    'Juno': '3 Juno,e,12.9817,169.8712,248.4100,2.670700,0.2258220,0.25544825,'
            '33.0772,12/09.0/2014,2000,H 5.33,0.32',
    'Vesta': '4 Vesta,e,7.1404,103.8514,151.1984,2.361793,0.2715446,0.08874010,'
             '20.8639,12/09.0/2014,2000,H 3.20,0.32'
}

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

        :type refresh_apdm: bool
        """
        super(WtoAlgorithm3, self).__init__(
            refresh_apdm=refresh_apdm, path=path, allc2=allc2, loadp1=loadp1)

    def sched_db(self):
        pass

    def write_ephem_coords(self):

        self.create_extrainfo()

        ephem_sb = pd.merge(
            self.schedblocks.query('RA == 0 and DEC == 0'),
            self.target_tables.query('isQuery == False'),
            on='SB_UID',
            how='left',
            suffixes=["_sb", "_fs"]).set_index('SB_UID')

        results = ephem_sb.apply(
            lambda x: self.calc_ephem_coords(x['solarSystem'], x['ephemeris']),
            axis=1)

        for r in results.iteritems():
            self.schedblocks.ix[r[0], 'RA'] = r[1][0]
            self.schedblocks.ix[r[0], 'DEC'] = r[1][1]

    @staticmethod
    def calc_ephem_coords(ekind, ephemstring='', alma=ALMA1):

        if ekind == 'Ephemeris':
            try:
                ra, dec, ephe = wtool.read_ephemeris(ephemstring, ALMA1.date)
            except TypeError:
                # print(ephemeris, sourcename)
                ephe = False
            if not ephe:
                # print("Source %s doesn't have ephemeris for current's date" %
                #        ekind)
                return 0., 0., False

        elif ekind in MOON:
            obj = eval('ephem.' + ekind + '()')
            obj.compute(alma)
            ra = np.rad2deg(obj.ra)
            dec = np.rad2deg(obj.dec)
            ephe = True

        elif ekind in ASTEROIDS.keys():
            obj = ephem.readdb(ASTEROIDS[ekind])
            obj.compute(alma)
            ra = np.rad2deg(obj.ra)
            dec = np.rad2deg(obj.dec)
            ephe = True

        elif ekind in SSO:
            obj = eval('ephem.' + ekind + '()')
            obj.compute(alma)
            ra = np.rad2deg(obj.ra)
            dec = np.rad2deg(obj.dec)
            ephe = True

        else:
            # print("What??")
            return 0., 0., False

        # noinspection PyUnboundLocalVariable
        return ra, dec, ephe

    def observable_param(self, horizon=20):

        self.obs_param = self.schedblocks.apply(
            lambda r: wtool.observable(
                r['RA'], r['DEC'], wtool.alma1, r['RA'], r['minAR'],
                r['maxAR'], r['array'], r['SB_UID'], horizon=horizon), axis=1
        )
