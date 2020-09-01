import numpy as np


class MtbDataProviderBase:

    def __init__(self):
        super().__init__()

    def get_columns(self):
        print("Did not override function get_headers")

    def create_mapped_data(self, input_filename, garmin_data):
        print("Did not override function create_mapped_data(garmin_data)")

    def get_values_for(self, data, keys, prepend_timestamp=False):
        results = []
        data_values = list(data.values()) if isinstance(data,dict) else  data
        for key in keys:
            result = [row[key] if key in row else 0 for row in data_values]
            results.append(result)

        # Add the timestamp as first value
        if prepend_timestamp:
            results = np.vstack((list(data.keys()), results))

        return np.asarray(results).T

