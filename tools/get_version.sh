#!/bin/bash

# Returns version for helm chart
# <tag>: if current commit is tagged
# <latest-tag+1>-<sha> - if current commit in other branches

REPO_DIR=$(cd $(dirname "$0")/../ && pwd)
GIT_SHA=$(git -C $REPO_DIR rev-parse --short HEAD)

if git -C $REPO_DIR  describe --exact-match --tags ${GIT_SHA} > /dev/null 2>&1; then
    GIT_TAG=$(git -C $REPO_DIR  describe --exact-match --tags ${GIT_SHA})
    IMG_TAG="${GIT_TAG}"
else
    GIT_LATEST_TAG=$(git -C $REPO_DIR  describe --tags --abbrev=0)
    tag_part1=$(echo ${GIT_LATEST_TAG} | awk -F '.' '{print $1}')
    tag_part2=$(echo ${GIT_LATEST_TAG} | awk -F '.' '{print $2}')
    tag_part3=$(echo ${GIT_LATEST_TAG} | awk -F '.' '{print $3}')
    next_tag="${tag_part1}.${tag_part2}.$(( tag_part3 + 1 ))"
    IMG_TAG="${next_tag}-${GIT_SHA}"
fi
echo $IMG_TAG
