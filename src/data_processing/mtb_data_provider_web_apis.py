
import pandas as pd
import numpy as np
import glob
from sklearn.utils import shuffle
import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
import subprocess
import requests
from xml.etree.ElementTree import fromstring, ElementTree
from geopy.distance import geodesic
import polyline
from tqdm import tqdm_notebook as tqdm
from .mtb_data_provider_base import MtbDataProviderBase
import config as cfg

LATITUDE_KEY = 'position_lat'
LONGITUDE_KEY = 'position_long'

class MtbDataProviderWebApis(MtbDataProviderBase):

    def __init__(self):
        super().__init__()

    def get_columns(self):
        return ['osm_uid', 'osm_name', 'osm_highway', 'osm_incline', 'osm_mtb:scale', 'osm_surface', 'osm_trail_visibility', 'osm_width',
        'osm_sac_scale', 'osm_bicycle', 'osm_foot', 'osm_tracktype',
        'trailforks_trailid', 'trailforks_title', 'trailforks_difficulty', 'trailforks_trailtype', 'trailforks_biketype', 'trailforks_physical_rating', 'trailforks_ttfs',
        'trailforks_wet_weather', 'trailforks_season', 'trailforks_condition', 'trailforks_difficulty_votes',
        'trailforks_difficulty_user_avg', 'trailforks_family_friendly', 'trailforks_amtb-rating', 'trailforks_activitytypes']

    def create_mapped_data(self, _, garmin_data):
        latitudes = garmin_data[:, -2]
        longitudes = garmin_data[:, -1]
        top_left, bottom_right = self.get_bounding_box_for_recording(latitudes, longitudes, padding=0.0)
        response_openstreetmap = self.fetch_area_from_openstreetmap(top_left, bottom_right)
        response_trailforks = self.fetch_area_from_trailforks(top_left, bottom_right)
        openstreetmap_meta = self.create_openstreetmap_meta(top_left, bottom_right, response_openstreetmap)
        trailforks_meta = self.create_trailforks_meta(top_left, bottom_right, response_trailforks)
        closest_items = self.find_meta_data_for_recording(latitudes, longitudes, openstreetmap_meta, trailforks_meta, distance_threshold=10, fill_empties=5)
        data = self.get_values_for(closest_items, self.get_columns())
        return data

    def get_bounding_box_for_recording(self, latitudes, longitudes, padding=0.):
        min_latitude = np.min(latitudes[np.nonzero(latitudes)])
        max_latitude = np.max(latitudes)
        min_longitude = np.min(longitudes[np.nonzero(longitudes)])
        max_longitude = np.max(longitudes)

        top_left = (max_latitude + padding, min_longitude - padding)
        bottom_right = (min_latitude - padding, max_longitude + padding)

        return (top_left, bottom_right)

    #https://overpass-api.de/api/map?bbox=11.7020,47.6756,11.9303,47.7750
    def fetch_area_from_openstreetmap(self, top_left, bottom_right):
        bbox= 'bbox=' + str(top_left[1]) + ',' + str(bottom_right[0]) + ',' + str(bottom_right[1]) + ',' + str(top_left[0])
        url = 'https://overpass-api.de/api/map?' + bbox
        print("fetching from: ", url)
        response = requests.get(url)
        return response

    #https://www.trailforks.com/api/1/maptrails?output=encoded&filter=bbox%3A%3A47.41852456703782%2C12.356023974716663%2C47.41852456703782%2C12.356023974716663&api_key=docs
    def fetch_area_from_trailforks(self, top_left, bottom_right):
        bbox= 'bbox::' + str(top_left[0]) + ',' + str(top_left[1]) + ',' + str(bottom_right[0]) + ',' + str(bottom_right[1])
        url= 'https://www.trailforks.com/api/1/trails?scope=track&filter=' + bbox + '&app_secret=' + cfg.trailforks["app_secret"] + '&app_id=' + cfg.trailforks["app_id"]
        print("fetching from: ", url)
        response = requests.get(url)
        return response

    def create_openstreetmap_meta(self, top_left, bottom_right, response = None):
        if response is None:
            response = fetch_area_from_openstreetmap(top_left, bottom_right)
        tree = ElementTree(fromstring(response.content))
        root = tree.getroot()
        position_nodes = {}
        mapped_nodes = {}

        for child in root:
            if (child.tag == 'node'):
                position_nodes[child.attrib['id']] = {'lat': child.attrib['lat'], 'lon': child.attrib['lon'], 'uid': child.attrib['uid']}

        for child in root:
            if (child.tag == 'way'):
                metas = {}

                for sub_child in child:
                    if (sub_child.tag == 'tag'):
                        metas[sub_child.attrib['k']] = sub_child.attrib['v']

                for sub_child in child:
                    if (sub_child.tag == 'nd'):
                        node = position_nodes[sub_child.attrib['ref']]
                        mapped_nodes[sub_child.attrib['ref']] = {**node, **metas}

        return mapped_nodes

    def create_trailforks_meta(self, top_left, bottom_right, response = None):
        if response is None:
            response = fetch_area_from_trailforks(top_left, bottom_right)
        datas = response.json()['data']

        for data in datas:
            encoded_path = data['track']['encodedPath']
            decoded_path = polyline.decode(encoded_path)
            del data['track']
            data['positions'] = decoded_path

        return datas

    def find_meta_data_for_recording(self, latitudes, longitudes, openstreetmap_meta, trailforks_meta, distance_threshold=10, fill_empties=2):
        print("Mapping Meta Data from Web APIs...")
        closest_items = []

        last_latitude = 0
        last_longitude = 0

        fill_empties_count_osm = 0
        fill_empties_count_tf = 0
        last_item_osm = {}
        last_item_tf = {}

        for i in tqdm(range(len(latitudes))):
            lat = latitudes[i]
            lon = longitudes[i]

            if last_latitude == lat and last_longitude == lon:
                closest_items.append(closest_items[-1])
                continue

            last_latitude = lat
            last_longitude = lon
            closest_item_osm = {}
            closest_item_trailforks = {}
            smallest_distance_osm = distance_threshold
            smallest_distance_trailforks = distance_threshold
            origin = (lat, lon)

            # Loop through OSM data
            for _, position_meta in openstreetmap_meta.items():

                    # if 'mtb:scale' not in position_meta.keys() and 'mtb:type' not in position_meta.keys():
                    #     continue

                    # Check if the item is in distance
                    dest = (position_meta['lat'], position_meta['lon'])
                    distance = geodesic(origin, dest).meters

                    # Set as the closest OSM item
                    if distance < smallest_distance_osm:
                        closest_item_osm = position_meta
                        smallest_distance_osm = distance

            # Loop through Trailforks data
            for position_meta_trailforks in trailforks_meta:
                # Loop through positions in trailforks data
                for latitude, longitude in position_meta_trailforks['positions']:

                    # Check if the item is in distance
                    dest = (latitude, longitude)
                    distance = geodesic(origin, dest).meters

                    # Set as the closest trailforks item
                    if distance < smallest_distance_trailforks:
                        closest_item_trailforks = position_meta_trailforks
                        smallest_distance_trailforks = distance

            if not closest_item_osm and fill_empties_count_osm < fill_empties: # Fill gaps for "fill_empties" times with the last known object
                closest_item_osm = last_item_osm
                fill_empties_count_osm +=1
            elif closest_item_osm:
                last_item_osm = closest_item_osm
                fill_empties_count_osm = 0

            if not closest_item_trailforks and fill_empties_count_tf < fill_empties: # Fill gaps for "fill_empties" times with the last known object
                closest_item_trailforks = last_item_tf
                fill_empties_count_tf +=1
            elif closest_item_trailforks:
                last_item_tf = closest_item_trailforks
                fill_empties_count_tf = 0

            if closest_item_osm or closest_item_trailforks:
                closest_item_osm_prefixed = {f'osm_{k}': v for k, v in closest_item_osm.items()}
                closest_item_trailforks_prefixed = {f'trailforks_{k}': v for k, v in closest_item_trailforks.items()}
                closest_items.append({**closest_item_osm_prefixed, **closest_item_trailforks_prefixed})
            else:
                closest_items.append({})

        for closest_item in closest_items:
            if 'encodedPath' in closest_item:
                del closest_item['encodedPath']
            if 'positions' in closest_item:
                del closest_item['positions']
            if 'encodedLevels' in closest_item:
                del closest_item['encodedLevels']

        return closest_items

