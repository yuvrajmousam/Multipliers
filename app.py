import streamlit as st
import pandas as pd
import os

# --- Helper Function ---
def parse_list(raw, is_columns=False, is_multipliers=False):
    if not raw:
        return []
    items = [x.strip() for x in raw.replace("\n", " ").replace("\t", " ").replace(",", " ").split(" ") if x.strip()]
    if is_columns:
        # Auto-append _PMF if missing, just like original code
        items = [x if x.endswith("_PMF") else x + "_PMF" for x in items]
    if is_multipliers:
        items = [float(x) for x in items]
    return items

# --- Initialize Session State ---
if 'ads' not in st.session_state:
    st.session_state.ads = None
if 'rules' not in st.session_state:
    st.session_state.rules = []
if 'filename' not in st.session_state:
    st.session_state.filename = "modified_data"
if 'last_uploaded_file' not in st.session_state:
    st.session_state.last_uploaded_file = None

st.set_page_config(page_title="Data Rule Modifier", layout="wide")
st.title("Data Rule Modifier")

# --- 1. File Upload (Replaces Tkinter) ---
st.header("1. Upload Data")
uploaded_file = st.file_uploader("Select a File", type=["csv", "xlsx"])

if uploaded_file is not None:
    # If a new file is uploaded, reset the session state and load it
    if st.session_state.last_uploaded_file != uploaded_file.name:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            
            st.session_state.ads = df
            st.session_state.filename = os.path.splitext(uploaded_file.name)[0]
            st.session_state.rules = [] # Clear old rules
            st.session_state.last_uploaded_file = uploaded_file.name
        except Exception as e:
            st.error(f"Error loading file: {e}")

# --- 2. Data Processing (Replaces IPyWidgets) ---
if st.session_state.ads is not None:
    ads = st.session_state.ads
    
    st.success(f"✅ File '{st.session_state.filename}' loaded successfully!")
    with st.expander(f"View Data Info (Shape: {ads.shape})"):
        st.write("**Columns:**", list(ads.columns))

    st.divider()
    st.header("2. Apply Rules")

    # Detect Geography and Period/Season columns
    default_geo = next((c for c in ["Geography","Geo","Region"] if c in ads.columns), None)
    default_period = next((c for c in ["Season","Time_Periods","Period_Definition"] if c in ads.columns), None)

    # Let user map the columns in case auto-detection fails
    col_map1, col_map2 = st.columns(2)
    with col_map1:
        geo_col = st.selectbox("Select Geography Column:", options=ads.columns, 
                               index=list(ads.columns).index(default_geo) if default_geo else 0)
    with col_map2:
        period_col = st.selectbox("Select Period/Season Column:", options=ads.columns, 
                                  index=list(ads.columns).index(default_period) if default_period else 0)

    # Dropdowns for filtering
    geo_options = ["All"] + list(ads[geo_col].dropna().unique())
    period_options = ["All"] + list(ads[period_col].dropna().unique())

    col1, col2 = st.columns(2)
    with col1:
        geo_val = st.selectbox("Geography:", options=geo_options)
        cols_text = st.text_input("Columns:", placeholder="e.g. Sales, Profit")
    with col2:
        period_val = st.selectbox("Period/Season:", options=period_options)
        mults_text = st.text_input("Multipliers:", placeholder="e.g. 1.1, 0.9")

    # Apply Rule Logic
    if st.button("Apply Rule", type="primary"):
        cols = parse_list(cols_text, is_columns=True)
        try:
            mults = parse_list(mults_text, is_multipliers=True)
        except ValueError:
            st.error("⚠️ Error: Multipliers must be numbers.")
            st.stop()

        # Validations
        if not cols or not mults:
            st.warning("⚠️ Please enter both columns and multipliers.")
        elif len(cols) != len(mults):
            st.error(f"⚠️ Mismatch: You have {len(cols)} columns but {len(mults)} multipliers.")
        else:
            missing = [c for c in cols if c not in ads.columns]
            if missing:
                st.error(f"⚠️ Missing columns in dataset: {missing}")
            else:
                # Build Mask
                mask = pd.Series(True, index=ads.index)
                if geo_val != "All":
                    mask &= (ads[geo_col] == geo_val)
                if period_val != "All":
                    mask &= (ads[period_col] == period_val)

                affected_rows = mask.sum()
                
                if affected_rows == 0:
                    st.warning("⚠️ No rows matched this selection criteria. Nothing changed.")
                else:
                    # Apply multiplication
                    ads.loc[mask, cols] = ads.loc[mask, cols].mul(mults, axis=1)
                    st.session_state.ads = ads  # Save changes to session state
                    
                    # Log the rule
                    st.session_state.rules.append({
                        "geography": geo_val,
                        "period": period_val,
                        "columns": cols,
                        "multipliers": mults,
                        "rows_affected": affected_rows
                    })

                    st.success(f"✅ Rule Applied! ({affected_rows} rows updated)")
                    st.dataframe(ads.loc[mask, cols].head())

    # --- 3. Summary & Download ---
    st.divider()
    st.header("3. Summary & Download")
    
    if st.session_state.rules:
        st.subheader("Applied Rules Summary:")
        for i, r in enumerate(st.session_state.rules, start=1):
            st.text(f"{i}. Geo: {r['geography']} | Period: {r['period']} | Cols: {r['columns']} | Mults: {r['multipliers']}")

    save_name = st.text_input("Save As:", value=f"{st.session_state.filename}_modified.csv")
    if not save_name.lower().endswith(".csv"):
        save_name += ".csv"

    # Convert dataframe to CSV for the download button
    csv_data = st.session_state.ads.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="Download Modified CSV",
        data=csv_data,
        file_name=save_name,
        mime='text/csv'
    )
else:
    st.info("⚠️ Please upload a file to begin.")
