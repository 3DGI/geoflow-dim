build:
  sudo docker build -t dim_reconstructor .

rebuild:
  sudo docker build --no-cache -t dim_reconstructor .

save:
  docker save dim_reconstructor:latest -o dim_reconstructor_$(git describe).tar

run-it:
  sudo docker run -it -u 0 \
  -v ./config:/data/config \
  -v ./example_data/10_268_594/bag:/data/poly \
  -v ./example_data/10_268_594/true-ortho:/data/img \
  -v ./example_data/10_268_594/laz/2020_dim:/data/laz/2020_dim \
  -v ./example_data/10_268_594/laz/ahn3:/data/laz/ahn3 \
  -v ./example_data/10_268_594/laz/ahn4:/data/laz/ahn4 \
  -v /dev/shm/rypeters/tmp:/data/tmp \
  -v /dev/shm/rypeters/ouput:/data/output \
  dim_reconstructor
