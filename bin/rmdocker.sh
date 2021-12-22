#!/bin/bash
docker rm $(docker ps --all -q -f status=exited)
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
