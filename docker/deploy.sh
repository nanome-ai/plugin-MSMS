#!/bin/bash

echo "./deploy.sh $*" > redeploy.sh
chmod +x redeploy.sh

existing=$(docker ps -aq -f name=high-quality-surfaces)
if [ -n "$existing" ]; then
    echo "removing existing container"
    docker rm -f $existing
fi

docker run -d \
--name high-quality-surfaces \
--restart unless-stopped \
-e ARGS="$*" \
high-quality-surfaces
