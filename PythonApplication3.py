import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
COVID_LOCAL_PATH = "covid.csv"
FLU_URL = "https://drive.google.com/uc?export=download&id=1moYESuDnMJSwfmAbchv8uRlvFB0Fp5Q0"

# ✅ Diabetes Google Drive CSV (your file)
DIABETES_URL = "https://drive.google.com/uc?export=download&id=1FXRoXPDTstl35YeODJsxfFjyEMV-LznR"

# ================= LOAD DATA =================
@st.cache_data(ttl=86400)
def load_covid_data():
    df = pd.read_csv(COVID_LOCAL_PATH, parse_dates=["Date"])
    countries = sorted(df["Country"].unique())
    years = sorted(df["Date"].dt.year.unique())
    return df, countries, years

@st.cache_data(ttl=86400)
def load_flu_data():
    df = pd.read_csv(FLU_URL)

    df = df.rename(columns={
        "COUNTRY_AREA_TERRITORY": "Country",
        "ISO_WEEKSTARTDATE": "Date",
        "ISO_YEAR": "Year",
        "INF_ALL": "Cases",
        "INF_A": "Influenza_A",
        "INF_B": "Influenza_B"
    })

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Cases"] = pd.to_numeric(df["Cases"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Date", "Country"])

    countries = sorted(df["Country"].unique())
    years = sorted(df["Year"].unique())

    return df, countries, years

# ✅ Diabetes loader (keeps your app logic same: needs Country + Date)
@st.cache_data(ttl=86400)
def load_diabetes_data():
    df = pd.read_csv(DIABETES_URL)

    # Try to normalize common column names into: Country, Year, Value
    df.columns = [c.strip() for c in df.columns]

    rename_map = {}
    for c in df.columns:
        lc = c.lower().strip()
        if lc in ["country", "entity", "location", "country_name"]:
            rename_map[c] = "Country"
        elif lc in ["year", "time"]:
            rename_map[c] = "Year"
        elif lc in ["value", "prevalence", "diabetes", "diabetes_prevalence", "diabetes prevalence", "diabetes prevalence (%)", "sh.sta.diab.zs"]:
            rename_map[c] = "Value"

    df = df.rename(columns=rename_map)

    # If Value not found by name, choose first numeric column that's not Year
    if "Value" not in df.columns:
        numeric_candidates = []
        for c in df.columns:
            if c in ["Country", "Year"]:
                continue
            s = pd.to_numeric(df[c], errors="coerce")
            if s.notna().mean() > 0.5:
                numeric_candidates.append(c)
        if numeric_candidates:
            df = df.rename(columns={numeric_candidates[0]: "Value"})

    # Must-have columns
    if not {"Country", "Year", "Value"}.issubset(df.columns):
        st.error("Diabetes CSV must contain columns like Country/Entity, Year, and Value/Prevalence.")
        st.stop()

    df["Country"] = df["Country"].astype(str).str.strip()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)

    df = df.dropna(subset=["Country", "Year"])
    df["Year"] = df["Year"].astype(int)

    # Create Date column so the rest of your dashboard works without changes
    df["Date"] = pd.to_datetime(df["Year"].astype(str) + "-01-01", errors="coerce")
    df = df.dropna(subset=["Date"])

    countries = sorted(df["Country"].unique())
    years = sorted(df["Year"].unique())
    return df, countries, years

covid_df, covid_countries, covid_years = load_covid_data()
flu_df, flu_countries, flu_years = load_flu_data()
diabetes_df, diabetes_countries, diabetes_years = load_diabetes_data()

shortname_map = {
    "UAE": "United Arab Emirates", "KSA": "Saudi Arabia", "SAUDI": "Saudi Arabia",
    "UK": "United Kingdom", "US": "United States", "USA": "United States"
}

# ================= SIDEBAR =================
with st.sidebar:
    st.header("Analysis Settings")
    disease = st.selectbox("Select Disease", ["COVID-19", "Influenza (FluNet)", "Diabetes (Worldwide)"])
    
    if disease == "COVID-19":
        all_countries = covid_countries
        available_years = covid_years
        df_source = covid_df
    elif disease == "Influenza (FluNet)":
        all_countries = flu_countries
        available_years = flu_years
        df_source = flu_df
    else:
        all_countries = diabetes_countries
        available_years = diabetes_years
        df_source = diabetes_df
    
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
st.markdown("Interactive dashboard for COVID-19, Influenza (FluNet), and Diabetes (Worldwide) data.")

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
        elif disease == "Influenza (FluNet)":
            df["Cases"] = pd.to_numeric(df["Cases"], errors='coerce').fillna(0)
            main_metric = "Cases"
            new_metric = "Cases"
            metric_label = "Influenza Positives"
            new_label = "Positives (Weekly)"
            color_sequence = ["#ef4444"]
        else:  # Diabetes
            df["Value"] = pd.to_numeric(df["Value"], errors='coerce').fillna(0)
            main_metric = "Value"
            new_metric = "Value"
            metric_label = "Diabetes Prevalence (%)"
            new_label = "Prevalence (%) Over Time"
            color_sequence = ["#10b981"]
        
        years = sorted(df["Date"].dt.year.unique())
        
        # Individual bars
        st.header(f"{metric_label} per Year by Country")
        cols = st.columns(min(3, len(valid_countries)))
        for i, country in enumerate(valid_countries):
            with cols[i % len(cols)]:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader(country)
                country_df = df[df["Country"] == country]

                # Diabetes is prevalence (not cumulative), so use mean per year (safe)
                if disease == "Diabetes (Worldwide)":
                    yearly = country_df.groupby(country_df["Date"].dt.year)[main_metric].mean().reindex(years, fill_value=0)
                else:
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

            comparison_data = {}
            for c in valid_countries:
                cdf = df[df["Country"] == c]
                if disease == "Diabetes (Worldwide)":
                    comparison_data[c] = cdf.groupby(cdf["Date"].dt.year)[main_metric].mean()
                else:
                    comparison_data[c] = cdf.groupby(cdf["Date"].dt.year)[main_metric].sum()

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

                    if disease == "Diabetes (Worldwide)":
                        summary.append({
                            "Country": country,
                            "Latest Date": latest["Date"].date(),
                            f"Latest {metric_label}": float(total_value) if pd.notna(total_value) else 0.0
                        })
                    else:
                        total_int = int(total_value) if pd.notna(total_value) else 0
                        summary.append({
                            "Country": country,
                            "Latest Date": latest["Date"].date(),
                            f"Total {metric_label}": total_int
                        })

            summary_df = pd.DataFrame(summary).set_index("Country")

            if disease == "Diabetes (Worldwide)":
                styled = summary_df.style.format({f"Latest {metric_label}": "{:.2f}"}).background_gradient(cmap="Greens")
            else:
                styled = summary_df.style.format({f"Total {metric_label}": "{:,.0f}"}).background_gradient(cmap="Blues")

            st.dataframe(styled, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.info("COVID-19: cumulative daily (up to 2022). Influenza: weekly positives (FluNet, recent). Diabetes: prevalence (%) by year.")

else:
    st.info("👈 Select a disease, enter or choose countries in the sidebar, then click **Analyze Data** to generate the dashboard.")
