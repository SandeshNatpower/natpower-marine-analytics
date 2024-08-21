import streamlit as st
import pandas as pd
import leafmap.foliumap as leafmap
from shapely.geometry import Point, mapping
import geopandas as gpd
from shapely import wkb
import folium
from streamlit_folium import folium_static
import binascii
from folium import GeoJson, Popup, GeoJsonTooltip

st.set_page_config(layout="wide")
st.image("images/LinkedIn Header - NatPower Marine.png", caption='© Natpower Marine', use_column_width=True)

# st.sidebar.info(
#     """
#     - Web App URL: <https://streamlit.gishub.org>
#     - GitHub repository: <https://github.com/giswqs/streamlit-geospatial>
#     """
# )

# st.sidebar.title("Vessels")
# st.sidebar.info(
#     """
#     Qiusheng Wu at [wetlands.io](https://wetlands.io) | [GitHub](https://github.com/giswqs) | [Twitter](https://twitter.com/giswqs) | [YouTube](https://www.youtube.com/c/QiushengWu) | [LinkedIn](https://www.linkedin.com/in/qiushengwu)
#     """
# )

st.title("Vessel Position")

conn = st.connection("postgresql", type="sql")

# query = """SELECT jsonb_build_object('type', 'FeatureCollection', 'features', jsonb_agg(feature))
# FROM (
#     SELECT jsonb_build_object('type', 'Feature', 'geometry', ST_AsGeoJSON(location)::jsonb, 'properties', to_jsonb(row) - 'location') AS feature
#     FROM ( 
#         select * from reporting.mview_vessel_position limit 100
#         )row
#     ) features"""

result = conn.query('select * from reporting.mview_vessel_position limit 100', ttl="10m")
df = conn.query('select distinct  vessel_category, vessel_type, vesseltypeandsize from reference.ref_vessel_type_category  order by vessel_category,vessel_type, vesseltypeandsize', ttl="10m")
# Display filtered results


# Filter options
# vessel_type_filter = st.sidebar.selectbox("Select Vessel Type", options=["All"] + sorted(df["vessel_type"].unique()), default='Ferry')
# Filter by type
# type_options = st.sidebar.multiselect("Select Type", options=gdf["type"].unique(), default='Port')
# Sidebar filters
st.sidebar.header("Filter options")
# st.write("Filtered Data", df)
vessel_type_filter = st.sidebar.multiselect("Select Vessel Type", options=df["vessel_type"].unique(), default='Cargo')

# vesseltypeandsize_filter = st.sidebar.multiselect("Select Vessel Type and Size", options=df["vesseltypeandsize"].unique(), default='Cargo, all ships of this type')
# vessel_category = st.sidebar.multiselect("Select vessel_category", options=df["vessel_category"].unique(), default='Cruise ships')

# Text search across any column
search_term = st.sidebar.text_input("Search")
print(vessel_type_filter[0])
print(f"select * from reporting.mview_vessel_position where vessel_type ilike '{vessel_type_filter[0]}' limit 100")
# Apply filters
if vessel_type_filter != "All":
    result = conn.query(f"select * from reporting.mview_vessel_position where vessel_type ilike '{vessel_type_filter[0]}' limit 100", ttl="10m")
    # st.write("Filtered Data", result)
    # result = result[result["vessel_type"] == vessel_type_filter]

# if vesseltypeandsize_filter != "All":
#     result = conn.query(f"select * from reporting.mview_vessel_position where vesseltypeandsize ilike '{vesseltypeandsize_filter[0]}' limit 10000", ttl="10m")
#     # result = result[result["vesseltypeandsize"] == vesseltypeandsize_filter]

# if vessel_category != "All":
#     result = conn.query(f"select * from reporting.mview_vessel_position where vessel_category ilike '{vessel_category[0]}' limit 10000", ttl="10m")
#     # result = result[result["vessel_category"] == vessel_category]

if search_term:
    result = conn.query('select * from reporting.mview_vessel_position limit 100000', ttl="10m")
    # result = result[result.apply(lambda row: search_term.lower() in row.astype(str).str.lower().values, axis=1)]

# with st.expander("See source code"):
# with st.echo():
# Create a GeoDataFrame
# gdf = gpd.GeoDataFrame(result, geometry=[Point(xy) for xy in zip(result.longitude, result.latitude)], crs="EPSG:4326")
# gdf = gpd.GeoDataFrame(result, geometry=[Point(xy) for xy in zip(result.longitude, result.latitude)], crs="EPSG:4326")


# # Convert GeoDataFrame to GeoJSON
# geojson_data = gdf.to_json()

# # Create the map
# m = leafmap.Map(center=[40, -100], zoom=4)

# # Add GeoJSON layer to the map
# m.add_geojson(geojson_data, layer_name="Vessel Locations")

# Function to create popup content
def create_popup(row):
    popup_content = f"""
    <div style="width: 200px;">
        <b>MMSI:</b> {row['mmsi']}<br>
        <b>Vessel Name:</b> {row['vessel_name']}<br>
        <b>Vessel Type:</b> {row['vessel_type']}<br>
        <b>Vessel Type and Size:</b> {row['vesseltypeandsize']}<br>
        <b>Flag:</b> {row['flag']}<br>
        <b>Owner Name:</b> {row['owner_name']}<br>
        <b>Position Record Time:</b> {row['position_record_time']}<br>
    </div>
    """
    return popup_content

# Create map
m = leafmap.Map(center=[40, -100], zoom=4)
# Add GeoJSON layer with popups
for _, row in result.iterrows():
    popup_content = create_popup(row)
    m.add_marker([row['latitude'], row['longitude']], popup_content)

# Display the map
m.to_streamlit(height=700)


# # Create a folium map centered around the first geometry
# if not result.empty:
#     m = folium.Map(location=[55, -3], zoom_start=5)  # Center map around the UK

#     # Add each geometry to the map with different colors based on type
#     for _, row in result.iterrows():
#         folium.GeoJson(
#             row["location"],
#             name=row["mmsi"],
#             style_function=lambda x, color=color: {'color': color},
#             popup=folium.Popup(popup_content, max_width=300, id='popup-content'),
#             # popup=folium.Popup(f"<a href='/click?id={row['id']}' target='_blank'>{row['name']}</a>", max_width=300),
#             tooltip=f'{row["mmsi"]} - {row["type"]} ({row["country"]})',
#             # Add click event handling
#             highlight_function=lambda x: {'weight': 5, 'color': 'yellow', 'fillOpacity': 0.7},
#             on_click=f"function(e) {{ window.open('/?port_id={row['id']}'); }}"
#         ).add_to(m)


#     # Display the map in Streamlit
#     st.title("Geospatial Data Visualization")
#     st.write("Map displaying the locations from the filtered geometries:")
#     folium_static(m)

# # m = leafmap.Map(center=[40, -100], zoom=4)
# # m = leafmap.Map(center=[40, -100], zoom=4)
# # regions = result['jsonb_build_object'][0]
# # m.add_geojson(regions, layer_name="US Regions")

# m.to_streamlit(height=700)

# # Display filtered results
# st.write("Filtered Data", result)