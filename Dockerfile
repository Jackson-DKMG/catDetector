FROM nvidia/cuda:11.4.1-runtime-ubuntu20.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Paris

ARG OPENCV_VERSION=4.5.3
ARG CUDA_COMPUTE_CAPABILITY=7.5
ARG LIBCUDNN=libcudnn8_8.2.2.26-1+cuda11.4_amd64.deb
ARG LIBCUDNNDEV=libcudnn8-dev_8.2.2.26-1+cuda11.4_amd64.deb

#need that repo to install libjasper-dev
RUN echo "deb http://security.ubuntu.com/ubuntu xenial-security main" >> /etc/apt/sources.list

RUN apt update && apt upgrade -y &&\
    # Install build tools, build dependencies and python
    apt install -y build-essential cmake git wget unzip yasm pkg-config \
        checkinstall curl g++ gcc \
        libswscale-dev libtbb2 libtbb-dev libjpeg-dev libpng-dev libtiff-dev \
        libavformat-dev libpq-dev libxine2-dev libglew-dev libtiff5-dev zlib1g-dev \
        libjpeg-dev libavcodec-dev libavformat-dev libavutil-dev libpostproc-dev \
        libswscale-dev libeigen3-dev libtbb-dev libgtk2.0-dev libv4l-dev \
        libjasper-dev libdc1394-22-dev \
        libxvidcore-dev libx264-dev libgtk-3-dev pkg-config \
        python3 python3-dev python3-numpy python3-pip vim \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*
#install CUDNN, copy ssh key and known_hosts, copy the program files.
ADD ssh /root/.ssh
ADD catDetector /catDetector
COPY $LIBCUDNN /$LIBCUDNN
COPY $LIBCUDNNDEV /$LIBCUDNNDEV
RUN dpkg -i $LIBCUDNN
RUN dpkg -i $LIBCUDNNDEV
RUN rm $LIBCUDNN $LIBCUDNNDEV


#install needed python modules
RUN pip3 install gpiozero pigpio

#download & unzip opencv and opencv-contrib, then delete the archives.
RUN wget https://github.com/opencv/opencv/archive/$OPENCV_VERSION.zip &&\
    unzip $OPENCV_VERSION.zip &&\
    rm $OPENCV_VERSION.zip &&\
    wget https://github.com/opencv/opencv_contrib/archive/$OPENCV_VERSION.zip &&\
    unzip ${OPENCV_VERSION}.zip &&\
    rm ${OPENCV_VERSION}.zip &&\
    # Create build folder and switch to it
    mkdir opencv-${OPENCV_VERSION}/build && cd opencv-${OPENCV_VERSION}/build &&\
#Cmake configure
    cmake -D CMAKE_BUILD_TYPE=RELEASE \
          -D CMAKE_INSTALL_PREFIX=/usr/local \
          -D OPENCV_EXTRA_MODULES_PATH=../../opencv_contrib-${OPENCV_VERSION}/modules \
          -D INSTALL_PYTHON_EXAMPLES=OFF \
          -D INSTALL_C_EXAMPLES=OFF \
          -D OPENCV_ENABLE_NONFREE=ON \
          -D WITH_CUDA=ON \
          -D CUDNN_LIBRARY="/usr/lib/x86_64-linux-gnu/libcudnn.so" \
          -D CUDNN_INCLUDE_DIR="/usr/include/" \
          -D WITH_CUDNN=ON \
          -D OPENCV_DNN_CUDA=ON \
          -D FORCE_VTK=ON \
          -D OPENCV_GENERATE_PKGCONFIG=ON \
          -D WITH_CSTRIPES=ON \
          -D WITH_EIGEN=ON \
          -D WITH_GDAL=ON \
          -D WITH_GSTREAMER=ON \
          -D WITH_GSTREAMER_0_10=OFF \
          -D WITH_GTK=ON \
          -D WITH_IPP=ON \
          -D WITH_OPENCL=ON \
          -D WITH_OPENMP=ON \
          -D WITH_TBB=ON \
          -D WITH_V4L=ON \
          -D WITH_WEBP=ON \
          -D WITH_XINE=ON \
          -D ENABLE_FAST_MATH=1 \
          -D CUDA_FAST_MATH=1 \
          -D CUDA_ARCH_BIN=$CUDA_COMPUTE_CAPABILITY \
          -D WITH_CUBLAS=1 \
          -D BUILD_opencv_python2=OFF \
          -D BUILD_opencv_python3=ON \
          -D BUILD_PERF_TESTS=OFF \
          -D BUILD_EXAMPLES=OFF \
          -D BUILD_TESTS=OFF \
          -D BUILD_DOCS=OFF .. &&\
    # Make
    make -j"$(nproc)" && \
    # Install to /usr/local/lib
    make install && \
    ldconfig &&\
    # Remove OpenCV sources and build folder
    cd / && rm -rf opencv-${OPENCV_VERSION} && rm -rf opencv_contrib-${OPENCV_VERSION}

WORKDIR /catDetector

CMD python3 main.py
