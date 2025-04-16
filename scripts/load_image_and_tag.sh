#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <path_to_image_file>"
    exit 1
fi

image_path="$1"
image_filename=$(basename "$image_path")
pattern=$(echo "$image_filename" | sed -E 's/^metrics-db-api_(.+)\.tar(.gz)?$/\1/')

if [ ! -f "$image_path" ]; then
    echo "Error: Image file not found at $image_path"
    exit 1
fi

docker load -i "$image_path"
docker image ls | grep "$pattern"
image_id=$(docker image ls | grep "$pattern" | awk '{print $3}')

if [ -z "$image_id" ]; then
    echo "Error: No image found matching the pattern $pattern"
    exit 1
fi

docker tag "$image_id" metrics-db-api:latest
docker image ls | grep "metrics-db-api"