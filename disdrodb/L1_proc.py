#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#-----------------------------------------------------------------------------.
# Copyright (c) 2021-2022 DISDRODB developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-----------------------------------------------------------------------------.

# File content  
# - Functions to convert L0 Apache parquet files to L1 netCDF or Zarr files

#-----------------------------------------------------------------------------.
import logging
import zarr
import numpy as np 
import dask.array as da
import xarray as xr   
from disdrodb.check_standards import check_sensor_name
from disdrodb.check_standards import check_L1_standards
from disdrodb.data_encodings import get_L1_dtype

from disdrodb.standards import get_diameter_bin_center
from disdrodb.standards import get_diameter_bin_lower
from disdrodb.standards import get_diameter_bin_upper
from disdrodb.standards import get_diameter_bin_width
from disdrodb.standards import get_velocity_bin_center
from disdrodb.standards import get_velocity_bin_lower
from disdrodb.standards import get_velocity_bin_upper
from disdrodb.standards import get_velocity_bin_width
from disdrodb.standards import get_raw_field_nbins

logger = logging.getLogger(__name__)

def check_L0_raw_fields_available(df, sensor_name): 
    n_bins_dict = get_raw_field_nbins(sensor_name=sensor_name)
    raw_vars = np.array(list(n_bins_dict.keys()))
    missing_vars = raw_vars[np.isin(raw_vars, list(df.columns), invert=True)]
    if len(missing_vars) > 0: 
        raise ValueError(f"The following L0 raw fields are missing: {missing_vars}")
        
def convert_L0_raw_fields_arr_flags(arr, key):
    # TODO: FieldN and FieldV --> -9.999, has floating number 
    pass
    return arr 
 
def set_raw_fields_arr_dtype(arr, key):
    if key == 'RawData':
        arr = arr.astype(int)
    else:
        arr = arr.astype(float)   
    return arr

def reshape_L0_raw_datamatrix_to_2D(arr, n_bins_dict, n_timesteps):   
    try:
        arr = arr.reshape(n_timesteps,
                      n_bins_dict['FieldN'],
                      n_bins_dict['FieldV'])
    except Exception as e:
        msg = f"It was not possible to reshape RawData matrix to 2D. The error is: \n {e}"
        logger.error(msg)
        print(msg)
        raise ValueError(msg)
    return arr     

def retrieve_L1_raw_data_matrix(df, sensor_name, lazy=True, verbose=False):
    # Log 
    msg = "Retrieval of L1 data matrix started."
    if verbose:
        print(msg)
    logger.info(msg)
    #----------------------------------------------------------.
    # Check L0 raw field availability 
    check_L0_raw_fields_available(df, sensor_name)
    # Retrieve raw fields matrix bins dictionary
    n_bins_dict = get_raw_field_nbins(sensor_name=sensor_name)
    # Retrieve number of timesteps 
    n_timesteps = df.shape[0].compute() 
    # Retrieve arrays                
    dict_data = {}
    for key, n_bins in n_bins_dict.items(): 
        # Parse the string splitting at , 
        df_series = df[key].astype(str).str.split(",")
        # Create array 
        if lazy: 
            arr = da.stack(df_series, axis=0)
        else: 
            arr = np.stack(df_series, axis=0) 
        # Remove '' at the last array position  
        arr = arr[: , 0:n_bins_dict[key]]
        # Deal with flag values (-9.9999)  
        arr = convert_L0_raw_fields_arr_flags(arr, key=key)
        # Set dtype of the matrix 
        arr = set_raw_fields_arr_dtype(arr, key=key)
        # For key='RawData', reshape to 2D matrix 
        if key == "RawData":
            arr = reshape_L0_raw_datamatrix_to_2D(arr, n_bins_dict, n_timesteps)
        # Add array to dictionary 
        dict_data[key] = arr
    # Log 
    msg = "Retrieval of L1 data matrix finished."
    if verbose:
        print(msg)
    logger.info(msg)
    # Return 
    return dict_data       

def get_L1_coords(sensor_name): 
    check_sensor_name(sensor_name=sensor_name)
    coords = {} 
    coords["diameter_bin_center"] = get_diameter_bin_center(sensor_name=sensor_name)
    coords["diameter_bin_lower"] = (["diameter_bin_center"], get_diameter_bin_lower(sensor_name=sensor_name))
    coords["diameter_bin_upper"] = (["diameter_bin_center"], get_diameter_bin_upper(sensor_name=sensor_name))
    coords["diameter_bin_width"] = (["diameter_bin_center"], get_diameter_bin_width(sensor_name=sensor_name))
    coords["velocity_bin_center"] = (["velocity_bin_center"], get_velocity_bin_center(sensor_name=sensor_name))
    coords["velocity_bin_lower"] = (["velocity_bin_center"], get_velocity_bin_lower(sensor_name=sensor_name))
    coords["velocity_bin_upper"] = (["velocity_bin_center"], get_velocity_bin_upper(sensor_name=sensor_name))
    coords["velocity_bin_width"] = (["velocity_bin_center"], get_velocity_bin_width(sensor_name=sensor_name))
    return coords 

def create_L1_dataset_from_L0(df, attrs, lazy=True, verbose=False): 
    # Retrieve sensor name 
    sensor_name = attrs['sensor_name']
    # Retrieve raw data matrices
    dict_data = retrieve_L1_raw_data_matrix(df, sensor_name, lazy=lazy, verbose=verbose)
    # Define raw data matrix variables for xarray Dataset 
    data_vars = {"FieldN": (["time", "diameter_bin_center"], dict_data['FieldN']),
                 "FieldV": (["time", "velocity_bin_center"], dict_data['FieldV']),
                 "RawData": (["time", "diameter_bin_center", "velocity_bin_center"], dict_data['RawData']),
                }
    #-----------------------------------------------------------.
    # TODO: add other standard data variables 
    
    
    
    #-----------------------------------------------------------.
    # Define coordinates for xarray Dataset
    coords = get_L1_coords(sensor_name=sensor_name)
    coords['time'] = df['time'].values
    coords['latitude'] = attrs['latitude']
    coords['longitude'] = attrs['longitude']
    coords['altitude'] = attrs['altitude']
    coords['crs'] = attrs['crs']

    ##-----------------------------------------------------------
    # Create xarray Dataset
    try:
        ds = xr.Dataset(data_vars = data_vars, 
                        coords = coords, 
                        attrs = attrs,
                        )
    except Exception as e:
        msg = f'Error in the creation of L1 xarray Dataset. The error is: \n {e}'
        logger.error(msg)
        print(msg)
        # raise SystemExit
    
    ##-----------------------------------------------------------
    # Check L1 standards 
    check_L1_standards(ds)
    
    ##-----------------------------------------------------------
    # TODO: Replace NA flags
    
    ##-----------------------------------------------------------
    # TODO: Add L1 encoding 
                    
    ##-----------------------------------------------------------
    return ds 
        
####--------------------------------------------------------------------------.
#### Writers 
def write_L1_to_zarr(ds, fpath, sensor_name):
    ds = rechunk_L1_dataset(ds, sensor_name=sensor_name)
    zarr_encoding_dict = get_L1_zarr_encodings_standards(sensor_name=sensor_name)
    ds.to_zarr(fpath, encoding=zarr_encoding_dict, mode = "w")
    return None 

def write_L1_to_netcdf(ds, fpath, sensor_name):
    ds = rechunk_L1_dataset(ds, sensor_name=sensor_name) # very important for fast writing !!!
    nc_encoding_dict = get_L1_nc_encodings_standards(sensor_name=sensor_name)
    ds.to_netcdf(fpath, engine="netcdf4", encoding=nc_encoding_dict)
        
####--------------------------------------------------------------------------.        
#### L1 encodings defaults 
# TODO correct values 
def _get_default_nc_encoding(chunks, dtype='float32'):
    encoding_kwargs = {} 
    encoding_kwargs['dtype']  = dtype
    encoding_kwargs['zlib']  = True
    encoding_kwargs['complevel']  = 4
    encoding_kwargs['shuffle']  = True
    encoding_kwargs['fletcher32']  = False
    encoding_kwargs['contiguous']  = False
    encoding_kwargs['chunksizes']  = chunks
 
    return encoding_kwargs

def _get_default_zarr_encoding(dtype='float32'):
    compressor = zarr.Blosc(cname="zstd", clevel=3, shuffle=2)
    encoding_kwargs = {} 
    encoding_kwargs['dtype']  = dtype
    encoding_kwargs['compressor']  = compressor 
    return encoding_kwargs

def get_L1_nc_encodings_standards(sensor_name): 
    # Define variable names 
    vars = ['FieldN', 'FieldV', 'RawData']   
    # Get chunks based on sensor type
    chunks_dict = get_L1_chunks(sensor_name=sensor_name) 
    dtype_dict = get_L1_dtype()
    # Define encodings dictionary 
    encoding_dict = {} 
    for var in vars:
        encoding_dict[var] = _get_default_nc_encoding(chunks=chunks_dict[var],
                                                      dtype=dtype_dict[var]) # TODO
        # encoding_dict[var]['scale_factor'] = 1.0
        # encoding_dict[var]['add_offset']  = 0.0
        # encoding_dict[var]['_FillValue']  = fill_value
        
    return encoding_dict 
    
def get_L1_zarr_encodings_standards(sensor_name): 
    # Define variable names 
    vars = ['FieldN', 'FieldV', 'RawData']   
    dtype_dict = get_L1_dtype()
    # Define encodings dictionary 
    encoding_dict = {} 
    for var in vars:
        encoding_dict[var] = _get_default_zarr_encoding(dtype=dtype_dict[var]) # TODO        
    return encoding_dict 
####--------------------------------------------------------------------------.
#### L1 chunks defaults               
def get_L1_chunks(sensor_name):
    check_sensor_name(sensor_name=sensor_name)
    if sensor_name == "Parsivel":
        chunks_dict = {'FieldN': (5000,32),
                       'FieldV': (5000,32),
                       'RawData': (5000,32,32),
                      }
    elif sensor_name == "Parsivel2":
        logger.exception(f'Not implemented {sensor_name} device')
        raise NotImplementedError
        
    elif sensor_name == "ThiesLPM":
        logger.exception(f'Not implemented {sensor_name} device')
        raise NotImplementedError
        
    else:
        logger.exception(f'L0 chunks for sensor {sensor_name} are not yet defined')
        raise ValueError(f'L0 chunks for sensor {sensor_name} are not yet defined')
    return chunks_dict

def rechunk_L1_dataset(ds, sensor_name):
    chunks_dict = get_L1_chunks(sensor_name=sensor_name) 
    for var, chunk in chunks_dict.items():
       if chunk is not None: 
           ds[var] = ds[var].chunk(chunk) 
    return ds 

#### L1 Summary statistics 
def create_L1_summary_statistics(ds, processed_dir, station_id, sensor_name):
    # TODO[GG]
    pass 
    return 