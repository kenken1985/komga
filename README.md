[![Open Collective backers and sponsors](https://img.shields.io/opencollective/all/komga?label=OpenCollective%20Sponsors&color=success)](https://opencollective.com/komga) [![GitHub Sponsors](https://img.shields.io/github/sponsors/gotson?label=Github%20Sponsors&color=success)](https://github.com/sponsors/gotson)
[![Discord](https://img.shields.io/discord/678794935368941569?label=Discord&color=blue)](https://discord.gg/TdRpkDu)

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/gotson/komga/tests.yml?branch=master)](https://github.com/gotson/komga/actions?query=workflow%3ATests+branch%3Amaster)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/gotson/komga?color=blue&label=download&sort=semver)](https://github.com/gotson/komga/releases) [![GitHub all releases](https://img.shields.io/github/downloads/gotson/komga/total?color=blue&label=github%20downloads)](https://github.com/gotson/komga/releases)
[![Docker Pulls](https://img.shields.io/docker/pulls/gotson/komga)](https://hub.docker.com/r/gotson/komga)

[![Translation status](https://hosted.weblate.org/widgets/komga/-/webui/svg-badge.svg)](https://hosted.weblate.org/engage/komga/)

# ![app icon](./.github/readme-images/app-icon.png) Komga

> **DEVELOPMENT BRANCH NOTICE**: This branch contains experimental features including Kindle integration via Python scripts and AI-generated Dockerfile. These features are not planned for merging to main to prevent polluting the codebase.

## Enhanced Features in DEVELOPMENT Branch

- **CBR to CBZ Conversion**: Automatically converts CBR files to CBZ format for better Kindle compatibility
- **Image Format Conversion**: Converts AVIF and WebP images to JPG format for Kindle compatibility
- **Kindle Integration**: Push books directly to Kindle devices via SCP

## Building with Docker Compose

```bash
# Build and run the development environment
docker-compose up -d
```

The Docker setup includes all necessary dependencies for the Python Kindle integration script.

Komga is a media server for your comics, mangas, BDs, magazines and eBooks.

#### Chat on [Discord](https://discord.gg/TdRpkDu)

## Features

- Browse libraries, series and books via a responsive web UI that works on desktop, tablets and phones
- Organize your library with collections and read lists
- Edit metadata for your series and books
- Import embedded metadata automatically
- Webreader with multiple reading modes
- Manage multiple users, with per-library access control, age restrictions, and labels restrictions
- Offers a REST API, many community tools and scripts can interact with Komga
- OPDS v1 and v2 support
- Kobo Sync with your Kobo eReader
- KOReader Sync
- Download book files, whole series, or read lists
- Duplicate files detection
- Duplicate pages detection and removal
- Import books from outside your libraries directly into your series folder
- Import ComicRack `cbl` read lists

## Installation

Refer to the [website](https://komga.org/docs/category/installation) for instructions.

## Documentation

Head over to our [website](https://komga.org) for more information.

## Develop in Komga

Check the [development guidelines](./DEVELOPING.md).

## Kindle Integration

This fork includes a custom Python script for pushing comics to Kindle devices. The script automatically converts comics to Kindle-compatible formats and uploads them via SSH.

### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and update the Kindle configuration:
   ```bash
   # Kindle Configuration
   KINDLE_IP=192.168.29.55      # Your Kindle's IP address
   KINDLE_USER=root             # SSH username (usually 'root')
   KINDLE_REMOTE_PATH=/mnt/us/book/Others/  # Target directory on Kindle
   
   # SSH Configuration
   KINDLE_SSH_PASSWORD=         # Leave empty for passwordless auth (SSH keys)
   KINDLE_SSH_PORT=2222         # SSH port (usually 2222 for Kindle)
   ```

3. **SSH Authentication Setup:**
   
   **Option A: Passwordless Authentication (Recommended)**
   - Set up SSH keys between your server and Kindle
   - Leave `KINDLE_SSH_PASSWORD` empty in `.env`
   
   **Option B: Password-based Authentication**
   - Set `KINDLE_SSH_PASSWORD=your_password` in `.env`
   - Make sure your Kindle has a password set

4. Make sure your Kindle is jailbroken and has SSH enabled on port 2222.

### Usage

- **Single Book**: Navigate to a book in the web UI and click "Push to Kindle"
- **Entire Series**: Navigate to a series and click "Push Series to Kindle"

The script will:
- Convert CBR files to CBZ format
- Convert non-JPG images to JPG for Kindle compatibility
- Upload the processed files to your Kindle

### Docker Commands

```bash
# Build the image
make build-dev

# Run with test library
make run-test

# Run development environment
make run-dev
```

## Translation

[![Translation status](https://hosted.weblate.org/widgets/komga/-/webui/horizontal-auto.svg)](https://hosted.weblate.org/engage/komga/)

## Sponsors

[![Jetbrains_logo](./.github/readme-images/jetbrains.svg)](https://www.jetbrains.com/?from=Komga)

## Credits

The Komga icon is based on an icon made by [Freepik](https://www.freepik.com/home) from www.flaticon.com
