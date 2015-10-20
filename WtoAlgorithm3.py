import numpy as np
import pandas as pd
import ephem
import wto3_tools as wtool

# from astropy import units as u
# from astropy.coordinates import SkyCoord, EarthLocation, AltAz
# from astropy.time import Time
from WtoDataBase3 import Database

# noinspection PyUnresolvedReferences
# ALMA = EarthLocation(
#     lat=-23.0262015*u.deg, lon=-67.7551257*u.deg, height=5060*u.m)

SSO = ['Moon', 'Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn',
       'Uranus', 'Neptune', 'Pluto']
MOON = ['Ganymede', 'Europa', 'Callisto', 'Io', 'Titan']

ALMA1 = ephem.Observer()
ALMA1.lat = '-23.0262015'
ALMA1.long = '-67.7551257'
ALMA1.elev = 5060
ALMA1.horizon = ephem.degrees(str('20'))


# noinspection PyAttributeOutsideInit
class WtoAlgorithm3(Database):
    """
    Inherits from WtoDatabase, adds the methods for selection and scoring.
    It also sets the default parameters for these methods: pwv=1.2, date=now,
    array angular resolution, transmission=0.5, minha=-5, maxha=3, etc.

    :return: A WtoAlgorithm instance.
    """
    def __init__(self, refresh_apdm=True):

        super(WtoAlgorithm3, self).__init__(refresh_apdm)

    def sched_db(self):
        pass

    def ephem_coords(self):

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
            print r
            self.schedblocks.ix[r[0], 'RA'] = r[1][0]
            self.schedblocks.ix[r[0], 'DEC'] = r[1][1]

    @staticmethod
    def calc_ephem_coords(ekind, ephemstring='', alma=ALMA1):

        if ekind in SSO:
            obj = eval('ephem.' + ekind + '()')
            obj.compute(alma)
            ra = np.rad2deg(obj.ra)
            dec = np.rad2deg(obj.dec)
            ephe = True

        elif ekind in MOON:
            obj = eval('ephem.' + ekind + '()')
            obj.compute(alma)
            ra = np.rad2deg(obj.ra)
            dec = np.rad2deg(obj.dec)
            ephe = True

        elif ekind == 'Ephemeris':
            try:
                ra, dec, ephe = wtool.read_ephemeris(ephemstring, ALMA1.date)
            except TypeError:
                # print(ephemeris, sourcename)
                ephe = False
            if not ephe:
                # print("Source %s doesn't have ephemeris for current's date" %
                #        ekind)
                return 0., 0., False

        else:
            # print("What??")
            return 0., 0., False

        return ra, dec, ephe

    def observable_param(self):

        self.obs_param = self.schedblocks.apply(
            lambda r: wtool.observable(
                r['RA'], r['DEC'], wtool.alma1, r['RA'], r['minAR'],
                r['maxAR'], r['array'], r['SB_UID']), axis=1
        )
