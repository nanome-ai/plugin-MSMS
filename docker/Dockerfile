FROM nanome/plugin-env

ENV ARGS=''
WORKDIR /app

ARG CACHEBUST
COPY requirements.txt .
COPY setup_embree.sh .

ENV AOEMBREE_BINARY=nanome_msms/AO_binaries/Linux64/AOEmbree

RUN pip install -r requirements.txt
RUN setup_embree.sh 
RUN chmod +x  $AOEMBREE_BINARY

COPY . .

CMD python run.py ${ARGS}
