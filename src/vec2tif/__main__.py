import argparse
from .fgd2tif import Fgd2Tif
from .csv2tif import Csv2Tif
from .shp2tif import Shp2Tif

def command_fgd(args):
    fgd2tif = Fgd2Tif(args.input, args.merge, args.output)
    fgd2tif.execute_all()

def command_csv(args):
    csv2tif = Csv2Tif(args.input, args.crs, args.resolution)
    csv2tif.execute_all()

def command_shp(args):
    shp2tif = Shp2Tif(args.input, args.resolution)
    shp2tif.execute_all()

# Argument parser
parser = argparse.ArgumentParser(
    prog="python -m vec2tif",
    description="Conversion from vector data to GeoTiff.")
subparsers = parser.add_subparsers(help="Input data type")

# fgd
parser_fgd = subparsers.add_parser(
    "fgd",
    help="Fundamental Geo Data of GSI Japan")
parser_fgd.add_argument(
    "input",
    help="Input xml/zip files (one or more).",
    nargs="+")
parser_fgd.add_argument(
    "--merge", "-m",
    action="store_true",
    help="Merge all the input files if specified."
)
parser_fgd.add_argument(
    "--output", "-o",
    default="merge.tif",
    help="Output file name if '--merge' is specified (default merge.tif)."
)
parser_fgd.set_defaults(handler=command_fgd)

# csv
parser_csv = subparsers.add_parser(
    "csv",
    help="CSV with Latitude & Longitude columns")
parser_csv.add_argument(
    "input",
    help="Input csv files (one or more).",
    nargs="+")
parser_csv.add_argument(
    "--crs", "-c",
    help="CRS code (default 4326).",
    default=4326,
    type=int
)
parser_csv.add_argument(
    "--resolution", "-r",
    help="Spatial resolution of the input files.",
    default=3.0,
    type=float,
    required=True,
)
parser_csv.set_defaults(handler=command_csv)

# shp
parser_shp = subparsers.add_parser(
    "shp",
    help="ESRI Shapefile")
parser_shp.add_argument(
    "input",
    help="Input shp files (one or more).",
    nargs="+")
parser_shp.add_argument(
    "--resolution", "-r",
    help="Spatial resolution of the input files.",
    default=3.0,
    type=float,
    required=True,
)
parser_shp.set_defaults(handler=command_shp)


# Parse arguments
args = parser.parse_args()
if hasattr(args, "handler"):
    args.handler(args)
else:
    parser.print_help()
