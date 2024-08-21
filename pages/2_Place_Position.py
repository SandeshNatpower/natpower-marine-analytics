import streamlit as st
import geopandas as gpd
from shapely import wkb
import folium
from streamlit_folium import folium_static
import binascii
import pandas as pd
from folium import GeoJson, Popup, GeoJsonTooltip

# Sample DataFrame (already provided)
st.set_page_config(layout="wide")
st.image("images/LinkedIn Header - NatPower Marine.png", caption='© Natpower Marine', use_column_width=True)

conn = st.connection("postgresql", type="sql")
df = conn.query("select * from reporting.mview_geometry_port_term_berth;", ttl="10m")

# Convert the 'geometry' column from WKB hex string to Shapely geometry objects
df['location'] = df['location'].apply(lambda x: wkb.loads(binascii.unhexlify(x)))

# Create a GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry='location')

# Sidebar filters
st.sidebar.header("Filter options")

# Filter by type
type_options = st.sidebar.multiselect("Select Type", options=gdf["type"].unique(), default='Port')

# Filter by country
# Default to only showing "United Kingdom"
default_country = "United Kingdom"
country_options = st.sidebar.multiselect("Select Country", options=gdf["country"].unique(), default=[default_country])

# Search by name or ID
search_query = st.sidebar.text_input("Search by Name or ID")

# Apply filters
filtered_gdf = gdf[(gdf["type"].isin(type_options)) & (gdf["country"].isin(country_options))]

# Apply search filter
if search_query:
    filtered_gdf = filtered_gdf[
        (filtered_gdf["name"].str.contains(search_query, case=False, na=False)) |
        (filtered_gdf["id"].astype(str).str.contains(search_query))
    ]

color_mapping = {
    
"Berth"	: "blue",
"Port"	: "green",
"Terminal"	: "yellow",
"Anchorage"	: "red"

}


# Create a folium map centered around the first geometry
if not filtered_gdf.empty:
    m = folium.Map(location=[55, -3], zoom_start=5)  # Center map around the UK

    # Add each geometry to the map with different colors based on type
    for _, row in filtered_gdf.iterrows():
        color = color_mapping.get(row["type"], "gray")  # Default to gray if type not in mapping
        
        # Create HTML content for the popup
        popup_content = (
            f"<div><strong>Name:</strong> {row['name']}<br>"
            f"<strong>Description:</strong> {row['short_name']}<br>"
            f"<strong>Type:</strong> {row['type']}<br>"
            f"<strong>Country:</strong> {row['country']}<br>"
            f"<strong>Area Size:</strong> {row['areasize']}<br>"
            f"<strong>Vessel Details :</strong> <br> <a href='/1_Vessel?id={row['id']}' target='_blank'>{row['name']}</a></div>"
        )
        
        # # Add vessel counts if type is "Port"
        # if row['type'].lower() == 'port':
        #     # st.write(row['id'])
        #     info = conn.query(f"SELECT reporting.get_vessel_activity_by_port (4066);", ttl="10m")
        #     # info = conn.query(f"SELECT reporting.get_vessel_activity_by_port (4066);", ttl="10m")
        #     # st.write(info['get_vessel_activity_by_port'][0])
        #     info = info['get_vessel_activity_by_port'][0]
        #     # if len(info) > 2:
        #     # st.write(info)
        #     # st.write(len(info))
        #     incoming_info = info['Incoming']['vessel_counts']
        #     outgoing_info = info['Outgoing']['vessel_counts']
            
        #     # Format vessel counts for each type
        #     # Format vessel counts for each type
        #     vessel_types = ["Ferry", "Cruise ships", "Cargo vessels", "not identified", "Service Vessles", "Chemical Tankers", "Container vessels", "non-serviceble in out business model"]
        #     incoming_counts = ''.join([
        #         f"<div><strong>{vessel_type}:</strong> {incoming_info.get(vessel_type, {}).get('total_incoming_count', 0)}</div>"
        #         for vessel_type in vessel_types
        #         if vessel_type in incoming_info
        #     ])
        #     outgoing_counts = ''.join([
        #         f"<div><strong>{vessel_type}:</strong> {outgoing_info.get(vessel_type, {}).get('total_outgoing_count', 0)}</div>"
        #         for vessel_type in vessel_types
        #         if vessel_type in outgoing_info
        #     ])

        #     additional_info_content = (
        #         f"<hr><div><strong>Incoming Vessels:</strong><br>{incoming_counts}</div>"
        #         f"<hr><div><strong>Outgoing Vessels:</strong><br>{outgoing_counts}</div>"
        #         f"<hr><div><strong>Vessel Details :</strong> <br> <a href='/1_Vessel?id={row['id']}' target='_blank'>{row['name']}</a></div>"
        #     )
        #     popup_content += additional_info_content

        
        folium.GeoJson(
            row["location"],
            name=row["name"],
            style_function=lambda x, color=color: {'color': color},
            popup=folium.Popup(popup_content, max_width=300, id='popup-content'),
            # popup=folium.Popup(f"<a href='/click?id={row['id']}' target='_blank'>{row['name']}</a>", max_width=300),
            tooltip=f'{row["name"]} - {row["type"]} ({row["country"]})',
            # Add click event handling
            highlight_function=lambda x: {'weight': 5, 'color': 'yellow', 'fillOpacity': 0.7},
            on_click=f"function(e) {{ window.open('/?port_id={row['id']}'); }}"
        ).add_to(m)


    # Display the map in Streamlit
    st.title("Geospatial Data Visualization")
    st.write("Map displaying the locations from the filtered geometries:")
    folium_static(m)
else:
    st.write("No data available with the selected filters.")


# # Handle URL query parameters
# query_params = st.experimental_get_query_params()
# port_id = query_params.get("port_id", [None])[0]

# if port_id:
#     info = conn.query(f"SELECT reporting.get_vessel_activity_by_port ({port_id});", ttl="10m")
#     # info = conn.query(f"SELECT reporting.get_vessel_activity_by_port (4066);", ttl="10m")
#     # st.write(info['get_vessel_activity_by_port'][0])
#     info = info['get_vessel_activity_by_port'][0]
#     if len(info) > 2:
#         st.write(info)
#         st.write(len(info))
#         incoming_info = info['Incoming']['vessel_counts']
#         outgoing_info = info['Outgoing']['vessel_counts']
        
#         # Format vessel counts for each type
#         # Format vessel counts for each type
#         vessel_types = ["Ferry", "Cruise ships", "Cargo vessels", "not identified", "Service Vessles", "Chemical Tankers", "Container vessels", "non-serviceble in out business model"]
#         incoming_counts = ''.join([
#             f"<div><strong>{vessel_type}:</strong> {incoming_info.get(vessel_type, {}).get('total_incoming_count', 0)}</div>"
#             for vessel_type in vessel_types
#             if vessel_type in incoming_info
#         ])
#         outgoing_counts = ''.join([
#             f"<div><strong>{vessel_type}:</strong> {outgoing_info.get(vessel_type, {}).get('total_outgoing_count', 0)}</div>"
#             for vessel_type in vessel_types
#             if vessel_type in outgoing_info
#         ])

#         additional_info_content = (
#             f"<hr><div><strong>Incoming Vessels:</strong><br>{incoming_info}</div>"
#             f"<hr><div><strong>Outgoing Vessels:</strong><br>{outgoing_info}</div>"
#         )
#         popup_content += additional_info_content
        
#         st.write(f"**Port ID:** {port_id}")
#         st.write(f"**Incoming Vessels:**<br>{incoming_info}")
#         st.write(f"**Outgoing Vessels:**<br>{outgoing_info}")
#     else:
#         st.write("No additional information available.")
# else:
#     st.write("Click on a feature to get more information.")