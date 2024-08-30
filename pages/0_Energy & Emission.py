import streamlit as st
import geopandas as gpd
from shapely import wkb
import folium
from streamlit_folium import folium_static
import binascii
import pandas as pd
from folium import GeoJson, Popup, GeoJsonTooltip
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
from fpdf import FPDF
from io import BytesIO
from PIL import Image
import tempfile
pd.options.mode.chained_assignment = None  # default='warn'


# Sample DataFrame (already provided)
st.set_page_config(layout="wide")
st.image("images/LinkedIn Header - NatPower Marine.png", caption='© Natpower Marine', use_column_width=True)

st.sidebar.image("images/natpowermarine.png", caption='© Natpower Marine', use_column_width=True)

# Cached database connection and query execution
@st.cache_resource(ttl="10m")
def get_connection():
    return st.connection("postgresql", type="sql")

@st.cache_data(ttl="10m")
def get_data(queryval):
    return conn.query(queryval)

conn = get_connection()

queryval = "SELECT DISTINCT country, port_name, terminal_name, berth_name, port_id, terminal_id, berth_id FROM reference.port_hierarchy;"
df = get_data(queryval)

# Sidebar filters
st.sidebar.header("Filter options - Port Selection Mandatory")

# Filter by Country
country_list = df["country"].unique()
if 'UNITED KINGDOM' in country_list:
    uk_index = list(country_list).index('UNITED KINGDOM')
else:
    uk_index = 0 

country_options =  st.sidebar.selectbox("Country", options=country_list,index=uk_index)

# Filter by Port
port_list = df[df['country'] == country_options]["port_name"].unique()
if 'ABERDEEN' in port_list:
    uk_index = list(port_list).index('HEYSHAM')
else:
    uk_index = 0 
port_options =  st.sidebar.selectbox("Select Port", options=port_list,index=uk_index)

def on_port_toggle():
    if st.session_state.port_level:
        st.session_state.terminal_level = False
        st.session_state.berth_level = False

Port_level = st.sidebar.toggle("Show Port level details",key="port_level",value=True, on_change=on_port_toggle)
# Initialize session state variables if they do not exist
st.session_state.Port_level = True
color = 'red'
query = f"SELECT * FROM reference.port_hierarchy where country = '{country_options}' and port_name = '{port_options}';"


terminal_options_list = df[(df['country'] == country_options) & (df['port_name'] == port_options)]["terminal_name"].unique().tolist()
terminal_options_list.insert(0, None)
terminal_options =  st.sidebar.selectbox("Select Terminal", options= terminal_options_list,index=1)

def on_terminal_toggle():
    if st.session_state.terminal_level:
        st.session_state.port_level = False
        st.session_state.berth_level = False 

if terminal_options != None:
    terminal_level = st.sidebar.toggle("Show Terminal level details",key="terminal_level", on_change=on_terminal_toggle)
    color = 'yellow'
    query = f"SELECT * FROM reference.port_hierarchy where country = '{country_options}' and port_name = '{port_options}' and terminal_name = '{terminal_options}';"


# Filter by Port
berth_options_list = df[(df['country'] == country_options) & (df['port_name'] == port_options) & (df['terminal_name'] == terminal_options) ]["berth_name"].unique().tolist()
berth_options_list.insert(0, None)
berth_options =  st.sidebar.selectbox("Select Berth", options=berth_options_list,index=1)

def on_berth_toggle():
    if st.session_state.berth_level:
        st.session_state.terminal_level = False
        st.session_state.port_level = False 

if berth_options != None:
    berth_level = st.sidebar.toggle("Show Berth level details",key="berth_level", on_change=on_berth_toggle)
    color = 'blue'
    query = f"SELECT * FROM reference.port_hierarchy where country = '{country_options}' and port_name = '{port_options}' and terminal_name = '{terminal_options}' and berth_name = '{berth_options}';"

df_loc = get_data(query)

# # Convert the 'geometry' column from WKB hex string to Shapely geometry objects
df_loc['port_geometry'] = df_loc['port_geometry'].apply(lambda x: wkb.loads(binascii.unhexlify(x)))
df_loc['terminal_location'] = df_loc['terminal_location'].apply(lambda x: wkb.loads(binascii.unhexlify(x)))
df_loc['berth_location'] = df_loc['berth_location'].apply(lambda x: wkb.loads(binascii.unhexlify(x)))

@st.cache_data(ttl="10m")
def convert_and_create_geodataframe(df_loc):
    gdf = gpd.GeoDataFrame(df_loc, geometry='port_geometry')
    return gdf

gdf = convert_and_create_geodataframe(df_loc)

# Create a folium map centered around the first geometry
if not gdf.empty:
    m = folium.Map(location=[55, -3], zoom_start=5,use_column_width=True)  # Center map around the UK

    # Add each geometry to the map with different colors based on type
    for _, row in gdf.iterrows():       
        if st.session_state.port_level:
            for _, row in df_loc.iterrows():
                popup_content = (
                    f"<div><strong>Port Location:</strong> {row['port_name']}<br>"
                    f"<strong>Country:</strong> {row['country']}<br></div>"
                )

                folium.GeoJson(
                    row["port_geometry"],
                    name=row["port_name"],
                    style_function=lambda x: {'Opacity': 0.8, 'color': 'green'},
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=f'{row["port_name"]} - {row["port_id"]} ({row["country"]})',
                    highlight_function=lambda x: {'weight': 5, 'color': 'yellow', 'fillOpacity': 0.7}
                ).add_to(m)
                # Calculate the bounds for each feature
                feature_shape = row["port_geometry"]
                query_energy  = f"""select t1.*, mvd.vessel_name, mvd.new_vessel_type, mvd.new_vessel_category, mvd.vesseltypeandsize, mvd.imo, mvd.mmsi, 
                mvd.flag, mvd.callsign, mvd.dwt, mvd.gross_tonnage, mvd.build, 
				mvd.average_hoteling_kw, mvd.propulsion_consumption, mvd.engine_type, mvd.engine_count, mvd.engine_value, mvd.engine_horsepower,
				mvd.owner_name, mvd.operator_name,mvd.registered_owner,mvd.third_party_operator,mvd.technical_manager,mvd.ism_manager,
                mvd.length_m,mvd.breadth_m   From reporting.get_port_energy_emission({df_loc['port_id'][0]}) t1 left join reporting.mview_vessel_details mvd on t1.vessel_id = mvd.vessel_id;"""
                display_name = 'Port'

        elif st.session_state.terminal_level:
            for _, row in df_loc.iterrows():
                popup_content = (
                    f"<div><strong>Terminal Location: {row['terminal_name']}</strong><br>"
                    f"<strong>Port:</strong> {row['port_name']}<br>"
                    f"<strong>Country:</strong> {row['country']}<br></div>"
                )

                folium.GeoJson(
                    row["terminal_location"],
                    name=row["port_name"],
                    style_function=lambda x: {'Opacity': 0.8, 'color': 'blue'},
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=f'{row["terminal_name"]} - {row["terminal_id"]} ({row["country"]})',
                    highlight_function=lambda x: {'weight': 5, 'color': 'yellow', 'fillOpacity': 0.7}
                ).add_to(m)
                # Calculate the bounds for each feature
                feature_shape = row["terminal_location"]
                query_energy  = f"""select  t1.*, mvd.vessel_name, mvd.new_vessel_type, mvd.new_vessel_category, mvd.vesseltypeandsize, mvd.imo, mvd.mmsi,
                mvd.flag, mvd.callsign, mvd.dwt, mvd.gross_tonnage, mvd.build, 
				mvd.average_hoteling_kw, mvd.propulsion_consumption, mvd.engine_type, mvd.engine_count, mvd.engine_value, mvd.engine_horsepower,
				mvd.owner_name, mvd.operator_name,mvd.registered_owner,mvd.third_party_operator,mvd.technical_manager,mvd.ism_manager,
                mvd.length_m,mvd.breadth_m   From reporting.get_terminal_energy_emission({df_loc['port_id'][0]},{df_loc['terminal_id'][0]}) t1 left join reporting.mview_vessel_details mvd on t1.vessel_id = mvd.vessel_id;"""
                display_name = 'Terminal'

        elif st.session_state.berth_level:
            for _, row in df_loc.iterrows():
                popup_content = (
                    f"<div><strong>Berth Location: {row['berth_name']}</strong><br>"
                    f"<strong>Terminal Location: {row['terminal_name']}</strong><br>"
                    f"<strong>Port Location: {row['port_name']}</strong><br>"
                    f"<strong>Country:</strong> {row['country']}<br></div>"
                )

                folium.GeoJson(
                    row["berth_location"],
                    name=row["port_name"],
                    style_function=lambda x: {'Opacity': 0.8, 'color': 'red'},
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=f'{row["berth_name"]} - {row["berth_id"]} - {row["port_name"]} - {row["terminal_name"]}-  {row["country"]}',
                    highlight_function=lambda x: {'weight': 5, 'color': 'yellow', 'fillOpacity': 0.7}
                ).add_to(m)
                 # Calculate the bounds for each feature
                feature_shape = row["berth_location"]
                query_energy  = f"""select  t1.*, mvd.vessel_name, mvd.new_vessel_type, mvd.new_vessel_category, mvd.vesseltypeandsize, mvd.imo, mvd.mmsi,
                mvd.flag, mvd.callsign, mvd.dwt, mvd.gross_tonnage, mvd.build, 
				mvd.average_hoteling_kw, mvd.propulsion_consumption, mvd.engine_type, mvd.engine_count, mvd.engine_value, mvd.engine_horsepower,
				mvd.owner_name, mvd.operator_name,mvd.registered_owner,mvd.third_party_operator,mvd.technical_manager,mvd.ism_manager,
                mvd.length_m,mvd.breadth_m    From reporting.get_berth_energy_emission({df_loc['port_id'][0]},{df_loc['terminal_id'][0]},{df_loc['berth_id'][0]}) t1 left join reporting.mview_vessel_details mvd on t1.vessel_id = mvd.vessel_id;"""
                display_name = 'Berth'

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

# df_main = conn.query(query_energy, ttl="10m")

@st.cache_data(ttl="10m")
def get_emission_data(query):
    return get_data(query)

df_main = get_emission_data(query_energy)

col1, col2 = st.columns(2)
with col1:
    st.title(f'Total {display_name} Vessel Visit Count - ' + str(df_main['vessel_id'].count()))
with col2:
    st.title(f'Unique {display_name} Vessel Visit Count - ' + str(df_main['vessel_id'].nunique())) 

st.title("Docking & Dwelling Time")

if st.session_state.port_level:
    col1, col2,col3 = st.columns(3)
    
    with col1:
        st.write(f'Average {display_name} Docking Time Hrs')
        st.write(str(df_main['port_docking_time_hr'].mean()))
        st.write(f'Total {display_name} Docking Time Hrs')
        st.write(str(df_main['port_docking_time_hr'].sum()))
    with col2:
        st.write('Average Berth Docking Time Hrs')
        st.write(str(df_main['berth_docking_time_hr'].mean()))
        st.write('Total Berth Docking Time Hrs')
        st.write(str(df_main['berth_docking_time_hr'].sum()))
    with col3:
        st.write('Average Port Dwelling Time Hrs')
        st.write(str(df_main['port_dwelling_time_hr'].mean()))
        st.write('Total Port Dwelling Time Hrs')
        st.write(str(df_main['port_dwelling_time_hr'].sum()))
            
elif st.session_state.terminal_level:
    col1, col2,col3 = st.columns(3)
    with col1:
        st.write(f'Average {display_name} Docking Time Hrs')
        st.write(str(df_main['terminal_docking_time_hr'].mean()))
        st.write(f'Total {display_name} Docking Time Hrs')
        st.write(str(df_main['terminal_docking_time_hr'].sum()))
    with col2:
        st.write('Average Berth Docking Time Hrs')
        st.write(str(df_main['berth_docking_time_hr'].mean()))
        st.write('Total Berth Docking Time Hrs')
        st.write(str(df_main['berth_docking_time_hr'].sum()))
    with col3:
        st.write(f'Average {display_name}  Dwelling Time Hrs')
        st.write(str(df_main['terminal_dwelling_time_hr'].mean()))
        st.write(f'Total {display_name}  Dwelling Time Hrs')
        st.write(str(df_main['terminal_dwelling_time_hr'].sum()))

elif st.session_state.berth_level:
    col1, col2 = st.columns(2)
    with col1:
        st.write('Average Berth Docking Time Hrs')
        st.write(str(df_main['berth_docking_time_hr'].mean()))
        st.write('Total Berth Docking Time Hrs')
        st.write(str(df_main['berth_docking_time_hr'].sum()))
    with col2:
        st.write('Average Berth Dwelling Time Hrs')
        st.write(str(df_main['berth_dwelling_time_hr'].mean()))
        st.write('Total Berth Dwelling Time Hrs')
        st.write(str(df_main['berth_dwelling_time_hr'].sum()))   


st.title("Cold Ironing & Propulsion Consumption in MW")
col1, col2 = st.columns(2)
with col1:
    st.write('Average Cold Ironing in MW')
    st.write(str(df_main['cold_ironing_mw'].mean()))
    st.write('Total Cold Ironing in MW')
    st.write(str(df_main['cold_ironing_mw'].sum()))
with col2:
    st.write('Average Propulsion Consumption in MW')
    st.write(str(df_main['propulsion_consumption_mw'].mean()))
    st.write('Total Propulsion Consumption in MW')
    st.write(str(df_main['propulsion_consumption_mw'].sum()))

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
st.image("images/carbon emissions.png", caption='© Natpower Marine', use_column_width=True)

@st.cache_data(ttl="10m")
def calculate_emission_summary(df, emission_type):
    st.title(f"{emission_type.upper()} Emission")
    cold_ironing_sum = df[f'{emission_type}_cold_ironing_emission'].sum()
    cold_ironing_mean = df[f'{emission_type}_cold_ironing_emission'].mean()
    
    propulsion_sum = df[f'{emission_type}_propulsion_consumption_emission'].sum()
    propulsion_mean = df[f'{emission_type}_propulsion_consumption_emission'].mean()
    
    total_sum = cold_ironing_sum + propulsion_sum
    total_mean = cold_ironing_mean + propulsion_mean
    
    summary_df = pd.DataFrame({
        f'{emission_type.upper()} Cold Ironing Emission Sum': [cold_ironing_sum],
        f'{emission_type.upper()} Cold Ironing Emission Mean': [cold_ironing_mean],
        f'{emission_type.upper()} Propulsion Consumption Emission Sum': [propulsion_sum],
        f'{emission_type.upper()} Propulsion Consumption Emission Mean': [propulsion_mean],
        f'Total {emission_type.upper()} Emission Sum': [total_sum],
        f'Total {emission_type.upper()} Emission Mean': [total_mean]
    })
    
    return summary_df

# Define the emission types you want to summarize
emission_types = ['co2', 'so2', 'n20', 'ch4', 'nox', 'pm10']

# Loop through emission types and display summaries
for emission_type in emission_types:
    summary_df = calculate_emission_summary(df_main, emission_type)
    st.dataframe(summary_df)

# Display the main DataFrame at the end
st.title(f"{display_name} Detail")
st.dataframe(df_main)

if st.session_state.port_level:
    columns_to_remove = ['vessel_id', 'port_id']
elif st.session_state.terminal_level:
    columns_to_remove = ['vessel_id', 'terminal_id']
elif st.session_state.berth_level:
    columns_to_remove = ['vessel_id', 'berth_id']

@st.cache_data(ttl="10m")
def process_and_group_data(df, columns_to_remove):
    # Remove specified columns
    df_filtered = df.drop(columns=columns_to_remove)

    # Identify numerical columns
    numerical_cols = df_filtered.select_dtypes(include=['number']).columns

    # Define aggregation functions
    agg_funcs = {col: ['sum', 'mean'] for col in numerical_cols}

    # Group by 'new_vessel_category' and apply aggregations
    grouped_df = df.groupby('new_vessel_category').agg(agg_funcs).reset_index()

    # Flatten the MultiIndex columns
    grouped_df.columns = ['_'.join(col).strip() for col in grouped_df.columns.values]

    return grouped_df

grouped_df = process_and_group_data(df_main, columns_to_remove)

st.dataframe(grouped_df)


# Define time classification function
@st.cache_data(ttl="10m")
def classify_time(dt):
    if 5 <= dt.hour < 12:
        return 'Morning'
    elif 12 <= dt.hour < 17:
        return 'Afternoon'
    elif 17 <= dt.hour < 21:
        return 'Evening'
    else:
        return 'Night'

@st.cache_data(ttl="10m")
def process_docking_times(df, display_name):
    # Apply classification
    df['arrival_time_of_day'] = df[f'min_{display_name.lower()}_arrival'].apply(classify_time)

    # Order for time of day
    time_order = ['Morning', 'Afternoon', 'Evening', 'Night']

    # Aggregate docking times
    arrival_docking_times = df.groupby(['new_vessel_category', 'arrival_time_of_day'])['berth_docking_time_hr'].sum().unstack(fill_value=0)

    # Ensure time of day and vessel category order
    arrival_docking_times = arrival_docking_times.reindex(columns=time_order).fillna(0)

    # Order vessel categories by total docking time
    arrival_totals = arrival_docking_times.sum(axis=1).sort_values(ascending=False)

    arrival_docking_times = arrival_docking_times.loc[arrival_totals.index]

    return arrival_docking_times

# Example usage in Streamlit
arrival_docking_times = process_docking_times(df_main, display_name)

# Streamlit app
st.title('Docking Times Analysis')

# Plotting
fig, ax = plt.subplots(figsize=(12, 8))

# Plot arrival docking times
arrival_docking_times.plot(kind='bar', ax=ax, position=0, width=0.4, label='Arrival Docking Time')

# Labels and title
ax.set_xlabel('Vessel Category')
ax.set_ylabel('Total Docking Time (hours)')
ax.set_title('Total Docking Time by Vessel Category and Time of Day')
ax.legend(title='Event Type')

# Show the plot in Streamlit
st.pyplot(fig)

########################################################################################################

# Extract month and year for aggregation
df_main['year_month'] = df_main[f'min_{display_name.lower()}_arrival'].dt.to_period('M')

# Aggregate docking times by month and category
monthly_docking_times = df_main.groupby(['year_month', 'new_vessel_category'])['berth_docking_time_hr'].sum().unstack(fill_value=0)

# Streamlit app
st.title('Monthly Docking Times Analysis')

# Plotting
fig, ax = plt.subplots(figsize=(12, 8))

# Plot time series
for category in monthly_docking_times.columns:
    ax.plot(monthly_docking_times.index.to_timestamp(), monthly_docking_times[category], marker='o', label=category)

# Labels and title
ax.set_xlabel('Date')
ax.set_ylabel('Total Docking Time (hours)')
ax.set_title('Monthly Docking Times by Vessel Category')
ax.legend(title='Vessel Category')

# Show the plot in Streamlit
st.pyplot(fig)

###################################################################################
st.title('Future Forecast')

# Extract unique vessel categories
categories = df_main['new_vessel_category'].unique()

# Format categories for SQL query
formatted_categories = ",".join([f"'{cat}'" for cat in categories])

df = conn.query(f"SELECT * FROM public.ref_future_power_consumption where year between 2024 and 2070 and change_type in('Low','Medium','High',{formatted_categories});", ttl="10m")
df['year'] = pd.to_datetime(df['year'], format='%Y')
df['year_val'] = df['year']
df.set_index('year', inplace=True)
# Set up columns in Streamlit

col1, col2, col3, col4 = st.columns(4)

# Cold Ironing chart
with col1:
    st.write("Cold Ironing")
    pivot_df = df[df['type'] == 'Cold Ironing'].pivot( columns='change_type', values='change_in_percentage')
    st.dataframe(pivot_df)
    st.line_chart(pivot_df)

# Propulsion Adoption chart
with col2:
    st.write("Propulsion Adoption")
    pivot_df = df[df['type'] == 'Propulsion Adoption'].pivot( columns='change_type', values='change_in_percentage')
    st.dataframe(pivot_df)
    st.line_chart(pivot_df)

# Propulsion Distance chart
with col3:
    st.write("Propulsion Distance")
    pivot_df = df[df['type'] == 'Propulsion Distance'].pivot( columns='change_type', values='change_in_percentage')
    st.dataframe(pivot_df)
    st.line_chart(pivot_df)

# Traffic Forecast chart
with col4:
    st.write("Traffic Forecast")
    pivot_df = df[df['type'] == 'Traffic Forecast'].pivot( columns='change_type', values='change_in_percentage')
    st.dataframe(pivot_df)
    st.line_chart(pivot_df)

@st.cache_data(ttl="10m")
def preprocess_and_forecast(df_extracted, df):
    # Extract and prepare data
    df_extracted['key'] = 1
    df['key'] = 1
    
    # Merge dataframes
    merged_df = pd.merge(df_extracted, df, on='key').drop('key', axis=1)
    
    try:
        # Prepare traffic data
        traffic = df[df['type'] == 'Traffic Forecast'].copy()
        traffic['traffic'] = traffic['change_in_percentage']
        traffic = traffic[['traffic', 'year_val']]
        
        # Merge traffic data
        merged_df = pd.merge(merged_df, traffic, on='year_val')

        # Calculate new values
        merged_df['new_cold_ironing_mw_vessel'] = merged_df['cold_ironing_mw'] * ((1 + merged_df['traffic']) / 100)
        merged_df['change_cold_ironing_mw_vessel'] = (merged_df['change_in_percentage'] / 100) * (
            merged_df['cold_ironing_mw'] * ((1 + merged_df['traffic']) / 100))
        merged_df['new_propulsion_consumption'] = merged_df['propulsion_consumption_mw'] * (1 + merged_df['traffic'] / 100)
        merged_df['change_propulsion_consumption'] = (merged_df['change_in_percentage'] / 100) * (
            merged_df['propulsion_consumption_mw'] * ((1 + merged_df['traffic']) / 100))

        merged_df['year'] = merged_df['year_val']
        merged_df.set_index('year', inplace=True)

        return merged_df
    except Exception as e:
        st.write("No data available for future forecast")
        st.write(str(e))
        return pd.DataFrame()  # Return empty DataFrame if there's an error

@st.cache_data(ttl="10m")
def plot_forecasts(merged_df):
    try:
        # Plot Cold Ironing forecast
        st.write("Cold Ironing - Future Forecast")
        pivot_df = merged_df[merged_df['type'] == 'Cold Ironing'].pivot_table(
            index='year_val', columns='change_type', values='change_cold_ironing_mw_vessel', aggfunc='sum')
        st.line_chart(pivot_df)

        # Plot Propulsion Adoption forecast
        st.write("Propulsion Adoption - Future Forecast")
        pivot_df = merged_df[merged_df['type'] == 'Propulsion Adoption'].pivot_table(
            index='year_val', columns='change_type', values='change_cold_ironing_mw_vessel', aggfunc='sum')
        st.line_chart(pivot_df)

        # Plot Propulsion Distance forecast
        st.write("Propulsion Distance - Future Forecast")
        pivot_df = merged_df[merged_df['type'] == 'Propulsion Distance'].pivot_table(
            index='year_val', columns='change_type', values='change_cold_ironing_mw_vessel', aggfunc='sum')
        st.line_chart(pivot_df)

        # Plot Traffic Forecast
        st.write("Traffic Forecast - Future Forecast")
        pivot_df = merged_df[merged_df['type'] == 'Traffic Forecast'].pivot_table(
            index='year_val', columns='change_type', values='change_cold_ironing_mw_vessel', aggfunc='sum')
        st.line_chart(pivot_df)
    except Exception as e:
        st.write("Error generating plots")
        st.write(str(e))

merged_df = preprocess_and_forecast(df_main, df)
plot_forecasts(merged_df)