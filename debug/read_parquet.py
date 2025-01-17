#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 10 11:41:47 2021

@author: kimbo
"""

import os
os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir))
import pandas as pd
import dask.dataframe as dd
import os
import numpy as np
# from disdrodb.io import col_dtype_check

# /SharedVM/Campagne/GPM/processed/MC3E/L0/MC3E_sapu01.parquet

campagna = 'PAYERNE_2014'
path = f"/SharedVM/Campagne/EPFL/Processed/{campagna}/L0"
file = campagna + '_s10.parquet'
file_path = os.path.join(path, file)

file_path = '/SharedVM/Campagne/EPFL/Processed/PLATO_2019/L0/PLATO_2019_s10.parquet'

df = dd.read_parquet(file_path)

df = df.compute()
print(df)

campagna = 'HPICONET_2010'
device = 's12'
path = f"/SharedVM/Campagne/EPFL/Processed/{campagna}/L0"
file = campagna + '_' + device + '.parquet'
parquet_path = os.path.join(path, file)
# file_path = '/SharedVM/Campagne/DELFT/Processed/TEST_DATA/L0/TEST_DATA_s10.parquet'

df2 = dd.read_parquet(parquet_path)

df2 = df2.compute()



# df = df.iloc[0:100,:] # df.head(100) 
# np_arr_str =  df['raw_drop_number'].values.astype(str)
# list_arr_str = np.char.split(np_arr_str,",")
# print(len(list_arr_str[0]))

# df2 = df2.iloc[0:100,:] # df.head(100) 
# np_arr_str2 =  df2['raw_drop_number'].values.astype(str)
# list_arr_str2 =  np.char.split(np_arr_str2,",")
# print(len(list_arr_str2[0]))


# col_dtype_check(df, path, verbose=True)
