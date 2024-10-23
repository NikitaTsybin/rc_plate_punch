from math import pi, ceil, floor
import numpy as np

def solve_sw_min(kb, h0, Rbt, Rsw, Asw, dx, dy):
    sw_min_code = 0 #0 - по расчету, 1 - конструктивные требования
    if kb<1.25: kb = 1.25 #Проверяем условияе Fswult>=0.25*Fbult
    sw_min = 0.8*Rsw*Asw/(Rbt*h0*(kb-1)) #Вычисляем минимальный шаг
    if sw_min>min(dx/4, dy/4): #Не менее 5 рядов (4 интервала) на каждый участок контура
        sw_min = min(sw_min, dx/4, dy/4) 
        sw_min_code = 1
    #Округляем до 0.5см в большую сторону
    sw_min =round(floor(sw_min/0.5)*0.5,1)
    return sw_min, sw_min_code

def solve_geom_props (V):
    #V - массив координат линий контура [ [[x1,x2], [y1,y2]],    [[x1,x2], [y1,y2]], ...   ]
    V = np.array(V)
    #Максимум и минимум координат относительно начальной системы
    xmin0, xmax0 = round(V[:,0].min(), 2), round(V[:,0].max(), 2)
    ymin0, ymax0 = round(V[:,1].min(), 2), round(V[:,1].max(), 2)
    #Размеры контура
    dx, dy = round(xmax0 - xmin0, 2), round(ymax0 - ymin0, 2)
    L_arr, Lx_arr, Ly_arr = [], [], [] #Массивы длин участков и длин их проекций
    cx0_arr, cy0_arr = [], [] #Массивы центров тяжести относительно начальной системы
    cx_arr, cy_arr = [], [] #Массивы центров тяжести относительно центра контура
    Sx0_arr, Sy0_arr = [], [] #Массивы статических моментов инерции относительно начальной системы
    Ix0_arr, Iy0_arr = [], [] #Массивы собственных моментов инерции
    Ix_arr, Iy_arr = [], [] #Массивы моментов инерции
    u, Sx0, Sy0, Ix, Iy = 0, 0, 0, 0, 0
    j = 0
    for i in V:
        #Извлекаем координаты начала и конца i-го участка
        x1, x2 = i[0]
        y1, y2 = i[1]
        #Вычисляем длину i-го участка
        L_i = round(((x1 - x2)**2 + (y1 - y2)**2)**0.5, 2)
        L_arr.append(L_i)
        Lx_i = round(abs(x1 - x2), 2)
        Lx_arr.append(Lx_i)
        Ly_i = round(abs(y1 - y2), 2)
        Ly_arr.append(Ly_i)
        #Добавляем его длину в суммарную
        u += L_i
        #Вычисляем координаты центра i-го участка
        cx0_i = round((x2 - x1)/2 + x1,2)
        cy0_i = round((y2 - y1)/2 + y1,2)
        cx0_arr.append(cx0_i)
        cy0_arr.append(cy0_i)
        #Вычисляем статические моменты i-го участка
        Sx0_i = round(L_i*cx0_i,1)
        Sy0_i = round(L_i*cy0_i,1)
        Sx0_arr.append(Sx0_i)
        Sy0_arr.append(Sy0_i)     
        #Добавляем их в суммарные
        Sx0 += Sx0_i
        Sy0 += Sy0_i
        j += 1
    Sx0, Sy0 = round(Sx0, 1), round(Sy0, 1)
    #Вычисляем координаты центра тяжести всего контура
    xc, yc = round(Sx0/u, 2), round(Sy0/u, 2)
    #Вычисляем координаты минимума и максимума относительно геометрического центра тяжести
    xL, xR = round(xmin0 - xc, 2), round(xmax0 - xc, 2)
    yB, yT = round(ymin0 - yc, 2), round(ymax0 - yc, 2)
    for i in range(len(V)):
        #Извлекаем координаты начала и конца i-го участка
        #и пересчитываем их относительно центра тяжести
        x1, x2 = V[i, 0] - xc
        y1, y2 = V[i, 1] - yc
        #Вычисляем центр тяжести
        cx_i = round((x2 - x1)/2 + x1, 2)
        cy_i = round((y2 - y1)/2 + y1, 2)
        cx_arr.append(cx_i)
        cy_arr.append(cy_i)
        #Собственные моменты инерции
        Ix0_i = round(Lx_arr[i]**3/12, 1)
        Iy0_i = round(Ly_arr[i]**3/12, 1)
        Ix0_arr.append(Ix0_i)
        Iy0_arr.append(Iy0_i)
        #Моменты инерции относительно центра тяжести
        Ix_i = round(Ix0_i + L_arr[i]*cx_i**2, 1)
        Iy_i = round(Iy0_i + L_arr[i]*cy_i**2, 1)
        Ix_arr.append(Ix_i)
        Iy_arr.append(Iy_i)
        Ix = Ix + Ix_i
        Iy = Iy + Iy_i
    Ix, Iy = round(Ix, 1), round(Iy, 1)
    WxL, WxR = round(Ix/abs(xL), 1), round(Ix/xR, 1)
    Wx = min(WxL, WxR)
    WyB, WyT = round(Iy/abs(yB), 1), round(Iy/yT, 1)
    Wy = min(WyB, WyT)
    xmax, ymax = max(abs(xL),xR), max(abs(yB),yT)
    return {'u': u, 'xc': xc, 'yc': yc, 'Ix': Ix, 'Iy': Iy, 'Wx': Wx, 'Wy': Wy,
            'WxL': WxL, 'WxR': WxR, 'WyB': WyB, 'WyT': WyT,
            'xL': xL, 'xR': xR, 'yB': yB, 'yT': yT,
            'xmax': xmax, 'ymax': ymax,
            'dx': dx, 'dy': dy,
            'Sx0': Sx0, 'Sy0': Sy0,
            'Sx0_arr': Sx0_arr, 'Sy0_arr': Sy0_arr,
            'Ix0_arr': Ix0_arr, 'Iy0_arr': Iy0_arr,
            'Ix_arr': Ix_arr, 'Iy_arr': Iy_arr,
            'L_arr': L_arr, 'Lx_arr': Lx_arr, 'Ly_arr': Ly_arr,
            'cx0_arr': cx0_arr, 'cy0_arr': cy0_arr,
            'cx_arr': cx_arr, 'cy_arr': cy_arr
            }

