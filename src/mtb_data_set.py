import sys, os
import numpy as np
import glob
from data_processing.mtb_data_provider_garmin import MtbDataProviderGarmin
from data_processing.mtb_data_provider_web_apis import MtbDataProviderWebApis
from data_processing.mtb_data_provider_gopro import MtbDataProviderGopro

sys.path.append('../src')
class MtbDataSet:

    def __init__(self):
        super().__init__()

        self.data_provider_garmin = MtbDataProviderGarmin(speed_threshold = .5)
        self.data_provider_web_apis = MtbDataProviderWebApis()
        self.data_provider_gopro = MtbDataProviderGopro()

    def create_data_set(self, input_filenames, output_filename):

        print("Creating dataset " + output_filename)

        if input_filenames is None:
            input_filenames = []
            for input_filepath in glob.glob("../data/*.fit"):
                basename = os.path.basename(input_filepath)
                basename_wo_ext = os.path.splitext(basename)[0]
                input_filenames.append(basename_wo_ext)

        # Write header for CSV
        garmin_headers = self.data_provider_garmin.get_columns()
        web_apis_headers = self.data_provider_web_apis.get_columns()
        gopro_headers = self.data_provider_gopro.get_columns()

        data = None
        headers = np.hstack(["input_filename", "rider_id", "trail_name", garmin_headers, web_apis_headers, gopro_headers])

        for input_filename in input_filenames:

            file_name_parts = input_filename.split("_")
            trail_name = file_name_parts[0]
            rider_id = file_name_parts[-1]

            # Create Data blocks
            garmin_data = self.data_provider_garmin.create_mapped_data(input_filename, None)
            web_apis_data = self.data_provider_web_apis.create_mapped_data(input_filename, garmin_data)
            gopro_data = self.data_provider_gopro.create_mapped_data(input_filename, garmin_data)

            input_file_column = np.asarray([input_filename] * len(garmin_data)).reshape(len(garmin_data), 1)
            rider_id_column = np.asarray([rider_id] * len(garmin_data)).reshape(len(garmin_data), 1)
            trail_name_column = np.asarray([trail_name] * len(garmin_data)).reshape(len(garmin_data), 1)
            data_block = np.hstack([input_file_column, rider_id_column, trail_name_column, garmin_data, web_apis_data, gopro_data])
            if data is not None:
                data = np.vstack([data, data_block])
            else:
                data = data_block

        np.savetxt("../data/" + output_filename, data, delimiter=",", header=','.join(headers), fmt='"%s"', comments='')
        print("Dataset successfully created: data/" + output_filename)



if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\nUsage: \npython3 mtb_data_set.py [input_filename1, input_filename2, ...] output_filename\n")
    mtb_data_set = MtbDataSet()
    mtb_data_set.create_data_set(sys.argv[1:], sys.argv[0])

