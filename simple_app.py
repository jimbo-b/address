import os
import streamlit as st
import geopandas as gpd
import pandas as pd
import pydeck as pdk
from sqlalchemy import create_engine, text
import math
import json

# =========================
# CONFIG
# =========================

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg2://postgres:password@localhost:5433/address_gis")  # set in your environment
ADDRESS_TABLE = "overturemaps"

# Default center (can change)
DEFAULT_LAT = 39.9672433944
DEFAULT_LNG = -103.7715563417


# =========================
# DB CONNECTION (CACHED)
# =========================

@st.cache_resource
def get_engine():
    return create_engine(POSTGRES_URL)

# ============================================================
# HELPERS
# ============================================================

def miles_to_meters(miles: float) -> float:
    return miles * 1609.344


# =========================
# QUERY FUNCTION
# =========================

def search_radius(lat: float, lng: float, radius_miles: float):
    """
    Returns all addresses within radius (miles) of lat/lng
    Uses PostGIS ST_DWithin with geography (meters)
    """

    radius_meters = radius_miles * 1609.344

    sql = f"""
        SELECT *
        FROM {ADDRESS_TABLE}
        WHERE ST_DWithin(
            geometry::geography,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :radius_meters
        )
    """

    gdf = gpd.read_postgis(
        text(sql),
        get_engine(),
        geom_col="geometry",
        params={
            "lat": lat,
            "lng": lng,
            "radius_meters": radius_meters
        }
    )

    return gdf

@st.cache_data(ttl=120)
def get_radius_circle_geojson(lat: float, lng: float, radius_miles: float) -> dict:
    radius_meters = miles_to_meters(radius_miles)

    sql = """
        SELECT ST_AsGeoJSON(
            ST_Buffer(
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                :radius_meters
            )::geometry
        ) AS geojson
    """

    df = pd.read_sql(
        text(sql),
        get_engine(),
        params={
            "lat": lat,
            "lng": lng,
            "radius_meters": radius_meters,
        },
    )

    return {
        "type": "Feature",
        "geometry": json.loads(df.iloc[0]["geojson"]),
        "properties": {"name": "Search Radius"},
    }


# =========================
# MAP FUNCTION
# =========================

def zoom_for_radius(radius_miles):
    """
    Approximate Web Mercator zoom so the radius fits in view.
    Works well for Streamlit/PyDeck.
    """
    radius_meters = miles_to_meters(radius_miles)
    diameter_meters = radius_meters * 2

    # Approximate visible world width at zoom 0
    earth_circumference_meters = 40_075_016.686

    zoom = math.log2(earth_circumference_meters / diameter_meters)

    # Clamp to reasonable zoom levels
    return max(1, min(18, zoom - 1))

def build_map(gdf: gpd.GeoDataFrame, lat: float, lng: float, zoom: int, radius_miles:float):

    layers = []

    # Selected point
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=[{"lat": lat, "lng": lng}],
            get_position="[lng, lat]",
            get_radius=100,
            get_fill_color=[255, 0, 0, 180],
            pickable=True,
        )
    )

    # Results
    if gdf is not None and not gdf.empty:
        df = gdf.copy()
        df["lat"] = df.geometry.y
        df["lng"] = df.geometry.x

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position="[lng, lat]",
                get_radius=40,
                get_fill_color=[0, 100, 255, 160],
                pickable=True,
            )
        )

        circle_feature = get_radius_circle_geojson(lat, lng, radius_miles)

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=circle_feature,
                stroked=True,
                filled=True,
                get_line_width=3,
                get_fill_color=[80, 80, 80, 40],
                get_line_color=[40, 40, 40, 180],
                pickable=False,
            )
        )

    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(
            latitude=lat,
            longitude=lng,
            zoom=zoom,
        ),
        layers=layers,
        tooltip={"text": "{number} {street} {unit}, {postal_city}, {region} {postcode}"},
    )



# =========================
# UI
# =========================

st.set_page_config(layout="wide")
st.title("Radius Address Search by Latitude & Longitude")

# Persistent map location
map_container = st.empty()

# Always show initial map
map_container.pydeck_chart(
    build_map(gdf=None, lat=DEFAULT_LAT, lng=DEFAULT_LNG, zoom=3, radius_miles=0),
    use_container_width=True,
)

st.sidebar.header("Search Parameters")

lat = st.sidebar.number_input(
    "Latitude",
    value=DEFAULT_LAT,
    format="%.6f"
)

lng = st.sidebar.number_input(
    "Longitude",
    value=DEFAULT_LNG,
    format="%.6f"
)

radius = st.sidebar.slider(
    "Radius (miles)",
    min_value=1,
    max_value=100,
    value=10
)

run_search = st.sidebar.button("Search")


# =========================
# EXECUTION
# =========================

if run_search:
    with st.spinner("Querying addresses..."):
        results = search_radius(lat, lng, radius)
    
    map_zoom = zoom_for_radius(radius)

    st.subheader(f"{len(results):,} addresses found")

    # Map
    map_container.pydeck_chart(build_map(results, lat, lng, map_zoom, radius), use_container_width=True)

    # Table
    if not results.empty:
        display_df = pd.DataFrame(results.drop(columns=["geometry", "bbox", "overture_id", 
                                                        "country", "source_dataset", "s3_filename", "file_name"]))
        st.dataframe(display_df, use_container_width=True)