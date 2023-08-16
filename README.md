# Intro Geoflow-DIM
Geoflow building reconstruction from both lidar pointclouds and Dense Matching pointclouds with rooflines extracted from true ortho images.

## what does it do
1. select and crop data for each building
2. extract rooflines from true-ortho images (only for buildings for which dim is selected)
3. reconstruct buildings (seperate workflows for lidar and dim)
4. merge output into one cityjson file

## how to use this image with large datasets
In case of large datasets tile your data and run this image for each tile.


# Running

## config file
Needs to have config toml file.

explain input pointclouds
Specify parameters
Specify data paths

## volumes
```
docker run -it \
  -v ./config:/config \
  -v ./example_data/10_268_594/bag:/data/poly \
  -v ./example_data/10_268_594/true-ortho:/data/img \
  -v ./example_data/10_268_594/laz/2020_dim:/data/laz/2020_dim \
  -v ./example_data/10_268_594/laz/ahn3:/data/laz/ahn3 \
  -v ./example_data/10_268_594/laz/ahn4:/data/laz/ahn4 \
  -v ./tmp:/data/tmp \
  -v ./ouput:/data/output \
  dim_pipeline_runner
```

```
Usage: run.py [OPTIONS]

Options:
  -c, --config PATH               Main configuration file
  -l, --loglevel [INFO|WARNING|DEBUG]
                                  Print debug information
  -j, --jobs INTEGER              Number of parallel jobs to use. Default is
                                  all cores.
  --keep-tmp-data                 Do not remove temporary files (could be
                                  helpful for debugging)
  --output-tile PATH              Export output tile file stem (CityJSON, GPKG
                                  formats). NB. does not include file
                                  extension.  [default: /data/output/tile]
  --help                          Show this message and exit.
```
## Run with example data
```
docker run -it \
  -v ./config:/config \
  -v ./example_data/10_268_594/bag:/data/poly \
  -v ./example_data/10_268_594/true-ortho:/data/img \
  -v ./example_data/10_268_594/laz/2020_dim:/data/laz/2020_dim \
  -v ./example_data/10_268_594/laz/ahn3:/data/laz/ahn3 \
  -v ./example_data/10_268_594/laz/ahn4:/data/laz/ahn4 \
  -v ./tmp:/data/tmp \
  -v ./ouput:/data/output \
  dim_pipeline_runner -c /config/config.toml -l INFO
```
Example output:
```
2023-08-16 12:11:12,695 [INFO]: Config read from /config/config.toml
2023-08-16 12:11:12,696 [INFO]: Pointcloud selection and cropping...
2023-08-16 12:12:20,713 [INFO]: Roofline extraction from true orthophotos...
2023-08-16 12:12:20,757 [INFO]: Building reconstruction...
2023-08-16 12:12:32,620 [INFO]: Generating CityJSON file...
```

# Issues
