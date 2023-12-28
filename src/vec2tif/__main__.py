import argparse
from .fgd2tif import Fgd2Tif

parser = argparse.ArgumentParser(
    prog="python -m fgd2tif",
    description="Conversion from FGD to GeoTiff."
)
parser.add_argument(
    "input",
    help="Input xml/zip files (one or more).",
    nargs="+")
parser.add_argument(
    "--merge",
    action="store_true",
    help="Merge all the input files if specified."
)
parser.add_argument(
    "--output",
    default="merge.tif",
    help="Output file name if '--merge' is specified (default merge.tif)."
)
args = parser.parse_args()

fgd2tif = Fgd2Tif(args.input, args.merge, args.output)
fgd2tif.execute_all()
