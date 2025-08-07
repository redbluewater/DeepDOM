
import os
from pathlib import Path   
import requests
import zipfile



def check_excel(filePath):
    url = "https://cmapdatavalidation.com/excel/zip"
    err = False
    try:
        print(f"Validating {filePath} ...")
        outPath = f"{Path(filePath).name.split('.xlsx')[0]}.zip"
        headers = {
            "accept": "application/json'",
        }
        files = {'file': (filePath, open(filePath, 'rb'), 'application/vnd.ms-excel', {'Expires': '0'})}
        resp = requests.post(url, headers=headers, files=files, timeout=1000) 
        totalbits = 0
        with open(outPath, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    totalbits += 1024
                    print("Downloaded",totalbits*1025,"KB...")
                    f.write(chunk)

        unzipDir = f"{Path(filePath).name.split('.xlsx')[0]}"
        with zipfile.ZipFile(outPath, 'r') as zip_ref:
            zip_ref.extractall(unzipDir)
        os.remove(outPath)    
    except Exception as e:
        print(str(e))
        err = True
        outPath = ""
    return outPath, err



#path to excel file
filePath = "./data/CMAP_TOS.zip"
check_excel(filePath)

