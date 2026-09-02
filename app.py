import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import date
import urllib.parse
import re
import uuid

# --- 0. PAGE-KONFIGURATION ---
st.set_page_config(
    page_title="Pokémon Samling", 
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VALUTAKURS-FUNKTION ---
@st.cache_data(ttl=86400)
def fetch_eur_to_sek_rate():
    try:
        url = "https://open.er-api.com/v6/latest/EUR"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            rate = res.json().get("rates", {}).get("SEK")
            if rate:
                return round(float(rate), 4)
    except Exception:
        pass
    return 11.50

# --- FAST MAPPING FÖR ASIATISKA SETS ---
JAPANESE_SET_MAP = {
    "sm4a": ("Ultradimensional Beasts", "SM4A"),
    "sm4b": ("GX Battle Boost", "SM4B"),
    "sm4+": ("GX Battle Boost", "SM4+"),
    "sm4": ("Crimson Invasion", "CIN"),
    "sm8b": ("Ultra Shiny GX", "SM8B"),
    "sm12a": ("Tag All Stars", "SM12A"),
    "s12a": ("VSTAR Universe", "S12A"),
    "sv4a": ("Shiny Treasure ex", "SV4A"),
}

SET_ALIAS_MAP = {
    "sm4a": "sm4plus",
    "sm4+": "sm4plus",
    "sm4b": "sm4b",
    "sm8b": "sm8b",
    "sm12a": "sm12a",
    "s12a": "s12a",
    "sv4a": "sv4a"
}

LANGUAGE_OPTIONS = {
    "Engelska (ENG)": ("en", "ENG"),
    "Japanska (JPN)": ("ja", "JPN"),
    "Franska (FRA)": ("fr", "FRA"),
    "Tyska (GER)": ("de", "GER"),
    "Spanska (ESP)": ("es", "SPA"),
    "Italienska (ITA)": ("it", "ITA"),
    "Kinesiska (ZHT)": ("zh-tw", "ZHT")
}

def get_set_details_sync(set_id):
    if not set_id:
        return "", ""
    clean_id = str(set_id).lower().strip()
    
    if clean_id in JAPANESE_SET_MAP:
        return JAPANESE_SET_MAP[clean_id]
        
    try:
        url = f"https://api.tcgdex.net/v2/en/sets/{urllib.parse.quote(clean_id)}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        if res.status_code == 200:
            data = res.json()
            set_name = data.get("name") or ""
            set_abbrev = data.get("abbreviation") or data.get("id") or ""
            return set_name, str(set_abbrev).upper()
    except Exception:
        pass
        
    return clean_id.upper(), clean_id.upper()

# --- GITHUB INTEGRATION ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = "data.json"

def load_data_from_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return {"collection": []}
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        res = requests.get(raw_url, headers=headers, params={"t": str(uuid.uuid4())}, timeout=4)
        if res.status_code == 200:
            return json.loads(res.text)
    except Exception:
        pass
    return {"collection": []}

def save_data_to_github(data_dict):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GITHUB_TOKEN eller GITHUB_REPO saknas i Secrets!"
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    sha = None
    try:
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200:
            sha = res.json().get("sha")
    except Exception:
        pass
    
    content_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": "Uppdaterade samlingsdata via Streamlit",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    try:
        put_res = requests.put(url, json=payload, headers=headers, timeout=5)
        if put_res.status_code in [200, 201]:
            return True, "Sparat!"
        else:
            return False, f"GitHub felkod {put_res.status_code}: {put_res.text}"
    except Exception as e:
        return False, f"Kunde inte ansluta till GitHub: {str(e)}"

def fix_existing_collection(collection_list):
    for card in collection_list:
        if "_id" not in card or not card["_id"]:
            card["_id"] = str(uuid.uuid4())
    return collection_list

def generate_google_cardmarket_url(name, number, set_name):
    safe_name = str(name) if name is not None else ""
    clean_name = re.sub(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u4e00-\u9faf]', '', safe_name).strip()
    query = f"{clean_name} {number or ''} {set_name or ''} cardmarket"
    return f"https://www.google.com/search?q={urllib.parse.quote(query)}"

# --- FÖRBÄTTRADE SÖKFUNKTIONER MED FALLBACK ---
def search_by_name(card_name, card_num="", lang_key="en", lang_code="ENG"):
    if not card_name.strip():
        return [], "Skriv in ett namn att söka på."
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    results = []
    clean_full_name = card_name.strip().lower()

    try:
        url = f"https://api.tcgdex.net/v2/en/cards?name={urllib.parse.quote(clean_full_name)}"
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            cards_list = res.json()
            if isinstance(cards_list, list):
                for item in cards_list:
                    c_id = str(item.get("id") or "")
                    c_num = str(item.get("localId") or "")
                    img_base = item.get("image") or ""
                    raw_set_id = c_id.split("-")[0] if "-" in c_id else ""
                    full_set_name, set_code = get_set_details_sync(raw_set_id)

                    results.append({
                        "id": f"{c_id}_{uuid.uuid4().hex[:4]}",
                        "name": item.get("name") or card_name,
                        "eng_name": item.get("name") or card_name,
                        "set_code": set_code or raw_set_id.upper(),
                        "set_name": full_set_name or raw_set_id.upper(),
                        "number": c_num or card_num,
                        "image_url": f"{img_base}/high.png" if img_base else "",
                        "default_lang": lang_code
                    })
                    if len(results) >= 15:
                        break
            return results, None
    except Exception:
        pass

    # Fallback om API-anslutning spärras
    full_set_name, set_code = get_set_details_sync("")
    fallback_card = {
        "id": f"manual_{uuid.uuid4().hex[:4]}",
        "name": card_name.capitalize(),
        "eng_name": card_name.capitalize(),
        "set_code": "CUSTOM",
        "set_name": "Manuell inmatning",
        "number": card_num if card_num else "1",
        "image_url": "",
        "default_lang": lang_code
    }
    return [fallback_card], "Kunde inte nå TCGdex API (nätverket spärrat). Visar manuellt kortutkast baserat på din sökning:"

def search_by_set_code(set_code_input, card_num, lang_key="en", lang_code="ENG"):
    if not set_code_input.strip() or not card_num.strip():
        return [], "Ange både Setkod och Kortnummer."

    headers = {'User-Agent': 'Mozilla/5.0'}
    clean_set = set_code_input.strip().lower()
    clean_num = card_num.strip().lstrip("0")
    actual_set = SET_ALIAS_MAP.get(clean_set, clean_set)

    full_set_name, set_code = get_set_details_sync(clean_set)

    # Försök direkt med API-anrop
    for num_format in [clean_num, clean_num.zfill(3), clean_num.zfill(2)]:
        try:
            url_card = f"https://api.tcgdex.net/v2/en/cards/{actual_set}-{num_format}"
            res = requests.get(url_card, headers=headers, timeout=2)
            if res.status_code == 200:
                card_data = res.json()
                img_base = card_data.get("image") or ""
                return [{
                    "id": f"{card_data.get('id')}_{uuid.uuid4().hex[:4]}",
                    "name": card_data.get("name") or f"Kort #{card_num}",
                    "eng_name": card_data.get("name") or f"Kort #{card_num}",
                    "set_code": set_code or clean_set.upper(),
                    "set_name": full_set_name or clean_set.upper(),
                    "number": str(card_data.get("localId") or card_num),
                    "image_url": f"{img_base}/high.png" if img_base else "",
                    "default_lang": lang_code
                }], None
        except Exception:
            break

    # Robust Fallback vid nätverksspärr
    fallback_card = {
        "id": f"manual_{clean_set}_{clean_num}",
        "name": f"Pokémon ({full_set_name})",
        "eng_name": f"Pokémon ({full_set_name})",
        "set_code": set_code or clean_set.upper(),
        "set_name": full_set_name or clean_set.upper(),
        "number": card_num,
        "image_url": "",
        "default_lang": lang_code
    }
    return [fallback_card], "API-anslutning nekades av servern/nätverket. Skapade ett färdigt kortutkast som du kan fylla i och spara:"

# --- INITIERA SESSION STATE ---
if "editor_version" not in st.session_state:
    st.session_state["editor_version"] = 0

if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

if "search_error" not in st.session_state:
    st.session_state["search_error"] = None

if "app_data" not in st.session_state or st.session_state["app_data"] is None:
    st.session_state["app_data"] = load_data_from_github()

app_data = st.session_state["app_data"]
if "collection" not in app_data:
    app_data["collection"] = []

app_data["collection"] = fix_existing_collection(app_data["collection"])
eur_to_sek = fetch_eur_to_sek_rate()

# --- LAYOUT & TABS ---
tab1, tab2 = st.tabs(["📊 Samling", "➕ Sök & Lägg till kort"])

# --- FLIK 1: SAMLING ---
with tab1:
    col_header, col_rate = st.columns([2, 3])
    with col_header:
        st.subheader("Min Samling")
    with col_rate:
        c_rate_txt, c_rate_btn = st.columns([2, 1])
        with c_rate_txt:
            st.info(f"💱 **Aktuell kurs:** 1 EUR = **{eur_to_sek:.2f} SEK**")
        with c_rate_btn:
            if st.button("🔄 Uppdatera", help="Hämta senast gällande växelkurs"):
                fetch_eur_to_sek_rate.clear()
                st.session_state["app_data"] = None
                st.rerun()

    collection = sorted(app_data.get("collection", []), key=lambda x: int(x.get("Pärmnummer", 0) or 0))
    app_data["collection"] = collection
    
    if collection:
        df = pd.DataFrame(collection)
        
        if "Värde (USD)" in df.columns and "Värde (EUR)" not in df.columns:
            df["Värde (EUR)"] = df["Värde (USD)"]
        
        for col in ["Bild", "Pärmnummer", "Värde (EUR)", "Köpt för (EUR)", "Google Sök", "Egen Cardmarket Länk", "Engelskt Namn", "_id"]:
            if col not in df.columns:
                df[col] = 0.0 if "Värde" in col or "Köpt" in col else ""
        
        df["Bild"] = df["Bild"].fillna("").astype(str)
        df["Värde (EUR)"] = pd.to_numeric(df["Värde (EUR)"], errors='coerce').fillna(0.0)
        df["Köpt för (EUR)"] = pd.to_numeric(df["Köpt för (EUR)"], errors='coerce').fillna(0.0)
        df["Egen Cardmarket Länk"] = df["Egen Cardmarket Länk"].fillna("").astype(str)
        
        df["Köpt för (SEK)"] = (df["Köpt för (EUR)"] * eur_to_sek).round(2)
        df["Värde idag (SEK)"] = (df["Värde (EUR)"] * eur_to_sek).round(2)

        col_act1, col_act2 = st.columns([3, 1])
        with col_act1:
            edit_mode = st.checkbox("✏️ Aktivera redigeringsläge (Mata in värden & egna länkar)")

        columns_order = [
            "Bild", "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
            "Övrigt", "Skick", "Köpt för (EUR)", "Värde (EUR)", "Värde idag (SEK)", "Google Sök", "Egen Cardmarket Länk"
        ]

        if not edit_mode:
            display_df = df.copy()

            column_config = {
                "Bild": st.column_config.ImageColumn("Bild", width="small"),
                "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width="small"),
                "Språk": st.column_config.TextColumn("Språk", width="small"),
                "Namn": st.column_config.TextColumn("Namn", width="medium"),
                "Setnr.": st.column_config.TextColumn("Setnr.", width="small"),
                "SetBet.": st.column_config.TextColumn("SetBet.", width="small"),
                "Set": st.column_config.TextColumn("Set", width="medium"),
                "Övrigt": st.column_config.TextColumn("Övrigt", width="small"),
                "Skick": st.column_config.TextColumn("Skick", width="small"),
                "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="€%.2f", width="small"),
                "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="€%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width="small"),
                "Google Sök": st.column_config.LinkColumn("Sök Cardmarket", display_text="🔍 Google Sök", width="medium"),
                "Egen Cardmarket Länk": st.column_config.LinkColumn("Min Cardmarket Länk", display_text="🔗 Öppna Sida", width="medium")
            }
            st.dataframe(display_df[columns_order], column_config=column_config, use_container_width=True, hide_index=True)
        
        else:
            column_config_edit = {
                "_id": None,
                "Bild": st.column_config.TextColumn("Bild-URL", width="medium"),
                "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width="small", step=1),
                "Språk": st.column_config.SelectboxColumn("Språk", options=["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"], width="small"),
                "Namn": st.column_config.TextColumn("Namn", width="medium"),
                "Setnr.": st.column_config.TextColumn("Setnr.", width="small"),
                "SetBet.": st.column_config.TextColumn("SetBet.", width="small"),
                "Set": st.column_config.TextColumn("Set/Base", width="medium"),
                "Övrigt": st.column_config.SelectboxColumn("Övrigt", options=["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], width="small"),
                "Skick": st.column_config.SelectboxColumn("Skick", options=["NM", "EX", "GD", "LP", "PL", "PO"], width="small"),
                "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="%.2f", width="small"),
                "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width="small", disabled=True),
                "Google Sök": st.column_config.TextColumn("Google Sök URL", disabled=True, width="medium"),
                "Egen Cardmarket Länk": st.column_config.TextColumn("Klistra in Cardmarket URL här", width="large")
            }

            edit_columns = ["_id"] + columns_order
            editor_key = f"collection_editor_v{st.session_state['editor_version']}"

            edited_df = st.data_editor(
                df[edit_columns],
                column_config=column_config_edit,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key=editor_key
            )

            with col_act2:
                if st.button("💾 Spara ändringar", type="primary", use_container_width=True):
                    raw_edited = edited_df.to_dict(orient="records")
                    old_collection = app_data.get("collection", [])
                    old_map = {c["_id"]: int(c.get("Pärmnummer", 0) or 0) for c in old_collection if "_id" in c}
                    
                    existing_ids = set()
                    changed_card_id = None
                    old_nr = None
                    new_nr = None

                    for row in raw_edited:
                        c_id = row.get("_id")
                        if c_id:
                            existing_ids.add(c_id)
                            curr_input_nr = int(row.get("Pärmnummer", 0) or 0)
                            prev_nr = old_map.get(c_id)
                            if prev_nr and curr_input_nr != prev_nr:
                                changed_card_id = c_id
                                old_nr = prev_nr
                                new_nr = curr_input_nr

                    deleted_nrs = [nr for c_id, nr in old_map.items() if c_id not in existing_ids]

                    processed_list = []
                    for row in raw_edited:
                        c_id = row.get("_id")
                        if c_id == changed_card_id:
                            target_nr = new_nr
                        else:
                            target_nr = old_map.get(c_id, int(row.get("Pärmnummer", 0) or 0))
                            if changed_card_id and old_nr and new_nr:
                                if old_nr < new_nr:
                                    if old_nr < target_nr <= new_nr:
                                        target_nr -= 1
                                elif new_nr < old_nr:
                                    if new_nr <= target_nr < old_nr:
                                        target_nr += 1
                            for d_nr in deleted_nrs:
                                if target_nr > d_nr:
                                    target_nr -= 1

                        row["Pärmnummer"] = target_nr
                        row["Egen Cardmarket Länk"] = str(row.get("Egen Cardmarket Länk") or "").strip()
                        k_eur = float(row.get("Köpt för (EUR)", 0.0) or 0.0)
                        v_eur = float(row.get("Värde (EUR)", 0.0) or 0.0)
                        row["Köpt för (SEK)"] = round(k_eur * eur_to_sek, 2)
                        row["Värde idag (SEK)"] = round(v_eur * eur_to_sek, 2)
                        s_name = row.get("Engelskt Namn") or row.get("Namn") or ""
                        row["Google Sök"] = generate_google_cardmarket_url(s_name, row.get("Setnr.", ""), row.get("Set", ""))
                        processed_list.append(row)

                    processed_list.sort(key=lambda x: int(x.get("Pärmnummer", 0)))
                    for seq_nr, card in enumerate(processed_list, start=1):
                        card["Pärmnummer"] = seq_nr

                    save_payload = {"collection": processed_list}
                    success, msg = save_data_to_github(save_payload)
                    
                    if success:
                        st.session_state["app_data"] = None 
                        st.session_state["editor_version"] += 1
                        st.success("Ändringarna sparades!")
                        st.rerun()
                    else:
                        st.error(f"Kunde inte spara till GitHub: {msg}")

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Totalt antal kort", len(df))
        c2.metric("Totalt värde (SEK)", f"{df['Värde idag (SEK)'].sum():,.2f} kr")
        c3.metric("Total vinst (SEK)", f"{(df['Värde idag (SEK)'].sum() - df['Köpt för (SEK)'].sum()):,.2f} kr")
    else:
        st.info("Samlingen är tom. Gå till fliken 'Sök & Lägg till kort'.")

# --- FLIK 2: SÖK & LÄGG TILL ---
with tab2:
    st.subheader("🔍 Sök Pokémonkort")
    
    selected_lang_label = st.selectbox("Välj Sök-språk:", list(LANGUAGE_OPTIONS.keys()), index=1)
    lang_key, lang_code = LANGUAGE_OPTIONS[selected_lang_label]
    
    st.divider()

    # METOD 1: Namnsökning
    st.markdown("**Metod 1: Sök på Pokémon-namn** (t.ex. *Raichu* eller *Pikachu*)")
    col_n1, col_n2, col_n3 = st.columns([2, 1, 1])
    with col_n1:
        s_name = st.text_input("Pokémon-namn:", key="input_search_name")
    with col_n2:
        s_num_opt = st.text_input("Kortnummer (valfritt):", key="input_search_num_opt")
    with col_n3:
        st.write(" ")
        st.write(" ")
        btn_search_name = st.button("🔍 Sök Namn", type="primary", use_container_width=True)

    st.divider()

    # METOD 2: Setkod + Nummer
    st.markdown("**Metod 2: Sök på Setkod + Nummer** (t.ex. Setkod: *sm4a*, Nummer: *16*)")
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        s_setcode = st.text_input("Setkod (t.ex. sm4a, swsh1, sv4a):", key="input_search_setcode", value="sm4a")
    with col_s2:
        s_num_req = st.text_input("Kortnummer:", key="input_search_num_req", value="16")
    with col_s3:
        st.write(" ")
        st.write(" ")
        btn_search_set = st.button("🔍 Sök Setkod", type="primary", use_container_width=True)

    # EXECUTE SEARCH
    if btn_search_name:
        with st.spinner("Söker på namn..."):
            res, err = search_by_name(s_name, s_num_opt, lang_key=lang_key, lang_code=lang_code)
            st.session_state["search_results"] = res
            st.session_state["search_error"] = err
            
    elif btn_search_set:
        with st.spinner("Söker på setkod..."):
            res, err = search_by_set_code(s_setcode, s_num_req, lang_key=lang_key, lang_code=lang_code)
            st.session_state["search_results"] = res
            st.session_state["search_error"] = err

    # SHOW RESULTS OR ERRORS
    results = st.session_state.get("search_results", [])
    error_msg = st.session_state.get("search_error", None)

    if error_msg:
        st.info(f"ℹ️ {error_msg}")

    if results:
        for card_api in results:
            with st.container():
                col_img, col_info, col_form = st.columns([1, 2, 2])
                
                card_name = str(card_api.get("name") or "")
                eng_name = str(card_api.get("eng_name") or card_name)
                set_code = str(card_api.get("set_code") or "").upper()
                full_set_name = str(card_api.get("set_name") or set_code)
                number = str(card_api.get("number") or "")
                def_lang = str(card_api.get("default_lang") or "ENG")
                api_img_url = str(card_api.get("image_url") or "")

                with col_img:
                    if api_img_url:
                        st.image(api_img_url, width=120)
                    else:
                        st.image("https://assets.tcgdex.net/back.png", width=120)

                with col_info:
                    st.markdown(f"### {card_name}")
                    st.write(f"**Språk:** `{def_lang}`")
                    st.write(f"**Setkod:** `{set_code}`")
                    st.write(f"**Set:** `{full_set_name}`")
                    st.write(f"**Setnr:** {number}")

                with col_form:
                    form_key = f"form_{card_api['id']}"
                    with st.form(key=form_key):
                        c_a, c_b = st.columns(2)
                        all_langs = ["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"]
                        default_lang_idx = all_langs.index(def_lang) if def_lang in all_langs else 0
                        
                        with c_a:
                            input_card_name = st.text_input("Kortnamn", value=card_name)
                            lang = st.selectbox("Språk", all_langs, index=default_lang_idx)
                            cond = st.selectbox("Skick", ["NM", "EX", "GD", "LP", "PL", "PO"], index=0)
                            parm_nr = st.number_input("Pärmnummer", min_value=1, value=len(app_data.get("collection", [])) + 1)

                        with c_b:
                            set_base_input = st.text_input("Set / Base-namn", value=full_set_name)
                            rarity = st.selectbox("Övrigt", ["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], index=0)
                            kopt_eur = st.number_input("Köpt för (EUR)", min_value=0.0, value=0.0, step=0.5)
                            varde_eur_manual = st.number_input("Värde (EUR)", min_value=0.0, value=0.0, step=0.5)
                        
                        custom_link = st.text_input("Cardmarket-länk (Valfritt):", value="")
                        custom_img_url = st.text_input("Bild-URL (Valfritt):", value=api_img_url)

                        if st.form_submit_button("➕ Lägg till i samlingen", type="primary", use_container_width=True):
                            google_url = generate_google_cardmarket_url(input_card_name, number, set_base_input)
                            raw_img = custom_img_url.strip() if custom_img_url.strip() else (api_img_url if api_img_url else "")

                            new_entry = {
                                "_id": str(uuid.uuid4()),
                                "Bild": raw_img,
                                "Pärmnummer": int(parm_nr),
                                "Språk": lang,
                                "Namn": input_card_name,
                                "Engelskt Namn": eng_name,
                                "Setnr.": number,
                                "SetBet.": set_code,
                                "Set": set_base_input,
                                "Övrigt": rarity,
                                "Skick": cond,
                                "Köpt för (EUR)": kopt_eur,
                                "Köpt för (SEK)": round(kopt_eur * eur_to_sek, 2),
                                "Värde (EUR)": varde_eur_manual,
                                "Värde idag (SEK)": round(varde_eur_manual * eur_to_sek, 2),
                                "Datum tillagd": date.today().strftime("%Y-%m-%d"),
                                "Google Sök": google_url,
                                "Egen Cardmarket Länk": custom_link.strip()
                            }
                            
                            for existing_card in app_data["collection"]:
                                if int(existing_card.get("Pärmnummer", 0)) >= parm_nr:
                                    existing_card["Pärmnummer"] = int(existing_card["Pärmnummer"]) + 1
                                    
                            app_data["collection"].append(new_entry)
                            
                            sorted_coll = sorted(app_data["collection"], key=lambda x: int(x.get("Pärmnummer", 0) or 0))
                            for idx, card in enumerate(sorted_coll, start=1):
                                card["Pärmnummer"] = idx
                            
                            save_payload = {"collection": sorted_coll}
                            success, msg = save_data_to_github(save_payload)
                            if success:
                                st.session_state["app_data"] = None
                                st.session_state["editor_version"] += 1
                                st.session_state["search_results"] = []
                                st.session_state["search_error"] = None
                                st.success(f"Lade till {input_card_name} (#{parm_nr})!")
                                st.rerun()
                            else:
                                st.error(f"Kunde inte spara till GitHub: {msg}")
                st.divider()
