.PHONY: help build build-dev build-prod run run-test run-dev clean logs

# Default target
help:
	@echo "Available commands:"
	@echo "  build      - Build production image"
	@echo "  build-dev  - Build development image with cache"
	@echo "  build-prod - Build production image without cache"
	@echo "  run        - Run production container"
	@echo "  run-test   - Run container with test library mounted"
	@echo "  run-dev    - Run development container with volumes"
	@echo "  clean      - Clean up containers and images"
	@echo "  logs       - Show container logs"

# Build production image
build:
	docker build -t komga:latest .

# Build development image (faster with cache)
build-dev:
	docker build -t komga:dev .

# Build production image without cache
build-prod:
	docker build --no-cache -t komga:latest .

# Run production container
run:
	docker run -p 25601:25601 komga:dev

# Run container with test library mounted
run-test:
	docker run -d -p 25601:25601 -v $(PWD)/test_library:/data -e KOMGA_LIBRARIES_PATHS=/data -e SPRING_PROFILES_ACTIVE=dev,noclaim --name komga-test komga:dev

# Run development container with volume mounts
run-dev:
	docker compose -f docker-compose.dev.yml up komga-dev

# Clean up
clean:
	docker system prune -f
	docker image prune -f

# Show logs
logs:
	docker compose -f docker-compose.dev.yml logs -f komga-dev 