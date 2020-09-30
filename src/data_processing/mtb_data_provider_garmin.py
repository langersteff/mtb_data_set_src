import os
import subprocess
import pandas as pd
import numpy as np
from .mtb_data_provider_base import MtbDataProviderBase

LATITUDE_KEY = 'position_lat'
LONGITUDE_KEY = 'position_long'

class MtbDataProviderGarmin(MtbDataProviderBase):

    def __init__(self, speed_threshold):
        super().__init__()
        self.speed_threshold = speed_threshold

    def get_columns(self):
        return ['timestamp', 'distance', 'SensorSpeed', 'heart_rate', 'altitude', 'SensorHeading', 'SensorAccelerationX_HD', 'SensorAccelerationY_HD', 'SensorAccelerationZ_HD', LATITUDE_KEY, LONGITUDE_KEY]

    def create_mapped_data(self, input_file_name, _):
        file_name = '../data/' + input_file_name
        data = self.convert_and_read_fit_file(file_name)
        data = self.filter_data(data, self.speed_threshold)
        data = self.split_hd_values(data)
        data = self.get_values_for(data, self.get_columns()[1:], prepend_timestamp=True)
        # Save tmp file, this is needed for syncing the gopro data through pandas
        np.savetxt("../data/" + input_file_name + '-tmp.csv', data, delimiter=",", header=','.join(self.get_columns()), fmt='"%s"', comments='')
        return data

    def convert_and_read_fit_file(self, file_name):
        print("Converting Garmin .fit file", file_name + ".fit")
        converter = os.path.abspath("../FitSDKRelease_21.16.00/java/FitCSVTool.jar")
        filepath = os.path.abspath(file_name + ".fit")
        subprocess.run(["java", "-jar", converter,  filepath])
        data = pd.read_csv(file_name + ".csv", low_memory=False)
        datav = data.query("Message == 'record'").values
        return datav

    def filter_data(self, df, speed_threshold):
        result = {}

        for row in df:
            current_object = {}
            current_objects = []
            current_timestamp = 0
            for i in range(len(row)):
                column = row[i]

                if column == 'timestamp':
                    current_timestamp = row[i+1]
                elif column in self.get_columns():
                    if column.endswith("_HD"):
                        current_object[column] = row[i+1]
                    # lat/long is written in semicircles
                    elif column in [LATITUDE_KEY, LONGITUDE_KEY]:
                        current_object[column] = float(row[i+1]) * 180.0 / 2**31
                    else:
                        current_object[column] = float(row[i+1])

            # SPEED THRESHOLD
            if 'SensorSpeed' in current_object and current_object['SensorSpeed'] >= speed_threshold:
                result[current_timestamp] = current_object

        return result

    def split_hd_values(self, data):
        result = {}
        for timestamp, row in data.items():

            if 'SensorAccelerationX_HD' in row:
                if (type(row['SensorAccelerationX_HD']) is str and '|' in row['SensorAccelerationX_HD']):
                    hd_values_x = row['SensorAccelerationX_HD'].split('|')
                    hd_values_y = row['SensorAccelerationY_HD'].split('|')
                    hd_values_z = row['SensorAccelerationZ_HD'].split('|')

                    for i in range(len(hd_values_x)):
                        new_row = row.copy()
                        new_row['SensorAccelerationX_HD'] = float(hd_values_x[i])
                        new_row['SensorAccelerationY_HD'] = float(hd_values_y[i])
                        new_row['SensorAccelerationZ_HD'] = float(hd_values_z[i])
                        result[int(timestamp) * 1000 + i*40] = new_row # TODO: changed *4 to *40, does this make sense???
            else:
                result[int(timestamp) * 1000] = row # TODO: Added *1000, does this make sense???

        return result
