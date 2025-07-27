# Stage 1: Build the frontend
FROM node:18 AS frontend-build
WORKDIR /app/komga-webui
# Copy package files first for better caching
COPY komga-webui/package*.json ./
RUN npm install
# Copy source code after dependencies
COPY komga-webui/ .
RUN npm run build

# Stage 2: Build the backend
FROM gradle:8.5.0-jdk21 AS backend-build
WORKDIR /app
# Copy gradle files first for better caching
COPY gradle/ ./gradle/
COPY gradlew ./
COPY build.gradle.kts ./
COPY settings.gradle ./
# Download dependencies
RUN ./gradlew dependencies --no-daemon
# Copy source code after dependencies
COPY . .
# Copy built frontend from previous stage
COPY --from=frontend-build /app/komga-webui/dist ./komga/src/main/resources/public
RUN ./gradlew clean build -x test -PskipGitProperties=true

# Stage 3: Run the app
FROM eclipse-temurin:21-jre
WORKDIR /app
# Install system dependencies first (these change less frequently)
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv rar unrar sshpass && rm -rf /var/lib/apt/lists/*
# Copy Python requirements and install dependencies (separate from source)
COPY requirements.txt ./
RUN if [ -f requirements.txt ]; then \
        python3 -m venv /opt/venv && \
        . /opt/venv/bin/activate && \
        pip3 install --no-cache-dir -r requirements.txt; \
    fi
# Copy the Python script
COPY komga_custom/push_to_kindle.py /app/komga_custom/push_to_kindle.py
# Create a wrapper script to use the virtual environment
RUN echo '#!/bin/bash\n/opt/venv/bin/python3 "$@"' > /usr/local/bin/python3-venv && \
    chmod +x /usr/local/bin/python3-venv
# Copy the final JAR (this changes most frequently, so do it last)
COPY --from=backend-build /app/komga/build/libs/komga-*.jar /app/komga.jar
EXPOSE 25601
ENTRYPOINT ["java", "-jar", "/app/komga.jar", "--server.port=25601"] 