# Krista Longnecker, 13 July 2025
# Run this after running getBCODMOinfo.ipynb
# This script will convert the BCO-DMO json file into the format required by CMAP
# Work on the input for one file, with the end result as one Excel file; will only end up here if the data 
# file is a CSV file
# This script works on the discrete data file (the first one I wrote)

#some of these are residual from assembling the data file, keep for now.
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
            #actually want the descrption, so return that
            description = item['bcodmo:description']
            units = item['bcodmo:units']

    return description, units

#set up a function to remove <p> and </p> from the beginning and end, occurs multiple times
def clean(a):
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
    #idx_json = 1
    
    biosscope = Package('datapackage.json')
    data_url = biosscope.resources[idx_json].path
    md = biosscope.resources[idx_json].custom['bcodmo:parameters'] #this is a list, don't forget 'custom' (!!)
    
    #make a short name out of the data_url, will use this as part of the name for the final Excel file 
    exportFile = re.split('/',data_url).pop().replace('.csv','')
    
    #super easy to work with the CSV file once I have the URL
    bcodmo = pd.read_csv(data_url,na_values = ['nd']) #now I have NaN...but they get dropped when writing the file
    
    # Required variables are time, lat, lon, depth
    df = pd.DataFrame(columns=['time','lat','lon','depth'])
    
    # time --> CMAP requirement is this: #< Format  %Y-%m-%dT%H:%M:%S,  Time-Zone:  UTC,  example: 2014-02-28T14:25:55 >
    # Do this in two steps so I can check the output more easily
    temp = bcodmo.copy()

    #In the TOS data, time is labeled differently from other datasets :( 
    if exportFile == 'TOS':
        useDate = 'date_utc_YYYYMMDD_start'
        useTime = 'time_utc_HHMM_start'
        useDepth = 'depth_m'
    else:
        useDate = 'date_start_utc'
        useTime = 'time_start_utc'
        useDepth = 'depth'
        
    temp['date'] = pd.to_datetime(temp[useDate].apply(str) + ' ' + temp[useTime].apply(str).str.zfill(4), format="%Y%m%d %H%M")
    temp['date_cmap'] = temp['date'].dt.strftime("%Y-%m-%dT%H:%M:%S")
    df['time'] = temp['date_cmap']
    
    # lat (-90 to 90) and lon (-180 to 180); use variable names at BCO-DMO
    df['lat'] = bcodmo['lat_start']
    df['lon'] = bcodmo['lon_start']  #BCO-DMO already has this as negative
    df['depth'] = bcodmo[useDepth]
    
    # all remaining columns in bcodmo can be considered data
    #remember: bcodmo_trim will have the list of variables that I will use later to get metadata about the variables
    bcodmo_trim = bcodmo.drop(columns=['lat_start', 'lon_start', useDepth])
    nVariables = bcodmo_trim.shape[1] #remember in Python indexing starts with 0 (rows, 1 is the columns)
    # and then add to the datafile I am assembling (essentially re-order columns
    df = pd.concat([df, bcodmo_trim], axis=1)
       
    # work on the second sheet: metadata about the variables; use the CMAP dataset template to setup the dataframe so I get the column headers right
    templateName = 'datasetTemplate.xlsx'
    sheet_name = 'vars_meta_data'
    vars = pd.read_excel(templateName, sheet_name=sheet_name)
    metaVarColumns = vars.columns.tolist()
    #df2 will be the dataframe with the metadata about the variables, set it up empty here
    df2 = pd.DataFrame(columns=metaVarColumns,index = pd.RangeIndex(start=0,stop=nVariables)) #remember, Python is 0 indexed
    
    #the variables I need to search for are here: bcodmo_trim.columns, put them in the first column
    df2['var_short_name'] = bcodmo_trim.columns
    #Need the information from BCO-DMO to fill in the metadata about the variables.
    #md = biosscope.resources[idx].custom['bcodmo:parameters'] #this is a list, don't forget 'custom' (!!)
        
    #there is most certainly a better way to do this, but I understand this option
    for idx,item in enumerate(df2.iterrows()):
        a,b = getDetails(md,df2.loc[idx,'var_short_name']) #getDetails is the function I wrote (see above)
        df2.loc[idx,'var_long_name'] = clean(a)
        df2.loc[idx,'var_unit'] = b
    
    LUsensors = {'Alpkem RFA300':['NO3_NO2','silicate','NO2','PO4','NH4'],
                 'Shimadzu TOC-V':['NPOC','TN']
                    }
    
    #setup the column so Python does not make a column for floats
    df['var_sensor'] = ""
    
    # this will return the sensor given a possible variable, surely there is a better way to do this...
    for idx,item in enumerate(df2.iterrows()):
        oneVar = df2.loc[idx,'var_short_name']
        sensor =  str([k for k, v in LUsensors.items() if oneVar in v])[2:-2]
        if len(sensor): #only try and fill in if a sensor was found
            df2.loc[idx,'var_sensor'] = str(sensor)
            
    #there are a few pieces of metadata that CMAP wants that will be easier to track in an Excel file. Right now this means I run through 
    # this twice. Annoying, but haven't figured out a better way (yet).
    #The keywords include cruises, and all possible names for a variable.
    fName = 'CMAP_variableMetadata_additions.xlsx'
    sheetName = exportFile[0:31] #Excel limits the length of the sheet name
    moreMD = pd.read_excel(fName,sheet_name = sheetName)
    
    #suffixes are added to column name to keep them separate; '' adds nothing while '_td' adds _td that can get deleted next
    df2 = moreMD.merge(df2[['var_short_name','var_long_name','var_sensor','var_unit']],on='var_short_name',how='left',suffixes=('_td', '',))
    
    # Discard the columns that acquired a suffix:
    df2 = df2[[c for c in df2.columns if not c.endswith('_td')]]
    
    df2 = df2.loc[:,metaVarColumns]
    #these two are easy: just add them here
    df2.loc[:,('var_spatial_res')] = 'irregular'
    df2.loc[:, ('var_temporal_res')] = 'irregular'
    
    #metadata about the project    
    #stuck some variables in the Excel file and can pull them from here
    varProject = pd.read_excel(fName,sheet_name = 'project')
    one = varProject.loc[varProject['name'] == sheetName]
    # finally gather up the dataset_meta_data: for now I just wrote the information here, I might setup in a separate text file later
    #pdb.set_trace()
    df3 = pd.DataFrame({
        'dataset_short_name': ['DeepDOM_v1'],
        'dataset_long_name': ['DeepDOM ' + exportFile],
        'dataset_version': ['1.0'],
        'dataset_release_date': [date.today()],
        'dataset_make': ['observation'],
        'dataset_source': [one.loc[:,'dataset_source'].values[0]],
        'dataset_distributor': [one.loc[:,'dataset_distributor'].values[0]],
        'dataset_acknowledgement': [one.loc[:,'dataset_acknowledgement'].values[0]],
        'dataset_history': [''],
        'dataset_description': [biosscope.resources[idx_json].sources[0]['title']],
        'dataset_references': [one.loc[:,'dataset_references'].values[0]],
        'climatology': [0],
        'cruise_names': 'KN210-04'
        })
    
    
    #export the result as an Excel file with three tabs
    #make the data folder if it is not already there (it is in .gitignore, so it will not end up at GitHub)
    folder = "data"
    os.chdir(".")
    
    if os.path.isdir(folder):
        print("Data will go here: %s" % (os.getcwd()) + '\\' + folder + '\\' + exportFile)
    else:
        os.mkdir(folder)
    
    fName_CMAP = 'data/' + 'DeepDOM_BCODMO_' + exportFile + '.xlsx' 
    dataset_names = {'data': df, 'dataset_meta_data': df3, 'vars_meta_data': df2}
    with pd.ExcelWriter(fName_CMAP) as writer:
        for sheet_name, data in dataset_names.items():
            data.to_excel(writer, sheet_name=sheet_name, index=False)



#######################################
#                                     #
#                                     #
#                 main                #
#                                     #
#                                     #
#######################################

if __name__ == "__main__":    
    main()    
