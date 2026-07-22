# Multi-stage Dockerfile for Komga - builds both frontend and backend

# Stage 1: Build the frontend
FROM node:18-alpine as frontend-build

WORKDIR /app

# Copy frontend package files
COPY komga-webui/package*.json ./
COPY komga-webui/babel.config.js ./
COPY komga-webui/tsconfig.json ./
COPY komga-webui/vue.config.js ./

# Install frontend dependencies
RUN npm install

# Copy frontend source code
COPY komga-webui/ ./

# Build the frontend
RUN npm run build

# Stage 2: Build the backend with the built frontend
FROM eclipse-temurin:21-jdk-alpine as backend-build

# Install Node.js and Git for build tasks
RUN apk add --no-cache nodejs npm git

WORKDIR /app

# Copy gradle wrapper and build files
COPY gradlew ./
COPY gradle/ gradle/
COPY build.gradle.kts ./
COPY settings.gradle ./
COPY gradle.properties ./

# Copy the main komga module build file
COPY komga/build.gradle.kts komga/build.gradle.kts

# Make gradlew executable
RUN chmod +x ./gradlew

# Download dependencies for faster build
# Use local gradle wrapper to avoid network issues
COPY gradle-8.14.3-all.zip gradle/wrapper/gradle-8.14.3-all.zip

# Initialize git repository for git properties
RUN git init && git config user.email "docker@build.local" && git config user.name "Docker Build"

RUN ./gradlew --no-daemon dependencies --no-configuration-cache || true

# Copy the frontend build to the expected location before backend build
COPY --from=frontend-build /app/dist/ ./komga-webui/dist/

# Copy the frontend source code for npm tasks
COPY --from=frontend-build /app/ ./komga-webui/

# Copy the rest of the source code
COPY komga/ komga/

# Build the backend with the frontend assets
RUN ./gradlew --no-daemon prepareThymeLeaf bootJar -x test

# Stage 3: Runtime image (Ubuntu-based)
FROM ubuntu:25.04 AS runtime-amd64

# Prevent interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# ---- Java ----
ENV JAVA_HOME=/opt/java/openjdk
COPY --from=eclipse-temurin:24-jre ${JAVA_HOME} ${JAVA_HOME}
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# ---- System dependencies ----
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        locales \
        libjxl-dev \
        libheif-dev \
        libwebp-dev \
        libarchive-dev \
        wget \
        curl \
        python3 \
        python3-pip \
        python3-venv \
        python3-pil \
        python3-psutil \
        python3-slugify \
        p7zip-full \
        sshpass \
        openssh-client \
        tesseract-ocr \
        tesseract-ocr-eng \
        libopencv-dev \
        libgtk-3-dev \
        libglib2.0-0 \
        libmupdf-dev \
        unrar \
        libopenblas-dev \
        libjpeg-dev \
        libpng-dev \
        libtiff-dev && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen && \
    rm -rf /var/lib/apt/lists/*

# ---- Kepubify ----
RUN wget -O /usr/bin/kepubify \
        https://github.com/pgaskin/kepubify/releases/latest/download/kepubify-linux-64bit && \
    chmod +x /usr/bin/kepubify

# ---- Runtime library path ----
ENV LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}"

# ---- Python dependencies ----
COPY requirements.txt /tmp/requirements.txt
RUN if [ -f /tmp/requirements.txt ]; then \
        pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt; \
    fi

# ---- Custom Python scripts ----
COPY komga_custom/ /app/komga_custom/
RUN chmod +x /app/komga_custom/*.py

# ---- App directory ----
WORKDIR /app

# ---- Komga JAR ----
COPY --from=backend-build --chown=1000:1000 \
    /app/komga/build/libs/*.jar /app/komga.jar

# ---- Config volume ----
VOLUME /config
RUN mkdir -p /config && chown 1000:1000 /config

# ---- Runtime user ----
USER ubuntu

# ---- Locale & Komga config ----
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    KOMGA_CONFIGDIR=/config

# ---- Network ----
EXPOSE 25600

# ---- Entrypoint ----
ENTRYPOINT ["java", "-Dspring.profiles.include=docker", "--enable-native-access=ALL-UNNAMED", "-jar", "komga.jar", "--spring.config.additional-location=file:/config/"]
