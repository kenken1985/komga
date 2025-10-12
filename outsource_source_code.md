# Komga Frontend Routing Bug Analysis and Fix

## Goal
Fix the "No mapping for GET" errors when accessing Komga URLs directly via IP address (e.g., `<ip>/book/0KD1JKYHXH0XG/read`). The issue occurs in a Docker environment without reverse proxy where users access Komga directly via IP:PORT.

### Error Log
```
komga-kindle-1  | 2025-10-12T06:51:46.533-04:00  WARN 1 --- [io-25600-exec-3] o.s.web.servlet.PageNotFound             : No mapping for GET /book/0KD1JKYHXH0XG/read
komga-kindle-1  | 2025-10-12T06:51:46.615-04:00  WARN 1 --- [io-25600-exec-1] o.s.web.servlet.PageNotFound             : No mapping for GET /book/0KD1JKYHXH0XG/js/chunk-vendors.3366e51a.js
komga-kindle-1  | 2025-10-12T06:51:46.619-04:00  WARN 1 --- [io-25600-exec-6] o.s.web.servlet.PageNotFound             : No mapping for GET /book/0KD1JKYHXH0XG/css/app.c113e1ad.css
komga-kindle-1  | 2025-10-12T06:51:46.619-04:00  WARN 1 --- [io-25600-exec-7] o.s.web.servlet.PageNotFound             : No mapping for GET /book/0KD1JKYHXH0XG/js/app.c8577053.js
komga-kindle-1  | 2025-10-12T06:51:46.619-04:00  WARN 1 --- [io-25600-exec-4] o.s.web.servlet.PageNotFound             : No mapping for GET /book/0KD1JKYHXH0XG/css/chunk-vendors.420551a9.css
```

## Root Cause Analysis
The issue stems from a mismatch between the Vue.js router base path configuration and how users access the application in a Docker environment. When users access Komga via `<ip>:<port>/`, the Vue.js router expects all routes to be relative to this base path, but the application is not properly configured to handle this scenario.

### Problem Details
1. **Vue Router Configuration**: The router uses `mode: 'history'` with a dynamic base path determined by `urls.base`
2. **URL Base Configuration**: The base path is set differently for development (`'/'`) and production (`'./'`)
3. **Access Pattern**: Users access via `<ip>:<port>/` but the router expects routes to be relative to this path
4. **Resource Loading**: JavaScript and CSS files are being requested with incorrect paths, causing 404 errors

## Complete Folder Structure
```
komga/
├── build.gradle.kts                 # Gradle build configuration
├── Dockerfile                       # Multi-stage Docker build configuration
├── komga-webui/
│   ├── src/
│   │   ├── functions/
│   │   │   └── urls.ts              # URL configuration and base path logic
│   │   ├── main.ts                  # Vue.js application entry point
│   │   ├── router.ts                # Vue.js router configuration
│   │   ├── views/
│   │   │   ├── PageNotFound.vue     # 404 page component
│   │   │   ├── DivinaReader.vue     # Book reader component (for /book/:bookId/read)
│   │   │   └── EpubReader.vue       # EPUB reader component (for /book/:bookId/read-epub)
│   │   └── public-path.js           # Webpack public path configuration
│   └── vue.config.js                # Vue CLI configuration
└── komga/src/main/kotlin/org/gotson/komga/
    └── infrastructure/web/
        └── WebMvcConfiguration.kt    # Spring Boot resource handling configuration
```

## Source Code Files Analysis

### File: build.gradle.kts
This is the main Gradle build configuration file that defines the project structure, dependencies, and build processes. It includes configuration for multi-stage Docker builds and dependency management.


```text
import com.github.benmanes.gradle.versions.updates.DependencyUpdatesTask
import org.jreleaser.model.Active
import org.jreleaser.model.Distribution.DistributionType.SINGLE_JAR
import org.jreleaser.model.api.common.Apply
import kotlin.io.path.Path
import kotlin.io.path.exists

plugins {
  run {
    val kotlinVersion = "2.2.0"
    kotlin("jvm") version kotlinVersion
    kotlin("plugin.spring") version kotlinVersion
    kotlin("kapt") version kotlinVersion
  }
  id("org.jlleitschuh.gradle.ktlint") version "13.0.0"
  id("com.github.ben-manes.versions") version "0.52.0"
  id("org.jreleaser") version "1.19.0"
}

fun isNonStable(version: String): Boolean {
  val stableKeyword = listOf("RELEASE", "FINAL", "GA").any { version.uppercase().contains(it) }
  val unstableKeyword = listOf("ALPHA", "RC").any { version.uppercase().contains(it) }
  val regex = "^[0-9,.v-]+(-r)?$".toRegex()
  val isStable = stableKeyword || regex.matches(version)
  return unstableKeyword || !isStable
}

group = "org.gotson"

allprojects {
  repositories {
    mavenCentral()
  }
  apply(plugin = "org.jlleitschuh.gradle.ktlint")
  apply(plugin = "com.github.ben-manes.versions")

  tasks.named<DependencyUpdatesTask>("dependencyUpdates").configure {
    // disallow release candidates as upgradable versions from stable versions
    rejectVersionIf {
      isNonStable(candidate.version) && !isNonStable(currentVersion)
    }
    gradleReleaseChannel = "current"
    checkConstraints = true
  }

  configure<org.jlleitschuh.gradle.ktlint.KtlintExtension> {
    version = "1.7.1"
    filter {
      exclude("**/generated-src/**")
      exclude("**/generated/**")
    }
  }
}

tasks.wrapper {
  gradleVersion = "8.14.3"
  distributionType = Wrapper.DistributionType.ALL
}

jreleaser {
  project {
    description = "Media server for comics/mangas/BDs with API and OPDS support"
    copyright = "Gauthier Roebroeck"
    authors.add("Gauthier Roebroeck")
    license = "MIT"
    links {
      homepage = "https://komga.org"
    }
  }

  release {
    github {
      discussionCategoryName = "Announcements"
      skipTag = true
      tagName = "{{projectVersion}}"

      changelog {
        formatted = Active.ALWAYS
        preset = "conventional-commits"
        skipMergeCommits = true
        links = true
        content = (if (Path("./release_notes/release_notes.md").exists()) "{{#f_file_read}}{{basedir}}/release_notes/release_notes.md{{/f_file_read}}" else "") +
          """
          ## Changelog

          {{changelogChanges}}
          {{changelogContributors}}
          """.trimIndent()
        format = "- {{#commitIsConventional}}{{#conventionalCommitIsBreakingChange}}🚨 {{/conventionalCommitIsBreakingChange}}{{#conventionalCommitScope}}**{{conventionalCommitScope}}**: {{/conventionalCommitScope}}{{conventionalCommitDescription}}{{#conventionalCommitBreakingChangeContent}}: *{{conventionalCommitBreakingChangeContent}}*{{/conventionalCommitBreakingChangeContent}} ({{commitShortHash}}){{/commitIsConventional}}{{^commitIsConventional}}{{commitTitle}} ({{commitShortHash}}){{/commitIsConventional}}{{#commitHasIssues}}, closes{{#commitIssues}} {{issue}}{{/commitIssues}}{{/commitHasIssues}}"
        hide {
          uncategorized = true
          contributors = listOf("Weblate", "GitHub", "semantic-release-bot", "[bot]", "github-actions")
        }
        excludeLabels.add("chore")
        category {
          title = "🏎 Perf"
          key = "perf"
          labels.add("perf")
          order = 25
        }
        category {
          title = "🌐 Translation"
          key = "i18n"
          labels.add("i18n")
          order = 70
        }
        category {
          title = "⚙️ Dependencies"
          key = "dependencies"
          labels.add("dependencies")
          order = 80
        }
        labeler {
          label = "perf"
          title = "regex:^(?:perf(?:\\(.*\\))?!?):\\s.*"
          order = 120
        }
        labeler {
          label = "i18n"
          title = "regex:^(?:i18n(?:\\(.*\\))?!?):\\s.*"
          order = 130
        }
        labeler {
          label = "dependencies"
          title = "regex:^(?:deps(?:\\(.*\\))?!?):\\s.*"
          order = 140
        }
        extraProperties.put("categorizeScopes", true)
        append {
          enabled = true
          title = "# [{{projectVersion}}]({{repoUrl}}/compare/{{previousTagName}}...{{tagName}}) ({{#f_now}}YYYY-MM-dd{{/f_now}})"
          target = rootDir.resolve("CHANGELOG.md")
          content =
            """
            {{changelogTitle}}
            {{changelogChanges}}
            """.trimIndent()
        }
      }

      issues {
        enabled = true
        comment = "🎉 This issue has been resolved in `{{tagName}}` ([Release Notes]({{releaseNotesUrl}}))"
        applyMilestone = Apply.ALWAYS
        label {
          name = "released"
          description = "Issue has been released"
          color = "#ededed"
        }
      }
    }
  }

  distributions {
    create("komga") {
      active = Active.RELEASE
      distributionType = SINGLE_JAR
      artifact {
        path = rootDir.resolve("komga/build/libs/komga-{{projectVersion}}.jar")
      }
    }
  }

  packagers {
    docker {
      active = Active.RELEASE
      continueOnError = true
      templateDirectory = rootDir.resolve("komga/docker")
      repository.active = Active.NEVER
      buildArgs = listOf("--cache-from", "gotson/komga:latest")
      imageNames =
        listOf(
          "komga:latest",
          "komga:{{projectVersion}}",
          "komga:{{projectVersionMajor}}.x",
        )
      registries {
        create("docker.io") { externalLogin = true }
        create("ghcr.io") { externalLogin = true }
      }
      buildx {
        enabled = true
        createBuilder = false
        platforms =
          listOf(
            "linux/amd64",
            "linux/arm/v7",
            "linux/arm64/v8",
          )
      }
    }
  }
}

```
### File: Dockerfile
Multi-stage Docker build configuration that builds the frontend (Vue.js) and backend (Kotlin/Spring Boot) separately, then combines them into a final production image. This is critical for understanding how the application is deployed and how the frontend static resources are served.


```text
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
FROM gradle:8.14.3-jdk24 AS backend-build
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
# Use the Gradle installed in the container directly to skip wrapper download
RUN gradle dependencies --no-daemon
# Copy source code after dependencies
# Copy only the files needed for backend build, excluding komga_custom
COPY komga/ ./komga/
# Copy built frontend from previous stage
COPY --from=frontend-build /app/komga-webui/dist ./komga/src/main/resources/public
RUN gradle clean build -x test -x ktlintKotlinScriptCheck -x ktlintMainSourceSetCheck -x ktlintTestSourceSetCheck -x ktlintBenchmarkSourceSetCheck -PskipGitProperties=true

# Stage 3: Extract layers
FROM eclipse-temurin:24-jre AS builder
WORKDIR /builder
COPY --from=backend-build /app/komga/build/libs/komga-*.jar application.jar
RUN java -Djarmode=tools -jar application.jar extract --layers --destination extracted

# Stage 4: Architecture-specific runtime setup
# amd64 runtime
FROM ubuntu:25.04 AS runtime-amd64
ENV JAVA_HOME=/opt/java/openjdk
COPY --from=eclipse-temurin:24-jre $JAVA_HOME $JAVA_HOME
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
        sshpass \
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
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen en_US.UTF-8 && \
    wget "https://github.com/pgaskin/kepubify/releases/latest/download/kepubify-linux-64bit" -O /usr/bin/kepubify && \
    chmod +x /usr/bin/kepubify && \
    apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/lib/x86_64-linux-gnu"

# arm64 runtime
FROM ubuntu:25.04 AS runtime-arm64
ENV JAVA_HOME=/opt/java/openjdk
COPY --from=eclipse-temurin:24-jre $JAVA_HOME $JAVA_HOME
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
        sshpass \
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

```
### File: komga-webui/src/functions/urls.ts
This file contains the URL configuration logic that determines the base path for the Vue.js router. The current implementation uses `window.resourceBaseUrl` which may not be properly set in the Docker environment.


```typescript
import {PageHashKnownDto, PageHashUnknownDto} from '@/types/komga-pagehashes'

const fullUrl = process.env.VUE_APP_KOMGA_API_URL
  ? process.env.VUE_APP_KOMGA_API_URL
  : window.location.origin + window.resourceBaseUrl
const baseUrl = process.env.NODE_ENV === 'production' ? window.resourceBaseUrl : '/'

const urls = {
  origin: !fullUrl.endsWith('/') ? `${fullUrl}/` : fullUrl,
  originNoSlash: fullUrl.endsWith('/') ? fullUrl.slice(0, -1) : fullUrl,
  base: !baseUrl.endsWith('/') ? `${baseUrl}/` : baseUrl,
  baseNoSlash: baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl,
} as Urls

export default urls

export function bookThumbnailUrl(bookId: string): string {
  return `${urls.originNoSlash}/api/v1/books/${bookId}/thumbnail`
}

export function bookThumbnailUrlByThumbnailId(bookId: string, thumbnailId: string) {
  return `${urls.originNoSlash}/api/v1/books/${bookId}/thumbnails/${thumbnailId}`
}

export function bookFileUrl(bookId: string): string {
  return `${urls.originNoSlash}/api/v1/books/${bookId}/file`
}

export function bookPageUrl(bookId: string, page: number, convertTo?: string): string {
  let url = `${urls.originNoSlash}/api/v1/books/${bookId}/pages/${page}`
  if (convertTo) {
    url += `?convert=${convertTo}`
  }
  return url
}

export function bookPageThumbnailUrl(bookId: string, page: number): string {
  return `${urls.originNoSlash}/api/v1/books/${bookId}/pages/${page}/thumbnail`
}

export function bookManifestUrl(bookId: string): string {
  return `${urls.originNoSlash}/api/v1/books/${bookId}/manifest`
}

export function bookPositionsUrl(bookId: string): string {
  return `${urls.originNoSlash}/api/v1/books/${bookId}/positions`
}
export function seriesFileUrl(seriesId: string): string {
  return `${urls.originNoSlash}/api/v1/series/${seriesId}/file`
}

export function seriesThumbnailUrl(seriesId: string): string {
  return `${urls.originNoSlash}/api/v1/series/${seriesId}/thumbnail`
}

export function seriesThumbnailUrlByThumbnailId(seriesId: string, thumbnailId: string) {
  return `${urls.originNoSlash}/api/v1/series/${seriesId}/thumbnails/${thumbnailId}`
}

export function collectionThumbnailUrl(collectionId: string): string {
  return `${urls.originNoSlash}/api/v1/collections/${collectionId}/thumbnail`
}

export function collectionThumbnailUrlByThumbnailId(collectionId: string, thumbnailId: string) {
  return `${urls.originNoSlash}/api/v1/collections/${collectionId}/thumbnails/${thumbnailId}`
}

export function readListThumbnailUrl(readListId: string): string {
  return `${urls.originNoSlash}/api/v1/readlists/${readListId}/thumbnail`
}

export function readListFileUrl(readListId: string): string {
  return `${urls.originNoSlash}/api/v1/readlists/${readListId}/file`
}

export function readListThumbnailUrlByThumbnailId(readListId: string, thumbnailId: string) {
  return `${urls.originNoSlash}/api/v1/readlists/${readListId}/thumbnails/${thumbnailId}`
}

export function transientBookPageUrl(transientBookId: string, page: number): string {
  return `${urls.originNoSlash}/api/v1/transient-books/${transientBookId}/pages/${page}`
}

export function pageHashUnknownThumbnailUrl(pageHash: PageHashUnknownDto, resize?: number): string {
  let url = `${urls.originNoSlash}/api/v1/page-hashes/unknown/${pageHash.hash}/thumbnail`
  if(resize) {
    url += `?resize=${resize}`
  }
  return url
}

export function pageHashKnownThumbnailUrl(pageHash: PageHashKnownDto): string {
  return `${urls.originNoSlash}/api/v1/page-hashes/${pageHash.hash}/thumbnail`
}

```
### File: komga-webui/src/router.ts
Contains the Vue.js router configuration with history mode and route definitions. The router uses the `urls.base` configuration as its base path.


```typescript
import urls from '@/functions/urls'
import Vue from 'vue'
import Router from 'vue-router'
import store from './store'
import {LIBRARIES_ALL, LIBRARY_ROUTE} from '@/types/library'

const qs = require('qs')

Vue.use(Router)

const lStore = store as any

const adminGuard = (to: any, from: any, next: any) => {
  if (!lStore.getters.meAdmin) next({name: 'home'})
  else next()
}

const noLibraryGuard = (to: any, from: any, next: any) => {
  if (lStore.state.komgaLibraries.libraries.length === 0) {
    next({name: 'welcome'})
  } else next()
}

const noLibraryNorPinGuard = (to: any, from: any, next: any) => {
  if (lStore.state.komgaLibraries.libraries.length === 0) {
    next({name: 'welcome'})
  } else if (lStore.getters.getLibrariesPinned.length === 0) {
    next({name: 'no-pins'})
  } else next()
}

const getLibraryRoute = (libraryId: string) => {
  switch ((lStore.getters.getLibraryRoute(libraryId) as LIBRARY_ROUTE)) {
    case LIBRARY_ROUTE.COLLECTIONS:
      return 'browse-collections'
    case LIBRARY_ROUTE.READLISTS:
      return 'browse-readlists'
    case LIBRARY_ROUTE.BROWSE:
      return 'browse-libraries'
    case LIBRARY_ROUTE.BOOKS:
      return 'browse-books'
    case LIBRARY_ROUTE.RECOMMENDED:
    default:
      return libraryId === LIBRARIES_ALL ? 'browse-libraries' : 'recommended-libraries'
  }
}

const router = new Router({
  mode: 'history',
  base: urls.base,
  parseQuery(query: string) {
    return qs.parse(query)
  },
  stringifyQuery(query: Object) {
    const res = qs.stringify(query)
    return res ? `?${res}` : ''
  },
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: {name: 'dashboard'},
      component: () => import(/* webpackChunkName: "home" */ './views/HomeView.vue'),
      children: [
        {
          path: '/welcome',
          name: 'welcome',
          component: () => import(/* webpackChunkName: "welcome" */ './views/WelcomeView.vue'),
        },
        {
          path: '/no-pins',
          name: 'no-pins',
          component: () => import(/* webpackChunkName: "no-pins" */ './views/NoPinnedLibraries.vue'),
        },
        {
          path: '/dashboard',
          name: 'dashboard',
          beforeEnter: noLibraryNorPinGuard,
          component: () => import(/* webpackChunkName: "dashboard" */ './views/DashboardView.vue'),
        },
        {
          path: '/settings/users',
          name: 'settings-users',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "settings-users" */ './views/SettingsUsers.vue'),
          children: [
            {
              path: '/settings/users/add',
              name: 'settings-users-add',
              component: () => import(/* webpackChunkName: "settings-user" */ './components/dialogs/UserAddDialog.vue'),
            },
          ],
        },
        {
          path: '/settings/server',
          name: 'settings-server',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "settings-server" */ './views/SettingsServer.vue'),
        },
        {
          path: '/settings/ui',
          name: 'settings-ui',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "settings-ui" */ './views/UISettings.vue'),
        },
        {
          path: '/settings/metrics',
          name: 'metrics',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "metrics" */ './views/MetricsView.vue'),
        },
        {
          path: '/settings/announcements',
          name: 'announcements',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "announcements" */ './views/AnnouncementsView.vue'),
        },
        {
          path: '/settings/updates',
          name: 'updates',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "updates" */ './views/UpdatesView.vue'),
        },
        {
          path: '/media-management/analysis',
          name: 'media-analysis',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "media-analysis" */ './views/MediaAnalysis.vue'),
        },
        {
          path: '/media-management/missing-posters',
          name: 'missing-posters',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "missing-posters" */ './views/MissingPosters.vue'),
        },
        {
          path: '/media-management/duplicate-files',
          name: 'duplicate-files',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "duplicate-files" */ './views/DuplicateFiles.vue'),
        },
        {
          path: '/media-management/duplicate-pages/known',
          name: 'settings-duplicate-pages-known',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "duplicate-pages-known" */ './views/DuplicatePagesKnown.vue'),
        },
        {
          path: '/media-management/duplicate-pages/unknown',
          name: 'settings-duplicate-pages-unknown',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "duplicate-pages-new" */ './views/DuplicatePagesUnknown.vue'),
        },
        {
          path: '/history',
          name: 'history',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "history" */ './views/HistoryView.vue'),
        },
        {
          path: '/account/me',
          name: 'account-me',
          component: () => import(/* webpackChunkName: "account-me" */ './views/AccountView.vue'),
        },
        {
          path: '/account/api-keys',
          name: 'account-api-keys',
          component: () => import(/* webpackChunkName: "account-api-keys" */ './views/ApiKeys.vue'),
        },
        {
          path: '/account/settings-ui',
          name: 'account-settings-ui',
          component: () => import(/* webpackChunkName: "account-settings-ui" */ './views/UIUserSettings.vue'),
        },
        {
          path: '/account/authentication-activity',
          name: 'account-activity',
          component: () => import(/* webpackChunkName: "account-activity" */ './views/SelfAuthenticationActivity.vue'),
        },
        {
          path: '/libraries/:libraryId?',
          name: 'libraries',
          redirect: (route) => ({
            name: getLibraryRoute(route.params.libraryId || LIBRARIES_ALL),
            params: {libraryId: route.params.libraryId || LIBRARIES_ALL},
          }),
        },
        {
          path: '/libraries/:libraryId/recommended',
          name: 'recommended-libraries',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "dashboard" */ './views/DashboardView.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/libraries/:libraryId/books',
          name: 'browse-books',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "browse-books" */ './views/BrowseBooks.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/libraries/:libraryId/series',
          name: 'browse-libraries',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "browse-libraries" */ './views/BrowseLibraries.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/libraries/:libraryId/collections',
          name: 'browse-collections',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "browse-collections" */ './views/BrowseCollections.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/libraries/:libraryId/readlists',
          name: 'browse-readlists',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "browse-readlists" */ './views/BrowseReadLists.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/collections/:collectionId',
          name: 'browse-collection',
          component: () => import(/* webpackChunkName: "browse-collection" */ './views/BrowseCollection.vue'),
          props: (route) => ({collectionId: route.params.collectionId}),
        },
        {
          path: '/readlists/:readListId',
          name: 'browse-readlist',
          component: () => import(/* webpackChunkName: "browse-readlist" */ './views/BrowseReadList.vue'),
          props: (route) => ({readListId: route.params.readListId}),
        },
        {
          path: '/series/:seriesId',
          name: 'browse-series',
          component: () => import(/* webpackChunkName: "browse-series" */ './views/BrowseSeries.vue'),
          props: (route) => ({seriesId: route.params.seriesId}),
        },
        {
          path: '/book/:bookId',
          name: 'browse-book',
          component: () => import(/* webpackChunkName: "browse-book" */ './views/BrowseBook.vue'),
          props: (route) => ({bookId: route.params.bookId}),
        },
        {
          path: '/oneshot/:seriesId',
          name: 'browse-oneshot',
          component: () => import(/* webpackChunkName: "browse-oneshot" */ './views/BrowseOneshot.vue'),
          props: (route) => ({seriesId: route.params.seriesId}),
        },
        {
          path: '/search',
          name: 'search',
          component: () => import(/* webpackChunkName: "search" */ './views/SearchView.vue'),
        },
        {
          path: '/import/books',
          name: 'import-books',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "import-books" */ './views/ImportBooks.vue'),
        },
        {
          path: '/import/readlist',
          name: 'import-readlist',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "import-readlist" */ './views/ImportReadList.vue'),
        },
      ],
    },
    {
      path: '/startup',
      name: 'startup',
      component: () => import(/* webpackChunkName: "startup" */ './views/StartupView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import(/* webpackChunkName: "login" */ './views/LoginView.vue'),
    },
    {
      path: '/book/:bookId/read',
      name: 'read-book',
      component: () => import(/* webpackChunkName: "read-book" */ './views/DivinaReader.vue'),
      props: (route) => ({bookId: route.params.bookId}),
    },
    {
      path: '/book/:bookId/read-epub',
      name: 'read-epub',
      component: () => import(/* webpackChunkName: "read-epub" */ './views/EpubReader.vue'),
      props: (route) => ({bookId: route.params.bookId}),
    },
    {
      path: '*',
      name: 'notfound',
      component: () => import(/* webpackChunkName: "notfound" */ './views/PageNotFound.vue'),
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      if (to.name !== from.name) {
        return {x: 0, y: 0}
      }
    }
  },
})

router.beforeEach((to, from, next) => {
  // avoid document.title flickering when changing route
  if (!['read-book', 'read-epub', 'browse-book', 'browse-oneshot', 'browse-series', 'browse-libraries', 'browse-books',
    'recommended-libraries', 'browse-collection', 'browse-collections', 'browse-readlist', 'browse-readlists'].includes(<string>to.name)
  ) {
    document.title = 'Komga'
  }

  if (window.opener !== null &&
    window.name === 'oauth2Login' &&
    to.query.server_redirect === 'Y'
  ) {
    if (!to.query.error) {
      // authentication succeeded, we redirect the parent window so that it can login via cookie
      window.opener.location.href = urls.origin
    } else {
      // authentication failed, we cascade the error message to the parent
      window.opener.location.href = window.location
    }
    // we can close the popup
    window.close()
  }

  if (to.name !== 'startup' && to.name !== 'login' && !lStore.getters.authenticated) {
    const query = Object.assign({}, to.query, {redirect: to.fullPath})
    next({name: 'startup', query: query})
  } else next()
})

export default router

```
### File: komga-webui/src/public-path.js
Configures the webpack public path for asset loading. This is critical for ensuring that JavaScript and CSS files are loaded correctly in different environments.


```javascript
// eslint-disable-next-line camelcase
__webpack_public_path__ = process.env.NODE_ENV === 'production' ? window.location.origin + window.resourceBaseUrl : '/'

```
### File: komga-webui/src/views/PageNotFound.vue
The 404 page component that users see when they encounter routing issues.


```vue
<template>
  <v-row justify="center">
    <empty-state :title="$t('page_not_found.page_not_found')"
                 :sub-title="$t('page_not_found.page_does_not_exist')"
                 icon="mdi-help-circle"
                 icon-color="secondary"
    >
      <v-btn color="primary" :to="{name: 'home'}">{{ $t('page_not_found.go_back_to_home_page') }}</v-btn>
    </empty-state>
  </v-row>
</template>

<script lang="ts">
import EmptyState from '@/components/EmptyState.vue'
import Vue from 'vue'

export default Vue.extend({
  name: 'PageNotFound',
  components: { EmptyState },
})
</script>

<style scoped>

</style>

```
### File: komga/src/main/kotlin/org/gotson/komga/infrastructure/web/WebMvcConfiguration.kt
Spring Boot configuration for serving static resources. This handles serving the built Vue.js application and static assets.

## Data Structures


```kotlin
package org.gotson.komga.infrastructure.web

import org.springframework.context.annotation.Configuration
import org.springframework.http.CacheControl
import org.springframework.web.method.support.HandlerMethodArgumentResolver
import org.springframework.web.servlet.config.annotation.InterceptorRegistry
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer
import org.springframework.web.servlet.mvc.WebContentInterceptor
import java.util.concurrent.TimeUnit

@Configuration
class WebMvcConfiguration : WebMvcConfigurer {
  override fun addResourceHandlers(registry: ResourceHandlerRegistry) {
    if (!registry.hasMappingForPattern("/webjars/**")) {
      registry
        .addResourceHandler("/webjars/**")
        .addResourceLocations("classpath:/META-INF/resources/webjars/")
    }

    if (!registry.hasMappingForPattern("/swagger-ui.html**")) {
      registry
        .addResourceHandler("/swagger-ui.html**")
        .addResourceLocations("classpath:/META-INF/resources/")
    }

    registry
      .addResourceHandler(
        "/index.html",
        "/favicon.ico",
        "/favicon-16x16.png",
        "/favicon-32x32.png",
        "/mstile-144x144.png",
        "/apple-touch-icon.png",
        "/apple-touch-icon-180x180.png",
        "/android-chrome-192x192.png",
        "/android-chrome-512x512.png",
        "/manifest.json",
      ).addResourceLocations("classpath:public/")
      .setCacheControl(CacheControl.noStore())

    listOf("css", "fonts", "img", "js")
      .forEach {
        registry
          .addResourceHandler("/$it/**")
          .addResourceLocations("classpath:public/$it/")
          .setCacheControl(CacheControl.maxAge(365, TimeUnit.DAYS).cachePublic())
      }
  }

  override fun addInterceptors(registry: InterceptorRegistry) {
    registry.addInterceptor(
      WebContentInterceptor().apply {
        addCacheMapping(
          cachePrivate,
          "/api/**",
          "/opds/**",
        )
      },
    )
  }

  override fun addArgumentResolvers(resolvers: MutableList<HandlerMethodArgumentResolver>) {
    resolvers.add(AuthorsHandlerMethodArgumentResolver())
    resolvers.add(DelimitedPairHandlerMethodArgumentResolver())
  }
}

```
### URL Configuration Structure
```typescript
interface Urls {
  origin: string        // Full URL with trailing slash
  originNoSlash: string // Full URL without trailing slash  
  base: string          // Base path with trailing slash
  baseNoSlash: string   // Base path without trailing slash
}
```

### Router Configuration
```typescript
const router = new Router({
  mode: 'history',
  base: urls.base,  // Dynamic base path
  routes: [
    {
      path: '/book/:bookId/read',
      name: 'read-book',
      component: () => import('./views/DivinaReader.vue'),
      props: (route) => ({bookId: route.params.bookId}),
    },
    // ... other routes
  ]
})
```

## Expected Output
After implementing the fix, users should be able to:
1. Access Komga directly via IP:PORT (e.g., `<ip>:25600/book/0KD1JKYHXH0XG/read`) without getting "No mapping for GET" errors
2. Load all JavaScript and CSS assets correctly
3. Navigate through all routes including book reading, series browsing, and admin pages
4. Have consistent behavior between development and production environments

## Required Changes
The fix needs to address the base path configuration in the Vue.js application to properly handle direct IP:PORT access in Docker environments. This involves updating the URL configuration logic and ensuring the router and webpack public path are properly synchronized.