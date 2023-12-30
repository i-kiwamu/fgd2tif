import os
import warnings
import numpy as np
from osgeo import gdal
from shapely.geometry import Point
import pyproj
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from haversine import inverse_haversine, Direction, Unit


def get_latlon_names(columns: pd.core.indexes.base.Index) -> dict:
    """
    Search and get latitude/longitude names in the columns.

    Args:
        columns (pd.core.indexes.base.Index): Columns of pandas data frame.
    
    Returns:
        result (dict): Tuple of column index and name of latitude/longitude.
    """
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

def get_xy_dim(
    bbox: tuple,
    crs: pyproj.crs.crs.CRS,
    resolution: float) -> tuple:
    """
    Calculate the number of cells of raster data.

    Args:
        bbox (tuple): (lng min, lat min, lng max, lat max).
        crs (pyproj.crs.crs.CRS): CRS of bbox.
        resolution (float): Spatial resolution to be exported.
    
    Returns:
        nxy (tuple): (the number of cells in x, the number of cells in y)
    """
    unit_name = crs.axis_info[0].unit_name

    if unit_name == "degree":
        point0 = (
            (bbox[3] + bbox[1]) / 2,
            (bbox[2] + bbox[0]) / 2)  # (lat, lng)
        point_east = inverse_haversine(
            point0, resolution, Direction.EAST, unit=Unit.METERS)
        point_north = inverse_haversine(
            point0, resolution, Direction.NORTH, unit=Unit.METERS)
        unit = (point_east[1] - point0[1], point_north[0] - point0[0])
        nxy = (
            int((bbox[2] - bbox[0]) / unit[0]),
            int((bbox[3] - bbox[1]) / unit[1]))
        return nxy
    elif unit_name == "metre":
        nxy = (
            int((bbox[2] - bbox[0]) / resolution),
            int((bbox[3] - bbox[1]) / resolution))
        return nxy
    else:
        raise NameError("Unknown unit of CRS!")


def get_dtype(df: pd.DataFrame) -> np.dtype:
    """
    Decide the data type of the exported GeoTiff file from data frame.

    Args:
        df (pd.DataFrame): Pandas data frame.
    
    Returns:
        dtype (np.dtype): Data type of the exported GeoTiff file.
    """
    dtypes = df.dtypes.values
    dtypes_set = set(dtypes)
    if len(dtypes_set) == 1:
        return dtypes[0]
    elif float in dtypes:
        return np.dtype("float")
    elif int in dtypes:
        return np.dtype("int")
    elif np.uint in dtypes:
        return np.dtype("uint")
    else:
        return np.dtype("object")


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
        nxy = get_xy_dim(bbox, gdf.crs, self.resolution)
        out_transform = rasterio.transform.from_bounds(*bbox, *nxy)
        out_dtype = get_dtype(df)
        nodata = -9999. if out_dtype == np.dtype("float") else -9999

        profile = {
            "driver": "GTiff",
            "width": nxy[0],
            "height": nxy[1],
            "count": len(df.columns),
            "dtype": out_dtype,
            "crs": gdf.crs.to_string(),
            "transform": out_transform,
            "nodata": nodata,
        }

        with rasterio.open(output_file_name, "w", **profile) as dst:
            for i, z_name in enumerate(df.columns):
                z_array = rasterize(
                    zip(gdf["geometry"], gdf[z_name]),
                    out_shape=nxy[::-1],
                    transform=out_transform,
                    fill=nodata,
                    all_touched=True)
                dst.write(z_array, i+1)
                dst.set_band_description(i+1, z_name.strip())
    

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
