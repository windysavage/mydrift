IMAGE_NAME=python312-slim-app
CONTAINER_NAME=python312-container

build:
	docker build -t $(IMAGE_NAME) .
up:
	docker run --rm -it --name $(CONTAINER_NAME) $(IMAGE_NAME) bash
