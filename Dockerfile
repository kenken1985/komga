# Stage 1: Build the frontend
FROM node:18 AS frontend-build
WORKDIR /app/komga-webui

ENV NODE_OPTIONS="--max-old-space-size=16384"

# Copy package files first for better caching
COPY komga-webui/package*.json ./
RUN npm install
# Copy source code after dependencies
COPY komga-webui/ .
RUN npm run build

# Stage 2: Build the backend
FROM gradle:8.14.3-jdk21 AS backend-build
WORKDIR /app
# Set up Gradle cache directory
ENV GRADLE_USER_HOME=/home/gradle/.gradle
# Copy gradle files first for better caching
COPY gradle/ ./gradle/
COPY gradle/wrapper/gradle-wrapper.jar ./gradle/wrapper/
COPY gradlew ./
COPY gradle.properties ./
COPY build.gradle.kts ./
COPY settings.gradle ./
# Download dependencies
RUN ./gradlew dependencies --no-daemon
# Copy source code after dependencies
# Copy only the files needed for backend build, excluding komga_custom
COPY komga/ ./komga/
# Copy built frontend from previous stage
COPY --from=frontend-build /app/komga-webui/dist ./komga/src/main/resources/public
RUN ./gradlew clean build -x test -x ktlintKotlinScriptCheck -x ktlintMainSourceSetCheck -x ktlintTestSourceSetCheck -x ktlintBenchmarkSourceSetCheck -PskipGitProperties=true

# Stage 3: Extract layers
FROM eclipse-temurin:21-jre AS builder
WORKDIR /builder
COPY --from=backend-build /app/komga/build/libs/komga-*.jar application.jar
RUN java -Djarmode=tools -jar application.jar extract --layers --destination extracted

# Stage 4: Architecture-specific runtime setup
# amd64 runtime
FROM ubuntu:25.04 AS runtime-amd64
ENV JAVA_HOME=/opt/java/openjdk
COPY --from=eclipse-temurin:21-jre $JAVA_HOME $JAVA_HOME
ENV PATH="${JAVA_HOME}/bin:${PATH}"
RUN apt-get update && \
    apt-get install -y \
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
        sshpass && \
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen en_US.UTF-8 && \
    wget "https://github.com/pgaskin/kepubify/releases/latest/download/kepubify-linux-64bit" -O /usr/bin/kepubify && \
    chmod +x /usr/bin/kepubify && \
    apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/lib/x86_64-linux-gnu"

# arm64 runtime
FROM ubuntu:25.04 AS runtime-arm64
ENV JAVA_HOME=/opt/java/openjdk
COPY --from=eclipse-temurin:21-jre $JAVA_HOME $JAVA_HOME
ENV PATH="${JAVA_HOME}/bin:${PATH}"
RUN apt-get update && \
    apt-get install -y \
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
        sshpass && \
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen en_US.UTF-8 && \
    wget "https://github.com/pgaskin/kepubify/releases/latest/download/kepubify-linux-arm64" -O /usr/bin/kepubify && \
    chmod +x /usr/bin/kepubify && \
    apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/lib/aarch64-linux-gnu"

# Use TARGETARCH to select appropriate runtime
FROM runtime-${TARGETARCH} AS final

# Configure volumes
VOLUME /tmp
VOLUME /config
WORKDIR /app

# Copy extracted layers and application jar from builder
COPY --from=builder /builder/extracted/dependencies/ ./
COPY --from=builder /builder/extracted/spring-boot-loader/ ./
COPY --from=builder /builder/extracted/snapshot-dependencies/ ./
COPY --from=builder /builder/extracted/application/ ./
COPY --from=builder /builder/application.jar ./

# Install Python dependencies
COPY requirements.txt ./
RUN if [ -f requirements.txt ]; then \
        pip3 install --no-cache-dir --break-system-packages -r requirements.txt; \
    fi

# Copy custom Python scripts
COPY komga_custom/ /app/komga_custom/
RUN chmod +x /app/komga_custom/*.py

# Environment configuration
ENV KOMGA_CONFIGDIR="/config"
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'

EXPOSE 25600
ENTRYPOINT ["java", "-Dspring.profiles.include=docker", "--enable-native-access=ALL-UNNAMED", "-jar", "application.jar", "--spring.config.additional-location=file:/config/"]
LABEL org.opencontainers.image.source="https://github.com/gotson/komga"
