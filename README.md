# PRISM Platform

This application is built in two parts:

-   A central server that hosts the database and object storage, along with the web UI and a backend for the web UI

-   Workers that run on user systems so that the central server can automate profiling on Android devices _connected to user systems_

# Worker Application

The worker application allows you to trace your own devices through the website. It listens to `adb devices` on your system and on handles requests from the central server to trace any Android devices connected to your system.

## Installation

1. Ensure that you have ADB installed on your system

2. Download the worker application from [the releases page](https://github.com/ranjithrd/prism-platform/releases)

3. Open the [host website](https://prism-ui.d.p.ranjithrd.in) to get an `API Key` for your system

    - On the home page, click on "Add a Worker"
    - Type in the name of your system
    - Click on "Generate Key" next to the worker that was created
    - Copy this key and save it for the next step

4. Open the downloaded binary and paste in the API key. Click on "Save API Key" to connect to the server

5. Connect your Android device to your system and verify it shows up on the GUI and in the website

6. You can now take traces from the website through the worker you registered

## Security

-   All data is stored on a central server

-   Data needed for the workers is exposed through a set of public endpoints secured by API Keys

# Central Server

The central server runs the UI and the services needed to manage traces.

## Prerequisites

1. [Postgres](https://www.postgresql.org/)

2. [Minio](https://github.com/seaweedfs/seaweedfs?tab=readme-ov-file#quick-start-for-s3-api-on-docker)/[SeaweedFS](https://github.com/seaweedfs/seaweedfs?tab=readme-ov-file#quick-start-for-s3-api-on-docker) or any other S3-compatible object storage

3. Android NDK with SimplePerf installed

4. Python (supported versions: 3.12, 3.14, 3.15)

5. [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer) (tested on v2.1.4)

6. [NodeJS](https://nodejs.org/en/download) (tested on v24.11.0)

## Installation

1. Ensure that all the prerequisites are installed

2. Clone this repository

    ```zsh
    git clone https://github.com/ranjithrd/prism-platform prism
    cd prism
    ```

3. Install dependencies

    ```zsh
    make install-server
    make install-frontend
    ```

4. Set environment variables in a `.env` file. 
    
    Refer to the [Environment Variables section](#environment-variables) for details

5. Run the server (by default, runs at port 8000)
    ```zsh
    make run
    # or
    PORT=XXXX make run
    ```

6. Build the frontend
    ```
    make build-frontend
    ```

7. Serve the frontend (by default, serves at port 8001)
    ```
    make serve-frontend
    ```

## Environment Variables

-   `DATABASE_URL`: Postgres connection string (e.g: `postgresql://username:password@host:port/db`)

-   `MINIO_HOST`: URL to connect to any S3-compatible API (e.g `127.0.0.1:9000`)

-   `MINIO_ACCESS_KEY`: Access key to connect to the S3-compatible API

-   `MINIO_SECRET_KEY`: Secret key to connect to the S3-compatible API

-   `HOSTNAME`: Any name that can identify the current system (e.g: `server_1`)

-   `SIMPLEPERF_SCRIPT_PATH`: Path to the `report_html.py` script provided in Simpleperf installations

    - Typically, this is found at the path: `<android sdk path>/ndk/<ndk version>/simpleperf/report_html.py`

    - The Android SDK path can be found with `which adb`, which returns the path `<android sdk path>/platform-tools/adb`
