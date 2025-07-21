# DeepDOM
Code to move DeepDOM data to CMAP\
Krista Longnecker, Woods Hole Oceangraphic Institution

Comments, newest at the top
### 21 July 2025
This code is set to (1) go to BCO-DMO and pull the DeepDOM files into a json file (using ```getBCODMOinfo.ipynb```, link [here](https://github.com/redbluewater/DeepDOM/blob/main/getBCODMOinfo.ipynb)) and then convert the files into Excel files in the format required by CMAP (using ```convertBCODMOtoCMAP_v2.ipynb```, link [here](https://github.com/redbluewater/DeepDOM/blob/main/convertBCODMOtoCMAP_v2.ipynb)).

Some notes:\
You will have to run through ```convertBCODMOtoCMAP_v2.ipynb``` twice as I have not found an easy way to automate adding the metadata about the variables. This requires some fussing around in something like the following order:
1. Make an Excel file that is named ```CMAP_variableMetadata_additions.xlsx```.
2. To that Excel file, add details about each project on the 'project' worksheet.
3. Make one worksheet for each datafile at BCO-DMO. These sheets can be empty except for the headers used for the metadata variables.
4. Run ```convertBCODMOtoCMAP_v2.ipynb``` to populate the Excel file with 'var_short_names' and details about the metadata that are available at BCO-DMO.
5. Edit the Excel file to add information as to whether or not the variable is visualizable, the type of data, and some keywords.
6. Run ```convertBCODMOtoCMAP_v2.ipynb``` again to produce the Excel files for each dataset. These are in the /data/ folder, which is *not* synced to GitHub.

### 18 July 2025
Working on this for the BIOS-SCOPE project and realized it would be useful to move the DeepDOM data over as well.
