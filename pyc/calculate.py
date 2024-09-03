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
            float1 = float(input("�п�J�Ĥ@�ӯB�I�ƭȡ]�ο�J'exit'�����^�G"))
            if float1 == "exit":
                break
            
            float2 = float(input("�п�J�ĤG�ӯB�I�ƭȡG"))
            
            interpolated = interpolate_values(float1, float2)
            for value in interpolated:
                print(value)
        
        except ValueError:
            print("��J�L�ġA�нT�O��J���O�B�I�ơC")
