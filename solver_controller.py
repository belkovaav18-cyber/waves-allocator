import pandas as pd

def smart_solve(guests, rooms):
    if not guests:
        return pd.DataFrame({'error': ['Нет гостей для расселения']}), {}
    if not rooms:
        return pd.DataFrame({'error': ['Нет комнат для расселения']}), {}
    
    try:
        from solver import solve_allocation
        result_df, debug_info = solve_allocation(guests, rooms)
        return result_df, debug_info
    except Exception as e:
        import traceback
        traceback.print_exc()
        return pd.DataFrame({'error': [str(e)]}), {}

def optimize_allocation(result_df, rooms_df):
    return []
