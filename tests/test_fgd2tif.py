import unittest
import subprocess
from fgd2tif.fgd2tif import Fgd2Tif

class TestFGD2TIF(unittest.TestCase):
    # def test_init(self):
    #     input_list = [
    #         "FG-GML-6644-10-DEM5A.zip",
    #         "FG-GML-6644-10-00-DEM5A-20161001.xml"
    #     ]
    #     actual = [
    #         Fgd2Tif(fname).output_file_name
    #         for fname in input_list
    #     ]
    #     expected = [
    #         "FG-GML-6644-10-DEM5A.tif",
    #         "FG-GML-6644-10-00-DEM5A-20161001.tif"
    #     ]
    #     self.assertEqual(expected, actual)

    def test_execute(self):
        input_file_name = "/Users/kiwamu/Documents/hro/Others/基盤地図_数値標高モデル5m_オホーツク/FG-GML-6644-10-DEM5A/FG-GML-6644-10-02-DEM5A-20161001.xml"
        gtiff_file_name = "/Users/kiwamu/Documents/hro/Remote_sensing_drainage_2021/DEM/fgd2tif/tests/FG-GML-6644-10-02-DEM5A-20161001.tif"
        f = Fgd2Tif(input_file_name)
        f.execute()
        actual = subprocess.run(
            ["gdalinfo", f.output_file_name],
            capture_output=True,
        ).stdout
        expected = subprocess.run(
            ["gdalinfo", gtiff_file_name],
            capture_output=True,
        ).stdout
        self.assertEqual(expected, actual)
