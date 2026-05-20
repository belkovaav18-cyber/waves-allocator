import streamlit as st
import pandas as pd

def process_comments(guests_df):
    """
    Обработка комментариев гостей
    """
    comments_report = []
    
    # Список программного комитета
    program_committee = [
        "Козарь А.В.", "Калиш А.Н.", "Архипов Р.М.", "Балакший В.И.",
        "Белотелов В.И.", "Боголюбов А.Н.", "Бородачев Л.В.", "Бугай А.Н.",
        "Денисов В.И.", "Звездин А.К.", "Игнатьева Д.О.", "Короновский А.А.",
        "Котова С.П.", "Макаров В.А.", "Пирогов Ю.А.", "Пятаков А.П.",
        "Руденко О.В.", "Сазонов С.В.", "Сапожников О.А.", "Тимофеев И.В.",
        "Храмов А.Е.", "Цысарь С.А.", "Чашечкин Ю.Д.", "Черепенин В.А.",
        "Шандаров С.М."
    ]
    
    def normalize_name(name):
        if not name:
            return ""
        return str(name).lower().replace('.', '').replace(' ', '')
    
    pc_normalized = [normalize_name(name) for name in program_committee]
    
    for _, guest in guests_df.iterrows():
        fio = guest.get('ФИО', '')
        comment = guest.get('comment', '')
        is_pc = False
        
        # Проверяем, член ли программного комитета
        normalized_fio = normalize_name(fio)
        for pc_name in pc_normalized:
            if pc_name in normalized_fio or normalized_fio in pc_name:
                is_pc = True
                break
        
        if comment and str(comment).strip() and str(comment).strip().lower() not in ['', 'нет', '-', 'nan']:
            if is_pc:
                comments_report.append({
                    'type': 'program_committee',
                    'fio': fio,
                    'comment': comment,
                    'message': f"👨‍💼 Член программного комитета {fio} оставил комментарий: \"{comment}\""
                })
            else:
                comments_report.append({
                    'type': 'regular',
                    'fio': fio,
                    'comment': comment,
                    'message': f"📝 {fio} оставил комментарий: \"{comment}\""
                })
    
    return comments_report

def display_comments_report(comments_report):
    """
    Отображение отчета по комментариям
    """
    if not comments_report:
        st.info("ℹ️ Нет комментариев от гостей")
        return
    
    st.subheader("📋 Отчет по комментариям")
    
    # Отдельно показываем комментарии членов программного комитета
    pc_comments = [c for c in comments_report if c['type'] == 'program_committee']
    regular_comments = [c for c in comments_report if c['type'] == 'regular']
    
    if pc_comments:
        st.markdown("### 👨‍💼 Комментарии членов программного комитета")
        for comment in pc_comments:
            st.warning(comment['message'])
    
    if regular_comments:
        st.markdown("### 📝 Комментарии остальных гостей")
        for comment in regular_comments:
            st.info(comment['message'])
    
    # Добавляем предупреждение о ручной обработке
    if regular_comments:
        st.markdown("---")
        st.warning("⚠️ **Внимание:** Гости с комментариями требуют ручной обработки расселения!")

def extract_room_preferences(comments_report):
    """
    Извлечение пожеланий по расселению из комментариев
    """
    preferences = []
    
    for comment in comments_report:
        comment_text = comment['comment'].lower()
        fio = comment['fio']
        
        # Ищем ключевые слова
        if 'поселить вместе' in comment_text or 'вместе с' in comment_text:
            # Извлекаем имена
            import re
            names = re.findall(r'[А-Я][а-я]+ [А-Я][а-я]+', comment_text)
            if names:
                preferences.append({
                    'fio': fio,
                    'type': 'together',
                    'with': names,
                    'original_comment': comment['comment']
                })
        
        if 'не с' in comment_text or 'отдельно от' in comment_text:
            preferences.append({
                'fio': fio,
                'type': 'separate',
                'original_comment': comment['comment']
            })
    
    return preferences
