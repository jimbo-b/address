from __future__ import annotations

from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from sqlalchemy.types import String
from geoalchemy2 import Geometry
from sqlalchemy import text
from config import db_engine

# ===============================================
# DATABASE CONFIGURATION
# ===============================================

def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def ensure_schema(engine, schema: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quote_ident(schema)}"))


def drop_table(engine, schema: str, table: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(f"DROP TABLE IF EXISTS {quote_ident(schema)}.{quote_ident(table)} CASCADE")
        )


def create_spatial_index(engine, schema: str, table: str, geom_col: str = "geom") -> None:
    index_name = f"{table}_{geom_col}_gix"
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS {quote_ident(index_name)}
                ON {quote_ident(schema)}.{quote_ident(table)}
                USING GIST ({quote_ident(geom_col)})
                """
            )
        )


# ===============================================
# SQL TABLE CONFIGURATION
# ===============================================

TARGET_TABLE_NAME = "overturemaps"

# Target schemas
TARGET_TABLE_SCHEMAS = {
    TARGET_TABLE_NAME: [
        "overture_id", 
        "number", 
        "street", 
        "unit", 
        "postal_city", 
        "region", 
        "postcode", 
        "municipality", 
        "country", 
        "source_dataset", 
        "s3_filename", 
        "file_name", 
        "bbox", 
        "geometry"
    ]
}


TARGET_TABLE_DTYPES = {
    TARGET_TABLE_NAME: {
        "overture_id": String(36),
        "number": String(74),
        "street": String(95),
        "unit": String(199),
        "postal_city": String(40),
        "region": String(2),
        "postcode": String(21),
        "municipality": String(70),
        "country": String(2),
        "source_dataset": String(60),
        "s3_filename": String(143),
        "file_name": String(10),
        "bbox": Geometry("POLYGON", srid=4326),
        "geometry": Geometry("GEOMETRY", srid=4326)
    }
}

# -----------------------------
# Data Processing Functions
# -----------------------------

def normalize_dict_columns(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Break out key, value pairs from dictionaries into separate columns with 
    keys as column names and values as cell values. This is necessary to make 
    the data more tabular and enables compatibiltity between postgres, 
    parquet, and geospatial formats.
    """
        
    # Normalize sources dictionary into separate columns with prefix 'source_'
    ndf = pd.json_normalize(gdf['sources'].str[0], record_prefix = 'source_')

    # Normalize address_levels dictionaries into separate columns with prefixes 'address_level_1_' and 'address_level_2_'
    ndf = ndf.join(pd.json_normalize(gdf['address_levels'].str[0], record_prefix = 'address_level_1_'))
    ndf = ndf.join(pd.json_normalize(gdf['address_levels'].str[1], record_prefix = 'address_level_2_'))
    ndf = ndf.rename(columns={'address_level_1_value': 'region', 'address_level_2_value': 'municipality',})

    # Normalize bbox dictionary into separate columns without prefix
    ndf = ndf.join(pd.json_normalize(gdf['bbox']))

    # Drop the columns that were typically blank
    ndf = ndf.drop(columns=['source_property', 'source_license', 'source_record_id', 'source_update_time', 'source_confidence', 'source_between'])

    return ndf


def process_overture_gdf(file_path: Path) -> gpd.GeoDataFrame:
    """
    Process the OvertureMaps geodataframe by normalizing the dictionary columns.
    Strips the white space from the column names and column values. It also converts
    all strings to uppercase to ensure consistency across all datasets. It also 
    drops the columns that are not necessary.
    """
    try:

        # Load the enriched GeoDataFrame from the Parquet file
        gdf = gpd.read_parquet(file_path)

        # Normalize the dictionary columns and join them back to the original geodataframe
        gdf = gdf.join(normalize_dict_columns(gdf)).drop(columns=['sources', 'address_levels', 'bbox', 
                'theme', 'type', 'version'])

        # Rename the filename column to s3_filename to be more descriptive and avoid confusion 
        # with other filename columns in the dataset
        gdf = gdf.rename(columns={'filename': 's3_filename', 'id': 'overture_id'})

        # Create a geometry column from the bounding box columns and drop the original bounding box columns
        gdf["bbox"] = gdf.apply(
            lambda row: box(row["xmin"], row["ymin"], row["xmax"], row["ymax"]),
            axis=1
        ).set_crs("EPSG:4326")

        gdf = gdf.drop(columns=['xmin', 'ymin', 'xmax', 'ymax'])

        # Strip the white space from the column names and lowercase them for database compatibility
        gdf.columns = gdf.columns.str.strip().str.lower()

        # Strip the white space from the column values and convert them to uppercase for consistency across all datasets
        for col in gdf.columns.difference(['overture_id', 's3_filename']):
            gdf[col] = gdf[col].apply(lambda x: x.upper() if isinstance(x, str) else x)

        # Add file_name column to the geodataframe to keep track of the source file for each record
        gdf['file_name'] = file_path.name

        # Reorder the columns to have the geometry column at the end of the dataframe for better readability
        col_order = ['overture_id', 'number', 'street', 'unit', 'postal_city', 'region', 'postcode', 'municipality', 
                    'country', 'source_dataset', 's3_filename', 'file_name', 'bbox', 'geometry']
        
        gdf = gdf[col_order]

        # Set the geometry to crs "EPSG:4326" to ensure compatibility with PostGIS and other geospatial databases
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        
        # Keep the geometry column as the prominent geometry column for the geodataframe
        gdf = gdf.set_geometry('geometry')

        return gdf
        
    except Exception as e:
        print(f"\nError processing file {file_path.name}: {e}")


def main() -> None:
    if not MASTER_DIR.exists() or not MASTER_DIR.is_dir():
        raise ValueError(f"MASTER_DIR does not exist or is not a directory: {MASTER_DIR}")

    # Ensure target schema exists
    ensure_schema(db_engine, TARGET_SCHEMA)

    # Replace existing table if it exists
    if REPLACE_EXISTING_TABLES:
        drop_table(db_engine, TARGET_SCHEMA, TARGET_TABLE_NAME)

    print(f"Exporting combined GeoDataFrame to PostGIS...")

    for file_name in MASTER_DIR.rglob("*.parquet"):
        print(f"\nProcessing file: {file_name}")
        try:
            gdf = process_overture_gdf(file_name)

            gdf.to_postgis(
                name=TARGET_TABLE_NAME,
                con=db_engine,
                schema=TARGET_SCHEMA,
                if_exists="append",
                index=False,
                dtype=TARGET_TABLE_DTYPES[TARGET_TABLE_NAME],
            )
        except Exception as e:
            print(f"Error processing file {file_name}: {e}")
            continue

    print(f"Creating spatial index...")

    create_spatial_index(db_engine, TARGET_SCHEMA, TARGET_TABLE_NAME, geom_col="geometry")


if __name__ == "__main__":
    MASTER_DIR = Path("./data/overturemaps")
    TARGET_SCHEMA = "public"
    REPLACE_EXISTING_TABLES = True
    main()
