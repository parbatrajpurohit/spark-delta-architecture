# adapted from https://github.com/mvanholsteijn/docker-makefile
# and https://gist.github.com/mpneuried/0594963ad38e68917ef189b4e6a269db
#
#   Copyright 2015  Xebia Nederland B.V.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

SHELL=/bin/bash

# strategy:
# If it is a clean build (no git changes left), build right from .release version string
# if the tag already exists, append the commit short hash
# if there are local changes left append "dirty" (only docker)

RELEASE_SUPPORT := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))/.make-release-support

RELEASE := $(shell . $(RELEASE_SUPPORT); getRelease)
DOCKER_VERSION := $(shell . $(RELEASE_SUPPORT); getDockerVersion)

IMAGE_NAME = metrics-db-api
TAG = ${DOCKER_VERSION}
TAG_LATEST = latest

# special here: image will be only stored locally
IMAGE=${IMAGE_NAME}
BUILD_TARGET = ${IMAGE}:${TAG}

GIT_TAG = $(shell . $(RELEASE_SUPPORT); getGitTag)
GIT_BRANCH = $(shell git rev-parse --abbrev-ref HEAD)
GIT_COMMIT = $(shell git rev-parse --short HEAD)

DOCKER_BUILD_CONTEXT=.
DOCKER_BUILD_ARGS=--build-arg GIT_COMMIT=${GIT_COMMIT}
DOCKER_FILE_PATH=Dockerfile

PARSE_IMAGE_INFO = docker image ls | grep ${IMAGE_NAME} | grep --color='auto' -e ${TAG} -e ${TAG_LATEST}
# -p host_port:container_port
DOCKER_RUN_COMMAND = docker run -it --rm -p 5000:8000 --name ${IMAGE_NAME}-test ${IMAGE}:${TAG}
# activating conda environments is not supported out of the box and needs additional setup code
# make executes every command in a separate shell: ONESHELL directive?
PYTHON_RUN_COMMAND = uv run -m app:main

REBUILD_OPTIONS = --no-cache --pull
BUILD_OPTIONS =

COMPOSE_FILE = docker-compose_test.yml

STAGING_TARGET=/home/hanauskaa-a/metricsdb

.PHONY: help rebuild build run all showver check-status tag

.DEFAULT_GOAL := help

help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)


run_tests:  ## runs tests
	uv run -m pytest test/

generate_docs:  ## generates the configuration schema documentation
#	grip doc/schema.md --export doc/schema.html

run-python:
	$(PYTHON_RUN_COMMAND)

# Docker
run-docker: ## Spin up a test container
	$(DOCKER_RUN_COMMAND)

run-docker-bash: ## Spin up bash in a test container
	$(DOCKER_RUN_COMMAND) /bin/bash

run-docker-dev: ## Mount the project's development version into the container to develop inside the container
	# Bind mount the project (in the working directory) to /app while retaining the .venv directory with an anonymous volume:
	docker run --rm --volume .:/src --volume /src/.venv

up: ## Spin up the project
	docker-compose -f $(COMPOSE_FILE) up

down: ## Stop running containers
	docker-compose -f $(COMPOSE_FILE) down


build: pre-build  ## Quick build
build: docker-build
build: post-build

# note: with the micromamba image the rebuild image size is bigger than the build image size
# due to a bigger file /var/log/lastlog
# https://stackoverflow.com/a/48770482/1504082
rebuild: pre-build ## Clean build of the image
rebuild: BUILD_OPTIONS=${REBUILD_OPTIONS}
rebuild: docker-build
rebuild: post-build

pre-build: # js

post-build:
	docker tag ${BUILD_TARGET} $(IMAGE):${TAG_LATEST}
	docker tag ${BUILD_TARGET} $(IMAGE):${RELEASE}
	@${PARSE_IMAGE_INFO}


docker-build: ## Build image with cache
	# redirect stderr to a log file
	# fixing ERROR using DOCKER_BUILDKIT=0 instead of 1
	DOCKER_BUILDKIT=0 docker buildx build $(DOCKER_BUILD_ARGS) $(BUILD_OPTIONS) $(DOCKER_BUILD_CONTEXT) -t ${BUILD_TARGET} -f $(DOCKER_FILE_PATH) 2>&1 | tee docker_build.log
	# fixing ERROR: failed to solve: error from sender: open hive-metastore: permission denied
	# https://github.com/docker/buildx/issues/1781#issuecomment-1540006373
	# does not work
	# DOCKER_BUILDKIT=1 docker build $(DOCKER_BUILD_ARGS) $(BUILD_OPTIONS) $(DOCKER_BUILD_CONTEXT) -t ${BUILD_TARGET} -f - . < tmp/Dockerfile 2>&1 | tee docker_build.log

# docker-rebuild: ## Clean build of the image, docker stage
#	docker build $(DOCKER_BUILD_ARGS) $(REBUILD_OPTIONS) -t ${BUILD_TARGET} $(DOCKER_BUILD_CONTEXT) -f $(DOCKER_FILE_PATH)



pre-push:

post-push:

dev-release:  generate_docs run_tests build push
release:  generate_docs run_tests check-status check-release build push

push: pre-push do-push post-push

do-push:  ## Save images to the local store
	docker save ${IMAGE}:${TAG} | gzip > images/${IMAGE}_${TAG}.tar.gz
# 	docker push ${IMAGE}:${TAG}
# 	docker push ${IMAGE}:${TAG_LATEST}

upload-stage:  ## Uploads the image to the staging server
	scp images/${IMAGE}_${TAG}.tar.gz staging:${STAGING_TARGET}
	scp docker-compose.yml staging:${STAGING_TARGET}

deploy-stage:
	ssh -t staging 'cd ${STAGING_TARGET} && sudo ./load_image_and_tag.sh ${IMAGE}_${TAG}.tar.gz && sudo docker compose up -d --force-recreate api'

push-stage: push upload-stage deploy-stage

# Versioning and git

show: .release  ## Shows information about the current settings
	@. $(RELEASE_SUPPORT); getRelease
	@echo "Docker tag: ${TAG}"
	@echo "Git tag: ${GIT_TAG}"
	@echo "Build target: ${BUILD_TARGET}"

tag: check-status ## Generate a git tag for the current configuration
	@. $(RELEASE_SUPPORT) ; ! tagExists $(GIT_TAG) || (echo "ERROR: tag $(GIT_TAG) for version $(DOCKER_VERSION) already tagged in git" >&2 && exit 1) ;
	 git tag $(GIT_TAG) ;
	@ if [ -n "$(shell git remote -v)" ] ; then git push --tags ; else echo 'no remote to push tags to' ; fi

check-status:  ## check source status
	@. $(RELEASE_SUPPORT) ; ! hasChanges || (echo "ERROR: there are still outstanding changes" >&2 && exit 1) ;

check-release:  ## check for sanity for release build
	@. $(RELEASE_SUPPORT) ; releaseNotesUpdated ${RELEASE} || (echo "ERROR: Release ${RELEASE} not documented in release_notes.md." >&2 && exit 1) ;
	@. $(RELEASE_SUPPORT) ; schemaUpdated ${RELEASE} || (echo "ERROR: Release ${RELEASE} not documented in doc/schema.md." >&2 && exit 1) ;
	@. $(RELEASE_SUPPORT) ; tagExists ${GIT_TAG} || (echo "ERROR: version not yet tagged in git. run make tag." >&2 && exit 1) ;
	# @. $(RELEASE_SUPPORT) ; ! differsFromRelease ${GIT_TAG} || (echo "ERROR: current directory differs from tagged ${GIT_TAG}. run make tag.") ; exit
