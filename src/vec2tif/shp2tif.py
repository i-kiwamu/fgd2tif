import os
import warnings
import numpy as np
from osgeo import gdal
import pyproj
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from haversine import inverse_haversine, Direction, Unit


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
    point0 = (
        (bbox[3] + bbox[1]) / 2,
        (bbox[2] + bbox[0]) / 2)  # (lat, lng)
    unit_name = crs.axis_info[0].unit_name

    if unit_name == "degree":
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


class Shp2Tif:
    """
    Convert from ESRI Shapefile to GeoTiff (tif).

    Attributes:
        input_file_list (list): List of input file names.
        n_inputs (int): The number of input_file_list.
        resolution (float): Spatial resolution (m) of input files.
        output_file_list (list): List of output file names.
    """
    def __init__(
        self,
        input_file_list: list,
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
        self.resolution = resolution
        self.output_file_list = []
    
    def convert_shp(
        self,
        input_file_name: str,
        output_file_name: str
    ):
        """
        Convert ESRI Shapefile to GeoTiff.

        Args:
            input_file_name (str): Input file name
            output_file_name (str): Output file name
        """
        gdf = gpd.read_file(input_file_name)

        bbox = tuple(gdf.total_bounds)
        nxy = get_xy_dim(bbox, gdf.crs, self.resolution)
        out_transform = rasterio.transform.from_bounds(*bbox, *nxy)
        columns = gdf.columns.drop("geometry")
        out_dtype = get_dtype(gdf[columns])
        nodata = -9999. if out_dtype == np.dtype("float") else -9999

        profile = {
            "driver": "GTiff",
            "width": nxy[0],
            "height": nxy[1],
            "count": len(columns),
            "dtype": out_dtype,
            "crs": gdf.crs.to_string(),
            "transform": out_transform,
            "nodata": nodata,
        }

        with rasterio.open(output_file_name, "w", **profile) as dst:
            for i, z_name in enumerate(columns):
                z_array = rasterize(
                    zip(gdf["geometry"], gdf[z_name]),
                    out_shape=nxy,
                    transform=out_transform,
                    fill=nodata,
                    all_touched=True)
                dst.write(z_array, i+1)
                dst.set_band_description(i+1, z_name)
    

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
        elif suffix != ".shp":
            raise OSError("File extension is invalid! Only 'shp' is available.")
        else:
            output_file_name = os.path.join(
                os.path.dirname(input_file_name),
                body + ".tif"
            )
            self.convert_shp(input_file_name, output_file_name)


    def execute_all(self):
        """
        Execute all input files.
        """
        for input_file_name in self.input_file_list:
            self.execute_one(input_file_name)
