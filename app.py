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

# --- DEFAULT DATA ---
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
        {"Pärmnummer": 10, "Språk": "JPN", "Namn": "Togepi", "Setnr.": "UNP", "SetBet.": "UNP", "Set": "Unnumbered Promos (UNP)", "Övrigt": "", "Skick": "GD", "Köpt för (EUR)": 1.04, "Köpt för (SEK)": 12.0, "Värde (EUR)": 38.0, "Datum tillagd": "2026-08-21"}
    ],
    "sets_list": [
        {"Maxnr": "111", "SetBet": "CIN", "Set": "Crimson Invasion (CIN)"},
        {"Maxnr": "236", "SetBet": "UNM", "Set": "Unified Minds (UNM)"}
    ],
    "languages": ["ENG", "JPN", "SWE", "GER"],
    "names": ["Alolan Raichu", "Togepi"],
    "extra_options": ["Holo", "Reverse Holo", "Non-Holo"]
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
            if loaded.get("collection"):
                return loaded
    except Exception:
        pass

    return DEFAULT_DATA

def save_data_to_github(data_dict):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        st.warning("GITHUB_TOKEN eller GITHUB_REPO saknas i Secrets.")
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
        
        # Knapp för att slå på/av redigeringsläge
        edit_mode = st.toggle("✏️ Redigeringsläge", value=False)
        
        if edit_mode:
            edited_df = st.data_editor(
                df_display,
                num_rows="dynamic",
                use_container_width=True,
                key="main_collection_editor",
                column_config={
                    "Köpt för (SEK)": st.column_config.NumberColumn(disabled=True),
                    "Värde idag (SEK)": st.column_config.NumberColumn(disabled=True),
                }
            )
            
            if st.button("💾 Spara ändringar i samlingen", type="primary"):
                app_data["collection"] = edited_df.to_dict(orient="records")
                save_data_to_github(app_data)
                st.success("Samlingen sparades!")
                st.rerun()
        else:
            # st.dataframe stöder inbyggd klicksortering på rubrikerna
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Samlingen är tom.")

# --- FLIK 2: INSTÄLLNINGAR & SETS ---
with tab2:
    st.subheader("Redigera Sets")
    sets_df = pd.DataFrame(app_data.get("sets_list", []))
    edited_sets_df = st.data_editor(
        sets_df,
        num_rows="dynamic",
        use_container_width=True,
        key="sets_list_editor"
    )
    
    if st.button("💾 Spara ändringar i Sets", type="primary"):
        app_data["sets_list"] = edited_sets_df.to_dict(orient="records")
        save_data_to_github(app_data)
        st.success("Sets-listan uppdaterades!")
        st.rerun()

    st.divider()
    
    col_names, col_langs, col_extra = st.columns(3)
    
    with col_names:
        st.subheader("Pokémon-namn")
        names_df = pd.DataFrame({"Namn": app_data.get("names", [])})
        edited_names_df = st.data_editor(names_df, num_rows="dynamic", use_container_width=True, key="names_editor")
        if st.button("Spara Namn"):
            app_data["names"] = edited_names_df["Namn"].dropna().tolist()
            save_data_to_github(app_data)
            st.success("Namn-listan sparad!")
            st.rerun()

    with col_langs:
        st.subheader("Språk")
        langs_df = pd.DataFrame({"Språk": app_data.get("languages", [])})
        edited_langs_df = st.data_editor(langs_df, num_rows="dynamic", use_container_width=True, key="langs_editor")
        if st.button("Spara Språk"):
            app_data["languages"] = edited_langs_df["Språk"].dropna().tolist()
            save_data_to_github(app_data)
            st.success("Språk-listan sparad!")
            st.rerun()

    with col_extra:
        st.subheader("Övrigt-val")
        extra_df = pd.DataFrame({"Övrigt": app_data.get("extra_options", [])})
        edited_extra_df = st.data_editor(extra_df, num_rows="dynamic", use_container_width=True, key="extra_editor")
        if st.button("Spara Övrigt-val"):
            app_data["extra_options"] = edited_extra_df["Övrigt"].dropna().tolist()
            save_data_to_github(app_data)
            st.success("Övrigt-listan sparad!")
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
