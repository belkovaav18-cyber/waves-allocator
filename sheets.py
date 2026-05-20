def save_results_with_details(sheet_id, sheet_name, result_df, raw_df, guests_df):
    """Сохранить результаты расселения в Google Sheets"""
    client = get_google_client()
    if client is None:
        st.warning("Нет подключения к Google Sheets, результаты не сохранены")
        return
    
    try:
        sheet = client.open_by_key(sheet_id)
        
        try:
            old_worksheet = sheet.worksheet(sheet_name)
            sheet.del_worksheet(old_worksheet)
        except:
            pass
        
        worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="50")
        
        save_df = result_df.copy()
        
        # Добавляем возраст и должность
        guests_info = {}
        for _, row in guests_df.iterrows():
            fio = row.get('ФИО', '')
            if fio:
                guests_info[fio] = {
                    'возраст': row.get('возраст', ''),
                    'должность': row.get('должность', ''),
                    'город': row.get('город', ''),
                    'организация': row.get('организация', ''),
                    'email': row.get('email', ''),
                    'телефон': row.get('телефон', '')
                }
        
        fio_col = 'ФИО' if 'ФИО' in save_df.columns else 'fio' if 'fio' in save_df.columns else None
        
        if fio_col:
            ages = [guests_info.get(fio, {}).get('возраст', '') for fio in save_df[fio_col]]
            positions = [guests_info.get(fio, {}).get('должность', '') for fio in save_df[fio_col]]
            cities = [guests_info.get(fio, {}).get('город', '') for fio in save_df[fio_col]]
            orgs = [guests_info.get(fio, {}).get('организация', '') for fio in save_df[fio_col]]
            emails = [guests_info.get(fio, {}).get('email', '') for fio in save_df[fio_col]]
            phones = [guests_info.get(fio, {}).get('телефон', '') for fio in save_df[fio_col]]
            
            save_df.insert(1, 'возраст', ages)
            save_df.insert(2, 'должность', positions)
            save_df.insert(3, 'город', cities)
            save_df.insert(4, 'организация', orgs)
            save_df.insert(5, 'email', emails)
            save_df.insert(6, 'телефон', phones)
        
        if 'Дата заезда' not in save_df.columns:
            save_df['Дата заезда'] = ''
        if 'Дата отъезда' not in save_df.columns:
            save_df['Дата отъезда'] = ''
        
        save_df = save_df.fillna('')
        
        # Сохраняем
        data = [save_df.columns.values.tolist()] + save_df.values.tolist()
        worksheet.update(data)
        worksheet.freeze(rows=1)
        
        st.success(f"Результаты сохранены в Google Sheets на листе '{sheet_name}'")
        
    except Exception as e:
        st.error(f"Ошибка сохранения результатов: {e}")
