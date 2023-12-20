build:
  DOCKER_BUILDKIT=1 sudo docker build -t geoflow-dim -f dockerfile_multistage --target geoflow-dim-runner --squash --build-arg JOBS=32 .

# rebuild:``
#   sudo docker build --no-cache -t dim_reconstructor .

save:
  sudo docker save geoflow-dim:latest | gzip > geoflow-dim_$(git describe).tar.gz

load:
  docker load < geoflow-dim.tar.gz

mount-azblob:
  blobfuse2 mount /azblob/gfdata -o allow_root --config-file=/home/ravi/git/3dbag-input-kadaster/blobfuse/bfuse_ahn.yml
  # blobfuse2 mount /azblob/bm -o allow_root --config-file=/home/ravi/git/3dbag-input-kadaster/blobfuse/bfuse_sure2021.yml

run *ARGS:
  sudo docker run \
  --env-file develop.env \
  -v /data:/data \
  geoflow-dim {{ARGS}}
  # -v ./tmp:/data/tmp \
  # -v ./ouput:/data/output \
