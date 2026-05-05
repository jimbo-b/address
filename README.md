# Address Database

This project provides an end-to-end pipeline for extracting Overture Maps data from AWS, loading it into a PostgreSQL/PostGIS database, and visualizing results through a Streamlit application.

---

## Setup and Execution

### Step 1: Add Dependencies

The required dependencies are specified in the `pyproject.toml` file included with the package. To install these dependencies, run the following command:

```
uv sync
```

### Step 2: Configure PostgreSQL Connection

Update the connection variables in `config.py` to match your local environment. It is recommended to keep the administrative database set to `POSTGRES_ADMIN_DB=postgres`.

```
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "password"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5433
POSTGRES_CREATE_DB = "address_gis"
```

### Step 3: Create the Database

Run the following script to create the PostgreSQL database and enable PostGIS:

```
uv run create_address_gis_database.py
```

### Step 4: Extract Overturemaps Data from AWS

This step extracts Overture Maps data from AWS on a per-state basis and writes the results as individual Parquet files to the data/overturemaps/ directory.

```
uv run extract_overturemaps_from_aws.py
```

### Step 5: Load Overturemaps Data to PostgreSQL

This step loads Overture Maps data into PostgreSQL by reading the Parquet files generated in the previous step, performing necessary transformations, and appending the processed data to the appropriate database tables.

```
uv run load_overturemaps_to_postgis.py
```

### Step 6: Launch Streamlit Application

This step launches the Streamlit application, which accepts latitude, longitude, and radius (in miles) as user inputs and returns all addresses located within the defined circular radius of the specified coordinates.

```
streamlit run simple_app.py
```

## Project Structure

```
address/
├── config.py
├── create_address_gis_database.py
├── extract_overturemaps_from_aws.py
├── load_overturemaps_to_postgis.py
├── simple_app.py
├── pyproject.toml
└── data/
    └── overturemaps/
```
