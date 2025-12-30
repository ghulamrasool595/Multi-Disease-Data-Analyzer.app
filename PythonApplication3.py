import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Multi-Disease Data Analyzer (COVID-19 & Influenza)",
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
COVID_URL = "https://raw.githubusercontent.com/datasets/covid-19/master/data/countries-aggregated.csv"
FLU_LOCAL_PATH = "flewdata.csv"

# ================= LOAD DATA =================
@st.cache_data(ttl=86400)
def load_covid_data():
    df = pd.read_csv(COVID_URL, parse_dates=["Date"])
    countries = sorted(df["Country"].unique())
    years = sorted(df["Date"].dt.year.unique())
    return df, countries, years

@st.cache_data(ttl=86400)
def load_flu_data():
    if not os.path.exists(FLU_LOCAL_PATH):
        st.error(f"Flu dataset '{FLU_LOCAL_PATH}' not found! Place it in the same folder.")
        st.stop()
    df = pd.read_csv(FLU_LOCAL_PATH)
    df = df.rename(columns={
        "COUNTRY_AREA_TERRITORY": "Country",
        "ISO_WEEKSTARTDATE": "Date",
        "ISO_YEAR": "Year",
        "INF_ALL": "Cases",
        "INF_A": "Influenza_A",
        "INF_B": "Influenza_B"
    })
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df["Cases"] = pd.to_numeric(df["Cases"], errors='coerce').fillna(0)
    df = df.dropna(subset=["Date", "Country"])
    countries = sorted(df["Country"].unique())
    years = sorted(df["Year"].unique())
    return df, countries, years

covid_df, covid_countries, covid_years = load_covid_data()
flu_df, flu_countries, flu_years = load_flu_data()

shortname_map = {
    "UAE": "United Arab Emirates", "KSA": "Saudi Arabia", "SAUDI": "Saudi Arabia",
    "UK": "United Kingdom", "US": "United States", "USA": "United States"
}

# ================= SIDEBAR =================
with st.sidebar:
    st.header("Analysis Settings")
    disease = st.selectbox("Select Disease", ["COVID-19", "Influenza (FluNet)"])
    
    if disease == "COVID-19":
        all_countries = covid_countries
        available_years = covid_years
        df_source = covid_df
    else:
        all_countries = flu_countries
        available_years = flu_years
        df_source = flu_df
    
    st.markdown("### Country Selection")
    # EMPTY default — no auto-selected countries
    user_input = st.text_input("Enter countries (comma-separated) or type 'all'", "")
    
    # Process input only when user clicks Analyze
    processed_countries = []
    if user_input.strip():
        if user_input.lower().strip() == "all":
            processed_countries = all_countries
        else:
            parts = [p.strip().title() for p in user_input.split(",") if p.strip()]
            for p in parts:
                upper = p.upper().replace(" ", "").replace(".", "")
                mapped = shortname_map.get(upper, p)
                if mapped in all_countries:
                    processed_countries.append(mapped)
                else:
                    matches = [c for c in all_countries if c.lower() == p.lower()]
                    if matches:
                        processed_countries.append(matches[0])
        processed_countries = list(set(processed_countries))  # dedupe
    
    # Multiselect starts empty and shows processed ones as default after input
    selected_countries = st.multiselect(
        "Selected Countries",
        all_countries,
        default=processed_countries  # only filled after user types something
    )
    
    st.markdown("### Time Period")
    year_options = ["All Years"] + [str(y) for y in available_years]
    selected_year = st.selectbox("Select Year", year_options)
    
    analyze_button = st.button("Analyze Data", type="primary")

# ================= MAIN =================
st.title("Multi-Disease Data Analyzer")
st.markdown("Interactive dashboard for COVID-19 and Influenza (FluNet) data.")

if analyze_button:
    if not selected_countries:
        st.warning("Please select at least one country before analyzing.")
    else:
        valid_countries = selected_countries  # already validated via multiselect
        st.success(f"Analyzing {disease} for: {', '.join(valid_countries)}")
        
        df = df_source[df_source["Country"].isin(valid_countries)].copy()
        df = df.sort_values("Date")
        
        if selected_year != "All Years":
            df = df[df["Date"].dt.year == int(selected_year)]
        
        # Metrics
        if disease == "COVID-19":
            df["Confirmed"] = pd.to_numeric(df["Confirmed"], errors='coerce').fillna(0)
            df["NewCases"] = df.groupby("Country")["Confirmed"].diff().fillna(0).clip(lower=0)
            main_metric = "Confirmed"
            new_metric = "NewCases"
            metric_label = "Confirmed Cases"
            new_label = "New Cases (Daily)"
            color_sequence = ["#60a5fa"]
        else:
            df["Cases"] = pd.to_numeric(df["Cases"], errors='coerce').fillna(0)
            main_metric = "Cases"
            new_metric = "Cases"
            metric_label = "Influenza Positives"
            new_label = "Positives (Weekly)"
            color_sequence = ["#ef4444"]
        
        years = sorted(df["Date"].dt.year.unique())
        
        # Individual bars
        st.header(f"{metric_label} per Year by Country")
        cols = st.columns(min(3, len(valid_countries)))
        for i, country in enumerate(valid_countries):
            with cols[i % len(cols)]:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader(country)
                country_df = df[df["Country"] == country]
                yearly = country_df.groupby(country_df["Date"].dt.year)[main_metric].sum().reindex(years, fill_value=0)
                fig = px.bar(yearly.reset_index(), x="Date", y=main_metric,
                             color_discrete_sequence=color_sequence,
                             labels={"Date": "Year", main_metric: metric_label})
                fig.update_layout(height=400, margin=dict(l=20,r=20,t=20,b=20), showlegend=False)
                fig.update_yaxes(tickformat=",")
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Comparison bar
        st.header(f"Yearly {metric_label} Comparison")
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            comparison_data = {c: df[df["Country"] == c].groupby(df["Date"].dt.year)[main_metric].sum() for c in valid_countries}
            comparison_df = pd.DataFrame(comparison_data).reindex(years, fill_value=0)
            melted = comparison_df.reset_index().melt(id_vars="Date", var_name="Country", value_name=metric_label)
            fig = px.bar(melted, x="Date", y=metric_label, color="Country", barmode="group")
            fig.update_layout(height=500, margin=dict(l=20,r=20,t=20,b=20))
            fig.update_yaxes(tickformat=",")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Time series
        st.header(f"{new_label} Over Time (7-period Rolling Average)")
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            fig = go.Figure()
            for country in valid_countries:
                ts = df[df["Country"] == country].set_index("Date")[new_metric].rolling(7, min_periods=1).mean()
                if ts.sum() > 0:
                    fig.add_trace(go.Scatter(x=ts.index, y=ts.values, mode="lines", name=country))
            fig.update_layout(height=500, xaxis_title="Date", yaxis_title=new_label,
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig.update_yaxes(tickformat=",")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Summary table
        st.header("Latest Cumulative/Total Summary")
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            summary = []
            for country in valid_countries:
                country_data = df[df["Country"] == country]
                if not country_data.empty:
                    latest = country_data.iloc[-1]
                    total_value = latest[main_metric]
                    total_int = int(total_value) if pd.notna(total_value) else 0
                    summary.append({
                        "Country": country,
                        "Latest Date": latest["Date"].date(),
                        f"Total {metric_label}": total_int
                    })
            summary_df = pd.DataFrame(summary).set_index("Country")
            styled = summary_df.style.format({f"Total {metric_label}": "{:,.0f}"}).background_gradient(cmap="Blues")
            st.dataframe(styled, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.info("COVID-19: cumulative daily (up to 2022). Influenza: weekly positives (FluNet, recent).")

else:
    st.info("👈 Select a disease, enter or choose countries in the sidebar, then click **Analyze Data** to generate the dashboard.")