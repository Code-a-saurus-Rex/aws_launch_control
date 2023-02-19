# get project path
project_path := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

# get path basename
project := $(shell basename $$PWD)
image_name=${project}-image
container_name=${project}-container

build:
	docker build --build-arg GITHUB_PAT=${GITHUB_PAT} --tag ${image_name} .

run:
	make build; \
	docker stop ${container_name}; \
	docker rm ${container_name}; \
	docker run \
		-ti \
		-d \
		-v ${project_path}:/home/ \
		--name ${container_name} \
		${image_name}

run_test:
	docker exec ${container_name} lc -v

test:
	make build; make run; make run_test;

shell:
	docker exec -ti ${container_name} bash

start:
	docker start ${container_name};

stop:
	docker stop ${container_name};

restart:
	docker restart ${container_name};

a:
	echo ${PROJECT_NAME}