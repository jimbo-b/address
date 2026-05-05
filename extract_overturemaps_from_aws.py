import duckdb
import os

def main():

    # List of US State ISO-2 codes and DC
    states = [
        "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS",
        "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY",
        "NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV",
        "WI","WY","DC"
    ]

    # Create output directory if it doesn't exist
    os.makedirs("./data/overturemaps", exist_ok=True)

    # Connect to DuckDB
    con = duckdb.connect()

    # Install and load httpfs extension for S3 access
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")

    # Set S3 region for httpfs
    con.execute("SET s3_region='us-west-2';")

    # Get the latest release version from the Overture STAC catalog
    latest = con.execute("""
        SELECT latest
        FROM 'https://stac.overturemaps.org/catalog.json'
    """).fetchone()[0]

    # Construct the S3 path to the address data for the latest release
    source = f"s3://overturemaps-us-west-2/release/{latest}/theme=addresses/type=address/*"

    # For each state, query the address data for that state and write it to a Parquet file
    for st in states[0:1]:
        out = f"./data/overturemaps/{st}.parquet"
        print(f"Writing {out}")
        con.execute(f"""
            COPY (
                SELECT *
                FROM read_parquet('{source}', filename=true, hive_partitioning=1)
                WHERE country = 'US' AND address_levels[1].value = '{st}' LIMIT 10
            )
            TO '{out}' (FORMAT 'parquet')
        """)

    # Close the DuckDB connection
    con.close()
    
    print("All files written successfully.")
    print("HAVE A GREAT DAY!")

if __name__ == "__main__":
    main()