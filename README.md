# PRISM Platform

## Structure

This application is built in two parts:

- A central server that hosts the database and object storage, along with the web UI and a backend for the web UI

- Workers that run on user systems so that the central server can automate profiling on Android devices _connected to user systems_

The instructions below are to run the worker, as the central server can be accessed via the given URL and credentials. 

## Prerequisites to run the Worker

1. Python 3.12.4 or higher
2. [Poetry 2.1.4](https://python-poetry.org/docs/#installing-with-the-official-installer) or higher 
3. Makefile support (in-built with Unix-based systems)

## Instructions to run the Worker

1. Use .`env.example` to create a `.env` file and set the required environment variables.
    ```bash
    cp .env.example .env
   ```

2. Set the `HOSTNAME` variable in the `.env` file to your machine's hostname or a unique identifier.

3. Install dependencies.
    ```bash
    make install
    ```

4. Run the application.
    ```bash
   make run-worker
   ```

## Instruction Variables & Central Server

- All data is currently stored on a central server that is accessible via a Tailscale account. 

- To connect your local version of the worker to the central database, log in to the Tailscale account on your device 

- Once logged in, ensure you can reach the central server with `ping 100.109.46.43`

- Set the environment variables to the appropriate values to connect your system to the central server

- If connected properly, your system's hostname will show up on the home page under the "Hosts" section
