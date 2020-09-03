import os
import subprocess
import pandas as pd
import numpy as np
from .mtb_data_provider_base import MtbDataProviderBase
from tqdm import tqdm_notebook as tqdm
import math
from geopy.distance import geodesic


class MtbDataProviderGopro(MtbDataProviderBase):

    def __init__(self):
        super().__init__()

    def get_columns(self):
        # TODO: Add Gopro Prefix
        return ['AcclX', 'AcclY', 'AcclZ', 'Latitude', 'Longitude', 'Altitude', 'Speed',
       'Speed3D', 'TS', 'GpsAccuracy', 'GpsFix', 'GyroX', 'GyroY', 'GyroZ']

    def create_mapped_data(self, input_file_name, garmin_data):
        file_name = '../data/' + input_file_name

        if (os.path.isfile(file_name + '.MP4')):

            self.convert_gopro_mp4_file(file_name)
            # Find the sync points and return the timestamp delta
            timestamp_delta = self.find_timestamp_delta(file_name, garmin_data)
            # Read the gopro csv files, change the timestamp by timestamp_delta and left join on the garmin timestamp column
            gopro_data = self.read_gopro_data(file_name, garmin_data, timestamp_delta)
            # Convert to objects TODO (is this necessary?)
            gopro_data = self.make_gopro_objects(gopro_data, self.get_columns())
            # Return the requested columns
            gopro_data = self.get_values_for(gopro_data, self.get_columns())

        else:
            print("No Gopro File found for: ", input_file_name)

        return gopro_data

    def convert_gopro_mp4_file(self, file_name):
        print("Converting gopro mp4 file", file_name)
        filepathMP4 = os.path.abspath(file_name + ".MP4")
        filepathBin = os.path.abspath(file_name + ".bin")
        filepathCsv = os.path.abspath(file_name + "_gopro.csv")
        converter2bin = ["ffmpeg", "-y", "-i", filepathMP4, "-codec", "copy", "-map", "0:2", "-f", "rawvideo", filepathBin]
        converter2csv = ["gpmd2csv", "-i", filepathBin, "-o", filepathCsv]
        subprocess.run(converter2bin)
        subprocess.run(converter2csv)

    def find_timestamp_delta(self, file_name, garmin_data, compare_percentage=100):#, gps_accuracy_threshold=60):
        print("Syncing data and gopro data...")

        filepathSubCsv = os.path.abspath(file_name + "_gopro-gps.csv")
        gopro_gps_data = pd.read_csv(filepathSubCsv, low_memory=False).values
        gopro_check_len = int(len(gopro_gps_data) * (compare_percentage/100)) # Only check e.g. the first third
        gopro_gps_data = gopro_gps_data[:gopro_check_len]

        garmin_check_len = int(len(garmin_data) * (compare_percentage/100)) # Only check e.g. the first third
        garmin_data = garmin_data[:garmin_check_len]

        last_latitude = 0
        last_longitude = 0
        last_item = []
        last_latitude_gopro = 0
        last_longitude_gopro = 0
        smallest_distance = 99999
        initial_gropro_timestamp = gopro_gps_data[0][0]
        gopro_sync_timestamp = 0
        garmin_sync_timestamp = 0
        closest_tuple = ()

        for i in tqdm(range(len(garmin_data))):
            garmin_data_object = garmin_data[i]
            lat = garmin_data_object[-2]
            lng = garmin_data_object[-1]

            if (last_latitude == lat and last_longitude == lng):
                continue

            last_latitude = lat
            last_longitude = lng

            origin = (lat, lng)

            for j in range(len(gopro_gps_data)):
                gopro_data_object = gopro_gps_data[j]
                gopro_lat = gopro_data_object[1]
                gopro_lng = gopro_data_object[2]

                if math.isnan(gopro_lat) or math.isnan(gopro_lng) or (last_latitude_gopro == gopro_lat and last_longitude_gopro == gopro_lng):
                    continue

                last_latitude_gopro = gopro_lat
                last_longitude_gopro = gopro_lng

                # Check if the item is in distance
                dest = (gopro_lat, gopro_lng)
                distance = geodesic(origin, dest).meters

                if (distance < smallest_distance):
                    smallest_distance = distance
                    garmin_sync_timestamp = garmin_data_object[0]
                    gopro_sync_timestamp = gopro_data_object[0]
                    closest_tuple = (origin, dest, i, j)

        # TODO: Create fallback if to big of a distance
        # Also: Add that distance as some sort of confidence measure to the data?
        print("Sync points are", smallest_distance, "meters apart", closest_tuple)
        return garmin_sync_timestamp - gopro_sync_timestamp

    def read_gopro_data(self, file_name, garmin_data, timestamp_delta):#, gps_accuracy_threshold=60
        gopro_datas = None
        # read an concatenate gopro datas
        for data_key in ["accl", "gps", "gyro"]:
            filepathSubCsv = os.path.abspath(file_name + "_gopro-" + data_key + '.csv')
            subValues = pd.read_csv(filepathSubCsv, low_memory=False)

            # if('GpsAccuracy' in subValues.columns):
            #     subValues = subValues[subValues.GpsAccuracy < gps_accuracy_threshold]

            if (gopro_datas is None):
                gopro_datas = subValues
            else:
                gopro_datas = gopro_datas.merge(subValues, left_on='Milliseconds', right_on='Milliseconds', how='outer')

        # change timestamp by timestamp delta
        gopro_datas['Milliseconds'] = gopro_datas['Milliseconds'] - timestamp_delta

        # Read garmin timestamps csv, remove all but the timestamp column, join left, get rid of timestamp columns, return data
        garmin_csv_data = pd.read_csv(file_name + "-tmp.csv", low_memory=False)
        resulting_gopro_data = garmin_csv_data.merge(gopro_datas, left_on='timestamp', right_on='Milliseconds', how='left')
        resulting_gopro_data = resulting_gopro_data.drop(columns=['Milliseconds'])
        resulting_gopro_data = resulting_gopro_data.drop(columns=garmin_csv_data.columns)

        return resulting_gopro_data.values

    def make_gopro_objects(self, gopro_values, gopro_csv_columns):
        result = []

        for row in gopro_values:
            current_object = {}
            for i in range(len(gopro_csv_columns)):
                column = gopro_csv_columns[i]
                current_object[column] = float(row[i])

            result.append(current_object)

        return result

