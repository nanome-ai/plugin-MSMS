FROM nanome/plugin-env

ENV ARGS=''
WORKDIR /app

RUN apt-get update && apt-get install -y libc6-i386

RUN wget -q https://github.com/embree/embree/releases/download/v3.13.1/embree-3.13.1.x86_64.linux.tar.gz &&\
  wget -q https://github.com/oneapi-src/oneTBB/releases/download/v2021.4.0/oneapi-tbb-2021.4.0-lin.tgz &&\
  tar xzf embree-3.13.1.x86_64.linux.tar.gz &&\
  tar xzf oneapi-tbb-2021.4.0-lin.tgz &&\
  mkdir -p /app/plugin/bin/linux/ &&\
  cp embree-3.13.1.x86_64.linux/lib/lib* /app/plugin/bin/linux/ &&\
  cp oneapi-tbb-2021.4.0/lib/intel64/gcc4.8/lib* /app/plugin/bin/linux/ &&\
  rm -r embree-3.13.1.x86_64.linux* oneapi-tbb-2021.4.0*

ARG CACHEBUST
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN chmod +x /app/plugin/bin/linux/AOEmbree

CMD python run.py ${ARGS}
