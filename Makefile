#!/usr/bin/make

ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
VERSION := $(shell cat $(ROOT_DIR)/VERSION)

DOCKER_IMAGE := simonklb/matrix-leaf

all: build

lint:
	flake8 $(ROOT_DIR)leaf/*

build:
	docker build -t $(DOCKER_IMAGE):$(VERSION) $(ROOT_DIR)

deploy: build
	docker tag $(DOCKER_IMAGE):$(VERSION) $(DOCKER_IMAGE):latest
	docker push $(DOCKER_IMAGE):$(VERSION)
	docker push $(DOCKER_IMAGE):latest

clean:
	find ./leaf -name "__pycache__" | xargs rm -rf
	find ./leaf -name "*.pyc" | xargs rm -rf

docs:
	sphinx-apidoc -f -o $(ROOT_DIR)docs/source $(ROOT_DIR)leaf
	cd $(ROOT_DIR)docs && make html

docs-coverage:
	SPHINX_APIDOC_OPTIONS=members sphinx-apidoc -f -o \
			$(ROOT_DIR)docs/source $(ROOT_DIR)leaf
	cd $(ROOT_DIR)docs && make coverage

.PHONY: lint build deploy clean docs docs-coverage
