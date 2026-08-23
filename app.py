import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import date
from PIL import Image, ImageOps
import io

# --- 0. MOBILAPP- & PAGE-KONFIGURATION ---
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
    <!-- Web App Manifest för Android -->
    <link rel="manifest" href="{manifest_href}">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#ffffff">

    <!-- Ikoner fallback -->
    <link rel="icon" type="image/png" sizes="192x192" href="{APP_ICON_URL}">
    <link rel="shortcut icon" href="{APP_ICON_URL}">

    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    
    <style>
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }}
        button, input, select {{
            touch-action: manipulation;
        }}
        
        [data-testid="stHeader"] button,
        div[role="columnheader"] {{
            pointer-events: none !important;
            touch-action: none !important;
            user-select: none !important;
        }}
        
        div[role="columnheader"] [data-testid="stTableSortIcon"] {{
            pointer-events: auto !important;
        }}
    </style>
""", unsafe_allow_html=True)

# --- GITHUB INTEGRATION ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = "data.json"

def load_data_from_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
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

# BILDHANTERING MED OPTIMERING
def process_uploaded_image(file_buffer):
    if file_buffer is None:
        return ""
    
    try:
        img = Image.open(file_buffer)
        img = ImageOps.exif_transpose(img)
        
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        img.thumbnail((450, 600), Image.Resampling.LANCZOS)
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=75, optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"Kunde inte behandla bilden: {e}")
        return ""

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

# DIALOGRUTA FÖR BILDER OCH SKANNING
@st.dialog("🎴 Kortdetaljer & Lägg till bild")
def show_card_dialog(selected_index, card_data):
    st.markdown(f"### {card_data.get('Namn', '')}")
    st.caption(f"Set: {card_data.get('Set', '')} ({card_data.get('Setnr.', '')}) | Skick: {card_data.get('Skick', '')}")
    
    raw_img = card_data.get("Bild", "")
    if raw_img:
        try:
            if isinstance(raw_img, str) and raw_img.startswith("data:image"):
                base64_data = raw_img.split(",")[1]
                img_bytes = base64.b64decode(base64_data)
                st.image(Image.open(io.BytesIO(img_bytes)))
            elif isinstance(raw_img, str) and (raw_img.startswith("http://") or raw_img.startswith("https://")):
                st.image(raw_img)
            else:
                st.info("Ingen bild finns sparad för detta kort ännu.")
        except Exception:
            st.info("Ingen bild finns sparad för detta kort ännu.")
    else:
        st.info("Ingen bild finns sparad för detta kort ännu.")
    
    st.divider()
    
    # type="image" tvingar mobilen att visa valet "Ta kort / Galleri"
    up_file = st.file_uploader(
        "Välj eller ta en bild", 
        type="image", 
        key=f"dialog_file_{selected_index}"
    )
    
    if up_file:
        new_img_str = process_uploaded_image(up_file)
        if new_img_str:
            if st.button("💾 Spara bild", type="primary", use_container_width=True):
                app_data["collection"][selected_index]["Bild"] = new_img_str
                save_data_to_github(app_data)
                st.success("Bilden sparades!")
                st.rerun()

# --- HUVUDLAYOUT ---
tab1, tab2, tab3 = st.tabs(["📊 Samling", "✏️ Redigera samling", "➕ Lägg till nytt kort"])

# --- FLIK 1: HUVUDSAMLING ---
with tab1:
    st.subheader("Min Samling")
    
    collection_df = pd.DataFrame(app_data.get("collection", []))
    
    if not collection_df.empty:
        if "Bild" not in collection_df.columns:
            collection_df.insert(0, "Bild", "")

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
            "Bild": st.column_config.ImageColumn("Bild", width="medium"),
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
                if max_rows > 0:
                    current_card_name = edited_df.iloc[selected_row_idx].get('Namn', '')
                    current_card_set = edited_df.iloc[selected_row_idx].get('Setnr.', '')
                    st.caption(f"Valt kort: **Rad {selected_row_num} - {current_card_name} ({current_card_set})**")

            with col_scan_btn:
                st.write("")
                st.write("")
                if st.button("🖼️ Hantera bild för valt kort", use_container_width=True):
                    if max_rows > 0:
                        show_card_dialog(selected_row_idx, edited_df.iloc[selected_row_idx])
            
            st.divider()
            if st.button("💾 Spara alla ändringar i samlingen", type="primary", use_container_width=True):
                app_data["collection"] = edited_df.to_dict(orient="records")
                save_data_to_github(app_data)
                st.success("Samlingen sparades!")
                st.rerun()
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
            "Bild": st.column_config.TextColumn("Bild (URL/Base64)", width="small"),
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
            app_data["collection"] = edited_df.to_dict(orient="records")
            save_data_to_github(app_data)
            st.success("Samlingen sparades!")
            st.rerun()

# --- FLIK 3: LÄGG TILL NYTT KORT ---
with tab3:
    st.subheader("➕ Lägg till nytt kort")
    
    # type="image" ger mobilen valet mellan Kamera och Galleri
    f_img = st.file_uploader("Välj eller ta bild på kortet", type="image", key="add_new_uploader")
    final_img_str = process_uploaded_image(f_img) if f_img else ""

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
            st.success(f"Kortet {namn} skapades och sparades!")
            st.rerun()
