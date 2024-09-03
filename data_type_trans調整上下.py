

import pandas as pd
from datetime import datetime
def process_satellite_data(power_file, transition_file, output_file):
    # 讀取輸入的Excel檔案
    power_df = pd.read_excel(power_file)
    transition_df = pd.read_excel(transition_file)

    # 確保 'power' 欄位名稱改為 '姿態轉換時的發電量'
    # if 'power' in power_df.columns:
    #     power_df.rename(columns={'power': '姿態轉換時的發電量'}, inplace=True)
    
    # 確保 transition_df 的時間欄位為 datetime 格式
    transition_df['time'] = pd.to_datetime(transition_df['time'])
    #   power_df ['time'] = pd.to_datetime(power_df ['time'])
    # 以 transition_df 的時間範圍為基礎，建立每 10 秒的時間序列 ###############################
    min_time = transition_df['time'].min()
    max_time = transition_df['time'].max()
    time_range = pd.date_range(start=min_time, end=max_time, freq='10S')

    # 創建一個新的 DataFrame 來保存時間序列和 situation 數據
    expanded_df = pd.DataFrame(time_range, columns=['time'])

    # 使用 merge_asof 來填充 expanded_df 中的 situation 值
    expanded_df = pd.merge_asof(expanded_df, transition_df[['time', 'situation']], on='time', direction='backward')

    # 將空的 situation 欄位用前一個值填充
    expanded_df['situation'].fillna(method='ffill', inplace=True)
    
    # 如果擴展後的第一個值是空的，用後續有效值填充
    expanded_df['situation'].fillna(method='bfill', inplace=True)
    
    # 調整時間序列以符合 00:00:00 起始，並每10秒遞增
    adjusted_df = adjust_to_midnight_and_increment(expanded_df, power_df)

    # 設置 'sun' 和 'priority'
    adjusted_df = set_sun_and_priority(adjusted_df)

    # 根據 '姿態轉換(Y/N)' 的變化更新 '衛星姿態' 和 'priority'
    adjusted_df = set_when_meet_Y(adjusted_df)


    adjusted_df = update_power_from_input1(adjusted_df, power_df)
    # 將處理過的 adjusted_df 寫入 temp.xlsx
    
    adjusted_df = clean_and_interpolate_power(adjusted_df )

    adjusted_df.to_excel('temp.xlsx', index=False)

    # 將資料存儲在字典中
    data = {
        'power_data': power_df,
        'transition_data': adjusted_df
    }

    # 輸出到 Excel 文件
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        # 將每個 DataFrame 寫入到不同的工作表
        data['power_data'].to_excel(writer, sheet_name='Power Data', index=False)
        data['transition_data'].to_excel(writer, sheet_name='Transition Data', index=False)

def adjust_to_midnight_and_increment(df, power_df):
    # 計算每個時間與 00:00:00 的差距
    df['time_diff'] = (df['time'] - df['time'].dt.normalize()).abs()

    # 找到最接近 00:00:00 的時間點
    closest_to_midnight_idx = df['time_diff'].idxmin()

    # 刪除該時間點之前的所有資料
    df = df.loc[closest_to_midnight_idx:].reset_index(drop=True)

    # 將第一筆資料的時間改為 00:00:00
    df.at[0, 'time'] = df.at[0, 'time'].normalize()

    # 為後續每筆資料設置時間為前一筆資料加上10秒
    df['time'] = df['time'].iloc[0] + pd.to_timedelta(df.index * 10, unit='s')

    # 移除 time_diff 欄位
    df.drop(columns=['time_diff'], inplace=True)
    
    # 新增 '姿態轉換(Y/N)' 和 '姿態轉換時的發電量' 欄位
    df['姿態轉換(Y/N)'] = ''
    df['姿態轉換時的發電量'] = ''
    df['衛星姿態'] = ''  # 新增 '衛星姿態' 欄位
    df['sun'] = 1  # 新增 'sun' 欄位，預設為 亮 (1)

    # 設置 '姿態轉換(Y/N)' 和 '姿態轉換時的發電量' 欄位的值
    for i in range(len(df) - 1):
        if df['situation'].iloc[i] != df['situation'].iloc[i + 1]:
            df.at[i + 1, '姿態轉換(Y/N)'] = 'Y'
        
        # 找到對應時間點的發電量
        time_for_power = df['time'].iloc[i]
        if time_for_power in power_df['time'].values:
            power_value = power_df.loc[power_df['time'] == time_for_power, '姿態轉換時的發電量']
            df.at[i + 1, '姿態轉換時的發電量'] = power_value.values[0] if not power_value.empty else None

    return df

def set_sun_and_priority(df):
    # 優先級順序
    priority = {
        'Target pointing': 1,
        'Nadir pointing': 2,
        'SUN pointing': 3,
        'LVLH': 4
    }
    
    # 設置 'sun'
    eclipse_active = False
    for i, row in df.iterrows():
        situation = row['situation']
        
        # 根據 situation 設定 'sun'
        if situation == 'eclipse entry':
            df.at[i, 'sun'] = 0  # 設為暗
            eclipse_active = True
        elif situation == 'eclipse exit':
            df.at[i, 'sun'] = 1  # 設為亮
            eclipse_active = False
        
        # 根據 situation 設定 '衛星姿態'
        if situation in ['F1 start', 'F2 start', 'F3 start', 'F4 start']:
            df.at[i, '衛星姿態'] = 'Nadir pointing'
        elif situation in ['NCU start', 'Svalbard start']:
            df.at[i, '衛星姿態'] = 'Target pointing'
        elif situation == 'eclipse exit':
            df.at[i, '衛星姿態'] = 'SUN pointing'
        elif eclipse_active:
            df.at[i, '衛星姿態'] = 'LVLH'
    
    for i, row in df.iterrows():
        sun = row['sun']
        sattype = row['衛星姿態']
        if sattype =="":
            if sun == 1:
                df.at[i, '衛星姿態'] = 'SUN pointing'
            elif sun == 0:
                df.at[i, '衛星姿態'] = 'LVLH'
    
    # 根據優先級設定 'priority'
    df['priority'] = df['衛星姿態'].map(priority)
    
    return df


def set_when_meet_Y(df):
    # 用來跟蹤已經處理過的行
    processed_rows = set()

    for i in range(len(df)):
        if df.at[i, '姿態轉換(Y/N)'] == 'Y' and i not in processed_rows:
            if i > 0:
                # 檢查前一行的 priority
                prev_priority = df.at[i - 1, 'priority']
                curr_priority = df.at[i, 'priority']
                
                # 如果優先級變化，更新前後 10 行的 '姿態轉換(Y/N)'
                if curr_priority ==prev_priority:
                    # 往上更新，範圍往上移一格
                    start_idx = max(0, i - 11)  # 注意這裡的 -11，保證範圍向上一格
                    end_idx = i - 1  # 更新範圍往上一格
                    df.loc[start_idx:end_idx, '姿態轉換(Y/N)'] = 'Y' 
                    # 將處理過的行添加到集合中
                    processed_rows.update(range(start_idx, end_idx))
                elif curr_priority < prev_priority:
                    # 往下更新
                    start_idx = i
                    end_idx = min(len(df), i + 9)  # 注意這裡的 +9，保證範圍往下一格
                    df.loc[start_idx:end_idx, '姿態轉換(Y/N)'] = 'Y'
                    # 將處理過的行添加到集合中
                    processed_rows.update(range(start_idx, end_idx))
    
    return df





def update_power_from_input1(df, power_df):
    for i, row in df.iterrows():
        if row['姿態轉換(Y/N)'] == 'Y':
            
            current_time =row['time'].time()
            #print(current_time)
            power_value = power_df.loc[power_df['time'] == current_time, 'Power (W) '].values[0]
            #print(power_value)
            df.at[i, '姿態轉換時的發電量'] = power_value
            
    print(type(power_df['time'].iloc[0]))      # 檢查DF中的time型別
    print(type(current_time)) # 檢查power_df中的time型別

    
    return df

import numpy as np

def clean_and_interpolate_power(df):
    # 首先找到所有 'Y' 的位置
    y_indices = df.index[df['姿態轉換(Y/N)'] == 'Y'].tolist()

    # 用來跟蹤已經處理過的行
    processed_rows = set()

    for i in y_indices:
        # 確認當前 'Y' 是不是孤立的
        if (i - 1 not in y_indices and i + 1 not in y_indices):
            # 如果是孤立的 'Y'，清除它
            df.at[i, '姿態轉換(Y/N)'] = ''
            continue
        
        if i in processed_rows:
            continue

        # 處理連續的 'Y'
        start_idx = i
        while start_idx >=0 and df.at[start_idx - 1, '姿態轉換(Y/N)'] == 'Y':
            start_idx -= 1
        
        end_idx = i
        while end_idx < len(df) - 1 and df.at[end_idx + 1, '姿態轉換(Y/N)'] == 'Y':
            end_idx += 1
        
        # 如果連續 'Y' 的數量是 10，進行內插處理
        if end_idx - start_idx + 1 == 10:
            # 取出發電量進行內插
            start_power = df.at[start_idx, '姿態轉換時的發電量']
            end_power = df.at[end_idx, '姿態轉換時的發電量']
            interpolated_powers = np.linspace(start_power, end_power, 10)

            # 將內插結果回填
            df.loc[start_idx:end_idx, '姿態轉換時的發電量'] = interpolated_powers

            # 將處理過的行添加到集合中
            processed_rows.update(range(start_idx, end_idx + 1))

    return df


# Example usage 
power_file = 'input1.xlsx'
transition_file = 'input2.xlsx'
output_file = 'output.xlsx'
process_satellite_data(power_file, transition_file, output_file)

