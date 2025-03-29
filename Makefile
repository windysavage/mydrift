build:
	docker compose -f docker/docker-compose.yaml build
clean-build:
	docker compose -f docker/docker-compose.yaml build --no-cache
up:
	docker compose -f docker/docker-compose.yaml up
