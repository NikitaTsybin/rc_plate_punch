from math import pi, ceil, floor
import numpy as np


def generate_contours (b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT):
    #Генерация расчетного контура
    contours = []
    sides = []
    if is_cL:
        contour_x = [round(-h0/2, 2), round(-h0/2, 2)]
        contour_y = [round(-h0/2, 2), round(h+h0/2, 2)]
        if not is_cB: contour_y[0] = round(-cB, 2)
        if not is_cT: contour_y[1] = round(h+cT, 2)
        contours.append([contour_x, contour_y])
        sides.append('левый')
    if is_cR:
        contour_x = [b+h0/2, b+h0/2]
        contour_y = [-h0/2, h+h0/2]
        if not is_cB: contour_y[0] = -cB
        if not is_cT: contour_y[1] = h+cT
        contours.append([contour_x, contour_y])
        sides.append('правый')
    if is_cB:
        contour_x = [-h0/2, b+h0/2]
        contour_y = [-h0/2, -h0/2]
        if not is_cL: contour_x[0] = -cL
        if not is_cR: contour_x[1] = b+cR
        contours.append([contour_x, contour_y])
        sides.append('нижний')
    if is_cT:
        contour_x = [-h0/2, b+h0/2]
        contour_y = [h+h0/2, h+h0/2]
        if not is_cL: contour_x[0] = -cL
        if not is_cR: contour_x[1] = b+cR
        contours.append([contour_x, contour_y])
        sides.append('верхний')
        
    return {'contours': contours, 'sides': sides}

def generate_bounds (b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT):
    #Генерация границ
    add = 0.5*h0
    bounds = []
    if not is_cL:
        contour_x = [-cL, -cL]
        contour_y = [-add, h+add]
        if not is_cB: contour_y[0] = -cB
        if not is_cT: contour_y[1] = h+cT
        bounds.append([contour_x, contour_y])
    if not is_cR:
        contour_x = [b+cR, b+cR]
        contour_y = [-add, h+add]
        if not is_cB: contour_y[0] = -cB
        if not is_cT: contour_y[1] = h+cT
        bounds.append([contour_x, contour_y])
    if not is_cB:
        contour_x = [-add, b+add]
        contour_y = [-cB, -cB]
        if not is_cL: contour_x[0] = -cL
        if not is_cR: contour_x[1] = b+cR
        bounds.append([contour_x, contour_y])
    if not is_cT:
        contour_x = [-add, b+add]
        contour_y = [h+cT, h+cT]
        if not is_cL: contour_x[0] = -cL
        if not is_cR: contour_x[1] = b+cR
        bounds.append([contour_x, contour_y])
    return {'bounds': bounds}

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

def solve_forces (F0, Mxloc, Myloc, deltaMx, deltaMy, F_dir, delta_M_exc, M_abs, xF, yF, xc, yc, q, A):
    Fq = round(q*A, 1) #Разгружающая сила
    F = round(F0 - Fq, 1) #Корректируем силу с учетом разгружающей нагрузки
    ex, ey = round(xc - xF, 2), round(yc - yF, 2) #Вычисляем эксцентриситеты продольной силы
    Mxexc = round(F*ex/100, 2) #Момент в направлении x от эксцентриситета
    Myexc = round(F*ey/100, 2) #Момент в направлении y от эксцентриситета
    if F_dir == 'вниз': #Если продольная сила направлена вниз, то меняем знак момента от эксцентриситета
        Mxexc, Myexc = -Mxexc, -Myexc
    if M_abs: #Если знак момента от эксцентриситета не учитывается, то все считаем по абссолютным величинам
        Mxexc = abs(Mxexc)
        Myexc = abs(Myexc)
        Mxloc = abs(Mxloc)
        Myloc = abs(Myloc)
    if delta_M_exc: #Если понижающий коэффициент учитывается в моментах от эксцентриситата
        Mxexc = round(Mxexc*deltaMx, 2)
        Myexc = round(Myexc*deltaMy, 2)
    Mx = abs(round(Mxloc*deltaMx + Mxexc, 2)) #Расчетное значение момента в направлении x
    My = abs(round(Myloc*deltaMy + Myexc, 2)) #Расчетное значение момента в направлении y
    return {'F': F, 'Fq': Fq, 'ex': ex, 'ey': ey, 'Mxexc': Mxexc, 'Myexc': Myexc, 'Mx': Mx, 'My': My}

def solve_fb_ult (Rbt, h0, u, Wbx, Wby):
    Fbult = round(Rbt*h0*u, 1)
    Mbxult = round(Rbt*h0*Wbx, 2)
    Mbyult = round(Rbt*h0*Wby, 2)
    return {'Fbult': Fbult, 'Mbxult': Mbxult, 'Mbyult': Mbyult}

def solve_fsw_ult (qsw, u, Wswx, Wswy, Fbult, Mbxult, Mbyult):
    Fsw_code, Mswx_code, Mswy_code = 0, 0, 0 #0 - по расчету, 1 - ограничение Fb, 2 - ограничение 0.25*Fb
   
   #Расчет предельной силы, воспринимаемой арматурой
    Fswult0 = round(0.8*qsw*u, 1) #Начальное значение
    if 0.25*Fbult <= Fswult0 <= Fbult: #Если укладываемся в требования по предельным силам в поперечной арматуре
        Fswult = Fswult0
        Fsw_code = 0
    if Fswult0 > Fbult: #Если сила в арматуре превышает силу в бетоне
        Fswult = Fbult
        Fsw_code = 1
    if Fswult0 < 0.25*Fbult: #Если сила в арматуре меньше 0.25*Fbult
        Fswult = 0.0
        Fsw_code = 2

    #Расчет предельного момента в направлении оси х, воспринимаемог арматурой
    Mswxult0 = round(0.8*qsw*Wswx, 2) #Начальное значение
    if Fsw_code == 2: #Если поперечная арматура не учитывается в расчте
        Mswxult = 0.00
        Mswx_code = 2
    else: #В противном случае сравниваем с предельным, воспринимаемым бетоном
        if Mswxult0>Mbxult: #Если превышает, то ограничиваем усилием в бетоне
            Mswxult = Mbxult
            Mswx_code = 1
        else: #В противном случае не ограничиваем
            Mswxult = Mswxult0
            Mswx_code = 0
    
    #Расчет предельного момента в направлении оси у, воспринимаемого арматурой
    Mswyult0 = round(0.8*qsw*Wswy, 2) #Начальное значение
    if Fsw_code == 2: #Если поперечная арматура не учитывается в расчте
        Mswyult = 0.00
        Mswy_code = 2
    else: #В противном случае сравниваем с предельным, воспринимаемым бетоном
        if Mswyult0>Mbyult: #Если превышает, то ограничиваем усилием в бетоне
            Mswyult = Mbyult
            Mswy_code = 1
        else: #В противном случае не ограничиваем
            Mswyult = Mswyult0
            Mswy_code = 0
    
    return {'Fswult0': Fswult0, 'Fswult': Fswult, 'Mswxult0': Mswxult0, 'Mswxult': Mswxult, 'Mswyult0': Mswyult0, 'Mswyult': Mswyult,
            'Fsw_code': Fsw_code, 'Mswx_code': Mswx_code, 'Mswy_code': Mswy_code}

def solve_kb_coeff (F, Fbult, Mx, Mbxult, My, Mbyult):
    kbM_code = 0 #0 - моменты не ограничены, 1 - ограничены
    kbF = round(F/Fbult, 3)
    kbM0 = round(Mx/Mbxult + My/Mbyult, 3)
    if kbM0>0.5*kbF:
        kbM = round(0.5*kbF, 3)
        kbM_code = 1
    else: kbM = kbM0
    return {'kbF': kbF, 'kbM0': kbM0, 'kbM': kbM, 'kbM_code': kbM_code}

def solve_k_coeff (F, Fbult, Fswult, Mx, Mbxult, Mswxult, My, Mbyult, Mswyult):
    kM_code = 0 #0 - моменты не ограничены, 1 - ограничены
    kF = round(F/(Fbult+Fswult), 3)
    kM0 = round(Mx/(Mbxult+Mswxult) + My/(Mbyult+Mswyult), 3)
    if kM0>0.5*kF:
        kM = round(0.5*kF, 3)
        kM_code = 1
    else: kM = kM0
    return {'kF': kF, 'kM0': kM0, 'kM': kM, 'kM_code': kM_code}

def find_contour_geometry (V, M, Rbt, Rsw, h0, F, Mxloc, Myloc, deltaMx,  deltaMy, xcol, ycol, M_abs, delta_M_exc, F_dir, is_sw, qsw, sw_mode, sw, nsw):
    #V - массив координат линий контура [   [[x1,x2], [y1,y2]],    [[x1,x2], [y1,y2]], ...   ]
    #M - вектор масс линий
    #Объявляем нулевыми суммарные длину и моменты инерции
    V = np.array(V)
    M = np.array(M)
    Sx_arr, Sy_arr = [], []
    Ix_arr, Iy_arr = [], []
    Ix0_arr, Iy0_arr = [], []
    #print(V1)
    Lsum, Sx, Sy, Ix, Iy = 0, 0, 0, 0, 0
    Fult = 0
    j = 0
    for i in V:
        #Извлекаем координаты начала и конца i-го участка
        x1, x2 = i[0]
        y1, y2 = i[1]
        #Вычисляем длину i-го участка
        L_i = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
        L_i = round(L_i,2)
        #Добавляем его длину в суммарную
        Lsum = Lsum + L_i
        #Вычисляем координаты центра i-го участка
        center_i = ((x2 - x1)/2 + x1, (y2 - y1)/2 + y1)
        #Вычисляем статические моменты i-го участка
        Sx_i = round(L_i*center_i[0], 1)
        Sx_arr.append(Sx_i)
        Sy_i = round(L_i*center_i[1], 1)
        Sy_arr.append(Sy_i)
        #Добавляем их в суммарные
        Sx = Sx + Sx_i
        Sy = Sy + Sy_i
        j += 1
    Sx, Sy = round(Sx, 1), round(Sy, 1)
    #Вычисляем координаты центра тяжести всего контура
    xc, yc = round(Sx/Lsum, 2), round(Sy/Lsum, 2)
    ex, ey = round(xc - xcol, 2), round(yc - ycol, 2)
    #Расчет характеристик "без масс"
    #Присваеваем максимум и минимум координат
    xmin0, xmax0 = round(V[:,0].min(), 2), round(V[:,0].max(), 2)
    ymin0, ymax0 = round(V[:,1].min(), 2), round(V[:,1].max(), 2)
    for i in V:
        #Вычисляем координаты минимума и максимума относительно геометрического центра тяжести
        xL, xR = round(xmin0 - xc, 2), round(xmax0 - xc, 2)
        yB, yT = round(ymin0 - yc, 2), round(ymax0 - yc, 2)
        #Извлекаем координаты начала и конца i-го участка
        #и пересчитываем их относительно центра тяжести
        x1, x2 = i[0] - xc
        y1, y2 = i[1] - yc
        #Вычисляем центр тяжести
        x0 = (x2 - x1)/2 + x1
        y0 = (y2 - y1)/2 + y1
        #Вычисляем длину i-го участка
        L_i = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
        #Длина i-го участка вдоль оси x и y
        Lx_i = ((x1 - x2)**2)**0.5
        Ly_i = ((y1 - y2)**2)**0.5
        #Собственные моменты инерции
        Ix0_i = round(Lx_i**3/12, 1)
        Iy0_i = round(Ly_i**3/12, 1)
        Ix0_arr.append(Ix0_i)
        Iy0_arr.append(Iy0_i)
        #Моменты инерции относительно центра тяжести
        Ix_i = round(Ix0_i + L_i*x0**2, 1)
        Iy_i = round(Iy0_i + L_i*y0**2, 1)
        Ix_arr.append(Ix_i)
        Iy_arr.append(Iy_i)
        Ix = Ix + Ix_i
        Iy = Iy + Iy_i
    Ix, Iy = round(Ix,1), round(Iy,1)
    Wxl, Wxr = Ix/abs(xL), Ix/xR
    Wxmin = round(min(Wxl, Wxr), 1)
    Wyb, Wyt = Iy/abs(yB), Iy/yT
    Wymin = round(min(Wyb, Wyt), 1)
    Mxexc0 = round(F*ex/100, 2)
    Myexc0 = round(F*ey/100, 2)
    if F_dir == 'вниз':
        Mxexc0, Myexc0 = -Mxexc0, -Myexc0
    Mxexc, Myexc = Mxexc0, Myexc0
    if M_abs:
        Mxexc = abs(Mxexc)
        Myexc = abs(Myexc)
        Mxloc = abs(Mxloc)
        Myloc = abs(Myloc)
    if delta_M_exc:
        Mxexc = Mxexc*deltaMx
        Myexc = Myexc*deltaMy
    Mx = round(Mxloc*deltaMx + Mxexc,2)
    My = round(Myloc*deltaMy + Myexc,2)
    Mx, My = abs(Mx), abs(My)
    #Предельная сила, воспринимаемая бетоном
    Fbult = round(Lsum*Rbt*h0,1)
    Mbxult = round(Wxmin*h0*Rbt/100, 2)
    Mbyult = round(Wymin*h0*Rbt/100, 2)
    Fswult_check0 = round(Lsum*0.8*qsw,1)
    Mswxult_check0 = round(Wxmin*0.8*qsw/100, 2)
    Mswyult_check0 = round(Wymin*0.8*qsw/100, 2)
    if Fswult_check0 > Fbult:
        Fswult_check = Fbult
        Mswxult_check = Mbxult
        Mswyult_check = Mbyult
    if Fswult_check0 < 0.25*Fbult:
        Fswult_check = 0.0
        Mswxult_check = 0.0
        Mswyult_check = 0.0
    if  0.25*Fbult <= Fswult_check0 <= Fbult:
        Fswult_check = Fswult_check0
        Mswxult_check = Mswxult_check0
        Mswyult_check = Mswyult_check0
    #Коэффициент использования по продольной силе
    kbF= round(F/Fbult, 3)
    
    kF_check= round(F/(Fbult+Fswult_check), 3)
    kbM0 = Mx/Mbxult + My/Mbyult
    kbM0 = round(kbM0, 3)
    kbM = round(min(kbM0, kbF/2), 3)

    kM_check = Mx/(Mbxult+Mswxult_check) + My/(Mbyult+Mswyult_check)
    kM0_check = round(kM_check, 3)
    kM_check = round(min(kM0_check, kF_check/2), 3)
    kb = round(kbF + kbM, 3)
   
    kbF0= F/Fbult
    kbM00 = Mx/(Mbxult) + My/(Mbyult)
    kbM00 = min(kbM00, kbF0/2)
    kb0 = kbF0 + kbM00
    sw_Asw_min = Rbt*h0*(kb0-1)/(0.8*Rsw)
    sw_Asw_max = Rbt*h0/(0.8*Rsw)
    if sw_Asw_min > 0:
        dsw_min = (sw_Asw_min*sw*4/pi/nsw)**0.5*10.0
    else: dsw_min = 0
    dsw_max = (sw_Asw_max*sw*4/pi/nsw)**0.5*10.0
    dsw_min = round(dsw_min,2)
    dsw_max = round(dsw_max,2)
    sw_Asw_min = round(sw_Asw_min, 4)
    sw_Asw_max = round(sw_Asw_max, 4)
    
    k_check = round(kF_check + kM_check, 3)
    xmax = max(abs(xL),xR)
    ymax = max(abs(yB),yT)
    return {'Lsum': Lsum, 'xc': xc, 'yc': yc, 'ex': ex, 'ey': ey,
            'xL': xL, 'xR': xR, 'yB': yB, 'yT': yT,
            'xmax': xmax, 'ymax': ymax,
            'Ix': Ix, 'Iy': Iy, 
            'Sx_arr': Sx_arr, 'Sy_arr': Sy_arr,
            'Ix0_arr': Ix0_arr, 'Iy0_arr': Iy0_arr,
            'Ix_arr': Ix_arr, 'Iy_arr': Iy_arr,
            'Sx': Sx, 'Sy': Sy,
            'Wxmin': Wxmin, 'Wymin': Wymin,
            'Mxexc': Mxexc, 'Myexc': Myexc,
            'Mxexc0': Mxexc0, 'Myexc0': Myexc0,
            'Mxloc': Mxloc, 'Myloc': Myloc,
            'Mx': Mx, 'My': My,
            'Fbult': Fbult, 'Mbxult': Mbxult, 'Mbyult': Mbyult,
            'Fswult_check0': Fswult_check0, 'Mswxult_check0': Mswxult_check0, 'Mswyult_check0': Mswyult_check0,
            'Fswult_check': Fswult_check, 'Mswxult_check': Mswxult_check, 'Mswyult_check': Mswyult_check,
            'kbF': kbF, 'kbM0': kbM0, 'kbM': kbM, 'kb': kb,
            'kF_check': kF_check, 'kM0_check': kM0_check, 'kM_check': kM_check, 'k_check': k_check,
            'sw_Asw_min': sw_Asw_min, 'dsw_min': dsw_min,
            'sw_Asw_max': sw_Asw_max, 'dsw_max': dsw_max
            }