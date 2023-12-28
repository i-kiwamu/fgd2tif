import os
import warnings
import numpy as np
from osgeo import gdal
from shapely.geometry import Point
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from haversine import inverse_haversine, Direction, Unit


def get_latlon_names(columns: pd.core.indexes.base.Index) -> dict:
    result = {
        "lat": (),
        "lng": (),
    }
    for i, x in enumerate(columns):
        xl = x.lower()
        if xl == "latitude" or xl == "lat":
            result["lat"] = (i, x)
        elif xl == "longitude" or xl == "lng":
            result["lng"] = (i, x)
        else:
            continue
    if result["lat"] == ():
        raise KeyError("Latitude is not found! {}".format(columns))
    elif result["lng"] == ():
        raise KeyError("Longitude is not found! {}".format(columns))
    else:
        return result


class Csv2Tif:
    """
    Convert from CSV file with Latitude & Longitude to GeoTiff (tif).

    Attributes:
        input_file_list (list): List of input file names.
        n_inputs (int): The number of input_file_list.
        crs_code (int): CRS code of input files.
        resolution (float): Spatial resolution (m) of input files.
        output_file_list (list): List of output file names.
    """
    def __init__(
        self,
        input_file_list: list,
        crs_code: int,
        resolution: float,
    ):
        """
        Init of Csv2Tif class

        Args:
            input_file_list (list): List of input file names (xml or zip).
            output_file_name (str): Output file name.
        """
        self.input_file_list = input_file_list
        self.n_inputs = len(input_file_list)
        self.crs_code = crs_code
        self.resolution = resolution
        self.output_file_list = []
    
    def convert_csv(
        self,
        input_file_name: str,
        output_file_name: str
    ):
        """
        Convert CSV to GeoTiff.

        Args:
            input_file_name (str): Input file name
            output_file_name (str): Output file name
        """
        df = pd.read_csv(input_file_name)
        latlng_names = get_latlon_names(df.columns)

        geom = [
            Point(xy) 
            for xy in zip(
                df[latlng_names["lng"][1]],
                df[latlng_names["lat"][1]]
            )]
        
        df = df.drop([x[1] for x in latlng_names.values()], axis=1)
        gdf = gpd.GeoDataFrame(df, crs=self.crs_code, geometry=geom)
        
        bbox = tuple(gdf.total_bounds)
        point0 = (gdf.geometry[0].y, gdf.geometry[0].x)
        point_east = inverse_haversine(
            point0, self.resolution, Direction.EAST, unit=Unit.METERS)
        point_north = inverse_haversine(
            point0, self.resolution, Direction.NORTH, unit=Unit.METERS)
        unit = (point_east[1] - point0[1], point_north[0] - point0[0])
        nxy = (
            int((bbox[2] - bbox[0]) / unit[0]),
            int((bbox[3] - bbox[1]) / unit[1]))
        out_transform = rasterio.transform.from_bounds(*bbox, *nxy)
        nodata = -9999.

        profile = {
            "driver": "GTiff",
            "width": nxy[0],
            "height": nxy[1],
            "count": len(df.columns),
            "dtype": "float32",
            "crs": "EPSG:{}".format(self.crs_code),
            "transform": out_transform,
            "nodata": nodata,
        }

        with rasterio.open(output_file_name, "w", **profile) as dst:
            for i, z_name in enumerate(df.columns):
                z_array = rasterize(
                    zip(gdf["geometry"], gdf[z_name]),
                    out_shape=nxy,
                    transform=out_transform,
                    fill=nodata,
                    all_touched=True)
                dst.write(z_array, i+1)
    

    def execute_one(self, input_file_name: str):
        """
        Execution of conversion one by one.

        Args:
            input_file_name (str): Input file name.
        """
        body, suffix = os.path.splitext(os.path.basename(input_file_name))
        suffix = suffix.lower()

        if not os.path.lexists(input_file_name):
            raise OSError("File not found!")
        elif suffix != ".csv":
            raise OSError("File extension is invalid! Only 'csv' is available.")
        else:
            output_file_name = os.path.join(
                os.path.dirname(input_file_name),
                body + ".tif"
            )
            self.convert_csv(input_file_name, output_file_name)


    def execute_all(self):
        """
        Execute all input files.
        """
        for input_file_name in self.input_file_list:
            self.execute_one(input_file_name)
