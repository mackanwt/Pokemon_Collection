import streamlit as st
import pandas as pd
import requests
import json
import base64
from datetime import date
from PIL import Image
import io

# --- 0. MOBILAPP- & PAGE-KONFIGURATION ---
st.set_page_config(
    page_title="Pokémon Samling", 
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# PWA Meta-tags för mobilapp-känsla
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="PokémonApp">
    
    <style>
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }
        button, input, select {
            touch-action: manipulation;
        }
    </style>
""", unsafe_allow_html=True)

# --- GITHUB INTEGRATION ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = "data.json"

# --- DEFAULT DATA ---
DEFAULT_DATA = {
    "collection": [
        {"Bild": "", "Pärmnummer": 1, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "31/111", "SetBet.": "CIN", "Set": "Crimson Invasion (CIN)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 2.0, "Datum tillagd": "2026-08-21"},
        {"Bild": "", "Pärmnummer": 2, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "31/111", "SetBet.": "CIN", "Set": "Crimson Invasion (CIN)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 2.0, "Datum tillagd": "2026-08-21"},
        {"Bild": "", "Pärmnummer": 3, "Språk": "ENG", "Namn": "Alolan Raichu", "Setnr.": "57/236", "SetBet.": "UNM", "Set": "Unified Minds (UNM)", "Övrigt": "Holo", "Skick": "NM", "Köpt för (EUR)": 0.0, "Köpt för (SEK)": 0.0, "Värde (EUR)": 6.0, "Datum tillagd": "2026-08-21"}
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

def process_uploaded_image(file_buffer):
    if not file_buffer:
        return ""
    img = Image.open(file_buffer)
    img.thumbnail((600, 800))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=75)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{img_str}"

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

tab1, tab2, tab3 = st.tabs(["📦 Samling", "⚙️ Hantera Listor & Sets", "➕ Lägg till / Skanna Kort"])

# Pop-up ruta för att förstora bilden vid dubbelklick/val
@st.dialog("🎴 Kortvisare")
def show_card_dialog(row):
    img_src = row.get("Bild", "")
    if img_src and str(img_src).strip() != "":
        st.image(img_src, use_column_width=True)
    else:
        st.info("Ingen bild finns skannad för detta kort.")
    st.markdown(f"### {row['Namn']}")
    st.write(f"**Set:** {row['Set']} ({row['Setnr.']})")
    st.write(f"**Skick:** {row['Skick']} | **Språk:** {row['Språk']}")
    st.write(f"**Värde idag:** {row['Värde idag (SEK)']} kr ({row['Värde (EUR)']} EUR)")

# --- FLIK 1: HUVUDSAMLING ---
with tab1:
    st.subheader("Min Samling")
    
    collection_df = pd.DataFrame(app_data.get("collection", []))
    
    if not collection_df.empty:
        if "Bild" not in collection_df.columns:
            collection_df.insert(0, "Bild", "")

        df_display = collection_df.copy()
        df_display["Värde idag (SEK)"] = (df_display["Värde (EUR)"] * current_rate).round(2)
        
        columns_order = [
            "Bild", "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
            "Övrigt", "Skick", "Köpt för (EUR)", "Köpt för (SEK)", 
            "Värde (EUR)", "Datum tillagd", "Värde idag (SEK)"
        ]
        
        column_config = {
            "Bild": st.column_config.ImageColumn("Bild", width="small"),
            "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width="small"),
            "Språk": st.column_config.TextColumn("Språk", width="small"),
            "Namn": st.column_config.TextColumn("Namn", width="medium"),
            "Setnr.": st.column_config.TextColumn("Setnr.", width="small"),
            "SetBet.": st.column_config.TextColumn("SetBet.", width="small"),
            "Set": st.column_config.TextColumn("Set", width="large"),
            "Övrigt": st.column_config.TextColumn("Övrigt", width="small"),
            "Skick": st.column_config.TextColumn("Skick", width="small"),
            "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", width="small", format="%.2f"),
            "Köpt för (SEK)": st.column_config.NumberColumn("Köpt (SEK)", width="small", disabled=True, format="%.2f"),
            "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", width="small", format="%.2f"),
            "Datum tillagd": st.column_config.DateColumn("Datum", width="small"),
            "Värde idag (SEK)": st.column_config.NumberColumn("Värde idag (SEK)", width="medium", disabled=True, format="%.2f"),
        }

        edit_mode = st.toggle("✏️ Redigeringsläge", value=False)
        
        if edit_mode:
            editable_config = column_config.copy()
            editable_config["Bild"] = st.column_config.TextColumn("Bild (URL/Base64)", width="small")
            
            edited_df = st.data_editor(
                df_display,
                column_order=columns_order,
                column_config=editable_config,
                num_rows="dynamic",
                use_container_width=True,
                key="main_collection_editor"
            )
            
            if st.button("💾 Spara ändringar i samlingen", type="primary"):
                app_data["collection"] = edited_df.to_dict(orient="records")
                save_data_to_github(app_data)
                st.success("Samlingen sparades!")
                st.rerun()
        else:
            # Visar din exakta ursprungliga tabell med bildkolumnen längst till vänster
            event = st.dataframe(
                df_display,
                column_order=columns_order,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )

            # När du klickar på raden/bilden i tabellen öppnas förstoringsfönstret automatiskt
            if event and event.selection and event.selection.rows:
                selected_idx = event.selection.rows[0]
                selected_row = df_display.iloc[selected_idx]
                show_card_dialog(selected_row)

        total_value_sek = df_display["Värde idag (SEK)"].sum()
        total_cost_sek = df_display["Köpt för (SEK)"].sum()
        total_profit_sek = total_value_sek - total_cost_sek

        st.divider()
        col_empty, col_val, col_profit = st.columns([2, 1, 1])
        with col_val:
            st.metric("Totalt värde (SEK)", f"{total_value_sek:,.2f} kr")
        with col_profit:
            st.metric("Total vinst (SEK)", f"{total_profit_sek:,.2f} kr", delta=f"{total_profit_sek:,.2f} kr")

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

# --- FLIK 3: LÄGG TILL / SKANNA KORT ---
with tab3:
    st.subheader("📷 Skanna / Ta bild & Lägg till kort")
    
    cam_image = st.camera_input("Ta foto på kortet med mobilkameran")
    file_image = st.file_uploader("Eller välj bild från mobilen/datorn", type=["png", "jpg", "jpeg"])
    
    final_img_str = ""
    if cam_image:
        final_img_str = process_uploaded_image(cam_image)
        st.success("Foto taget!")
    elif file_image:
        final_img_str = process_uploaded_image(file_image)
        st.success("Bild uppladdad!")

    st.divider()

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
                "Bild": final_img_str,
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
