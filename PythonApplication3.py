import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Multi-Disease Data Analyzer (COVID-19, Influenza, Diabetes, Heart Disease, Cancer, etc.)",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================= CUSTOM CSS =================
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fc; }
    h1, h2, h3 { color: #1e3a8a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { background-color: #3b82f6; color: white; border-radius: 8px; border: none; padding: 0.5rem 1rem; font-weight: 600; }
    .stButton>button:hover { background-color: #2563eb; }
    .card { background-color: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 1.5rem; margin-bottom: 1.5rem; }
    </style>
""", unsafe_allow_html=True)

# ================= DATA SOURCES =================
COVID_LOCAL_PATH = "covid.csv"
FLU_URL = "https://drive.google.com/uc?export=download&id=1moYESuDnMJSwfmAbchv8uRlvFB0Fp5Q0"

# Global Data URLs (new datasets added here)
DATA_URLS = {
    'COVID-19': "https://ghoapi.azureedge.net/api/IncidenceMortality?Format=csv",
    'Influenza': "https://apps.who.int/gho/athena/data/GHO/WHO_Flune_Incidence.csv?profile=csv",
    'Diabetes': "https://www.who.int/docs/default-source/gho-documents/global-health-estimates/ghe-diabetes-prevalence.csv",
    'Cancer': "https://ghoapi.azureedge.net/api/IncidenceMortality?format=csv",
    'HIV/AIDS': "https://data.unaids.org/pub/BaseDocument/2023/UNAIDS_Global_HIV_Estimates_2023_Data.csv",
    'Malaria': "https://apps.who.int/gho/athena/api/GHO/MALARIA_000000?format=csv",
    'Tuberculosis': "https://apps.who.int/gho/athena/api/GHO/TB_000000?format=csv",
    'Obesity': "https://www.who.int/data/gho/data/themes/topics/obesity",
    'COPD/Asthma': "https://apps.who.int/gho/athena/api/GHO/COPD_000000?format=csv",
    'Cardiovascular Disease': "https://apps.who.int/gho/athena/api/GHO/CVD_000000?format=csv",
    'Diarrheal Diseases': "https://apps.who.int/gho/athena/api/GHO/DIARRHOEAL_000000?format=csv",
    'Hepatitis': "https://apps.who.int/gho/athena/api/GHO/HEP_B_C_000000?format=csv",
    'Depression': "https://apps.who.int/gho/athena/api/GHO/DEPRESSION_000000?format=csv",
    'Heart Disease': "https://ghoapi.azureedge.net/api/IncidenceMortality_CVD?format=csv",
}

# ================= LOAD DATA =================
@st.cache_data(ttl=86400)
def load_data(dataset_name):
    url = DATA_URLS[dataset_name]
    try:
        df = pd.read_csv(url)
    except Exception as e:
        st.error(f"Error loading {dataset_name} data: {e}")
        return None
    return df

# ================= SIDEBAR =================
with st.sidebar:
    st.header("Analysis Settings")
    dataset_name = st.selectbox("Select Dataset", list(DATA_URLS.keys()))

    st.markdown("### Country Selection")
    user_input = st.text_input("Enter countries (comma-separated) or type 'all'", "")
    
    processed_countries = []
    if user_input.strip():
        if user_input.lower().strip() == "all":
            processed_countries = ["All Countries"]
        else:
            parts = [p.strip().title() for p in user_input.split(",") if p.strip()]
            processed_countries = parts
    
    selected_countries = st.multiselect(
        "Selected Countries",
        processed_countries,
        default=processed_countries
    )
    
    st.markdown("### Time Period")
    year_options = ["All Years"]
    selected_year = st.selectbox("Select Year", year_options)
    
    analyze_button = st.button("Analyze Data", type="primary")

# ================= MAIN =================
st.title("Multi-Disease Data Analyzer")
st.markdown("Interactive dashboard for global disease data including COVID-19, Influenza, Diabetes, Heart Disease, Cancer, and others.")

if analyze_button:
    if not selected_countries:
        st.warning("Please select at least one country before analyzing.")
    else:
        df = load_data(dataset_name)
        
        if df is None:
            st.error(f"Could not load data for {dataset_name}.")
        else:
            st.success(f"Analyzing {dataset_name} for: {', '.join(selected_countries)}")
            
            # Filter data by selected countries (if applicable)
            if "Country" in df.columns:
                df = df[df["Country"].isin(selected_countries)]
            
            # Handle missing or NaN values in the data
            df = df.fillna(0)
            
            # Plot the data (assumes time series or year-based data)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                
                # Group by Year and sum up the data
                df_yearly = df.groupby(df["Date"].dt.year).sum()
                
                # Plot
                fig = px.bar(df_yearly, x=df_yearly.index, y=df_yearly.columns, labels={"x": "Year"})
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown(f"Data analysis for **{dataset_name}** is now complete!")
            else:
                st.warning("Data does not have a 'Date' column for time series analysis.")

            # Export data as CSV
            st.download_button(
                label="Download Data as CSV",
                data=df.to_csv(index=False),
                file_name=f"{dataset_name}_data.csv",
                mime="text/csv",
            )

else:
    st.info("👈 Select a dataset, enter countries, then click **Analyze Data** to generate the dashboard.")
