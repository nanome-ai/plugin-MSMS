#!/bin/bash

wget https://github.com/embree/embree/releases/download/v3.13.1/embree-3.13.1.x86_64.linux.tar.gz
wget https://github.com/oneapi-src/oneTBB/releases/download/v2021.4.0/oneapi-tbb-2021.4.0-lin.tgz
tar xvzf embree-3.13.1.x86_64.linux.tar.gz
tar xvzf oneapi-tbb-2021.4.0-lin.tgz

cp embree-3.13.1.x86_64.linux/lib/lib.* nanome_msms/AO_binaries/Linux64
cp oneapi-tbb-2021.4.0/lib/intel64/gcc4.8/lib.* nanome_msms/AO_binaries/Linux64

rm -r embree-3.13.1.x86_64.linux
rm -r oneapi-tbb-2021.4.0