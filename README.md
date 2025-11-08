# PRISM Platform

## Structure

This application is built in two parts:

- A central server that hosts the database and object storage, along with the web UI and a backend for the web UI

- Workers that run on user systems so that the central server can automate profiling on Android devices _connected to user systems_

The instructions below are to run the worker, as the central server can be accessed via the given URL and credentials. 

## Prerequisites to run the Worker

1. Python 3.12.4 or higher with PySide6
2. [Poetry 2.1.4](https://python-poetry.org/docs/#installing-with-the-official-installer) or higher 
3. Makefile support (in-built with Unix-based systems)
4. ADB support

## Instructions to run the Worker

1. Open the [host website](https://prism-ui.d.p.ranjithrd.in) to get an `API Key` for your system
    - On the  home page, click on "Add a Worker"
    - Type in the name of your system
    - Click on "Generate Key" next to the worker that was created
    - Copy this key and save it for the next step

2. Install dependencies.
    ```bash
    make install
    ```

3. Run the application.
    ```bash
   make run-worker
   ```

4. In the GUI that opens, paste in the API key and click on "Save API Key"

5. Connect your Android device to your system and verify it shows up on the GUI and in the website

6. You can now take traces from the website through the worker you registered

## Instruction Variables & Central Server

- All data is currently stored on a central server

- Data needed for the workers are exposed through a set of public endpoints secured by API Keys 

- If connected properly, your system's hostname will show up on the home page under the "Hosts" section
