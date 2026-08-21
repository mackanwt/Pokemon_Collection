import streamlit as st
import pandas as pd
import requests
from datetime import date

st.set_page_config(page_title="Pokémon Samling", layout="wide")

# --- HÄMTA VÄXELKURS (EUR -> SEK) ---
@st.cache_data(ttl=86400)  # Cachar kursen i 24 timmar
def get_eur_to_sek():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR").json()
        return res["rates"]["SEK"]
    except:
        return 11.50  # Reservkurs om API misslyckas

current_rate = get_eur_to_sek()

# --- INITIALISERA SESSION STATE (DATABAS) ---
if "languages" not in st.session_state:
    st.session_state.languages = ["ENG", "JPN", "SWE", "GER"]

if "names" not in st.session_state:
    st.session_state.names = ["Alolan Raichu", "Togepi", "Togetic", "Ampharos", "Infernape", "Pachirisu"]

if "extra_options" not in st.session_state:
    st.session_state.extra_options = ["Holo", "Reverse Holo", "Non-Holo", "1st Edition"]

if "set_mapping" not in st.session_state:
    # Koppling: Maxnummer/Kod -> Setbet beteckning -> Fullt Set-namn
    st.session_state.set_mapping = [
        {"Maxnr": "111", "SetBet": "CIN", "Set": "Crimson Invasion (CIN)"},
        {"Maxnr": "236", "SetBet": "UNM", "Set": "Unified Minds (UNM)"},
        {"Maxnr": "214", "SetBet": "LOT", "Set": "Lost Thunder (LOT)"},
        {"Maxnr": "131", "SetBet": "FLI", "Set": "Forbidden Light (FLI)"},
    ]

if "collection" not in st.session_state:
    st.session_state.collection = pd.DataFrame(columns=[
        "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
        "Övrigt", "Skick", "Köpt för (EUR)", "Köpt för (SEK)", 
        "Värde (EUR)", "Värde idag (SEK)", "Datum tillagd"
    ])

# --- APP LAYOUT & FLIKAR ---
st.title("🎴 Min Pokémon-samling")
st.write(f"**Dagens växelkurs:** 1 EUR = **{current_rate:.2f} SEK**")

tab1, tab2, tab3 = st.tabs(["📦 Samling", "⚙️ Hantera Listor & Sets", "➕ Lägg till Kort"])

# --- FLIK 1: HUVUDSAMLING ---
with tab1:
    st.subheader("Min Samling")
    if not st.session_state.collection.empty:
        # Beräkna om Värde idag (SEK) live baserat på dagens växelkurs
        df_display = st.session_state.collection.copy()
        df_display["Värde idag (SEK)"] = (df_display["Värde (EUR)"] * current_rate).round(2)
        
        # Redigerbar tabell
        edited_df = st.data_editor(
            df_display,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Skick": st.column_config.SelectboxColumn(
                    options=["NM", "EX", "GD", "LP", "PL", "PO"]
                ),
                "Språk": st.column_config.SelectboxColumn(options=st.session_state.languages),
                "Namn": st.column_config.SelectboxColumn(options=st.session_state.names),
                "Övrigt": st.column_config.SelectboxColumn(options=st.session_state.extra_options),
                "Köpt för (SEK)": st.column_config.NumberColumn(disabled=True, help="Låst till kursen dagen kortet lades till."),
                "Värde idag (SEK)": st.column_config.NumberColumn(disabled=True, help="Uppdateras automatiskt varje dag."),
            }
        )
        st.session_state.collection = edited_df
    else:
        st.info("Samlingen är tom. Gå till fliken 'Lägg till Kort' för att börja!")

# --- FLIK 2: INSTÄLLNINGAR & SET-MAPPING ---
with tab2:
    st.subheader("Koppla Setnr (Maxnr) till SetBet & Set")
    
    # Tabell för att hantera Sets
    set_df = pd.DataFrame(st.session_state.set_mapping)
    edited_set_df = st.data_editor(set_df, num_rows="dynamic", use_container_width=True)
    st.session_state.set_mapping = edited_set_df.to_dict("records")
    
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Språk")
        new_lang = st.text_input("Lägg till nytt språk")
        if st.button("➕ Lägg till språk") and new_lang:
            if new_lang not in st.session_state.languages:
                st.session_state.languages.append(new_lang)
                st.rerun()

    with col2:
        st.subheader("Namn")
        new_name = st.text_input("Lägg till nytt Pokémon-namn")
        if st.button("➕ Lägg till namn") and new_name:
            if new_name not in st.session_state.names:
                st.session_state.names.append(new_name)
                st.rerun()

    with col3:
        st.subheader("Övrigt")
        new_opt = st.text_input("Lägg till nytt val under Övrigt")
        if st.button("➕ Lägg till i Övrigt") and new_opt:
            if new_opt not in st.session_state.extra_options:
                st.session_state.extra_options.append(new_opt)
                st.rerun()

# --- FLIK 3: LÄGG TILL NYTT KORT ---
with tab3:
    st.subheader("Lägg till ett nytt kort i samlingen")
    with st.form("add_card_form"):
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            parm = st.number_input("Pärmnummer", min_value=1, step=1)
            sprak = st.selectbox("Språk", st.session_state.languages)
            namn = st.selectbox("Namn", st.session_state.names)
            skick = st.selectbox("Skick", ["NM", "EX", "GD", "LP", "PL", "PO"])
            
        with col_b:
            setnr = st.text_input("Setnr. (t.ex. 12/111)", value="12/111")
            
            # Logik för att filtrera SetBet utifrån nämnaren i Setnr (t.ex. '111')
            max_nr = setnr.split("/")[-1].strip() if "/" in setnr else ""
            matching_sets = [s for s in st.session_state.set_mapping if s.get("Maxnr") == max_nr]
            
            setbet_options = [s["SetBet"] for s in matching_sets] if matching_sets else [s["SetBet"] for s in st.session_state.set_mapping]
            
            selected_setbet = st.selectbox("SetBet.", setbet_options if setbet_options else ["-"])
            
            # Auto-fyll fullt Set-namn
            auto_set_name = ""
            for s in st.session_state.set_mapping:
                if s.get("SetBet") == selected_setbet:
                    auto_set_name = s.get("Set")
                    break
            
            st.text_input("Set (Automatiskt)", value=auto_set_name, disabled=True)

        with col_c:
            ovrigt = st.selectbox("Övrigt", st.session_state.extra_options)
            kopt_eur = st.number_input("Köpt för (EUR)", min_value=0.0, step=0.5, format="%.2f")
            varde_eur = st.number_input("Värde (EUR)", min_value=0.0, step=0.5, format="%.2f")
        
        submit = st.form_submit_button("Spara kort")
        
        if submit:
            kopt_sek_fryst = round(kopt_eur * current_rate, 2)
            varde_sek_idag = round(varde_eur * current_rate, 2)
            
            new_row = {
                "Pärmnummer": parm,
                "Språk": sprak,
                "Namn": namn,
                "Setnr.": setnr,
                "SetBet.": selected_setbet,
                "Set": auto_set_name,
                "Övrigt": ovrigt,
                "Skick": skick,
                "Köpt för (EUR)": kopt_eur,
                "Köpt för (SEK)": kopt_sek_fryst,
                "Värde (EUR)": varde_eur,
                "Värde idag (SEK)": varde_sek_idag,
                "Datum tillagd": date.today().strftime("%Y-%m-%d")
            }
            
            st.session_state.collection = pd.concat([st.session_state.collection, pd.DataFrame([new_row])], ignore_index=True)
            st.success(f"Kortet {namn} ({setnr}) har lagts till!")
