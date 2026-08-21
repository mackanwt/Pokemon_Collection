import streamlit as st
import pandas as pd
import requests
import json
import base64
from datetime import date

st.set_page_config(page_title="Pokémon Samling", layout="wide")

# --- GITHUB INTEGRATION ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = "data.json"

# --- ALLA DINA 36 KORT OCH INSTÄLLNINGAR DIRECT I KODEN ---
DEFAULT_DATA = {
    "collection": [
        {"Pärmnummer": 1, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "31/111", "SetBet.": "CIN", "Set": "Crimson Invasion (CIN)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 2.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 2, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "31/111", "SetBet.": "CIN", "Set": "Crimson Invasion (CIN)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 2.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 3, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "57/236", "SetBet.": "UNM", "Set": "Unified Minds (UNM)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 6.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 4, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "30/30", "SetBet.": "TK10 A30", "Set": "SM Trainer Kit: Lycanroc & Alolan Raichu", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 3.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 5, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "30/30", "SetBet.": "TK10 A30", "Set": "SM Trainer Kit: Lycanroc & Alolan Raichu", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 3.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 6, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "SM65", "SetBet.": "SMP", "Set": "SM Black Star Promos", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 5.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 7, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "SM72", "SetBet.": "SMP", "Set": "SM Black Star Promos", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 22.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 8, "Språk": "ENG", "Namn": "Togepi", "Setnr.": "9/12", "SetBet.": "MCD16", "Set": "McDonald's Collection 2016 (MCD16)", "Övrigt": "Holo", "Skick": "GD", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 12.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 9, "Språk": "ENG", "Namn": "Togepi", "Setnr.": "9/12", "SetBet.": "MCD16", "Set": "McDonald's Collection 2016 (MCD16)", "Övrigt": "Holo", "Skick": "EX", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 13.5, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 10, "Språk": "JPN", "Namn": "Togepi", "Setnr.": "UNP", "SetBet.": "UNP", "Set": "Unnumbered Promos (UNP)", "Övrigt": "", "Skick": "GD", "Köpt för (EUR)": 1.04, "Köpt för (SEK)": 12.0, "Värde (EUR)": 38.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 11, "Språk": "ENG", "Namn": "Togetic", "Setnr.": "137/214", "SetBet.": "UNB", "Set": "Unbroken Bonds (UNB)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.3, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 12, "Språk": "JPN", "Namn": "Togetic", "Setnr.": "N1", "SetBet.": "N1", "Set": "Gold, Silver, to a New World (N1)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 1.04, "Köpt för (SEK)": 12.0, "Värde (EUR)": 15.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 13, "Språk": "ENG", "Namn": "Ampharos", "Setnr.": "78/214", "SetBet.": "LOT", "Set": "Lost Thunder (LOT)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 1.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 14, "Språk": "ENG", "Namn": "Infernape", "Setnr.": "59/131", "SetBet.": "FLI", "Set": "Forbidden Light (FLI)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 1.5, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 15, "Språk": "ENG", "Namn": "Infernape", "Setnr.": "59/131", "SetBet.": "FLI", "Set": "Forbidden Light (FLI)", "Övrigt": "Reverse Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 2.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 16, "Språk": "ENG", "Namn": "Infernape", "Setnr.": "23/156", "SetBet.": "UPR", "Set": "Ultra Prism (UPR)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.5, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 17, "Språk": "ENG", "Namn": "Pachirisu", "Setnr.": "80/214", "SetBet.": "LOT", "Set": "Lost Thunder (LOT)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.5, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 18, "Språk": "ENG", "Namn": "Pachirisu", "Setnr.": "80/214", "SetBet.": "LOT", "Set": "Lost Thunder (LOT)", "Övrigt": "Reverse Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 10.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 19, "Språk": "ENG", "Namn": "Pachirisu", "Setnr.": "49/156", "SetBet.": "UPR", "Set": "Ultra Prism (UPR)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.03, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 20, "Språk": "JPN", "Namn": "Pachirisu", "Setnr.": "019/051", "SetBet.": "BW8t", "Set": "Thunder Knuckle (BW8t)", "Övrigt": "1st ed", "Skick": "EX", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 1.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 21, "Språk": "JPN", "Namn": "Pachirisu", "Setnr.": "025/088", "SetBet.": "XY4", "Set": "Phantom Gate (XY4)", "Övrigt": "1st ed", "Skick": "EX", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.6, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 22, "Språk": "ENG", "Namn": "Dragalge", "Setnr.": "53/131", "SetBet.": "FLI", "Set": "Forbidden Light (FLI)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.3, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 23, "Språk": "ENG", "Namn": "Goodra", "Setnr.": "94/131", "SetBet.": "FLI", "Set": "Forbidden Light (FLI)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.8, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 24, "Språk": "ENG", "Namn": "Goodra", "Setnr.": "94/131", "SetBet.": "FLI", "Set": "Forbidden Light (FLI)", "Övrigt": "Reverse Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 1.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 25, "Språk": "ENG", "Namn": "Decidueye", "Setnr.": "11/149", "SetBet.": "SUM", "Set": "Sun & Moon (SUM)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.5, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 26, "Språk": "ENG", "Namn": "Decidueye", "Setnr.": "11/149", "SetBet.": "SUM", "Set": "Sun & Moon (SUM)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.5, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 27, "Språk": "ENG", "Namn": "Decidueye", "Setnr.": "SM55", "SetBet.": "SMP", "Set": "SM Black Star Promos", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 0.5, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 28, "Språk": "ENG", "Namn": "Mimikyu", "Setnr.": "58/145", "SetBet.": "GRI", "Set": "Guardians Rising (GRI)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 9.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 29, "Språk": "ENG", "Namn": "Mimikyu", "Setnr.": "58/145", "SetBet.": "GRI", "Set": "Guardians Rising (GRI)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 9.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 30, "Språk": "ENG", "Namn": "Mimikyu", "Setnr.": "58/145", "SetBet.": "GRI", "Set": "Guardians Rising (GRI)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 9.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 31, "Språk": "JPN", "Namn": "Mimikyu", "Setnr.": "010/026", "SetBet.": "smD", "Set": "Ash vs Team Rocket Deck Kit (smD)", "Övrigt": "", "Skick": "EX", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 200.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 32, "Språk": "ENG", "Namn": "Zeraora", "Setnr.": "60/214", "SetBet.": "UNB", "Set": "Unbroken Bonds (UNB)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 1.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 33, "Språk": "ENG", "Namn": "Zeraora GX", "Setnr.": "86/214", "SetBet.": "LOT", "Set": "Lost Thunder (LOT)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 7.0, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 34, "Språk": "JPN", "Namn": "Zeraora", "Setnr.": "055/193", "SetBet.": "m2a", "Set": "MEGA Dream ex (m2a)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 1.74, "Köpt för (SEK)": 20.0, "Värde (EUR)": 0.02, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 35, "Språk": "ENG", "Namn": "Gholdengo EX", "Setnr.": "139/182", "SetBet.": "PAR", "Set": "Paradox Rift (PAR)", "Övrigt": "", "Skick": "EX", "Köpt för (EUR)": 2.61, "Köpt för (SEK)": 30.0, "Värde (EUR)": 0.6, "Datum tillagd": "2026-08-21"},
        {"Pärmnummer": 36, "Språk": "ENG", "Namn": "Gholdengo EX", "Setnr.": "231/182", "SetBet.": "PAR", "Set": "Paradox Rift (PAR)", "Övrigt": "", "Skick": "NM", "Köpt för (EUR)": 3.48, "Köpt för (SEK)": 40.0, "Värde (EUR)": 3.0, "Datum tillagd": "2026-08-21"}
    ],
    "sets_list": [
        {"Maxnr": "111", "SetBet": "CIN", "Set": "Crimson Invasion (CIN)"},
        {"Maxnr": "236", "SetBet": "UNM", "Set": "Unified Minds (UNM)"},
        {"Maxnr": "214", "SetBet": "LOT", "Set": "Lost Thunder (LOT)"},
        {"Maxnr": "131", "SetBet": "FLI", "Set": "Forbidden Light (FLI)"},
        {"Maxnr": "156", "SetBet": "UPR", "Set": "Ultra Prism (UPR)"},
        {"Maxnr": "149", "SetBet": "SUM", "Set": "Sun & Moon (SUM)"},
        {"Maxnr": "145", "SetBet": "GRI", "Set": "Guardians Rising (GRI)"},
        {"Maxnr": "182", "SetBet": "PAR", "Set": "Paradox Rift (PAR)"},
        {"Maxnr": "12", "SetBet": "MCD16", "Set": "McDonald's Collection 2016 (MCD16)"},
        {"Maxnr": "30", "SetBet": "TK10 A30", "Set": "SM Trainer Kit: Lycanroc & Alolan Raichu"},
        {"Maxnr": "PROMO", "SetBet": "SMP", "Set": "SM Black Star Promos"},
        {"Maxnr": "UNP", "SetBet": "UNP", "Set": "Unnumbered Promos (UNP)"},
        {"Maxnr": "N1", "SetBet": "N1", "Set": "Gold, Silver, to a New World (N1)"},
        {"Maxnr": "051", "SetBet": "BW8t", "Set": "Thunder Knuckle (BW8t)"},
        {"Maxnr": "088", "SetBet": "XY4", "Set": "Phantom Gate (XY4)"},
        {"Maxnr": "026", "SetBet": "smD", "Set": "Ash vs Team Rocket Deck Kit (smD)"},
        {"Maxnr": "193", "SetBet": "m2a", "Set": "MEGA Dream ex (m2a)"}
    ],
    "languages": ["ENG", "JPN", "SWE", "GER"],
    "names": [
        "Alolan Raichu", "Togepi", "Togetic", "Ampharos", "Infernape", "Pachirisu",
        "Dragalge", "Goodra", "Decidueye", "Mimikyu", "Zeraora", "Zeraora GX", "Gholdengo EX"
    ],
    "extra_options": ["Holo", "Reverse Holo", "Non-Holo", "1st ed", "1st Edition"]
}

def load_data_from_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return DEFAULT_DATA
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = res.json()["content"]
            decoded_data = base64.b64decode(content).decode('utf-8')
            loaded = json.loads(decoded_data)
            # Om filen på GitHub finns men har tom samling, använd DEFAULT_DATA istället
            if loaded.get("collection"):
                return loaded
    except Exception:
        pass

    return DEFAULT_DATA

def save_data_to_github(data_dict):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        st.warning("GITHUB_TOKEN eller GITHUB_REPO saknas i Secrets. Ändringen sparades bara för denna session.")
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    sha = None
    res_get = requests.get(url, headers=headers)
    if res_get.status_code == 200:
        sha = res_get.json()["sha"]

    json_str = json.dumps(data_dict, indent=4, ensure_ascii=False)
    encoded_content = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    payload = {
        "message": "Uppdaterade samling [via Streamlit]",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha

    res_put = requests.put(url, headers=headers, json=payload)
    if res_put.status_code not in [200, 201]:
        st.error(f"Kunde inte spara till GitHub: {res_put.text}")

# Initialisera data
if "app_data" not in st.session_state:
    st.session_state.app_data = load_data_from_github()

app_data = st.session_state.app_data

@st.cache_data(ttl=86400)
def get_eur_to_sek():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR").json()
        return res["rates"]["SEK"]
    except Exception:
        return 11.50

current_rate = get_eur_to_sek()

st.title("🎴 Min Pokémon-samling")
st.write(f"**Dagens växelkurs:** 1 EUR = **{current_rate:.2f} SEK**")

tab1, tab2, tab3 = st.tabs(["📦 Samling", "⚙️ Hantera Listor & Sets", "➕ Lägg till Kort"])

# --- FLIK 1: HUVUDSAMLING ---
with tab1:
    st.subheader("Min Samling")
    collection_df = pd.DataFrame(app_data.get("collection", []))
    
    if not collection_df.empty:
        df_display = collection_df.copy()
        df_display["Värde idag (SEK)"] = (df_display["Värde (EUR)"] * current_rate).round(2)
        
        edited_df = st.data_editor(
            df_display,
            num_rows="dynamic",
            use_container_width=True,
            key="main_collection_editor",
            column_config={
                "Skick": st.column_config.SelectboxColumn(options=["NM", "EX", "GD", "LP", "PL", "PO"]),
                "Språk": st.column_config.SelectboxColumn(options=app_data["languages"]),
                "Namn": st.column_config.SelectboxColumn(options=app_data["names"]),
                "Övrigt": st.column_config.SelectboxColumn(options=app_data["extra_options"]),
                "Köpt för (SEK)": st.column_config.NumberColumn(disabled=True),
                "Värde idag (SEK)": st.column_config.NumberColumn(disabled=True),
            }
        )
        
        if st.button("💾 Spara ändringar i tabellen", type="primary"):
            app_data["collection"] = edited_df.to_dict(orient="records")
            save_data_to_github(app_data)
            st.success("Ändringar sparades permanent!")
            st.rerun()
    else:
        st.info("Samlingen är tom.")

# --- FLIK 2: INSTÄLLNINGAR & SETS ---
with tab2:
    st.subheader("Befintliga Sets")
    st.dataframe(pd.DataFrame(app_data["sets_list"]), use_container_width=True)

    st.subheader("➕ Lägg till nytt Set")
    with st.form("add_set_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        new_maxnr = c1.text_input("Maxnr (t.ex. 111)")
        new_setbet = c2.text_input("SetBet (t.ex. CIN)")
        new_setname = c3.text_input("Fullt Set-namn")
        
        if st.form_submit_button("Spara nytt Set"):
            if new_maxnr and new_setbet:
                app_data["sets_list"].append({
                    "Maxnr": new_maxnr.strip(),
                    "SetBet": new_setbet.strip(),
                    "Set": new_setname.strip()
                })
                save_data_to_github(app_data)
                st.success(f"Sparade Set: {new_setbet}")
                st.rerun()

# --- FLIK 3: LÄGG TILL KORT ---
with tab3:
    st.subheader("Lägg till ett nytt kort")
    with st.form("add_card_form"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            parm = st.number_input("Pärmnummer", min_value=1, step=1)
            sprak = st.selectbox("Språk", app_data["languages"])
            namn = st.selectbox("Namn", app_data["names"])
            skick = st.selectbox("Skick", ["NM", "EX", "GD", "LP", "PL", "PO"])
            
        with col_b:
            setnr = st.text_input("Setnr. (t.ex. 12/111)", value="12/111")
            max_nr = setnr.split("/")[-1].strip() if "/" in setnr else ""
            matching = [s for s in app_data["sets_list"] if str(s.get("Maxnr")).strip() == max_nr] or app_data["sets_list"]
            selected_setbet = st.selectbox("SetBet.", [s["SetBet"] for s in matching])
            auto_set_name = next((s.get("Set") for s in app_data["sets_list"] if s.get("SetBet") == selected_setbet), "")
            st.text_input("Set (Automatiskt)", value=auto_set_name, disabled=True)

        with col_c:
            ovrigt = st.selectbox("Övrigt", app_data["extra_options"])
            kopt_eur = st.number_input("Köpt för (EUR)", min_value=0.0, step=0.5, format="%.2f")
            varde_eur = st.number_input("Värde (EUR)", min_value=0.0, step=0.5, format="%.2f")
        
        if st.form_submit_button("Spara kort", type="primary"):
            new_card = {
                "Pärmnummer": parm,
                "Språk": sprak,
                "Namn": namn,
                "Setnr.": setnr,
                "SetBet.": selected_setbet,
                "Set": auto_set_name,
                "Övrigt": ovrigt,
                "Skick": skick,
                "Köpt för (EUR)": kopt_eur,
                "Köpt för (SEK)": round(kopt_eur * current_rate, 2),
                "Värde (EUR)": varde_eur,
                "Värde idag (SEK)": round(varde_eur * current_rate, 2),
                "Datum tillagd": date.today().strftime("%Y-%m-%d")
            }
            
            app_data["collection"].append(new_card)
            save_data_to_github(app_data)
            st.success(f"Kortet {namn} sparades!")
            st.rerun()
