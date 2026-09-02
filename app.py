import streamlit as st
import pandas as pd
import json
import requests
import base64

# --- INSTÄLLNINGAR & SIDA ---
st.set_page_config(page_title="Pokémon Samling & Databas", layout="wide")

# Parametrar för GitHub Integration
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "") # Format: "användarnamn/repo-namn"
DATA_FILE_PATH = "data.json"
SETS_FILE_PATH = "sets.json"

# --- HJÄLPFUNKTIONER FÖR GITHUB ---
def github_get_file(file_path):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None, "GitHub API-uppgifter saknas i secrets."
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        content_b64 = res.json().get("content", "")
        content = base64.b64decode(content_b64).decode("utf-8")
        return json.loads(content), None
    return None, f"Kunde inte hämta {file_path} (Status: {res.status_code})"

def github_save_file(file_path, data, commit_message):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GitHub API-uppgifter saknas."
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    # Hämta nuvarande fil för sha-hashen
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    b64_content = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": commit_message,
        "content": b64_content
    }
    if sha:
        payload["sha"] = sha
        
    put_res = requests.put(url, headers=headers, json=payload)
    if put_res.status_code in [200, 201]:
        return True, "Sparat framgångsrikt!"
    return False, f"Ett fel uppstod vid sparande: {put_res.text}"

# --- LADDA DATA ---
if "collection_data" not in st.session_state or st.session_state["collection_data"] is None:
    data, err = github_get_file(DATA_FILE_PATH)
    st.session_state["collection_data"] = data if data else []

if "sets_data" not in st.session_state or st.session_state["sets_data"] is None:
    sets_data, err = github_get_file(SETS_FILE_PATH)
    st.session_state["sets_data"] = sets_data if sets_data else []

collection = st.session_state["collection_data"]
sets_db = st.session_state["sets_data"]

# --- HUVUDFLIKAR ---
tab1, tab2, tab3, tab4 = st.tabs(["📚 Samling", "⚡ Snabb-registrering", "⚙️ Namn-inställningar", "📁 Set-databas"])

with tab1:
    st.subheader("Din Samling")
    if collection:
        df_coll = pd.DataFrame(collection)
        st.dataframe(df_coll, use_container_width=True)
    else:
        st.info("Inga kort i samlingen ännu.")

with tab2:
    st.subheader("Lägg till nytt kort")
    st.write("Registreringsformulär här...")

with tab3:
    st.subheader("Inställningar")
    st.write("Inställningar här...")

# --- FLIK 4: SET-DATABAS (JUSTERAD FÖR ATT TA BORT TOM LUFT) ---
with tab4:
    st.subheader("📁 Global Set-databas (`sets.json`)")
    st.caption("Filtrera, redigera och lägg till set. Ändringar du gör här sparas direkt i `sets.json` på GitHub.")

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        filter_lang = st.selectbox("Filtrera på språk:", ["ALLA", "ENG", "JPN", "ZHT", "SWE", "GER", "FRA", "ITA", "KOR", "SPA", "POR"])
    with col_f2:
        filter_search = st.text_input("Sök i set-namn eller kod:", placeholder="T.ex. sv3, Base eller Crimson")

    sets_df = pd.DataFrame(sets_db)
    
    # Säkerställ kolumner
    for c in ["SetBet", "SetName", "Language", "TotalCards", "ReleaseYear"]:
        if c not in sets_df.columns:
            sets_df[c] = ""

    filtered_df = sets_df.copy()
    if filter_lang != "ALLA":
        filtered_df = filtered_df[filtered_df["Language"] == filter_lang]
    if filter_search.strip():
        q = filter_search.strip().lower()
        filtered_df = filtered_df[
            filtered_df["SetBet"].astype(str).str.lower().str.contains(q) | 
            filtered_df["SetName"].astype(str).str.lower().str.contains(q)
        ]

    # Komprimerade kolumner: Fasta tajta bredder eliminerar luft mellan kolumnerna
    sets_config = {
        "SetBet": st.column_config.TextColumn("SetBet (Kod)", width="small"),
        "SetName": st.column_config.TextColumn("Set (Fullständigt Namn)", width="large"),
        "Language": st.column_config.SelectboxColumn("Språk", options=["ENG", "JPN", "ZHT", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR"], width="small"),
        "TotalCards": st.column_config.TextColumn("Maxantal kort", width="small"),
        "ReleaseYear": st.column_config.NumberColumn("Utgivningsår", format="%d", step=1, width="small")
    }

    filtered_df = filtered_df[["SetBet", "SetName", "Language", "TotalCards", "ReleaseYear"]]

    edited_sets_df = st.data_editor(
        filtered_df,
        column_config=sets_config,
        num_rows="dynamic",
        use_container_width=True,
        key="sets_db_editor"
    )

    if st.button("💾 Spara ändringar i Set-databasen", type="primary"):
        edited_list = edited_sets_df.to_dict(orient="records")
        
        merged_db = []
        edited_keys = {(r.get("SetBet"), r.get("Language")) for r in edited_list}
        
        for r in edited_list:
            if r.get("SetBet") and r.get("SetName"):
                merged_db.append(r)
                
        for s in sets_db:
            key = (s.get("SetBet"), s.get("Language"))
            if key not in edited_keys:
                merged_db.append(s)

        success, msg = github_save_file(SETS_FILE_PATH, merged_db, "Uppdaterade sets.json")
        if success:
            st.session_state["sets_data"] = None
            st.success("Set-databasen sparades till GitHub!")
            st.rerun()
        else:
            st.error(msg)
