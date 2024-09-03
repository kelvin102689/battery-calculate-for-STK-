#coding=Big5
def interpolate_values(value1, value2):
    diff = value2 - value1
    interpolated_values = []

    for i in range(20):
        interpolated = value1 + (diff / 19) * i
        rounded_interpolated = round(interpolated, 3)
        interpolated_values.append(rounded_interpolated)

    return interpolated_values

if __name__ == "__main__":
    while True:
        try:
            float1 = float(input("請輸入第一個浮點數值（或輸入'exit'結束）："))
            if float1 == "exit":
                break
            
            float2 = float(input("請輸入第二個浮點數值："))
            
            interpolated = interpolate_values(float1, float2)
            for value in interpolated:
                print(value)
        
        except ValueError:
            print("輸入無效，請確保輸入的是浮點數。")
