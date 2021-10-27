FROM nanome/plugin-env

ENV ARGS=''
WORKDIR /app

ARG CACHEBUST

RUN apt-get update && apt-get install libc6-i386

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN wget https://github.com/embree/embree/releases/download/v3.13.1/embree-3.13.1.x86_64.linux.tar.gz
RUN wget https://github.com/oneapi-src/oneTBB/releases/download/v2021.4.0/oneapi-tbb-2021.4.0-lin.tgz

RUN tar xvzf embree-3.13.1.x86_64.linux.tar.gz
RUN tar xvzf oneapi-tbb-2021.4.0-lin.tgz

RUN ls

RUN cp embree-3.13.1.x86_64.linux/lib/lib* /app/nanome_msms/AO_binaries/Linux64
RUN cp oneapi-tbb-2021.4.0/lib/intel64/gcc4.8/lib* /app/nanome_msms/AO_binaries/Linux64

RUN rm -r embree-3.13.1.x86_64.linux
RUN rm -r oneapi-tbb-2021.4.0
RUN rm embree-3.13.1.x86_64.linux.tar.gz
RUN rm oneapi-tbb-2021.4.0-lin.tgz

RUN chmod +x /app/nanome_msms/AO_binaries/Linux64/AOEmbree

CMD python run.py ${ARGS}
