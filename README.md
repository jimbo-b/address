## Address Database

Step 1: Add Dependencies

The required dependencies are specified in the `pyproject.toml` file included with the package. To install these dependencies, run the following command:

```
uv sync
```

Step 2: Change PostgreSQL Connection Variables in `config.py`

Change the following variables to meet your requirements. It is recommended to keep the **POSTGRES_ADMIN_DB** variable set to **postgres**

```
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "password"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5433
POSTGRES_CREATE_DB = "address_gis"
```

Step 3: Create the Database

```
uv run create_address_gis_database.py
```

Step 4: Extract Overturemaps Data from AWS

```
uv run extract_overturemaps_from_aws.py
```

Step 5: Load Overturemaps Data to PostgreSQL

```
uv run load_overturemaps_to_postgis.py
```

Step 6: Run Streamlit App

```
streamlit run simple_app.py
```
