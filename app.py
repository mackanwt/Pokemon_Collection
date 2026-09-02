import streamlit as st
import requests
import urllib.parse
import re

# ---------------------------------------------------------
# CONFIG & PAGE SETUP
# ---------------------------------------------------------
st.set_page_config(
    page_title="Pokémon TCG Samling",
    page_icon="🃏",
    layout="wide"
)

if "collection" not in st.session_state:
    st.session_state.collection = []

# Språkkoder som stöds av TCGdex API
LANGUAGE_OPTIONS = {
    "Japanska (JPN)": "ja",
    "Engelska (ENG)": "en",
    "Kinesiska (Traditionell)": "zh-tw",
    "Tyska (GER)": "de",
    "Franska (FRA)": "fr",
    "Spanska (ESP)": "es",
    "Italienska (ITA)": "it"
}

@st.cache_data(ttl=86400)
def get_set_details_sync(raw_set_id, lang_code):
    if not raw_set_id:
        return "", ""
    try:
        url = f"https://api.tcgdex.net/v2/{lang_code}/sets/{urllib.parse.quote(raw_set_id)}"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            return data.get("name", raw_set_id.upper()), raw_set_id.upper()
    except Exception:
        pass
    return raw_set_id.upper(), raw_set_id.upper()

# ---------------------------------------------------------
# SEARCH FUNCTION WITH LANGUAGE FILTER
# ---------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def search_pokemon_cards(query, lang_key):
    if not query or len(query.strip()) < 2:
        return []

    query_clean = query.strip().lower()
    if "/" in query_clean:
        query_clean = query_clean.split("/")[0].strip()

    words = [w for w in re.split(r'\s+', query_clean) if w]
    if not words:
        return []

    numbers = [w.lstrip("0") for w in words if w.isdigit()]
    text_words = [w for w in words if not w.isdigit()]

    headers = {'User-Agent': 'Mozilla/5.0'}
    results = []
    seen_ids = set()

    # 1. Om användaren skriver en exakt kombination som (t.ex. "sm4a 016" eller "sm4a 16")
    if text_words and numbers:
        set_candidate = text_words[0]
        num_candidate = numbers[0]
        possible_ids = [
            f"{set_candidate}-{num_candidate}",
            f"{set_candidate}-{num_candidate.zfill(3)}"
        ]
        
        for pid in possible_ids:
            try:
                url_direct = f"https://api.tcgdex.net/v2/{lang_key}/cards/{urllib.parse.quote(pid)}"
                res_direct = requests.get(url_direct, headers=headers, timeout=3)
                if res_direct.status_code == 200:
                    item = res_direct.json()
                    if isinstance(item, dict) and item.get("id"):
                        card_id = str(item.get("id"))
                        if card_id not in seen_ids:
                            seen_ids.add(card_id)
                            img_base = item.get("image") or ""
                            raw_set_id = item.get("set", {}).get("id") or (card_id.split("-")[0] if "-" in card_id else "")
                            full_set_name, set_code = get_set_details_sync(raw_set_id, lang_key)

                            results.append({
                                "id": card_id,
                                "name": item.get("name") or "",
                                "set_code": set_code,
                                "set_name": full_set_name,
                                "number": str(item.get("localId") or card_id.split("-")[-1]),
                                "image_url": f"{img_base}/high.png" if img_base else "",
                            })
            except Exception:
                pass

        if results:
            return results

    # 2. Fritextsökning i valt språk
    search_term = text_words[0] if text_words else words[0]
    
    try:
        url_search = f"https://api.tcgdex.net/v2/{lang_key}/cards?name={urllib.parse.quote(search_term)}"
        res_search = requests.get(url_search, headers=headers, timeout=4)

        if res_search.status_code == 200:
            cards_list = res_search.json()
            if isinstance(cards_list, list):
                for item in cards_list:
                    c_id = str(item.get("id") or "").lower()
                    c_name = str(item.get("name") or "").lower()
                    c_local_id = str(item.get("localId") or "").lstrip("0")

                    id_parts = c_id.split("-")
                    id_number = id_parts[-1].lstrip("0") if len(id_parts) > 1 else ""
                    card_num = c_local_id if c_local_id else id_number

                    # Matchning
                    text_match = all(tw in c_name or tw in c_id for tw in text_words)
                    num_match = True
                    if numbers:
                        num_match = any(num == card_num for num in numbers)

                    if text_match and num_match:
                        card_id = str(item.get("id") or "")
                        if card_id not in seen_ids:
                            seen_ids.add(card_id)
                            img_base = item.get("image") or ""
                            raw_set_id = card_id.split("-")[0] if "-" in card_id else ""
                            full_set_name, set_code = get_set_details_sync(raw_set_id, lang_key)

                            results.append({
                                "id": card_id,
                                "name": item.get("name") or "",
                                "set_code": set_code,
                                "set_name": full_set_name,
                                "number": str(item.get("localId") or (id_parts[-1] if len(id_parts) > 1 else "")),
                                "image_url": f"{img_base}/high.png" if img_base else "",
                            })
                            if len(results) >= 20:
                                break
    except Exception:
        pass

    return results

# ---------------------------------------------------------
# STREAMLIT UI
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["📊 Samling", "➕ Sök & Lägg till kort"])

with tab2:
    st.header("🔍 Sök Pokémon-kort")
    
    col_lang, col_search = st.columns([1, 3])
    with col_lang:
        selected_lang_label = st.selectbox("Välj Sök-språk / Region:", list(LANGUAGE_OPTIONS.keys()), index=0)
        selected_lang_code = LANGUAGE_OPTIONS[selected_lang_label]

    with col_search:
        search_query = st.text_input(
            "Sök på Setkod+Nr (t.ex. 'sm4a 016') eller Namn:",
            key="search_input",
            placeholder="t.ex. sm4a 016 eller Raichu"
        )

    if search_query:
        with st.spinner("Söker i TCGdex..."):
            found_cards = search_pokemon_cards(search_query, selected_lang_code)

        if found_cards:
            st.success(f"Hittade {len(found_cards)} kort på {selected_lang_label}.")
            cols = st.columns(3)
            for idx, card in enumerate(found_cards):
                with cols[idx % 3]:
                    st.markdown("---")
                    if card["image_url"]:
                        st.image(card["image_url"], use_container_width=True)
                    st.subheader(card["name"])
                    st.caption(f"Set: ({card['set_code']}) | Nr:")
                    
                    cond = st.selectbox("Skick", ["Near Mint", "Lightly Played", "Played", "Poor"], key=f"cond_{card['id']}_{idx}")
                    
                    if st.button("➕ Lägg till i samling", key=f"add_{card['id']}_{idx}"):
                        st.session_state.collection.append({
                            "name": card["name"],
                            "set_name": card["set_name"],
                            "set_code": card["set_code"],
                            "number": card["number"],
                            "language": selected_lang_label.split(" ")[0],
                            "condition": cond,
                            "image_url": card["image_url"]
                        })
                        st.toast(f"Lade till {card['name']} i samlingen!")
        else:
            st.warning("Inga kort hittades. Tips: Om du söker japanska kort, använd gärna setkod + nummer (t.ex. 'sm4a 016' eller 'sv4a 001').")

with tab1:
    st.header("📦 Din Samling")
    if st.session_state.collection:
        st.write(f"Totalt antal kort i samlingen: **{len(st.session_state.collection)}**")
        cols = st.columns(4)
        for idx, item in enumerate(st.session_state.collection):
            with cols[idx % 4]:
                if item["image_url"]:
                    st.image(item["image_url"], use_container_width=True)
                st.write(f"**{item['name']}**")
                st.caption(f"{item['set_name']} #{item['number']}")
                st.caption(f"Språk: {item['language']} | Skick: {item['condition']}")
                if st.button("🗑️ Ta bort", key=f"del_{idx}"):
                    st.session_state.collection.pop(idx)
                    st.rerun()
    else:
        st.info("Din samling är tom. Sök och lägg till kort i fliken ovan!")
