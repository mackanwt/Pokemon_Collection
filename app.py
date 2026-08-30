import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import date
from PIL import Image, ImageOps
import io

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

# CSS FIX FÖR MOBIL
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

# --- HJÄLPFUNKTION FÖR BILD-OMVANDLING OCH ROTATION (HÅRD KOMPRIMERING) ---
def process_pil_image(img, rotate_degrees=0):
    try:
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if rotate_degrees != 0:
            img = img.rotate(-rotate_degrees, expand=True)

        img = img.convert("RGB")
        # Minskat till 400px och 55% kvalitet för att hålla data.json extremt liten
        img.thumbnail((400, 400))
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=55, optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"Fel vid bildbehandling: {e}")
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

# --- GITHUB INTEGRATION (SÄKER INLÄSNING VIA RAW RAW-URL) ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = "data.json"

def load_data_from_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None
    
    # Hämta direkt från Raw URL för att kringgå 1MB-gränsen på REST API
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        res = requests.get(raw_url, headers=headers)
        if res.status_code == 200:
            return json.loads(res.text)
    except Exception:
        pass

    # Fallback till REST API om Raw misslyckas
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
    
    clean_collection = []
    for item in data_dict.get("collection", []):
        clean_item = dict(item)
        if "Bild" in clean_item:
            val = str(clean_item["Bild"]) if clean_item["Bild"] is not None else ""
            if not (val.startswith("data:image") or val.startswith("http")):
                val = ""
            clean_item["Bild"] = val
        clean_collection.append(clean_item)
    
    data_dict["collection"] = clean_collection
    
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

# Ladda data
app_data = load_data_from_github()
if not app_data:
    app_data = {
        "collection": [],
        "languages": ["ENG", "JAP", "SWE"],
        "names": ["Alolan Raichu", "Pikachu", "Charizard"],
        "extra_options": ["Normal", "Holo", "Reverse Holo", "Secret Rare"],
        "sets_list": [{"SetBet": "CIN", "Set": "Crimson Invasion (CIN)", "Maxnr": "111"}]
    }

current_rate = 11.5

# DIALOGRUTA FÖR BILDER MED ROTERING
@st.dialog("🎴 Kortdetaljer & Välj bild")
def show_card_dialog(selected_index, card_data):
    st.markdown(f"### {card_data.get('Namn', '')}")
    st.caption(f"Set: {card_data.get('Set', '')} ({card_data.get('Setnr.', '')}) | Skick: {card_data.get('Skick', '')}")
    
    rot_key = f"dialog_rotation_{selected_index}"
    if rot_key not in st.session_state:
        st.session_state[rot_key] = 0

    uploaded_file = st.file_uploader("🖼️ Välj bild från galleriet/filerna", type=["jpg", "jpeg", "png"], key=f"dialog_upload_{selected_index}")
    
    if uploaded_file:
        pil_img = get_pil_from_uploaded_file(uploaded_file)
        if pil_img:
            col_left, col_right = st.columns(2)
            with col_left:
                if st.button("🔄 Rotera 90° Vänster", key=f"rot_left_{selected_index}", use_container_width=True):
                    st.session_state[rot_key] = (st.session_state[rot_key] - 90) % 360
            with col_right:
                if st.button("🔄 Rotera 90° Höger", key=f"rot_right_{selected_index}", use_container_width=True):
                    st.session_state[rot_key] = (st.session_state[rot_key] + 90) % 360

            current_rot = st.session_state[rot_key]
            preview_img = pil_img.rotate(-current_rot, expand=True) if current_rot != 0 else pil_img
            
            st.image(preview_img, caption=f"Förhandsvisning (Rotation: {current_rot}°)")
            
            if st.button("💾 Spara denna bild på kortet", type="primary", use_container_width=True):
                img_b64 = process_pil_image(pil_img, rotate_degrees=current_rot)
                if img_b64:
                    app_data["collection"][selected_index]["Bild"] = img_b64
                    save_data_to_github(app_data)
                    
                    del st.session_state[rot_key]
                    for key in list(st.session_state.keys()):
                        if "editor" in key:
                            del st.session_state[key]

                    st.success("Bilden sparades!")
                    st.rerun()
    else:
        st.session_state[rot_key] = 0
        raw_img = card_data.get("Bild", "")
        if raw_img and isinstance(raw_img, str) and (raw_img.startswith("data:image") or raw_img.startswith("http")):
            try:
                if raw_img.startswith("data:image"):
                    base64_data = raw_img.split(",")[1]
                    img_bytes = base64.b64decode(base64_data)
                    st.image(Image.open(io.BytesIO(img_bytes)), caption="Nuvarande sparad bild")
                else:
                    st.image(raw_img, caption="Nuvarande sparad bild")
            except Exception:
                st.info("Ingen bild finns sparad för detta kort ännu.")
        else:
            st.info("Ingen bild finns sparad för detta kort ännu.")

# --- HUVUDLAYOUT ---
tab1, tab2, tab3 = st.tabs(["📊 Samling", "✏️ Redigera samling", "➕ Lägg till nytt kort"])

# --- FLIK 1: HUVUDSAMLING ---
with tab1:
    st.subheader("Min Samling")
    edit_mode = st.toggle("✏️ Redigeringsläge", value=False)
    
    image_preview_container = st.container()

    collection_df = pd.DataFrame(app_data.get("collection", []))
    
    if not collection_df.empty:
        if "Bild" not in collection_df.columns:
            collection_df.insert(0, "Bild", "")

        def sanitize_img(val):
            if val is None:
                return ""
            s_val = str(val).strip()
            if s_val.startswith("data:image") or s_val.startswith("http"):
                return s_val
            return ""

        collection_df["Bild"] = collection_df["Bild"].apply(sanitize_img)

        df_display = collection_df.copy()
        
        df_display["Värde (EUR)"] = pd.to_numeric(df_display["Värde (EUR)"], errors='coerce').fillna(0.0)
        df_display["Köpt för (EUR)"] = pd.to_numeric(df_display["Köpt för (EUR)"], errors='coerce').fillna(0.0)
        df_display["Köpt för (SEK)"] = pd.to_numeric(df_display["Köpt för (SEK)"], errors='coerce').fillna(0.0)
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
            "Datum tillagd": st.column_config.TextColumn("Datum", width="small"),
            "Värde idag (SEK)": st.column_config.NumberColumn("Värde idag (SEK)", width="medium", disabled=True, format="%.2f"),
        }
        
        if edit_mode:
            edited_df = st.data_editor(
                df_display,
                column_order=columns_order,
                column_config=column_config,
                num_rows="dynamic",
                use_container_width=True,
                key="main_collection_editor"
            )
            
            st.divider()
            
            max_rows = len(edited_df)
            col_scan_sel, col_scan_btn = st.columns([1, 1])
            
            with col_scan_sel:
                selected_row_num = st.number_input(
                    "🖼️ Välj radnummer för bild:", 
                    min_value=1, 
                    max_value=max(1, max_rows), 
                    value=1, 
                    step=1
                )
                selected_row_idx = selected_row_num - 1

            with col_scan_btn:
                st.write("")
                st.write("")
                if st.button("🖼️ Hantera/Byt bild på valt kort", use_container_width=True):
                    if max_rows > 0:
                        real_card_data = app_data["collection"][selected_row_idx]
                        show_card_dialog(selected_row_idx, real_card_data)
            
            st.divider()
            if st.button("💾 Spara alla ändringar i samlingen", type="primary", use_container_width=True):
                edited_records = edited_df.to_dict(orient="records")
                for idx, record in enumerate(edited_records):
                    if idx < len(app_data["collection"]):
                        record["Bild"] = app_data["collection"][idx].get("Bild", "")
                app_data["collection"] = edited_records
                save_data_to_github(app_data)
                st.success("Samlingen sparades!")
                st.rerun()
        else:
            event = st.dataframe(
                df_display,
                column_order=columns_order,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )

            selected_rows = event.selection.get("rows", [])
            if selected_rows:
                selected_idx = selected_rows[0]
                card_item = app_data["collection"][selected_idx]
                raw_img = card_item.get("Bild", "")
                
                with image_preview_container:
                    st.markdown(f"### 🔍 {card_item.get('Namn')} ({card_item.get('Set')})")
                    
                    if raw_img and isinstance(raw_img, str) and (raw_img.startswith("data:image") or raw_img.startswith("http")):
                        try:
                            if raw_img.startswith("data:image"):
                                base64_data = raw_img.split(",")[1]
                                img_bytes = base64.b64decode(base64_data)
                                st.image(Image.open(io.BytesIO(img_bytes)), use_container_width=True)
                            else:
                                st.image(raw_img, use_container_width=True)
                        except Exception:
                            st.error("Kunde inte ladda bilden.")
                    else:
                        st.info("Detta kort har ingen bild sparad ännu.")
                    st.divider()

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

# --- FLIK 2: REDIGERINGSLÄGE FÖR TEXT/DATA ---
with tab2:
    st.subheader("✏️ Massredigera text och värden")
    collection_df = pd.DataFrame(app_data.get("collection", []))
    
    if not collection_df.empty:
        df_display = collection_df.copy()
        columns_order = [
            "Bild", "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
            "Övrigt", "Skick", "Köpt för (EUR)", "Köpt för (SEK)", 
            "Värde (EUR)", "Datum tillagd", "Värde idag (SEK)"
        ]
        
        editable_config = {
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
            "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", width="small", format="%.2f"),
        }

        edited_df = st.data_editor(
            df_display,
            column_order=columns_order,
            column_config=editable_config,
            num_rows="dynamic",
            use_container_width=True,
            key="text_editor_grid"
        )
        
        if st.button("💾 Spara alla textändringar till GitHub", type="primary"):
            edited_records = edited_df.to_dict(orient="records")
            for idx, record in enumerate(edited_records):
                if idx < len(app_data["collection"]):
                    record["Bild"] = app_data["collection"][idx].get("Bild", "")
            app_data["collection"] = edited_records
            save_data_to_github(app_data)
            st.success("Samlingen sparades!")
            st.rerun()

# --- FLIK 3: LÄGG TILL NYTT KORT ---
with tab3:
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

    with st.form("add_new_card_form"):
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
        
        if st.form_submit_button("⚡ Spara nytt kort i samlingen", type="primary", use_container_width=True):
            img_b64 = ""
            if new_uploaded_file:
                pil_img_new = get_pil_from_uploaded_file(new_uploaded_file)
                if pil_img_new:
                    img_b64 = process_pil_image(pil_img_new, rotate_degrees=st.session_state.get("new_card_rotation", 0))
            
            new_card = {
                "Bild": img_b64,
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
            
            st.session_state["new_card_rotation"] = 0
            for key in list(st.session_state.keys()):
                if "editor" in key:
                    del st.session_state[key]

            st.success(f"Kortet {namn} skapades och sparades!")
            st.rerun()
