import pandas as pd
from collections import defaultdict

def check_feasibility(guests_df, rooms_df):
    """
    Проверка возможности расселения
    """
    issues = []
    
    # Получаем список резидентов
    residents = guests_df[guests_df['resident'] == True]
    
    # Общая вместимость
    total_capacity = rooms_df['вместимость'].sum()
    total_guests = len(residents)
    
    # Проверка 1: достаточно ли мест?
    if total_guests > total_capacity:
        issues.append({
            'type': 'capacity',
            'severity': 'error',
            'message': f"❌ Недостаточно мест! Гостей: {total_guests}, мест: {total_capacity}. Не хватает {total_guests - total_capacity} мест."
        })
    else:
        issues.append({
            'type': 'capacity',
            'severity': 'success',
            'message': f"✅ Мест достаточно. Гостей: {total_guests}, мест: {total_capacity}. Свободно: {total_capacity - total_guests} мест."
        })
    
    # Проверка 2: одноместные комнаты для программного комитета
    program_committee_names = [
        "Козарь А.В.", "Калиш А.Н.", "Архипов Р.М.", "Балакший В.И.",
        "Белотелов В.И.", "Боголюбов А.Н.", "Бородачев Л.В.", "Бугай А.Н.",
        "Денисов В.И.", "Звездин А.К.", "Игнатьева Д.О.", "Короновский А.А.",
        "Котова С.П.", "Макаров В.А.", "Пирогов Ю.А.", "Пятаков А.П.",
        "Руденко О.В.", "Сазонов С.В.", "Сапожников О.А.", "Тимофеев И.В.",
        "Храмов А.Е.", "Цысарь С.А.", "Чашечкин Ю.Д.", "Черепенин В.А.",
        "Шандаров С.М."
    ]
    
    def is_pc_member(fio):
        if pd.isna(fio):
            return False
        fio_str = str(fio).lower().replace('.', '').replace(' ', '')
        for pc_name in program_committee_names:
            pc_normalized = pc_name.lower().replace('.', '').replace(' ', '')
            if pc_normalized in fio_str or fio_str in pc_normalized:
                return True
        return False
    
    pc_members = residents[residents['ФИО'].apply(is_pc_member)]
    single_rooms = rooms_df[rooms_df['вместимость'] == 1]
    
    if len(pc_members) > len(single_rooms):
        issues.append({
            'type': 'pc_single_rooms',
            'severity': 'warning',
            'message': f"⚠️ Членов программного комитета: {len(pc_members)}, одноместных комнат: {len(single_rooms)}. {len(pc_members) - len(single_rooms)} членов ПК будут расселены в двухместные комнаты."
        })
    else:
        issues.append({
            'type': 'pc_single_rooms',
            'severity': 'success',
            'message': f"✅ Одноместных комнат ({len(single_rooms)}) достаточно для членов ПК ({len(pc_members)})."
        })
    
    # Проверка 3: гости с комментариями
    guests_with_comments = residents[residents['comment'].notna() & (residents['comment'] != '')]
    if len(guests_with_comments) > 0:
        issues.append({
            'type': 'comments',
            'severity': 'warning',
            'message': f"⚠️ {len(guests_with_comments)} гостей оставили комментарии. Требуется ручная обработка!"
        })
    
    # Проверка 4: распределение по городам
    cities = residents['город'].value_counts()
    if len(cities) > 0:
        issues.append({
            'type': 'cities',
            'severity': 'info',
            'message': f"📊 Гости из {len(cities)} городов. Наибольшее количество: {cities.iloc[0]} чел. из {cities.index[0]}"
        })
    
    return issues

def display_feasibility_report(issues):
    """
    Отображение отчета о возможности расселения
    """
    st.subheader("🔍 Проверка возможности расселения")
    
    for issue in issues:
        if issue['severity'] == 'error':
            st.error(issue['message'])
        elif issue['severity'] == 'warning':
            st.warning(issue['message'])
        elif issue['severity'] == 'success':
            st.success(issue['message'])
        else:
            st.info(issue['message'])

def suggest_allocation_strategy(guests_df, rooms_df):
    """
    Предложить стратегию расселения на основе анализа данных
    """
    suggestions = []
    
    residents = guests_df[guests_df['resident'] == True]
    
    # Анализ возрастных групп
    ages = residents['возраст'].dropna()
    if len(ages) > 0:
        age_groups = pd.cut(ages, bins=[0, 30, 40, 50, 60, 100], labels=['<30', '30-40', '40-50', '50-60', '60+'])
        suggestions.append(f"📊 Возрастные группы: {dict(age_groups.value_counts())}")
    
    # Анализ городов
    cities = residents['город'].value_counts()
    if len(cities) > 0:
        suggestions.append(f"🏙️ Рекомендуется селить вместе гостей из одного города. Крупнейшие группы: {dict(cities.head(3))}")
    
    # Анализ должностей
    positions = residents['должность'].value_counts().head(3)
    if len(positions) > 0:
        suggestions.append(f"💼 Среди гостей: {', '.join([f'{pos} ({count})' for pos, count in positions.items()])}")
    
    return suggestions
