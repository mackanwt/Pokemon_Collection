import streamlit as st
import pandas as pd
import json
import base64
import requests
import time
from datetime import date
from PIL import Image, ImageOps
import io
import uuid

# --- 0. PAGE-KONFIGURATION ---
st.set_page_config(
    page_title="Pokémon Samling", 
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

APP_ICON_URL = "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f3b4.png"

manifest_data = {
    "name": "Pokémon Samling",
    "short_name": "Pokémon",
    "start_url": ".",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#ffffff",
    "icons": [
        {"src": APP_ICON_URL, "sizes": "192x192", "type": "image/png"},
        {"src": APP_ICON_URL, "sizes": "512x512", "type": "image/png"}
    ]
}

manifest_json = json.dumps(manifest_data)
manifest_base64 = base64.b64encode(manifest_json.encode('utf-8')).decode('utf-8')
manifest_href = f"data:application/manifest+json;base64,{manifest_base64}"

st.markdown(f"""
    <link rel="manifest" href="{manifest_href}">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#ffffff">
    <link rel="icon" type="image/png" sizes="192x192" href="{APP_ICON_URL}">
    <link rel="shortcut icon" href="{APP_ICON_URL}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    
    <style>
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }}
        button, input, select {{
            touch-action: manipulation;
        }}
        
        div[data-testid="stImage"] img {{
            touch-action: pan-x pan-y !important;
            max-width: 100% !important;
            height: auto !important;
        }}
    </style>
""", unsafe_allow_html=True)

# --- GITHUB CONFIG & INTEGRATION ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = "data.json"

if "temp_image_cache" not in st.session_state:
    st.session_state["temp_image_cache"] = {}

def process_pil_image_to_bytes(img, rotate_degrees=0):
    try:
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if rotate_degrees != 0:
            img = img.rotate(-rotate_degrees, expand=True)

        img = img.convert("RGB")
        img.thumbnail((600, 600))
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=75, optimize=True)
        return buffered.getvalue()
    except Exception as e:
        st.error(f"Fel vid bildbehandling: {e}")
        return None

def upload_image_to_github(img_bytes):
    if not GITHUB_TOKEN or not GITHUB_REPO or not img_bytes:
        return ""
    
    filename = f"images/card_{uuid.uuid4().hex[:10]}.jpg"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    encoded_content = base64.b64encode(img_bytes).decode('utf-8')
    payload = {
        "message": f"Laddade upp bild: {filename}",
        "content": encoded_content
    }
    
    res = requests.put(url, json=payload, headers=headers)
    if res.status_code in [200, 201]:
        clean_repo = GITHUB_REPO.strip("/")
        return f"https://raw.githubusercontent.com/{clean_repo}/main/{filename}"
    else:
        st.error(f"Kunde inte ladda upp bilden till GitHub: {res.text}")
        return ""

def get_pil_from_uploaded_file(file_buffer):
    if not file_buffer:
        return None
    try:
        img = Image.open(file_buffer)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        return img
    except Exception:
        return None

def load_data_from_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None
    
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        res = requests.get(raw_url, headers=headers)
        if res.status_code == 200:
            return json.loads(res.text)
    except Exception:
        pass

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = base64.b64decode(res.json()["content"]).decode('utf-8')
            return json.loads(content)
    except Exception:
        pass

    return None

def save_data_to_github(data_dict):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    sha = res.json()["sha"] if res.status_code == 200 else None
    
    content_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": "Uppdaterade samlingsdata",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    put_res = requests.put(url, json=payload, headers=headers)
    return put_res.status_code in [200, 201]

def normalize_max_nr(val):
    s = str(val).strip().lstrip('0')
    return s if s else "0"

if "editor_version" not in st.session_state:
    st.session_state["editor_version"] = 0

app_data = load_data_from_github()
if not app_data:
    app_data = {
        "collection": [],
        "languages": ["ENG", "JPN", "SWE"],
        "names": ["Alolan Raichu", "Pikachu", "Charizard"],
        "extra_options": ["Normal", "Holo", "Reverse Holo", "Secret Rare"],
        "sets_list": [{"SetBet": "CIN", "Set": "Crimson Invasion (CIN)", "Maxnr": "111"}]
    }

current_rate = 11.5

# --- DIALOGRUTA FÖR BILDER MED ROTERING ---
@st.dialog("🎴 Kortdetaljer & Välj bild")
def show_card_dialog(selected_index, card_data):
    st.markdown(f"### {card_data.get('Namn', '')}")
    st.caption(f"Set: {card_data.get('Set', '')} ({card_data.get('Setnr.', '')}) | Skick: {card_data.get('Skick', '')}")
    
    rot_key = f"dialog_rotation_{selected_index}"
    if rot_key not in st.session_state:
        st.session_state[rot_key] = 0

    uploaded_file = st.file_uploader("🖼️ Välj bild från galleriet/filerna", type=["jpg", "jpeg", "png"], key=f"dialog_upload_{selected_index}")
    
    pil_img = get_pil_from_uploaded_file(uploaded_file) if uploaded_file else None

    if pil_img:
        col_left, col_right = st.columns(2)
        with col_left:
            if st.button("🔄 Rotera 90° Vänster", key=f"rot_left_{selected_index}", use_container_width=True):
                st.session_state[rot_key] = (st.session_state[rot_key] - 90) % 360
                st.rerun()
        with col_right:
            if st.button("🔄 Rotera 90° Höger", key=f"rot_right_{selected_index}", use_container_width=True):
                st.session_state[rot_key] = (st.session_state[rot_key] + 90) % 360
                st.rerun()

        current_rot = st.session_state[rot_key]
        preview_img = pil_img.rotate(-current_rot, expand=True) if current_rot != 0 else pil_img
        
        st.image(preview_img, caption=f"Förhandsvisning (Rotation: {current_rot}°)")
        
        if st.button("💾 Spara denna bild på kortet", type="primary", use_container_width=True, key=f"save_img_btn_{selected_index}"):
            with st.spinner("Laddar upp bilden till GitHub..."):
                img_bytes = process_pil_image_to_bytes(pil_img, rotate_degrees=current_rot)
                img_url = upload_image_to_github(img_bytes)
                
                if img_url:
                    app_data["collection"][selected_index]["Bild"] = img_url
                    app_data["collection"][selected_index]["Bild_Original"] = img_url
                    save_data_to_github(app_data)
                    
                    b64_str = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
                    st.session_state["temp_image_cache"][img_url] = b64_str
                    
                    st.session_state["editor_version"] += 1
                    
                    if rot_key in st.session_state:
                        del st.session_state[rot_key]
                    if "open_dialog_index" in st.session_state:
                        del st.session_state["open_dialog_index"]

                    st.success("Bilden sparades!")
                    st.rerun()
    else:
        st.session_state[rot_key] = 0
        raw_img = card_data.get("Bild", "")
        if raw_img and isinstance(raw_img, str) and (raw_img.startswith("http") or raw_img.startswith("data:image")):
            st.image(raw_img, caption="Nuvarande sparad bild")
        else:
            st.info("Ingen bild finns sparad för detta kort ännu.")

# --- HUVUDLAYOUT ---
tab1, tab2, tab3 = st.tabs(["📊 Samling", "➕ Lägg till nytt kort", "⚙️ Hantera inställningar"])

# --- FLIK 1: HUVUDSAMLING ---
with tab1:
    st.subheader("Min Samling")
    edit_mode = st.toggle("✏️ Redigeringsläge", value=False)
    
    collection_df = pd.DataFrame(app_data.get("collection", []))
    
    if not collection_df.empty:
        if "Bild" not in collection_df.columns:
            collection_df.insert(0, "Bild", "")

        if "Bild_Original" not in collection_df.columns:
            collection_df["Bild_Original"] = collection_df["Bild"]

        def sanitize_img(val):
            if not val:
                return ""
            s_val = str(val).strip()
            if s_val in st.session_state["temp_image_cache"]:
                return st.session_state["temp_image_cache"][s_val]
            if s_val.startswith("http://") or s_val.startswith("https://") or s_val.startswith("data:image"):
                return s_val
            return ""

        collection_df["Bild"] = collection_df["Bild"].apply(sanitize_img)
        df_display = collection_df.copy()
        
        df_display["Värde (EUR)"] = pd.to_numeric(df_display["Värde (EUR)"], errors='coerce').fillna(0.0)
        df_display["Köpt för (EUR)"] = pd.to_numeric(df_display["Köpt för (EUR)"], errors='coerce').fillna(0.0)
        df_display["Köpt för (SEK)"] = pd.to_numeric(df_display["Köpt för (SEK)"], errors='coerce').fillna(0.0)
        df_display["Värde idag (SEK)"] = (df_display["Värde (EUR)"] * current_rate).round(2)
        
        if "Pärmnummer" in df_display.columns:
            df_display["Pärmnummer"] = pd.to_numeric(df_display["Pärmnummer"], errors='coerce').fillna(0).astype(int)
            df_display = df_display.sort_values(by="Pärmnummer", ascending=True)

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
            "Datum tillagd": st.column_config.TextColumn("Datum", width="small"),
            "Värde idag (SEK)": st.column_config.NumberColumn("Värde idag (SEK)", width="medium", disabled=True, format="%.2f"),
        }
        
        if edit_mode:
            st.info("💡 **Tips:** Markera en rad och tryck på **Delete** för att radera den. Klicka sedan på **'Spara alla ändringar'**.")
            
            editor_key = f"main_editor_v_{st.session_state['editor_version']}"
            
            edited_df = st.data_editor(
                df_display,
                column_order=columns_order,
                column_config=column_config,
                num_rows="dynamic",
                use_container_width=True,
                key=editor_key
            )
            
            col_save, col_img_select, col_img_btn = st.columns([2, 1, 1])
            
            with col_save:
                if st.button("💾 Spara alla ändringar", type="primary", use_container_width=True):
                    edited_records = edited_df.to_dict(orient="records")
                    
                    # Sortera kvarvarande rader efter Pärmnummer
                    def parse_parm(val):
                        try:
                            return int(val)
                        except (ValueError, TypeError):
                            return 0

                    edited_records.sort(key=lambda x: parse_parm(x.get("Pärmnummer", 0)))
                    
                    # Bygg ny samling och numrera om 1, 2, 3... automatiskt utan att återställa raderade kort
                    new_collection = []
                    for idx, record in enumerate(edited_records, start=1):
                        record["Pärmnummer"] = int(idx)
                        
                        # Använd den ursprungliga bild-URL:en om 'Bild' ändrats till base64 eller tömts i editor
                        orig_img = record.get("Bild_Original", "")
                        if not orig_img:
                            orig_img = record.get("Bild", "")
                        
                        record["Bild"] = orig_img
                        record["Bild_Original"] = orig_img
                        
                        # Beräkna om SEK-värden
                        eur_kopt = float(record.get("Köpt för (EUR)", 0.0) or 0.0)
                        eur_varde = float(record.get("Värde (EUR)", 0.0) or 0.0)
                        record["Köpt för (SEK)"] = round(eur_kopt * current_rate, 2)
                        record["Värde idag (SEK)"] = round(eur_varde * current_rate, 2)

                        new_collection.append(record)
                    
                    app_data["collection"] = new_collection
                    save_data_to_github(app_data)
                    
                    st.session_state["editor_version"] += 1
                    st.success("Ändringarna sparades och raderna numrerades om!")
                    st.rerun()

            max_rows = len(edited_df)
            with col_img_select:
                selected_row_num = st.number_input(
                    "Rad för bild:", 
                    min_value=1, 
                    max_value=max(1, max_rows), 
                    value=1, 
                    step=1,
                    label_visibility="collapsed"
                )
                selected_row_idx = selected_row_num - 1

            with col_img_btn:
                if st.button("🖼️ Byt bild", use_container_width=True):
                    if max_rows > 0:
                        st.session_state["open_dialog_index"] = selected_row_idx

            if "open_dialog_index" in st.session_state:
                dlg_idx = st.session_state["open_dialog_index"]
                if dlg_idx < len(app_data["collection"]):
                    real_card_data = app_data["collection"][dlg_idx]
                    show_card_dialog(dlg_idx, real_card_data)

        else:
            st.dataframe(
                df_display,
                column_order=columns_order,
                column_config=column_config,
                use_container_width=True,
                hide_index=True
            )

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

# --- FLIK 2: LÄGG TILL NYTT KORT ---
with tab2:
    st.subheader("➕ Lägg till nytt kort")
    
    if "new_card_rotation" not in st.session_state:
        st.session_state["new_card_rotation"] = 0

    new_uploaded_file = st.file_uploader("🖼️ Välj bild från galleriet/filerna", type=["jpg", "jpeg", "png"], key="new_card_upload")

    if new_uploaded_file:
        pil_img_new = get_pil_from_uploaded_file(new_uploaded_file)
        if pil_img_new:
            col_l, col_r = st.columns(2)
            with col_l:
                if st.button("🔄 Rotera 90° Vänster", key="new_rot_l"):
                    st.session_state["new_card_rotation"] = (st.session_state["new_card_rotation"] - 90) % 360
            with col_r:
                if st.button("🔄 Rotera 90° Höger", key="new_rot_r"):
                    st.session_state["new_card_rotation"] = (st.session_state["new_card_rotation"] + 90) % 360

            cur_rot = st.session_state["new_card_rotation"]
            preview_new = pil_img_new.rotate(-cur_rot, expand=True) if cur_rot != 0 else pil_img_new
            st.image(preview_new, caption=f"Förhandsvisning (Rotation: {cur_rot}°)")

    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        parm = st.number_input("Pärmnummer", min_value=1, step=1)
        sprak = st.selectbox("Språk", sorted(app_data.get("languages", ["ENG"])))
        namn = st.selectbox("Namn", sorted(app_data.get("names", ["Pikachu"])))
        skick = st.selectbox("Skick", ["NM", "EX", "GD", "LP", "PL", "PO"])
        
    with col_b:
        setnr = st.text_input("Setnr. (t.ex. 12/111)", value="016/050", key="input_setnr")
        
        sets_list = app_data.get("sets_list", [])
        
        setbet_options = []
        if "/" in setnr:
            search_max = setnr.split("/")[-1].strip()
            norm_search_max = normalize_max_nr(search_max)
            
            filtered_sets = [
                s.get("SetBet", "") for s in sets_list 
                if normalize_max_nr(s.get("Maxnr", "")) == norm_search_max and s.get("SetBet")
            ]
            setbet_options = filtered_sets

        if not setbet_options:
            setbet_options = [s.get("SetBet", "") for s in sets_list if s.get("SetBet")]

        setbet_options = sorted(list(set(setbet_options)))

        if not setbet_options:
            setbet_options = [""]

        selected_setbet = st.selectbox("SetBet.", setbet_options, key="select_setbet")
        auto_set_name = next((s.get("Set", "") for s in sets_list if s.get("SetBet") == selected_setbet), "")
        st.text_input("Set (Automatiskt)", value=auto_set_name, disabled=True)

    with col_c:
        ovrigt = st.selectbox("Övrigt", sorted(app_data.get("extra_options", ["Normal"])))
        kopt_eur = st.number_input("Köpt för (EUR)", min_value=0.0, step=0.5, format="%.2f")
        varde_eur = st.number_input("Värde (EUR)", min_value=0.0, step=0.5, format="%.2f")
    
    if st.button("⚡ Spara nytt kort i samlingen", type="primary", use_container_width=True):
        img_url = ""
        if new_uploaded_file:
            pil_img_new = get_pil_from_uploaded_file(new_uploaded_file)
            if pil_img_new:
                img_bytes = process_pil_image_to_bytes(pil_img_new, rotate_degrees=st.session_state.get("new_card_rotation", 0))
                img_url = upload_image_to_github(img_bytes)
                if img_url:
                    b64_str = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
                    st.session_state["temp_image_cache"][img_url] = b64_str
        
        target_parm = int(parm)
        
        # Öka alla nummer som är större än eller lika med det valda numret
        for card in app_data["collection"]:
            curr_val = card.get("Pärmnummer")
            if curr_val is not None:
                try:
                    c_num = int(curr_val)
                    if c_num >= target_parm:
                        card["Pärmnummer"] = c_num + 1
                except (ValueError, TypeError):
                    pass

        new_card = {
            "Bild": img_url,
            "Bild_Original": img_url,
            "Pärmnummer": target_parm,
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
        
        st.session_state["new_card_rotation"] = 0
        st.session_state["editor_version"] += 1

        st.success(f"Kortet {namn} skapades på pärmnummer {target_parm}!")
        st.rerun()

# --- FLIK 3: HANTERA INSTÄLLNINGAR ---
with tab3:
    st.subheader("⚙️ Hantera val och alternativ")
    
    col_set, col_other = st.columns(2)
    
    with col_set:
        st.markdown("### 🎴 Lägg till nytt Set & SetBet")
        with st.form("add_new_set_form"):
            new_setbet = st.text_input("SetBet (Förkortning, t.ex. CIN, BS, EVO)")
            new_set_name = st.text_input("Fullständigt Setnamn (t.ex. Crimson Invasion (CIN))")
            new_set_maxnr = st.text_input("Max-nummer i setet (t.ex. 111)")
            
            if st.form_submit_button("➕ Spara nytt Set", type="primary", use_container_width=True):
                if new_setbet and new_set_name:
                    new_entry = {
                        "SetBet": new_setbet.strip(),
                        "Set": new_set_name.strip(),
                        "Maxnr": new_set_maxnr.strip()
                    }
                    if "sets_list" not in app_data:
                        app_data["sets_list"] = []
                    
                    app_data["sets_list"].append(new_entry)
                    save_data_to_github(app_data)
                    st.success(f"Setet '{new_set_name}' har lagts till!")
                    st.rerun()
                else:
                    st.warning("Fyll i både SetBet och Setnamn.")

    with col_other:
        st.markdown("### 📝 Lägg till nytt Kortnamn")
        with st.form("add_new_name_form"):
            new_card_name = st.text_input("Kortnamn (t.ex. Rayquaza GX)")
            if st.form_submit_button("➕ Spara nytt Namn", use_container_width=True):
                if new_card_name:
                    if "names" not in app_data:
                        app_data["names"] = []
                    if new_card_name.strip() not in app_data["names"]:
                        app_data["names"].append(new_card_name.strip())
                        app_data["names"].sort()
                        save_data_to_github(app_data)
                        st.success(f"Namnet '{new_card_name}' lades till!")
                        st.rerun()

    st.divider()
    
    col_lang, col_opt = st.columns(2)
    with col_lang:
        st.markdown("### 🌐 Lägg till Språk")
        with st.form("add_new_lang_form"):
            new_lang = st.text_input("Språk (t.ex. KOR, GER)")
            if st.form_submit_button("➕ Spara Språk", use_container_width=True):
                if new_lang:
                    if "languages" not in app_data:
                        app_data["languages"] = []
                    if new_lang.strip() not in app_data["languages"]:
                        app_data["languages"].append(new_lang.strip())
                        save_data_to_github(app_data)
                        st.success(f"Språket '{new_lang}' lades till!")
                        st.rerun()

    with col_opt:
        st.markdown("### ✨ Lägg till alternativ under Övrigt")
        with st.form("add_new_opt_form"):
            new_opt = st.text_input("Övrigt-alternativ (t.ex. Promo, Full Art)")
            if st.form_submit_button("➕ Spara Övrigt-kategori", use_container_width=True):
                if new_opt:
                    if "extra_options" not in app_data:
                        app_data["extra_options"] = []
                    if new_opt.strip() not in app_data["extra_options"]:
                        app_data["extra_options"].append(new_opt.strip())
                        save_data_to_github(app_data)
                        st.success(f"Kategorin '{new_opt}' lades till!")
                        st.rerun()
