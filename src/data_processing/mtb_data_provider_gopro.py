import os
import subprocess
import pandas as pd
import numpy as np
import glob
from .mtb_data_provider_base import MtbDataProviderBase
from tqdm import tqdm_notebook as tqdm
import math
from geopy.distance import geodesic

# This class maps data included in a Gopro .mp4 file to the Garmin data
# The datas are synced through their timestamps, however, drift is calculated in two ways:
# 1. Find the closest GPS Position and take that timestamp as the sync-timestamp (!Not recommended, the Gopro GPS is really bad)
# 2. Check whether there is a timestamp in the filename and set this as the sync timestamp (Recommended)
#    The filename timestamp has to be added manually.
#    A good way is to install a Unix Timestamp Watchface to your Garmin and start the video with filming the watchface to find the right timestamp
class MtbDataProviderGopro(MtbDataProviderBase):

    def __init__(self):
        super().__init__()

    def get_columns(self):
        return ['gopro_video_path', 'gopro_image_path', 'video_position']

    def create_mapped_data(self, input_file_name, garmin_data, image_width=256):
        # TODO: Add a max duration?
        garmin_file_name = '../data/' + input_file_name

        glob_file_names = glob.glob(garmin_file_name + '*.MP4')
        zeros = np.zeros((len(garmin_data), len(self.get_columns())))

        if not len(glob_file_names):
            print("No Gopro File found for: ", garmin_file_name)
            return zeros
        else:
            print("Creating Image snippets from Gopro File...")
            data = []
            # Read the timestamp delta from the filename
            gopro_file_name = os.path.splitext(glob_file_names[0])[0]

            gopro_file_name_split = gopro_file_name.split('_')
            if len(gopro_file_name_split) < 4:
                print("Could not find timestamp in filename")
                return zeros

            gopro_sync_timestamp = float(gopro_file_name_split[-1])
            os.makedirs(garmin_file_name, exist_ok=True)

            # Iterate through Garmin data
            for i in tqdm(range(len(garmin_data))):
                data_object = garmin_data[i]
                garmin_timestamp = data_object[0]

                # If the data was recorded before the video
                if (gopro_sync_timestamp > garmin_timestamp):
                    # fill with zeros
                    data.append([0, 0, 0])
                    continue
                else:
                    #   - Snip a Low resolution Image and save it to data/{file_name}/{timestamp}.png
                    image_path =  garmin_file_name + "/" + str(int(garmin_timestamp)) + ".png"
                    video_position = int(garmin_timestamp - gopro_sync_timestamp)
                    extract_png = ["ffmpeg", "-i", gopro_file_name + ".MP4", "-vcodec", "png", "-ss", str(video_position) + "ms", "-vframes", "1", "-vf", "scale=" + str(image_width) + ":-1", "-an", "-f", "rawvideo", str(image_path)]
                    subprocess.run(extract_png)

                    #   - Add to result [video_filename, relative_snippet_path, position_in_video]
                    data.append([glob_file_names[0], image_path, video_position])

            # Return result
            return data

