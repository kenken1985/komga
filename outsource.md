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

### File: Dockerfile
Multi-stage Docker build configuration that builds the frontend (Vue.js) and backend (Kotlin/Spring Boot) separately, then combines them into a final production image. This is critical for understanding how the application is deployed and how the frontend static resources are served.

### File: komga-webui/src/functions/urls.ts
This file contains the URL configuration logic that determines the base path for the Vue.js router. The current implementation uses `window.resourceBaseUrl` which may not be properly set in the Docker environment.

### File: komga-webui/src/router.ts
Contains the Vue.js router configuration with history mode and route definitions. The router uses the `urls.base` configuration as its base path.

### File: komga-webui/src/public-path.js
Configures the webpack public path for asset loading. This is critical for ensuring that JavaScript and CSS files are loaded correctly in different environments.

### File: komga-webui/src/views/PageNotFound.vue
The 404 page component that users see when they encounter routing issues.

### File: komga/src/main/kotlin/org/gotson/komga/infrastructure/web/WebMvcConfiguration.kt
Spring Boot configuration for serving static resources. This handles serving the built Vue.js application and static assets.

## Data Structures

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