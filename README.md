# PRISM Platform

## Prerequisites

1. Python 3.12.4 or higher
2. Poetry 2.1.4 or higher
3. Makefile support (in-built with Unix-based systems)

## Instructions to Run

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
   make run
   ```