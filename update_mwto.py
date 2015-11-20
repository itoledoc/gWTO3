#!/usr/bin/env python
import os.path
import time

import pandas as pd
from sqlalchemy import create_engine

import WtoAlgorithm3 as Wto

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
datas._query_array()
datas.selector(
    cycle=['2015.1', '2015.A'], minha=-4., maxha=4., letterg=['A', 'B'],
    conf=['C36-7'], calc_blratio=True, pwv=pwv)
datas.master_wto_df.to_sql(
    'master_wto', engine, index_label='SBUID', if_exists='replace')
datas.selection_df['PWV now'] = pwv
datas.selection_df['date'] = str(datas._ALMA_ephem.date)
datas.selection_df.to_sql(
    'selector', engine, index_label='SBUID', if_exists='replace', schema='wto')
datas._cursor.close()
datas._connection.close()