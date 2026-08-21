import streamlit as st
import pandas as pd
import requests
import json
import base64
from datetime import date

st.set_page_config(page_title="Pokémon Samling", layout="wide")

# --- GITHUB INTEGRATION (SPARA OCH LÄS) ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = "data.json"

def load_data_from_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return {"collection": [], "sets_list": [], "languages": ["ENG", "JPN", "SWE", "GER"], "names": ["Alolan Raichu", "Togepi"], "extra_options": ["Holo", "Reverse Holo"]}
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = res.json()["content"]
            decoded_data = base64.b64decode(content).decode('utf-8')
            return json.loads(decoded_data)
    except Exception:
        pass

    return {
        "collection": [],
        "sets_list": [
            {"Maxnr": "111", "SetBet": "CIN", "Set": "Crimson Invasion (CIN)"},
            {"Maxnr": "236", "SetBet": "UNM", "Set": "Unified Minds (UNM)"}
        ],
        "languages": ["ENG", "JPN", "SWE", "GER"],
        "names": ["Alolan Raichu", "Togepi", "Togetic", "Ampharos", "Infernape", "Pachirisu"],
        "extra_options": ["Holo", "Reverse Holo", "Non-Holo", "1st Edition"]
    }

def save_data_to_github(data_dict):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        st.error("Saknar GITHUB_TOKEN eller GITHUB_REPO i Secrets!")
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
        "message": "Uppdaterade samling/inställningar [via Streamlit]",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha

    res_put = requests.put(url, headers=headers, json=payload)
    if res_put.status_code not in [200, 201]:
        st.error(f"Kunde inte spara till GitHub: {res_put.text}")

# --- INITIALISERA DATA ---
if "app_data" not in st.session_state:
    st.session_state.app_data = load_data_from_github()

app_data = st.session_state.app_data

# --- HÄMTA VÄXELKURS ---
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
            st.success("Ändringar sparades till GitHub!")
            st.rerun()
    else:
        st.info("Samlingen är tom. Lägg till kort under fliken 'Lägg till Kort'.")

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
            st.success(f"Kortet {namn} sparades permanent till GitHub!")
            st.rerun()
