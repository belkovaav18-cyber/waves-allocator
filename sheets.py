def save_results_with_details(sheet_id, sheet_name, result_df, raw_df, guests_df):
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
        
        # Порядок колонок
        column_order = ['ФИО', 'пол', 'возраст', 'должность', 'город', 'организация',
                       'room_id', 'room_capacity', 'Дата заезда', 'Дата отъезда',
                       'число_ночей', 'тариф', 'стоимость', 'comment']
        
        # Добавляем даты если есть
        if 'Дата заезда' not in save_df.columns:
            save_df['Дата заезда'] = ''
        if 'Дата отъезда' not in save_df.columns:
            save_df['Дата отъезда'] = ''
        
        existing_cols = [col for col in column_order if col in save_df.columns]
        save_df = save_df[existing_cols]
        save_df = save_df.fillna('')
        
        # Конвертируем типы
        for col in save_df.columns:
            if col == 'возраст':
                save_df[col] = save_df[col].apply(lambda x: int(x) if str(x).isdigit() else 0)
            elif col == 'тариф':
                save_df[col] = save_df[col].apply(lambda x: int(x) if str(x).isdigit() else 0)
            elif col == 'число_ночей':
                save_df[col] = save_df[col].apply(lambda x: int(x) if str(x).isdigit() else 0)
            elif col == 'стоимость':
                save_df[col] = save_df[col].apply(lambda x: int(x) if str(x).isdigit() else 0)
            else:
                save_df[col] = save_df[col].apply(lambda x: str(x) if pd.notna(x) else '')
        
        data = [save_df.columns.values.tolist()] + save_df.values.tolist()
        worksheet.update(data)
        worksheet.freeze(rows=1)
        
        st.success(f"Результаты сохранены в Google Sheets на листе '{sheet_name}'")
        
    except Exception as e:
        st.error(f"Ошибка сохранения результатов: {e}")
        import traceback
        traceback.print_exc()
