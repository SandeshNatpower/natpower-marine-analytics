import streamlit as st
import geopandas as gpd
from shapely import wkb
import folium
from streamlit_folium import folium_static
import binascii
import pandas as pd
from folium import GeoJson, Popup, GeoJsonTooltip
from datetime import timedelta
import datetime

# Sample DataFrame (already provided)
st.set_page_config(layout="wide")
st.image("images/LinkedIn Header - NatPower Marine.png", caption='© Natpower Marine', use_column_width=True)

st.sidebar.image("images/natpowermarine.png", caption='© Natpower Marine', use_column_width=True)

conn = st.connection("postgresql", type="sql")
df = conn.query("select distinct vessel_category FROM reference.ref_vessel_type_category;", ttl="10m")

# Sidebar filters
st.sidebar.title("Vessel Types - Verticals")

# Filter by Vessel
vessel_cat_list = df["vessel_category"].unique()
if 'Cargo vessels' in vessel_cat_list:
    vessel_index = list(vessel_cat_list).index('Cargo vessels')
else:
    vessel_index = 0 

vessel_options =  st.sidebar.selectbox("Vessel Category", options=vessel_cat_list,index=vessel_index)
df_cold = conn.query(f"select * FROM public.ref_cold_ironing where  vessel_category = '{vessel_options}';", ttl="10m")
df_cold['min_gt'] = pd.to_numeric(df_cold['min_gt'], errors='coerce')

st.title('Energy Calculator')
maincol1,maincol2 = st.columns(2)
with  maincol1:
    st.title('Cold Ironing - Hoteling - KW')
    col1,col2 = st.columns(2)
    with  col1:
        min_gt = int(st.number_input("Gross Weight Tonnage",value = 150)) 
    with col2:
        average_hoteling_kw = df_cold[(df_cold['min_gt'] >= min_gt) ]['average_hoteling_kw'].iloc[0] #(df_cold['max_gt'] <= max_gt) & 
        average_hoteling_kw = st.number_input("average_hoteling_kw",value = average_hoteling_kw)

with maincol2:
    st.title('Propulsion Consumption MW')
    # Propulsion 
    df_prop = conn.query(f"select * FROM public.ref_vessel_propulsion_consumption where  vessel_category = '{vessel_options}';", ttl="10m")
    df_prop['min_dwt'] = pd.to_numeric(df_prop['min_dwt'], errors='coerce')
    col1,col2 = st.columns(2)
    with col1:
        min_dwt = int(st.number_input("Dead Weight Tonnage",value = 14001))
    with col2:
        propulsion_consumption = df_prop[(df_prop['min_dwt'] >= min_gt)  ]['propulsion_consumption'].iloc[0] #& (df_prop['max_dwt'] <= max_gt)
        propulsion_consumption = st.number_input("propulsion_consumption",value = propulsion_consumption)

# Title of the app
st.title('Select Port Start Time & End Time')
col1,col2,col3 =st.columns(3)
default_date = datetime.date(2023, 1, 1)
default_time = datetime.time(0, 0)
with col1:
    start_date_input = st.date_input("Select a Start date", value= default_date)
    start_time_input = st.time_input("Select a Start time",value=default_time) 
    st.write(f"Start Time: {start_date_input} {start_time_input}") 
with col2:
    end_date_input = st.date_input("Select a End date", value=start_date_input + timedelta(days=1))
    end_time_input = st.time_input("Select a End time",value=default_time) 
    st.write(f"Start Time: {end_date_input} {end_time_input}")
with col3:
    # Combine date and time inputs into datetime objects
    start_datetime = datetime.datetime.combine(start_date_input, start_time_input)
    end_datetime = datetime.datetime.combine(end_date_input, end_time_input)

    # Calculate the total docking time
    docking_time = end_datetime - start_datetime

    # Display the total docking time
    st.write(f"Total Docking Time: {docking_time}")

    # Optionally, display the total docking time in hours and minutes
    total_hours = docking_time.total_seconds() / 3600
    st.write(f"Total Docking Time (Hours):")
    st.title(f" {total_hours:.2f} hours")

    # Title of the app
st.title('Interactive Data Editor for Docking Management')

# Define default values
col1,col2,col3 =st.columns(3)
with col1:
    num_terminals = int(st.number_input("Number Of Terminals ",value = 1))
with col2:
    num_berths = int(st.number_input("Number Of Berth ",value = 2))
with col3:
    num_vessels = int(st.number_input("Number Of Vessels Visited ",value = 1))
col1,col2 =st.columns(2)
with col1:
    port_dwell_time = int(st.number_input("Port to Berth Dwelling Time",value = 15))
with col2:
    port_dock_time = int(st.number_input("Berth Docking Time",value = 45))

# Generate default data
def generate_default_data(num_vessels, num_terminals, num_berths, port_dwell_time,port_dock_time):
    data = []
    index = 1
    prev_berth_departure = ''
    for vessel in range(1, num_vessels + 1):
        vessel_start_time = start_datetime
        prev_berth_departure =''
        for terminal in range(1, num_terminals + 1):
            for berth in range(1, num_berths + 1):

                # Set berth arrival and departure times within the start and end times
                berth_arrival = vessel_start_time + timedelta(minutes=port_dwell_time)
                berth_departure = berth_arrival + timedelta(minutes=port_dock_time)
                if prev_berth_departure == '':
                    prev_berth_departure = vessel_start_time
                if berth_departure > end_datetime:
                    berth_departure = end_datetime
                
                data.append({
                    "Vessel ID": f"Vessel_{vessel}",
                    "Port_Arrival": start_datetime,
                    "Port_Departure": end_datetime,
                    "Terminal": f"Terminal {terminal}",
                    "Berth": f"Berth {berth}",
                    "Berth_Arrival": berth_arrival,
                    "Berth_Departure": berth_departure,
                    "Port_Dwelling_Time": (berth_arrival - prev_berth_departure).total_seconds() / 3600 ,
                    "Berth_Docking_Time": (berth_departure - berth_arrival).total_seconds() / 3600 ,
                    "average_hoteling_MW" : average_hoteling_kw/1000,
                    "propulsion_consumption_MW": propulsion_consumption,
                    "Total_energy_consumption": average_hoteling_kw/1000 + propulsion_consumption,
                    "average_hoteling_MW/h" : average_hoteling_kw/1000 * (berth_departure - berth_arrival).total_seconds() / 3600,
                    "propulsion_consumption_mw/h": propulsion_consumption * (berth_arrival - prev_berth_departure).total_seconds() / 3600,
                    "Total_energy_consumption_mw/h": (average_hoteling_kw/1000 * (berth_departure - berth_arrival).total_seconds() / 3600 ) + (propulsion_consumption * (berth_arrival - prev_berth_departure).total_seconds() / 3600),
                })
                index += 1
                # Increment the vessel start time for the next berth
                vessel_start_time = berth_departure + timedelta(minutes=port_dwell_time)
                prev_berth_departure = berth_departure#
    return pd.DataFrame(data)

# Generate default DataFrame
default_df = generate_default_data(num_vessels, num_terminals, num_berths,port_dwell_time,port_dock_time)
st.title('Data Generated')
st.dataframe(default_df)
st.session_state.default_df = default_df

# Initialize the default DataFrame in the session state if it doesn't exist
if 'default_df' not in st.session_state:
    st.session_state.default_df = default_df

# Function to update the values based on edits
def change_val():
    st.session_state.default_df = default_df
    st.session_state.edited_df = edited_df
    df = st.session_state.edited_df.copy()  # Work with a copy to avoid in-place modifications
    df['Berth_Docking_Time'] = (df['Berth_Departure'] - df['Berth_Arrival']) / pd.Timedelta(hours=1)
    df['average_hoteling_MW/h'] = df['average_hoteling_MW'] * df['Berth_Docking_Time']
    df['propulsion_consumption_mw/h'] = df['propulsion_consumption_MW'] * df['Port_Dwelling_Time']
    df["Total_energy_consumption"] =  df['average_hoteling_MW'] + df['propulsion_consumption_MW']
    df["Total_energy_consumption_mw/h"] =  df['average_hoteling_MW/h'] + df['propulsion_consumption_mw/h']
    
    # Update the session state with the modified DataFrame
    st.session_state.edited_df = df

st.title('Editable DataFrame')

# Display the editable DataFrame
edited_df = st.data_editor(st.session_state.default_df, use_container_width=True)

# Function to highlight changes
def highlight_changes(val):
    original_val = st.session_state.default_df.loc[val.name, val.index]
    return ['background-color: yellow' if val[col] != original_val[col] else '' for col in val.index]

# Store the editable DataFrame in the session state if it hasn't been stored yet
if 'edited_df' not in st.session_state:
    st.session_state.edited_df = edited_df
    st.session_state.default_df = edited_df.copy()
else:
    # If already stored, update it to reflect changes
    st.session_state.edited_df = edited_df
    st.session_state.default_df = default_df

# Manually trigger the calculation function
change_val()

# Display the updated DataFrame
# st.write(st.session_state.edited_df)

# Function to highlight changes
def highlight_changes(val):
    original_val = st.session_state.default_df.loc[val.name, val.index]
    return ['background-color: yellow' if val[col] != original_val[col] else '' for col in val.index]

# After Calculation Title
st.title('After Calculation')

# Apply the highlighting and display the DataFrame
styled_df = st.session_state.edited_df.style.apply(highlight_changes, axis=1)
st.write(styled_df)
new_df = styled_df.data

columns_list =['Port_Dwelling_Time', 'Berth_Docking_Time', 'average_hoteling_MW/h',
                      'propulsion_consumption_mw/h', 'Total_energy_consumption', 'Total_energy_consumption_mw/h']

# Calculate the average (mean) of the specified columns
mean_values = new_df[columns_list].mean()

# Calculate the sum of the specified columns
sum_values = new_df[columns_list].sum()

# Combine the mean and sum into a new DataFrame
result_df = pd.DataFrame({
    'Average Value': mean_values,
    'Total Value': sum_values
})

st.dataframe(result_df)

# Emission
st.title('Emission Calculator')
df = conn.query(f"SELECT engine_group, pollutant_name, fuel_type, engine_type, emission_factor_formula, values_g_per_kwh FROM reporting.ref_emission_factors where pollutant_name = 'CO2';", ttl="10m")
df['Selection'] = False

auxiliary_selected = False
propulsion_selected = False
for index, row in df.iterrows():
    if row['engine_group'] == 'Auxiliary' and not auxiliary_selected:
        df.at[index, 'Selection'] = True
        auxiliary_selected = True  # Mark auxiliary as selected
    elif row['engine_group'] == 'Propulsion'and not propulsion_selected:
        propulsion_selected = True
        df.at[index, 'Selection'] = True

# Initialize session state
if 'prev_auxiliary_idx' not in st.session_state:
    st.session_state.prev_auxiliary_idx = None
if 'prev_propulsion_idx' not in st.session_state:
    st.session_state.prev_propulsion_idx = None

col1, col2 = st.columns(2)
with col1:
    if 'prev_auxiliary_idx' not in st.session_state:
        st.session_state.prev_auxiliary_idx = None
        
    emission_df = st.data_editor(df,disabled=('engine_group', 'pollutant_name', 'fuel_type', 'engine_type', 'emission_factor_formula'))
    st.session_state.emission_df = emission_df
    
with col2:
   # Initialize selection variables
    selected_auxiliary_value = None
    selected_propulsion_value = None

    # Check if any Auxiliary is selected
    aux_selection = emission_df[(emission_df['Selection'] == True) & (emission_df['engine_group'] == 'Auxiliary')]
    if not aux_selection.empty:
        selected_auxiliary_value = aux_selection['values_g_per_kwh'].iloc[0]
        current_auxiliary_idx = aux_selection.index[0]

        # Unselect the previous Auxiliary if a new one is selected
        if st.session_state.prev_auxiliary_idx is not None and st.session_state.prev_auxiliary_idx != current_auxiliary_idx:
            emission_df.at[st.session_state.prev_auxiliary_idx, 'Selection'] = False

        # Update session state for Auxiliary
        st.session_state.prev_auxiliary_idx = current_auxiliary_idx

    # Check if any Propulsion is selected
    prop_selection = emission_df[(emission_df['Selection'] == True) & (emission_df['engine_group'] == 'Propulsion')]
    if not prop_selection.empty:
        selected_propulsion_value = prop_selection['values_g_per_kwh'].iloc[0]
        current_propulsion_idx = prop_selection.index[0]

        # Unselect the previous Propulsion if a new one is selected
        if st.session_state.prev_propulsion_idx is not None and st.session_state.prev_propulsion_idx != current_propulsion_idx:
            emission_df.at[st.session_state.prev_propulsion_idx, 'Selection'] = False

        # Update session state for Propulsion
        st.session_state.prev_propulsion_idx = current_propulsion_idx

    # Display selected values
    st.write("Selected Auxiliary Value:", selected_auxiliary_value if selected_auxiliary_value is not None else "None")
    st.write("Selected Propulsion Value:", selected_propulsion_value if selected_propulsion_value is not None else "None")


def co2_change_val():
    # Add code here to display the records
    print('x')
   

def highlight_changes_co2(val):
    original_val = st.session_state.emission_df.loc[val.name, val.index]
    return ['background-color: yellow' if val[col] != original_val[col] else '' for col in val.index]


# Manually trigger the calculation function
co2_change_val()

# Future Year Forecast
st.title('Future Year Forecast')

col1,col2 = st.columns(2)
with col1:
    start_year = int(st.number_input("Future Start Year",value = 2024))
with col2:
    end_year = int(st.number_input("Future End Yeat",value = 2070))

df = conn.query(f"select distinct main_vessel_category FROM reference.ref_vessel_type_category where vessel_category = '{vessel_options}';", ttl="10m")
main_vessel_category = df['main_vessel_category'].iloc[0]

df = conn.query(f"SELECT * FROM public.ref_future_power_consumption where year between {start_year} and {end_year} and change_type in('Low','Medium','High','{main_vessel_category}');", ttl="10m")
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

df_extracted = styled_df.data
df_extracted['key'] = 1
df['key'] = 1
merged_df = pd.merge(df_extracted, df, on='key').drop('key', axis=1)
traffic = df[df['type'] == 'Traffic Forecast']
traffic['traffic'] = traffic['change_in_percentage']
traffic= traffic[['traffic','year_val']]

merged_df = pd.merge(merged_df, traffic, on='year_val')
merged_df['new_cold_ironing_mw_vessel'] = merged_df['average_hoteling_MW'] * ((1 + merged_df['traffic'])/100 )
merged_df['change_cold_ironing_mw_vessel'] = (merged_df['change_in_percentage']/100) * ( merged_df['average_hoteling_MW'] * ((1 + merged_df['traffic'])/100 ))
merged_df['new_propulsion_consumption'] = merged_df['propulsion_consumption_MW'] * (1 + merged_df['traffic']/100 )
merged_df['change_propulsion_consumption'] = (merged_df['change_in_percentage']/100) * ( merged_df['propulsion_consumption_MW'] * ((1 + merged_df['traffic'])/100 ))

merged_df['year'] = merged_df['year_val']
merged_df.set_index('year', inplace=True)

# st.dataframe(merged_df)

st.write("Cold Ironing - Future Forecast")
pivot_df =merged_df[merged_df['type'] == 'Cold Ironing'].pivot_table(index='year_val', columns='change_type', values='change_cold_ironing_mw_vessel', aggfunc='sum')
# st.dataframe(pivot_df)
st.line_chart(pivot_df)

st.write("Propulsion Adoption - Future Forecast")
pivot_df =merged_df[merged_df['type'] == 'Propulsion Adoption'].pivot_table(index='year_val', columns='change_type', values='change_cold_ironing_mw_vessel', aggfunc='sum')
# st.dataframe(pivot_df)
st.line_chart(pivot_df)

st.write("Propulsion Distance - Future Forecast")
pivot_df =merged_df[merged_df['type'] == 'Propulsion Distance'].pivot_table(index='year_val', columns='change_type', values='change_cold_ironing_mw_vessel', aggfunc='sum')
# st.dataframe(pivot_df)
st.line_chart(pivot_df)

st.write("Traffic Forecast - Future Forecast")
pivot_df =merged_df[merged_df['type'] == 'Traffic Forecast'].pivot_table(index='year_val', columns='change_type', values='change_cold_ironing_mw_vessel', aggfunc='sum')
# st.dataframe(pivot_df)
st.line_chart(pivot_df)