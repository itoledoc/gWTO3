#!/usr/bin/env python
import os.path
import time

import pandas as pd
import WtoAlgorithm3 as Wto
import WtoScorers3 as WtoScor
from sqlalchemy import create_engine
from astropy.utils.data import download_file
from astropy.utils import iers
iers.IERS.iers_table = iers.IERS_A.open(
    download_file(iers.IERS_A_URL, cache=True))

engine = create_engine('postgresql://wto:wto2020@dmg02.sco.alma.cl:5432/aidadb')
refr = False
if time.time() - os.path.getmtime('/users/aod/.mwto/') > 3600.:
    refr = True
try:
    datas = Wto.WtoAlgorithm3(refresh_apdm=refr, path='/users/aod/.mwto/')
except IOError:
    datas = Wto.WtoAlgorithm3(path='/users/aod/.mwto/')
datas.write_ephem_coords()
datas.static_param()
pwv = pd.read_sql('pwv_data', engine).pwv.values[0]
datas.selector(
    cycle=['2015.1', '2015.A'], minha=-4., maxha=4., letterg=['A', 'B'],
    array_id='last', pwv=pwv)
datas.selection_df['PWV now'] = pwv
datas.selection_df['PWV now date'] = (
    pd.read_sql('pwv_data', engine).date.values[0] + ' ' +
    pd.read_sql('pwv_data', engine).time.values[0])
datas.selection_df['date'] = str(datas._ALMA_ephem.date)
datas.selection_df['arrayname'] = datas.bl_arrays.iloc[0, 3]
scorer = datas.master_wto_df.apply(
    lambda x: WtoScor.calc_all_scores(
        1.3, x['maxPWVC'], x['Exec. Frac'], x['sbName'], x['array'], x['ARcor'],
        x['DEC'], x['array_ar_cond'], x['minAR'], x['maxAR'], x['Observed'],
        x['EXECOUNT'], x['PRJ_SCIENTIFIC_RANK'], x['DC_LETTER_GRADE'],
        x['CYCLE'], x['HA']), axis=1)

datas.master_wto_df['allconfs'] = datas.obs_param.apply(
    lambda x: ','.join(
        [str(x['C36_1']), str(x['C36_2']), str(x['C36_3']), str(x['C36_4']),
         str(x['C36_5']), str(x['C36_7']), str(x['C36_8'])]), axis=1)

scorer.to_sql('scorer_wto_test', engine, index_label='SBUID',
              if_exists='replace', schema='wto')
datas.inputs.to_sql('inputs_wto_text', engine, index_label='Cycle',
                    if_exists='replace', schema='wto')
datas.selection_df.to_sql('selection_wto_test', engine, index_label='SBUID',
                          if_exists='replace', schema='wto')
datas.master_wto_df.to_sql('master_wto_test', engine, index_label='SBUID',
                           if_exists='replace', schema='wto')

datas._cursor.close()
datas._connection.close()
