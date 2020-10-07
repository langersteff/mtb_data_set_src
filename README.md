With this code, an auto labeled signal data set on Garmin .fit files can be created.
This has all been implemented to use .fit files generated with a Garmin Fenix 5 or newer utilizing the App "RawLogger".
With regular .fit files, the code needs some rewriting, since there is no 25Hz acceleration data within the files.
Removing the values from the array of columns in "mtb_data_provider_garmin.py" might be sufficient.

In *notebooks/MtbDataSet.ipynb*, an example is given.
The function ```mtb_data_set.create_data_set``` encapsulates the core functionality and needs either an array of file names in the "/data" folder or a "None", which leads to reading all .fit files in the data folder.
.fit filenames are split into three parts. 

```mytracking_w_1```
This leads to the trailname "mytracking", the gender "w" and the rider ID "1", which will be added to the dataset.

For now, the rest has to be read from code, better documentation might be coming soon.

For Gopro Mp4 Metadata To CSV: 
* Install ffmpeg and gpmd2csv
