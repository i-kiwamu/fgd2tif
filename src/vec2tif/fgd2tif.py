import os
import datetime
import re
import tempfile
import zipfile
from xml.dom import minidom
import numpy as np
from osgeo import gdal
import rasterio
from rasterio import Affine, merge


def floatr(num_str: str, min_repeat: int=6):
    """
    Repeat the last digits

    Args:
        num_string (str): string of the number.
        min_repeat (int): the detected minimum repeated number of the last digit.
    
    Returns:
        A number (float)
    """
    split_floating_point = re.split(r"\.", num_str)
    n_split = len(split_floating_point)
    if n_split > 2:
        raise TypeError("String cannot be converted to float!")
    elif n_split == 2:
        right = split_floating_point[1]
        n_right = len(right)
        if n_right >= min_repeat:
            last_char = right[-1]
            last_str = right[len(right)-min_repeat:len(right)]
            if last_str == last_char*min_repeat:
                return float(num_str + last_char*10)
            else:
                return float(num_str)
        else:
            return float(num_str)
    else:
        return float(num_str)

def anatomy(
    scanned: minidom.Document,
    tag: str):
    """
    Data extraction from parsed string of xml.

    Args:
        scanned (xml.dom.minidom.Document): parsed string of xml.
        tag (str): xml tag name.
    
    Returns:
        result (str): data in the tag.
    """
    result = (scanned.getElementsByTagName(tag)[0]
        .childNodes[0]
        .data.split(" "))
    return result


def merge_write(
    tif_name_list: list,
    output_file_name: str):
    """
    Merge multiple rasters into one and write it.

    Args:
        tif_name_list (list): Names of Tiff files to be merged.
        output_file_name (str): Output Tiff file name.
    """
    data, out_transform = merge.merge(tif_name_list, method="last")
    data = data[0,:,:]
    with rasterio.open(tif_name_list[0]) as example:
        profile = example.profile
        profile["height"] = data.shape[0]
        profile["width"] = data.shape[1]
        profile["transform"] = out_transform
        with rasterio.open(output_file_name, "w", **profile) as dst:
            dst.write(data, 1)


class Fgd2Tif:
    """
    Convert from FGD file (xml/zip) to GeoTiff (tif).

    Attributes:
        input_file_list (list): List of input file names (xml or zip).
        n_inputs (int): The number of input_file_list.
        is_merge (bool): Merge all the input files if True (default False).
        output_file_list (list): List of output file names.
        output_file_name (str): Final output file name.
    """
    def __init__(
        self,
        input_file_list: list,
        is_merge: bool,
        output_file_name: str
    ):
        """
        Init of Fgd2Tif class

        Args:
            input_file_list (list): List of input file names (xml or zip).
            is_merge (bool): Merge all the input files if True (default False).
            output_file_name (str): Output file name.
        """
        self.input_file_list = input_file_list
        self.n_inputs = len(input_file_list)
        self.is_merge = is_merge
        self.output_file_list = []
        self.output_file_name = output_file_name

    def convert_xml(
        self,
        text: str,
        output_file_name: str):
        """
        Convert XML to GeoTiff.

        Args:
            text (str): Content of the input XML file.
            output_file_name (str): Output file name.
        """
        header, body = text.split("<gml:tupleList>", 1)
        body, footer = body.rsplit("</gml:tupleList>", 1)
        squid = header + footer

        scanned = minidom.parseString(squid)
        lower_corner = anatomy(scanned, "gml:lowerCorner")
        upper_corner = anatomy(scanned, "gml:upperCorner")
        xl = floatr(lower_corner[1])
        xu = floatr(upper_corner[1])
        yl = floatr(lower_corner[0])
        yu = floatr(upper_corner[0])

        size = anatomy(scanned, "gml:high")
        nx = int(size[0]) + 1
        ny = int(size[1]) + 1

        start_point = anatomy(scanned, "gml:startPoint")
        x0 = int(start_point[0])
        y0 = int(start_point[1])

        psize_x = (xu - xl) / nx
        psize_y = (yl - yu) / ny

        transform = Affine(psize_x, 0, xl, 0, psize_y, yu)
        nodata_value = -9999.

        profile = {
            "driver": "GTiff",
            "width": nx,
            "height": ny,
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:6668",
            "transform": transform,
            "nodata": nodata_value,
        }

        elev_array = np.full((ny, nx), nodata_value)
        data = body.strip().split("\n")
        n_data = len(data)
        i = 0
        x00 = x0
        for y in range(y0, ny):
            for x in range(x00, nx):
                if i < n_data:
                    values = data[i].split(",")
                    if len(values) == 2 and values[1].find("-99") == -1:
                        elev_array[y][x] = float(values[1])
                    i += 1
                else:
                    break
            if i == n_data:
                break
            x00 = 0
        
        with rasterio.open(output_file_name, "w", **profile) as dst:
            dst.write(elev_array, 1)


    def convert_zip(
        self,
        input_file_name: str,
        output_file_name: str):
        """
        Convert ZIP to GeoTiff.

        Args:
            input_file_name (str): Input file name.
            output_file_name (str): Output file name.
        """
        tif_name_list = []
        with tempfile.TemporaryDirectory() as temp_dir_name:
            with zipfile.ZipFile(input_file_name) as z:
                for file_name in z.namelist():
                    tif_name = os.path.join(
                        temp_dir_name,
                        os.path.basename(file_name) + ".tif")
                    suffix = os.path.splitext(file_name)[1]
                    if suffix.lower() == ".xml" and not "meta" in file_name:
                        with z.open(file_name) as f:
                            self.convert_xml(f.read().decode("utf-8"), tif_name)
                    tif_name_list.append(tif_name)
        
            if len(tif_name_list) == 0:
                print("Zip file does not include XML file.")
            elif len(tif_name_list) == 1:
                os.rename(tif_name_list[0], output_file_name)
            else:
                merge_write(tif_name_list, output_file_name)

    def execute_one(
        self,
        input_file_name: str):
        """
        Execution of conversion one by one.

        Args:
            input_file_name (str): Input file name.
        """
        body, suffix = os.path.splitext(os.path.basename(input_file_name))
        suffix = suffix.lower()

        if not os.path.lexists(input_file_name):
            raise OSError("File not found!")
        elif not suffix in [".xml", ".zip"]:
            raise OSError("File extension is invalid! Only 'xml' or 'zip' are available.")
        else:
            output_file_name = os.path.join(
                os.path.dirname(input_file_name),
                body + ".tif"
            )
            if suffix == ".xml":
                with open(input_file_name) as f:
                    self.convert_xml(f.read().strip(), output_file_name)
            else:
                self.convert_zip(input_file_name, output_file_name)
            self.output_file_list.append(output_file_name)
    
    def execute_all(self):
        """
        Execution of all the file in the list.
        """
        for input_file_name in self.input_file_list:
            self.execute_one(input_file_name)
        
        if self.is_merge:
            if self.n_inputs == 1:
                os.rename(self.output_file_list[0], self.output_file_name)
            else:
                merge_write(self.output_file_list, self.output_file_name)
