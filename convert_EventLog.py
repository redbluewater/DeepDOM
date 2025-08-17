"""
Krista Longnecker, 21 July 2025
Updated 7 August 2025 to get time format right and add sensor information for everything
Run this after running getBCODMOinfo.ipynb
This script will convert the BCO-DMO json file into the format required by CMAP, and works on one file at a time.

"""

import pandas as pd
import requests
import os
import json
import re
import sys
import pdb
from datetime import date
from frictionless import describe, Package

# Make a function that searches for bcodmo:name and returns bcodmo:description and bcodmo:units
# input: md --> the list of parameters for one dataset
def getDetails(md,bcodmo_name):
    """
    Take the list of information from BCO-DMO, search for a name, and return the description and units for that name
    """
    for i, item in enumerate(md):
        if item['bcodmo:name'] == bcodmo_name:
            description = item['bcodmo:description']
            units = item['bcodmo:units']

    return description, units

#set up a function to remove <p> and </p> from the beginning and end, occurs multiple times
def clean(a):
    """Some of the descriptions have added markers, remove them using this function"""
    if a.startswith('<p>'):
        toStrip = '[</p><p>]'
        clean = re.sub(toStrip,'',a)
    elif a.endswith('.'):
        clean = re.sub('\.$','',a)
    else:
        clean = a
    
    return clean

def main():
    '''
    Go through the steps needed to go from BCO-DMO details in json file and end with output that is an Excel file
    '''
    idx_json = int(sys.argv[1])
    
    biosscope = Package('datapackage.json')
    data_url = biosscope.resources[idx_json].path
    md = biosscope.resources[idx_json].custom['bcodmo:parameters'] #this is a list, don't forget 'custom' (!!)
    
    #make a short name out of the data_url, will use this as part of the name for the final Excel file 
    exportFile = re.split('/',data_url).pop().replace('.csv','')
    
    #super easy to work with the CSV file once I have the URL
    bcodmo = pd.read_csv(data_url,na_values = ['nd']) #now I have NaN...but they get dropped when writing the file
    temp = bcodmo.copy()
    
    # need different options from event log
    df = pd.DataFrame(columns=['time','lat','lon','instrument','action','station','cast'])

    useDate = 'date_utc'
    useTime = 'time_utc'

    temp['date'] = pd.to_datetime(temp[useDate].apply(str) + ' ' + temp[useTime].apply(str).str.zfill(4), format="%Y%m%d %H%M")
    temp['date_cmap'] = temp['date'].dt.strftime("%Y-%m-%dT%H:%M:%S" + "+00:00") #update to add 0 offset from UTC
    df['time'] = temp['date_cmap']

    # lat (-90 to 90) and lon (-180 to 180); 
    df['lat'] = bcodmo['lat']
    df['lon'] = bcodmo['lon']  #BCO-DMO already has this as negative
    df['instrument'] = bcodmo['instrument']
    df['action'] = bcodmo['action']
    df['station'] = bcodmo['station']
    df['cast'] = bcodmo['cast']

    #just using the event log for Winn's data, so only need CTD data and 
    eventLog = df[(df['instrument'] == 'CTD911') & (df['action']=='deploy')]
    
    return eventLog
    

#######################################
#                                     #
#                                     #
#                 main                #
#                                     #
#                                     #
#######################################

if __name__ == "__main__":    
    main()    
