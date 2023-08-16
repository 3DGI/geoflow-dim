build:
  DOCKER_BUILDKIT=1 sudo docker build -t dim_pipeline_runner -f dockerfile_multistage --target dim-pipeline-runner --build-arg JOBS=32 .

# rebuild:
#   sudo docker build --no-cache -t dim_reconstructor .

save:
  sudo docker save dim_pipeline_runner:latest -o dim_pipeline_runner_$(git describe).tar

run-it *ARGS:
  sudo docker run -it \
  -v ./config:/config \
  -v ./example_data/10_268_594/bag:/data/poly \
  -v ./example_data/10_268_594/true-ortho:/data/img \
  -v ./example_data/10_268_594/laz/2020_dim:/data/laz/2020_dim \
  -v ./example_data/10_268_594/laz/ahn3:/data/laz/ahn3 \
  -v ./example_data/10_268_594/laz/ahn4:/data/laz/ahn4 \
  -v ./tmp:/data/tmp \
  -v ./ouput:/data/output \
  dim_pipeline_runner {{ARGS}}
