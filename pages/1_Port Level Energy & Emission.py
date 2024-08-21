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

st.sidebar.image("images/natpowermarine.png", caption='© Natpower Marine', use_column_width=True)

conn = st.connection("postgresql", type="sql")
df = conn.query("SELECT DISTINCT country,port_name,terminal_name,berth_name,port_id,terminal_id,berth_id FROM reference.port_hierarchy;", ttl="10m")

# Sidebar filters
st.sidebar.header("Filter options - Port Selection Mandatory")

# Filter by Country
country_list = df["country"].unique()
if 'United Kingdom' in country_list:
    uk_index = list(country_list).index('United Kingdom')
else:
    uk_index = 0 

country_options =  st.sidebar.selectbox("Country", options=country_list,index=uk_index)

# Filter by Port
port_list = df[df['country'] == country_options]["port_name"].unique()
if 'ABERDEEN' in port_list:
    uk_index = list(port_list).index('ABERDEEN')
else:
    uk_index = 0 
port_options =  st.sidebar.selectbox("Select Port", options=port_list,index=uk_index)
# Initialize session state variables if they do not exist
if 'show_port_details' not in st.session_state:
    st.session_state.show_port_details = True
Port_level = st.sidebar.toggle("Show Port level details",value=True)
color = 'red'
query = f"SELECT * FROM reference.port_hierarchy where country = '{country_options}' and port_name = '{port_options}';"


terminal_options_list = df[(df['country'] == country_options) & (df['port_name'] == port_options)]["terminal_name"].unique().tolist()
terminal_options_list.insert(0, None)
terminal_options =  st.sidebar.selectbox("Select Terminal", options= terminal_options_list)
terminal_level = st.sidebar.toggle("Show Terminal level details")
if terminal_options != None:
    print(terminal_options)
    color = 'yellow'
    query = f"SELECT * FROM reference.port_hierarchy where country = '{country_options}' and port_name = '{port_options}' and terminal_name = '{terminal_options}';"


# Filter by Port
berth_options_list = df[(df['country'] == country_options) & (df['port_name'] == port_options) & (df['terminal_name'] == terminal_options) ]["berth_name"].unique().tolist()
berth_options_list.insert(0, None)
berth_options =  st.sidebar.selectbox("Select Berth", options=berth_options_list)
berth_level = st.sidebar.toggle("Show Berth level details")
if berth_options != None:
    color = 'blue'
    query = f"SELECT * FROM reference.port_hierarchy where country = '{country_options}' and port_name = '{port_options}' and terminal_name = '{terminal_options}' and berth_name = '{berth_options}';"

print(query)
df_loc = conn.query(query, ttl="10m")

# # Convert the 'geometry' column from WKB hex string to Shapely geometry objects
df_loc['port_geometry'] = df_loc['port_geometry'].apply(lambda x: wkb.loads(binascii.unhexlify(x)))

# # Create a GeoDataFrame
gdf = gpd.GeoDataFrame(df_loc, geometry='port_geometry')


# Create a folium map centered around the first geometry
if not gdf.empty:
    m = folium.Map(location=[55, -3], zoom_start=5)  # Center map around the UK

    # Add each geometry to the map with different colors based on type
    for _, row in gdf.iterrows():       
        # Create HTML content for the popup
        popup_content = (
            f"<div><strong>Port_id:</strong> {row['port_id']}<br>"
            f"<strong>Country:</strong> {row['country']}<br></div>"
        )
        
        folium.GeoJson(
            row["port_geometry"],
            name=row["port_name"],
            style_function=lambda x: {'Opacity': 0.3, 'color': 'green'},
            popup=folium.Popup(popup_content, max_width=300, id='popup-content'),
            # popup=folium.Popup(f"<a href='/click?id={row['id']}' target='_blank'>{row['name']}</a>", max_width=300),
            tooltip=f'{row["port_name"]} - {row["port_id"]} ({row["country"]})',
            # Add click event handling
            highlight_function=lambda x: {'weight': 5, 'color': 'yellow', 'fillOpacity': 0.7}
        ).add_to(m)

        # Calculate the bounds for each feature
        feature_shape = row["port_geometry"]
        bounds = feature_shape.bounds  # (minx, miny, maxx, maxy)

        # Adjust the map view to fit the feature bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Display the map in Streamlit
    # col1, col2  = st.columns(2)
    # with col1:
    st.title("Data for 2023")
    st.write("Map displaying the locations from the filtered geometries:")
    folium_static(m)
else:
    st.write("No data available with the selected filters.")

query_energy  = f"select * From reporting.get_port_energy_emission({df_loc['port_id'][0]});"
df_main = conn.query(query_energy, ttl="10m")
# with col2:
st.title("Port Activity Details")
st.write('Total Port Vessel Visit Count - ' + str(df_main['vessel_id'].count()))
st.title("Docking & Dwelling Time")
col1, col2,col3 = st.columns(3)
with col1:
    st.write('Average Port Docking Time Hrs')
    st.write(str(df_main['port_docking_time_hr'].mean()))
with col2:
    st.write('Average Berth Docking Time Hrs')
    st.write(str(df_main['berth_docking_time_hr'].mean()))
with col3:
    st.write('Average Port Dwelling Time Hrs')
    st.write(str(df_main['port_dwelling_time_hr'].mean()))

st.title("Cold Ironing & Propulsion Consumption in MW")
col1, col2 = st.columns(2)
with col1:
    st.write('Average Cold Ironing in MW')
    st.write(str(df_main['cold_ironing_mw'].mean()))
with col2:
    st.write('Average Propulsion Consumption in MW')
    st.write(str(df_main['propulsion_consumption_mw'].mean()))

st.title("Cold Ironing & Propulsion Consumption in MW/h")
col1, col2 = st.columns(2)
with col1:
    st.write('Average Cold Ironing in MW/h')
    st.write(str(df_main['cold_ironing_mwh'].mean()))
    st.write('Total Cold Ironing in MW/h')
    st.write(str(df_main['cold_ironing_mwh'].sum()))
with col2:
    st.write('Average Propulsion Consumption in MW/h')
    st.write(str(df_main['propulsion_consumption_mwh'].mean()))
    st.write('Total Propulsion Consumption in MW/h')
    st.write(str(df_main['propulsion_consumption_mwh'].sum()))


st.title("Energy Consumption")
col1, col2 = st.columns(2)
with col1:
    st.write('Total Energy Consumption in MW/h')
    st.write(str( (df_main['cold_ironing_mwh'].sum()) + (df_main['propulsion_consumption_mwh'].sum()) ))
with col2:
    st.write('Average Energy Consumption in MW/h')
    st.write(str( (df_main['cold_ironing_mwh'].mean()) + (df_main['propulsion_consumption_mwh'].mean()) ))

# CO2 Emission
st.title("CO2 Emission")
co2_cold_ironing_sum_g = df_main['co2_cold_ironing_emission'].sum()
co2_cold_ironing_mean_g = df_main['co2_cold_ironing_emission'].mean()

co2_propulsion_sum_g = df_main['co2_propulsion_consumption_emission'].sum()
co2_propulsion_mean_g = df_main['co2_propulsion_consumption_emission'].mean()

total_co2_sum_g = co2_cold_ironing_sum_g + co2_propulsion_sum_g
total_co2_mean_g = co2_cold_ironing_mean_g + co2_propulsion_mean_g

# Combine all the values into a single row DataFrame
co2_summary_df = pd.DataFrame({
    'CO2 Cold Ironing Emission Sum': [co2_cold_ironing_sum_g],
    'CO2 Cold Ironing Emission Mean': [co2_cold_ironing_mean_g],
    'CO2 Propulsion Consumption Emission Sum': [co2_propulsion_sum_g],
    'CO2 Propulsion Consumption Emission Mean': [co2_propulsion_mean_g],
    'Total CO2 Emission Sum': [total_co2_sum_g],
    'Total CO2 Emission Mean': [total_co2_mean_g]
})
st.dataframe(co2_summary_df)

# SO2 Emission
st.title("SO2 Emission")
co2_cold_ironing_sum_g = df_main['so2_cold_ironing_emission'].sum()
co2_cold_ironing_mean_g = df_main['so2_cold_ironing_emission'].mean()

co2_propulsion_sum_g = df_main['so2_propulsion_consumption_emission'].sum()
co2_propulsion_mean_g = df_main['so2_propulsion_consumption_emission'].mean()

total_co2_sum_g = co2_cold_ironing_sum_g + co2_propulsion_sum_g
total_co2_mean_g = co2_cold_ironing_mean_g + co2_propulsion_mean_g

# Combine all the values into a single row DataFrame
co2_summary_df = pd.DataFrame({
    'SO2 Cold Ironing Emission Sum': [co2_cold_ironing_sum_g],
    'SO2 Cold Ironing Emission Mean': [co2_cold_ironing_mean_g],
    'SO2 Propulsion Consumption Emission Sum': [co2_propulsion_sum_g],
    'SO2 Propulsion Consumption Emission Mean': [co2_propulsion_mean_g],
    'Total SO2 Emission Sum': [total_co2_sum_g],
    'Total SO2 Emission Mean': [total_co2_mean_g]
})
st.dataframe(co2_summary_df)

# N20 Emission
st.title("N20 Emission")
co2_cold_ironing_sum_g = df_main['n20_cold_ironing_emission'].sum()
co2_cold_ironing_mean_g = df_main['n20_cold_ironing_emission'].mean()

co2_propulsion_sum_g = df_main['n20_propulsion_consumption_emission'].sum()
co2_propulsion_mean_g = df_main['n20_propulsion_consumption_emission'].mean()

total_co2_sum_g = co2_cold_ironing_sum_g + co2_propulsion_sum_g
total_co2_mean_g = co2_cold_ironing_mean_g + co2_propulsion_mean_g

# Combine all the values into a single row DataFrame
co2_summary_df = pd.DataFrame({
    'N20 Cold Ironing Emission Sum': [co2_cold_ironing_sum_g],
    'N20 Cold Ironing Emission Mean': [co2_cold_ironing_mean_g],
    'N20 Propulsion Consumption Emission Sum': [co2_propulsion_sum_g],
    'N20 Propulsion Consumption Emission Mean': [co2_propulsion_mean_g],
    'Total N20 Emission Sum': [total_co2_sum_g],
    'Total N20 Emission Mean': [total_co2_mean_g]
})
st.dataframe(co2_summary_df)

# CH4 Emission
st.title("CH4 Emission")
co2_cold_ironing_sum_g = df_main['ch4_cold_ironing_emission'].sum()
co2_cold_ironing_mean_g = df_main['ch4_cold_ironing_emission'].mean()

co2_propulsion_sum_g = df_main['ch4_propulsion_consumption_emission'].sum()
co2_propulsion_mean_g = df_main['ch4_propulsion_consumption_emission'].mean()

total_co2_sum_g = co2_cold_ironing_sum_g + co2_propulsion_sum_g
total_co2_mean_g = co2_cold_ironing_mean_g + co2_propulsion_mean_g

# Combine all the values into a single row DataFrame
co2_summary_df = pd.DataFrame({
    'CH4 Cold Ironing Emission Sum': [co2_cold_ironing_sum_g],
    'CH4 Cold Ironing Emission Mean': [co2_cold_ironing_mean_g],
    'CH4 Propulsion Consumption Emission Sum': [co2_propulsion_sum_g],
    'CH4 Propulsion Consumption Emission Mean': [co2_propulsion_mean_g],
    'Total CH4 Emission Sum': [total_co2_sum_g],
    'Total CH4 Emission Mean': [total_co2_mean_g]
})
st.dataframe(co2_summary_df)

# NOx Emission
st.title("NOx Emission")
co2_cold_ironing_sum_g = df_main['nox_cold_ironing_emission'].sum()
co2_cold_ironing_mean_g = df_main['nox_cold_ironing_emission'].mean()

co2_propulsion_sum_g = df_main['nox_propulsion_consumption_emission'].sum()
co2_propulsion_mean_g = df_main['nox_propulsion_consumption_emission'].mean()

total_co2_sum_g = co2_cold_ironing_sum_g + co2_propulsion_sum_g
total_co2_mean_g = co2_cold_ironing_mean_g + co2_propulsion_mean_g

# Combine all the values into a single row DataFrame
co2_summary_df = pd.DataFrame({
    'NOx Cold Ironing Emission Sum': [co2_cold_ironing_sum_g],
    'NOx Cold Ironing Emission Mean': [co2_cold_ironing_mean_g],
    'NOx Propulsion Consumption Emission Sum': [co2_propulsion_sum_g],
    'NOx Propulsion Consumption Emission Mean': [co2_propulsion_mean_g],
    'Total NOx Emission Sum': [total_co2_sum_g],
    'Total NOx Emission Mean': [total_co2_mean_g]
})
st.dataframe(co2_summary_df)

# PM10 Emission
st.title("PM10 Emission")
co2_cold_ironing_sum_g = df_main['pm10_cold_ironing_emission'].sum()
co2_cold_ironing_mean_g = df_main['pm10_cold_ironing_emission'].mean()

co2_propulsion_sum_g = df_main['pm10_propulsion_consumption_emission'].sum()
co2_propulsion_mean_g = df_main['pm10_propulsion_consumption_emission'].mean()

total_co2_sum_g = co2_cold_ironing_sum_g + co2_propulsion_sum_g
total_co2_mean_g = co2_cold_ironing_mean_g + co2_propulsion_mean_g

# Combine all the values into a single row DataFrame
co2_summary_df = pd.DataFrame({
    'PM10 Cold Ironing Emission Sum': [co2_cold_ironing_sum_g],
    'PM10 Cold Ironing Emission Mean': [co2_cold_ironing_mean_g],
    'PM10 Propulsion Consumption Emission Sum': [co2_propulsion_sum_g],
    'PM10 Propulsion Consumption Emission Mean': [co2_propulsion_mean_g],
    'Total PM10 Emission Sum': [total_co2_sum_g],
    'Total PM10 Emission Mean': [total_co2_mean_g]
})
st.dataframe(co2_summary_df)

st.title("Port Detail")
st.dataframe(df_main)