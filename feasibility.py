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
    
    # Проверка 3: гости с коммента
