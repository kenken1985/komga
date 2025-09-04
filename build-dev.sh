#!/bin/bash

# Development build script for faster iteration

set -e

echo "🚀 Starting development build..."

# Build with cache and no cache for specific stages if needed
if [ "$1" = "--no-cache" ]; then
    echo "🔄 Building without cache..."
    docker build --no-cache -t komga-dev .
elif [ "$1" = "--frontend-only" ]; then
    echo "🎨 Building frontend only..."
    docker build --target frontend-build -t komga-frontend .
elif [ "$1" = "--backend-only" ]; then
    echo "⚙️ Building backend only..."
    docker build --target backend-build -t komga-backend .
else
    echo "📦 Building with cache..."
    docker build -t komga-dev .
fi

echo "✅ Build completed!"

# Optional: Run the container
if [ "$2" = "--run" ]; then
    echo "🏃 Running container..."
    docker run -p 25601:25601 komga-dev
fi 