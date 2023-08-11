FROM ubuntu:mantic
ARG VERSION
LABEL org.opencontainers.image.authors="Ravi Peters <ravi.peters@3dgi.nl>"
LABEL org.opencontainers.image.vendor="3DGI"
LABEL org.opencontainers.image.title="dim-pipeline"
LABEL org.opencontainers.image.description="Custom image made for Kadaster to perform buildings reconstruction based on geoflow with rooflines extracted from true-ortho photos"
LABEL org.opencontainers.image.version=$VERSION
LABEL org.opencontainers.image.licenses="MIT"
ARG JOBS
SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get -y install \
    libgeos++-dev \
    libeigen3-dev \
    libpq-dev \
    nlohmann-json3-dev \
    libboost-filesystem-dev \
    libboost-numpy-dev \
    libboost-python-dev \
    libsqlite3-dev sqlite3\
    libgeotiff-dev \
    build-essential \
    wget \
    git \
    python3-dev \
    python3-numpy \
    python3-setuptools \
    python3-venv \
    python3-pip \
    cmake

ARG PROJ_VERSION=9.2.1
RUN cd /tmp && \
    wget https://download.osgeo.org/proj/proj-${PROJ_VERSION}.tar.gz && \
    tar -zxvf proj-${PROJ_VERSION}.tar.gz  && \
    cd proj-${PROJ_VERSION} && \
    mkdir build && \
    cd build/ && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF && \
    cmake --build . --config Release --parallel $JOBS && \
    cmake --install . && \
    rm -rf /tmp/*

ARG LASTOOLS_VERSION=9ecb4e682153436b044adaeb3b4bfdf556109a0f
RUN cd /tmp && \
    git clone https://github.com/LAStools/LAStools.git lastools && \
    cd lastools && \
    git checkout ${LASTOOLS_VERSION} && \
    mkdir build && \
    cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    cmake --build . --parallel $JOBS --config Release && \
    cmake --install . && \
    rm -rf /tmp/* && \
    mkdir /tmp/geoflow-bundle

ARG CGAL_VERSION=5.5.2
RUN cd /tmp && \
    apt-get install -y libboost-system-dev libboost-thread-dev libgmp-dev libmpfr-dev zlib1g-dev && \
    wget https://github.com/CGAL/cgal/releases/download/v${CGAL_VERSION}/CGAL-${CGAL_VERSION}.tar.xz && \
    tar xf CGAL-${CGAL_VERSION}.tar.xz && \
    cd CGAL-${CGAL_VERSION} && \
    mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    cmake --build . --parallel $JOBS --config Release && \
    cmake --install . && \
    rm -rf /tmp/*

ARG GDAL_VERSION=3.7.1
RUN cd /tmp && \
    wget http://download.osgeo.org/gdal/${GDAL_VERSION}/gdal-${GDAL_VERSION}.tar.gz && \
    tar -zxvf gdal-${GDAL_VERSION}.tar.gz && \
    cd gdal-${GDAL_VERSION} && \
    mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DENABLE_IPO=OFF -DBUILD_TESTING=OFF && \
    cmake --build . --parallel $JOBS --config Release && \
    cmake --install . && \
    ldconfig && \
    rm -rf /tmp/*

# # install geoflow
RUN cd /tmp && \
    git clone https://github.com/geoflow3d/geoflow-bundle.git && cd geoflow-bundle && \
    git checkout develop && \
    git submodule update --init --recursive && \
    mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DGF_BUILD_GUI=OFF && \
    cmake --build . --parallel $JOBS --config Release && \
    cmake --install . && \
    rm -rf /tmp/*

# install crop
RUN cd /tmp && \
    git clone https://github.com/3DGI/roofer.git && cd roofer && \
    git checkout develop && \
    git submodule update --init --recursive && \
    mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    cmake --build . --parallel $JOBS --config Release && \
    cmake --install . && \
    rm -rf /tmp/*

# install Rooflines
# RUN apt-get -y install python3 python3-pip python3-venv && \
#     apt-get update && apt-get install -y locales && rm -rf /var/lib/apt/lists/* \
# 	&& localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
# ENV LANG en_US.utf8

RUN cd /opt && \
    python3 -m venv roofenv && \
    source /opt/roofenv/bin/activate && \
    pip3 install shapely rtree wheel && \ 
    pip3 install --no-cache-dir --force-reinstall 'GDAL[numpy]'

# install opencv
RUN apt-get install -y unzip && \
    cd /tmp && \
    wget https://github.com/opencv/opencv/archive/4.8.0.zip && \
    unzip 4.8.0.zip && \
    cd opencv-4.8.0/ && \
    mkdir build && cd build/ && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/roofenv && \
    cmake --build . --parallel $JOBS --config Release  && \
    cmake --install .

RUN cd /opt && git clone https://github.com/Ylannl/Roofline-extraction-from-orthophotos.git && \
    cd Roofline-extraction-from-orthophotos && \
    cp class_definition.py /opt/roofenv/lib64/python3.11/site-packages/ && \
    cd kinetic_partition && \
    mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/roofenv && \
    cmake --build . --parallel $JOBS --config Release && \
    cp libkinetic_partition* /opt/roofenv/lib64/python3.11/site-packages/

RUN cd /opt && \
    source /opt/roofenv/bin/activate && \
    pip3 install click fiona

RUN cd /opt && git clone https://github.com/geoflow3d/gfc-brecon.git && cd gfc-brecon && \
    git checkout develop
# RUN apt-get update && apt-get -y install parallel

# RUN apt-get -y remove \
#     unzip \
#     build-essential \
#     wget \
#     git \
#     cmake && \
#     apt-get clean && apt-get -y autoremove

# RUN mkdir --parents "/usr/local/geoflow-flowcharts/"
# COPY ./flowcharts/*json /usr/local/geoflow-flowcharts/
# COPY ./config/run.py /opt/Roofline-extraction-from-orthophotos
# RUN chmod +x /usr/local/bin/fugro-reconstruct.sh

WORKDIR /opt
# USER 1000

# ENTRYPOINT ["/opt/roofenv/bin/python3 /data/config/run.py"]
# CMD ["--help"]

# docker build -t gf-ubuntu-base -f base-ubuntu.dockerfile .
# docker run -it gf-ubuntu-base 
