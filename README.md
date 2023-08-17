# Introductie Geoflow-DIM
Deze pijplijn doet Geoflow LoD1.2-2.2 3D gebouw reconstructie uit zowel lidar puntewolken als Dense Matching puntenwolken aangevuld met true-ortho beelden voor daklijn extractie. Voor ieder gebouw wordt automatisch bepaald welke puntenwolk het meest geschikt is op basis van puntdekking en/of acquisitie datum.

## Inputs en outputs
Voor de gebouw reconstructie zijn nodig:

0. 2D gebouw polygonen (bv BAG)
1. Een of meerdere lidar puntenwolken (bv AHN3, AHN4)
2. (optioneel) een Dense Matching puntenwolk + true-ortho beelden (beeldmateriaal van een recentere datum dan de laatste lidar puntenwolk)

Hiermee worden de volgende outputs gecreeerd:
1. Een CityJSON feature bestand per gebouw (`*.city.jsonl`)
2. Een normaal CityJSON bestand voor alle gebouwn (`*.city.json`)
3. Een GIS vector bestand (GPKG of postgis database output) .

Deze outputs bevatten dezelfde allemaal dezelfde gebouwdata, maar in verschillende bestandsformaten. 

## Werking pijplijn
De pijplijn is opgebouwd uit de volgende stappen:
1. Uitsnijden punten wolken per gebouw op basis van 2D gebouw polygonen. 
2. Per gebouw analyse + selectie van de optimale puntenwolk op basis van criteria puntdekking en actualiteit.
3. Voor gebouwen waarvoor de DIM puntenwolk is geselecteerd daklijn extractie uit de true-ortho beelden.
4. Reconstructie 3D gebouw modellen. Hierbij wordt voor de gebouwen met DIM puntenwolk een aparte versie van het algoritme gebruikt waarbij ook de true-ortho daklijnen worden meegenomen. Deze stap genereert de CityJSON feature bestanden.
5. Het samenvoegen van de CityJSON feature bestanden naar een reguliere CityJSON bestand (met alle gebouwen) en een GIS vector output (bv GPKG).

## Gebruik voor zeer grote gebieden
Voor het draaien van zeer grote gebieden is het aanbevolen de data van te voren in tegels op te splitsen en deze pijplijn per tegel te draaien.

# Gebruik
Deze pijplijn is beschikbaar is momenteel alleen beschikbaar als Docker image. Directe installatie op een systeem (zonder Docker) is in principe wel mogelijk maar erg ingewikkeld en wordt daarom afgeraden. Docker kan gegbruikt worden op alle besturingssystemen.

Om de docker image te downloaden en te importeren:
```
docker import url ...
```

Testen of de docker image juist geimporteerd is:
```
docker run dim_pipeline_runner --help
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

## Test met voorbeeld data

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

## Gebruik met eigen data
## config file
Needs to have config toml file.

explain input pointclouds
Specify parameters
Specify data paths

## volumes


# Issues
