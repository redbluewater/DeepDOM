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
    
    # Required variables are time, lat, lon, depth
    df = pd.DataFrame(columns=['time','lat','lon','depth'])
    
    #In the TOS data, multiple variables have different labels :( 
    if exportFile == 'TOS':
        useDate = 'date_utc_YYYYMMDD_start'
        useTime = 'time_utc_HHMM_start'
        useDepth = 'depth_m'
    else:
        useDate = 'date_start_utc'
        useTime = 'time_start_utc'
        useDepth = 'depth'
        
    temp['date'] = pd.to_datetime(temp[useDate].apply(str) + ' ' + temp[useTime].apply(str).str.zfill(4), format="%Y%m%d %H%M")
    temp['date_cmap'] = temp['date'].dt.strftime("%Y-%m-%dT%H:%M:%S" + "+00:00") #update to add 0 offset from UTC
    df['time'] = temp['date_cmap']
    
    # lat (-90 to 90) and lon (-180 to 180); 
    df['lat'] = bcodmo['lat_start']
    df['lon'] = bcodmo['lon_start']  #BCO-DMO already has this as negative
    df['depth'] = bcodmo[useDepth]
    
    # all remaining columns in bcodmo can be considered data
    #remember: bcodmo_trim has the list of variables that I will use later to get metadata about the variables
    bcodmo_trim = bcodmo.drop(columns=['lat_start', 'lon_start', useDepth])
    nVariables = bcodmo_trim.shape[1] #remember in Python indexing starts with 0 (rows, 1 is the columns)
    # and then add to the datafile I am assembling
    df = pd.concat([df, bcodmo_trim], axis=1)
       
    # work on the second sheet: metadata about the variables; 
    # use the CMAP dataset template to setup the dataframe so I get the column headers right
    templateName = 'datasetTemplate.xlsx'
    sheet_name = 'vars_meta_data'
    vars = pd.read_excel(templateName, sheet_name=sheet_name)
    metaVarColumns = vars.columns.tolist()
    #df2 will be the dataframe with the metadata about the variables, set it up empty here
    df2 = pd.DataFrame(columns=metaVarColumns,index = pd.RangeIndex(start=0,stop=nVariables)) #remember, Python is 0 indexed
    
    #the variables I need to search for are here: bcodmo_trim.columns, put them in the first column
    df2['var_short_name'] = bcodmo_trim.columns
        
    #there is most certainly a better way to do this, but I understand this option
    for idx,item in enumerate(df2.iterrows()):
        a,b = getDetails(md,df2.loc[idx,'var_short_name']) #getDetails is the function I wrote (see above)
        # var_unit has to be 50 characters or less...for now this only happens 1x, so manually edit
        if b == 'microEinsteins per square meter per second (μE/m2-sec)':
            b = 'microEinsteins per square meter per sec(μE/m2-sec)'
   
        df2.loc[idx,'var_long_name'] = clean(a)
        df2.loc[idx,'var_unit'] = b
               
    #these two are easy: just add them here
    df2.loc[:,('var_spatial_res')] = 'irregular'
    df2.loc[:, ('var_temporal_res')] = 'irregular'

    #there are a few pieces of metadata that CMAP wants that will be easier to track in an Excel file. Right now this means I run through 
    # this twice. Annoying, but haven't figured out a better way (yet). The keywords include cruises, and all possible names for a variable.
    fName = 'CMAP_variableMetadata_additions.xlsx'
    sheetName = exportFile[0:31] #Excel limits the length of the sheet name
    moreMD = pd.read_excel(fName,sheet_name = sheetName)

    #if moreMD is empty add the details to the CMAP_variableMetdata_additions.xlsx file so I can fill in the information
    if len(moreMD)==0:
        with pd.ExcelWriter(fName, engine='openpyxl', mode='a',if_sheet_exists = 'replace') as writer:  
            df2.to_excel(writer, sheet_name=sheetName,index = False)
    else:  
        #otherwise merge the information from moreMD into df2
        #suffixes are added to column name to keep them separate; '' adds nothing while '_td' adds _td that can get deleted next
        #update to remove var_sensor as that is now in the Excel file with the metadata details
        df2 = moreMD.merge(df2[['var_short_name','var_long_name','var_unit']],on='var_short_name',how='left',suffixes=('_td', '',))
        
        # Discard the columns that acquired a suffix:
        df2 = df2[[c for c in df2.columns if not c.endswith('_td')]]
        #reorder the result to match the expected order        
        df2 = df2.loc[:,metaVarColumns]
        
    #these two are easy: just add them here
    df2.loc[:,('var_spatial_res')] = 'irregular'
    df2.loc[:, ('var_temporal_res')] = 'irregular'
    
    #metadata about the project    
    #use variables for each datatset provided in the Excel file:
    varProject = pd.read_excel(fName,sheet_name = 'project')
    one = varProject.loc[varProject['name'] == sheetName]
    # finally gather up the dataset_meta_data 
    df3 = pd.DataFrame({
        'dataset_short_name': ['DeepDOM_' + exportFile],
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
        print("Data here: %s" % (os.getcwd()) + '\\' + folder + '\\' + exportFile)
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
