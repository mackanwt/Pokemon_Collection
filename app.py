with col_act2:
    if st.button("💾 Spara ändringar", type="primary", use_container_width=True):
        raw_edited = edited_df.to_dict(orient="records")
        old_collection = app_data.get("collection", [])
        
        # 1. Skapa en uppslagstabell för gamla nummer baserat på unikt _id
        old_map = {c["_id"]: int(c.get("Pärmnummer", 0) or 0) for c in old_collection if "_id" in c}
        
        # 2. Identifiera vilka kort som är kvar och om något ändrat nummer
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
                
                # Om numret skiljer sig från tidigare har vi hittat det ändrade kortet
                if prev_nr and curr_input_nr != prev_nr:
                    changed_card_id = c_id
                    old_nr = prev_nr
                    new_nr = curr_input_nr

        # 3. HANTERA RADERING (om en rad har tagits bort i datagriden)
        deleted_nrs = [nr for c_id, nr in old_map.items() if c_id not in existing_ids]

        # 4. TILLÄMPA LOGIK FÖR FÖRSKJUTNING
        processed_list = []
        for row in raw_edited:
            c_id = row.get("_id")
            
            # Om användaren ändrade detta kort manuellt, sätt det nya numret
            if c_id == changed_card_id:
                target_nr = new_nr
            else:
                target_nr = old_map.get(c_id, int(row.get("Pärmnummer", 0) or 0))
                
                # Om ett annat kort flyttades, skjut fram/bak övriga kort i intervallet
                if changed_card_id and old_nr and new_nr:
                    if old_nr < new_nr:
                        # Flyttat neråt (t.ex. 2 -> 5): Minska 3, 4, 5 med 1
                        if old_nr < target_nr <= new_nr:
                            target_nr -= 1
                    elif new_nr < old_nr:
                        # Flyttat uppåt (t.ex. 5 -> 2): Öka 2, 3, 4 med 1
                        if new_nr <= target_nr < old_nr:
                            target_nr += 1
                
                # Om kort raderades, minska alla högre nummer
                for d_nr in deleted_nrs:
                    if target_nr > d_nr:
                        target_nr -= 1

            row["Pärmnummer"] = target_nr
            
            # Beräkna om valuta & söklänkar
            k_eur = float(row.get("Köpt för (EUR)", 0.0) or 0.0)
            v_eur = float(row.get("Värde (EUR)", 0.0) or 0.0)
            row["Köpt för (SEK)"] = round(k_eur * eur_to_sek, 2)
            row["Värde idag (SEK)"] = round(v_eur * eur_to_sek, 2)
            s_name = row.get("Engelskt Namn") or row.get("Namn") or ""
            row["Google Sök"] = generate_google_cardmarket_url(s_name, row.get("Setnr.", ""), row.get("Set", ""))
            
            processed_list.append(row)

        # 5. Sortera strikt på de beräknade numren och ge ren sekvens (1, 2, 3...)
        processed_list.sort(key=lambda x: int(x.get("Pärmnummer", 0)))
        for seq_nr, card in enumerate(processed_list, start=1):
            card["Pärmnummer"] = seq_nr

        # 6. Spara till GitHub & nollställ minnet
        save_payload = {"collection": processed_list}
        success, msg = save_data_to_github(save_payload)
        
        if success:
            st.session_state["app_data"] = None 
            st.session_state["editor_version"] += 1
            st.success("Ändringarna sparades och ordningen justerades!")
            st.rerun()
        else:
            st.error(f"Kunde inte spara till GitHub: {msg}")
