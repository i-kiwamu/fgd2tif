# vec2tif: Conversion from vector data to GeoTiff file

This is a package for conversion from vector data to GeoTiff file.

## Example

```{shell}
$ python -m vec2tif fgd --merge --output merge.tif FG-GML-6644-10-DEM5A.zip FG-GML-6644-10-DEM5B.zip
```

## Available formats of vector data

`vec2tif` requires a subcommand compatible for the type of input data. Following subcommands are available.

| subcommand | note                              |
|------------|-----------------------------------|
| `fgd`      | Fundamental Geo Data of GSI Japan |
| `csv`      | with Latitude & Longitude columns |
| `shp`      | ESRI Shapefile (point data)       |
