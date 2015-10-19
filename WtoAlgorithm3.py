import numpy as np
import pandas as pd
import ephem
import wto3_tools as wtool

from astropy import units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from WtoDataBase3 import Database

# noinspection PyUnresolvedReferences
ALMA = EarthLocation(
    lat=-23.0262015*u.deg, lon=-67.7551257*u.deg, height=5060*u.m)


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

    def add_sbinfo(self):

        scitar = pd.merge(
            self.orderedtar.query('name != "Calibrators"'),
            self.target, on=['SB_UID', 'targetId'])
        scitar2 = pd.merge(
            scitar, self.scienceparam, on=['SB_UID', 'paramRef'])

        self.scitar2 = pd.merge(
            scitar2, self.fieldsource[
                ['SB_UID', 'fieldRef', 'name', 'RA', 'DEC', 'isQuery', 'use',
                 'solarSystem', 'isMosaic', 'pointings', 'ephemeris']
            ], on=['SB_UID', 'fieldRef'],
            suffixes=['_target', '_so'])

        sb_target_num = self.scitar2.groupby('SB_UID').agg(
            {'fieldRef': pd.Series.nunique, 'pointings': pd.Series.max,
             'targetId': pd.Series.nunique, 'paramRef': pd.Series.nunique,
             'specRef': pd.Series.nunique}).reset_index()
        self.multi_point_su = sb_target_num.query(
            'pointings > 1').SB_UID.unique()
        self.multi_field_su = sb_target_num.query(
            'fieldRef > 1').SB_UID.unique()
        self.ephem_su = self.scitar2.query(
            'solarSystem != "Unspecified"').SB_UID.unique()

    def observable_param(self):

        self.obs_param = self.schedblocks.apply(
            lambda r: wtool.observable(
                r['RA'], r['DEC'], wtool.alma1, r['RA'], r['minAR'],
                r['maxAR'], r['array'], r['SB_UID']), axis=1
        )
