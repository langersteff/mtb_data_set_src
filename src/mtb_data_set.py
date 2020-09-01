import sys
import numpy as np
from data_processing.mtb_data_provider_garmin import MtbDataProviderGarmin
from data_processing.mtb_data_provider_web_apis import MtbDataProviderWebApis

sys.path.append('../src')
class MtbDataSet:

    def __init__(self):
        super().__init__()

        self.data_provider_garmin = MtbDataProviderGarmin(speed_threshold = 1)
        self.data_provider_web_apis = MtbDataProviderWebApis()
        # self.data_provider_gopro = MtbDataProviderGopro()
        # self.data_provider_label = MtbDataProviderLabel()

    def create_data_set(self, input_filenames, output_filename):

        print("Creating dataset " + output_filename)

        # Write header for CSV
        garmin_headers = self.data_provider_garmin.get_columns()
        # openstreetmap_headers = self.data_provider_openstreetmap.get_columns()
        web_apis_headers = self.data_provider_web_apis.get_columns()
        # gopro_headers = self.data_provider_gopro.get_columns()
        # label_headers = self.data_provider_label.get_columns()
        data = None
        headers = np.hstack([garmin_headers, web_apis_headers])#, gopro_headers, label_headers])

        for input_filename in input_filenames:

            trail_name, rider_id, trail_id = input_filename.split(".")[0].split("_")

            # This is the base of all data
            garmin_data = self.data_provider_garmin.create_mapped_data(input_filename, None)

            # openstreetmap_data = self.data_provider_openstreetmap.create_mapped_data(input_filename, garmin_data)
            web_apis_data = self.data_provider_web_apis.create_mapped_data(input_filename, garmin_data)
            # gopro_data = self.data_provider_gopro.create_mapped_data(input_filename, garmin_data)
            # label_data = self.data_provider_label.create_mapped_data(input_filename, garmin_data)

            data_block = np.hstack([garmin_data, web_apis_data])#, openstreetmap_data, gopro_data, label_data])
            if data:
                data = np.vstack([data, data_block])
            else:
                data = data_block

        np.savetxt("../data/" + output_filename, data, delimiter=",", header=','.join(headers), fmt='"%s"')
        print("Dataset successfully created: data/" + output_filename)



if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\nUsage: \npython3 mtb_data_set.py [input_filename1, input_filename2, ...] output_filename\n")
    mtb_data_set = MtbDataSet()
    mtb_data_set.create_data_set(sys.argv[1:], sys.argv[0])

