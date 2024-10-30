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
    kb_sw_code = 0
    if kb<1.25:
        kb = 1.252 #Проверяем условияе Fswult>=0.25*Fbult
        kb_sw_code = 1
    sw_min = 0.8*Rsw*Asw/(Rbt*h0*(kb-1))*0.999 #Вычисляем минимальный шаг
    sw_min0 = round(sw_min, 1)
    #0.99 здесь чтобы не отлавливать пограничные значения. Иногда, после всех округлений использование составляло 1.001
    if sw_min>min(dx/4, dy/4): #Не менее 5 рядов (4 интервала) на каждый участок контура
        sw_min = min(sw_min, dx/4, dy/4) 
        sw_min_code = 1
    #Округляем до 0.5см в меньшую сторону
    sw_min = round(floor(sw_min/0.1)*0.1,1)
    return sw_min, sw_min_code, kb_sw_code, sw_min0

def solve_geom_props (V):
    #V - массив координат линий контура [ [[x1,x2], [y1,y2]],    [[x1,x2], [y1,y2]], ...   ]
    V = np.array(V)
    #Максимум и минимум координат относительно начальной системы
    xmin0, xmax0 = round(V[:,0].min(), 2), round(V[:,0].max(), 2)
    ymin0, ymax0 = round(V[:,1].min(), 2), round(V[:,1].max(), 2)
    #Размеры контура
    dx, dy = round(xmax0 - xmin0, 2), round(ymax0 - ymin0, 2)
    A = round(dx*dy,2)
    L_arr, Lx_arr, Ly_arr = [], [], [] #Массивы длин участков и длин их проекций
    xc0_arr, yc0_arr = [], [] #Массивы центров тяжести относительно начальной системы
    xc_arr, yc_arr = [], [] #Массивы центров тяжести относительно центра контура
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
        xc0_i = round((x2 - x1)/2 + x1,2)
        yc0_i = round((y2 - y1)/2 + y1,2)
        xc0_arr.append(xc0_i)
        yc0_arr.append(yc0_i)
        #Вычисляем статические моменты i-го участка
        Sx0_i = round(L_i*xc0_i,1)
        Sy0_i = round(L_i*yc0_i,1)
        Sx0_arr.append(Sx0_i)
        Sy0_arr.append(Sy0_i)     
        #Добавляем их в суммарные
        Sx0 += Sx0_i
        Sy0 += Sy0_i
        j += 1
    Sx0, Sy0 = round(Sx0, 1), round(Sy0, 1)
    u = round(u, 2)
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
        xc_i = round((x2 - x1)/2 + x1, 2)
        yc_i = round((y2 - y1)/2 + y1, 2)
        xc_arr.append(xc_i)
        yc_arr.append(yc_i)
        #Собственные моменты инерции
        Ix0_i = round(Lx_arr[i]**3/12, 1)
        Iy0_i = round(Ly_arr[i]**3/12, 1)
        Ix0_arr.append(Ix0_i)
        Iy0_arr.append(Iy0_i)
        #Моменты инерции относительно центра тяжести
        Ix_i = round(Ix0_i + L_arr[i]*xc_i**2, 1)
        Iy_i = round(Iy0_i + L_arr[i]*yc_i**2, 1)
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
    xmin, ymin = min(xL,xR), min(yB,yT)
    return {'u': u, 'xc': xc, 'yc': yc, 'Ix': Ix, 'Iy': Iy, 'Wx': Wx, 'Wy': Wy,
            'WxL': WxL, 'WxR': WxR, 'WyB': WyB, 'WyT': WyT,
            'xL': xL, 'xR': xR, 'yB': yB, 'yT': yT,
            'xmax': xmax, 'ymax': ymax,
            'xmin': xmin, 'ymin': ymin,
            'xmax0': xmax0, 'ymax0': ymax0,
            'xmin0': xmin0, 'ymin0': ymin0,
            'dx': dx, 'dy': dy, 'A': A,
            'Sx0': Sx0, 'Sy0': Sy0,
            'Sx0_arr': Sx0_arr, 'Sy0_arr': Sy0_arr,
            'Ix0_arr': Ix0_arr, 'Iy0_arr': Iy0_arr,
            'Ix_arr': Ix_arr, 'Iy_arr': Iy_arr,
            'L_arr': L_arr, 'Lx_arr': Lx_arr, 'Ly_arr': Ly_arr,
            'xc0_arr': xc0_arr, 'yc0_arr': yc0_arr,
            'xc_arr': xc_arr, 'yc_arr': yc_arr
            }

def solve_forces (F0, Mxloc, Myloc, deltaMx, deltaMy, F_dir, delta_M_exc, M_abs, xF, yF, xc, yc, q, A):
    Fq = round(floor(q*A*10)/10, 1) #Разгружающая сила
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
    Fbult = round(Rbt*h0*u, 1) #Предельная сила, воспринимаемая бетоном
    Mbxult = round(Rbt*h0*Wbx/100, 2) #Предельный момент в плоскости х, воспринимаемый бетоном
    Mbyult = round(Rbt*h0*Wby/100, 2) #Предельный момент в плоскости y, воспринимаемый бетоном
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
    Mswxult0 = round(0.8*qsw*Wswx/100, 2) #Начальное значение
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
    Mswyult0 = round(0.8*qsw*Wswy/100, 2) #Начальное значение
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
    kb = round(kbF + kbM, 3)
    return {'kbF': kbF, 'kbM0': kbM0, 'kbM': kbM, 'kb': kb, 'kbM_code': kbM_code}

def solve_k_coeff (F, Fbult, Fswult, Mx, Mbxult, Mswxult, My, Mbyult, Mswyult):
    kM_code = 0 #0 - моменты не ограничены, 1 - ограничены
    kF = round(F/(Fbult+Fswult), 3)
    kM0 = round(Mx/(Mbxult+Mswxult) + My/(Mbyult+Mswyult), 3)
    if kM0>0.5*kF:
        kM = round(0.5*kF, 3)
        kM_code = 1
    else: kM = kM0
    k = round(kF + kM,3)
    return {'kF': kF, 'kM0': kM0, 'kM': kM, 'k': k, 'kM_code': kM_code}

def single_solve(b, h, dh0, h0, Rbt, kh0,
                 is_cL, is_cR, is_cB, is_cT, cL, cR, cB, cT,
                 F0, Mxloc, Myloc, deltaMx, deltaMy,
                 F_dir, delta_M_exc, M_abs, xF, yF, q,
                 is_sw, Rsw, Asw, sw, sw_mode, **kwargs):
    data = {} #Словарь с результатами
    data.update({'b': b, 'h': h, 'dh0': dh0, 'h0': h0, 'kh0': kh0, 'is_cL': is_cL, 'is_cR': is_cR, 'is_cB': is_cB, 'is_cT': is_cT, 'cL': cL, 'cR': cR, 'cB': cB, 'cT': cT})
    data.update({'Rbt': Rbt, 'is_sw': is_sw, 'Asw': Asw, 'Rsw': Rsw})
    data.update({'sw_mode': sw_mode, 'sw': sw})
    data.update({'q': q, 'F0': F0, 'Mxloc': Mxloc, 'Myloc': Myloc, 'F_dir': F_dir, 'delta_M_exc': delta_M_exc, 'M_abs': M_abs})
    data.update({'deltaMx': deltaMx, 'deltaMy': deltaMy})
    data.update({'xF': xF, 'yF': yF})
    #data.update({'ctype': kwargs['ctype'], 'Rbt0': kwargs['Rbt0'], 'gammabt': kwargs['gammabt']})
    data.update(kwargs)

    #Генерация расчетного контура
    rez_contours = generate_contours(data['b'], data['h'], data['dh0'],
                                     data['cL'], data['is_cL'], data['cR'], data['is_cR'],
                                     data['cB'], data['is_cB'], data['cT'], data['is_cT'])
    data.update(rez_contours)

    #Генерация границ, при необходимости
    rez_bounds =  generate_bounds(data['b'], data['h'], data['dh0'],
                                  data['cL'], data['is_cL'], data['cR'], data['is_cR'],
                                  data['cB'], data['is_cB'], data['cT'], data['is_cT'])
    data.update(rez_bounds)

    #Расчет геометрических характеристик контура
    rez_geom_props =  solve_geom_props(data['contours'])
    data.update(rez_geom_props)

    #Расчет предельных усилий, воспринимаемых бетоном
    rez_fb_ult = solve_fb_ult(data['Rbt'], data['h0'], data['u'], data['Wx'], data['Wy'])
    data.update(rez_fb_ult)

    #Вычисление расчетных усилий
    #Вычисляем отпор
    #Генерируем контур на расстоянии h0 (основание пирамиды продавливания)
    bottom_area_contours = generate_contours(data['b'], data['h'], data['dh0']+data['h0'],
                                             data['cL'], data['is_cL'], data['cR'], data['is_cR'],
                                             data['cB'], data['is_cB'], data['cT'], data['is_cT'])
    bottom_area_bounds = generate_bounds(data['b'], data['h'], data['dh0']+data['h0'],
                                  data['cL'], data['is_cL'], data['cR'], data['is_cR'],
                                  data['cB'], data['is_cB'], data['cT'], data['is_cT'])
    #Вычисляем его характеристики
    bottom_area_contours_props = solve_geom_props(bottom_area_contours['contours'])
    #Извлекаем площадь нижнего основания пирамиды продавливания
    A = round(bottom_area_contours_props['A']/100/100,2)
    data.update({'Aq': A})
    data.update({'bottom_contours': bottom_area_contours['contours']})
    data.update({'xmin0b': bottom_area_contours_props['xmin0']})
    data.update({'xmax0b': bottom_area_contours_props['xmax0']})
    data.update({'ymin0b': bottom_area_contours_props['ymin0']})
    data.update({'ymax0b': bottom_area_contours_props['ymax0']})
    data.update({'dxb': bottom_area_contours_props['dx']})
    data.update({'dyb': bottom_area_contours_props['dy']})
    data.update({'bottom_bounds': bottom_area_bounds['bounds']})
    
    #Вычисляем расчетные усилия
    rez_forces = solve_forces(data['F0'], data['Mxloc'], data['Myloc'], data['deltaMx'], data['deltaMy'], data['F_dir'], data['delta_M_exc'], data['M_abs'], data['xF'], data['yF'], data['xc'], data['yc'], data['q'], data['Aq'])
    data.update(rez_forces)

    #Коэффициенты использования по бетону
    rez_b_coeff = solve_kb_coeff(data['F'], data['Fbult'], data['Mx'], data['Mbxult'], data['My'], data['Mbyult'])
    data.update(rez_b_coeff)

    #Проверка с арматурой
    if sw_mode == 'подбор':
        data.update({'sw_mode': 'подбор'})
        if data['kb']>1:
            #Вычисляем шаг
            sw, sw_min_code, kb_sw_code, sw_min0 = solve_sw_min(data['kb'], h0, Rbt, Rsw, Asw, data['dx'], data['dy'])
            data.update({'sw': sw, 'sw_min_code': sw_min_code, 'kb_sw_code': kb_sw_code, 'sw_min0': sw_min0})
            #Вычисляем интенсивность армирования
            qsw = round(Rsw*Asw/sw, 5)
            data.update({'qsw': qsw})
            ksw = round(0.8*qsw/Rbt/h0, 3)
            data.update({'ksw': ksw})
            #Вычисляем предельные усилия, воспринимаемые арматурой
            rez_sw_ult = solve_fsw_ult(qsw, data['u'], data['Wx'], data['Wy'], data['Fbult'], data['Mbxult'], data['Mbyult'])
            data.update(rez_sw_ult)
            #Коэффициенты использования с учетом поперечного армирования
            rez_coeff = solve_k_coeff(data['F'], data['Fbult'], data['Fswult'], data['Mx'], data['Mbxult'], data['Mswxult'], data['My'], data['Mbyult'], data['Mswyult'])
            data.update(rez_coeff)
    if sw_mode == 'проверка':
        #Вычисляем интенсивность армирования
        qsw = round(Rsw*Asw/sw, 5)
        data.update({'qsw': qsw})
        ksw = round(0.8*qsw/Rbt/h0, 3)
        data.update({'ksw': ksw})
        #Вычисляем предельные усилия, воспринимаемые арматурой
        rez_sw_ult = solve_fsw_ult(qsw, data['u'], data['Wx'], data['Wy'], data['Fbult'], data['Mbxult'], data['Mbyult'])
        data.update(rez_sw_ult)
        #Коэффициенты использования с учетом поперечного армирования
        rez_coeff = solve_k_coeff(data['F'], data['Fbult'], data['Fswult'], data['Mx'], data['Mbxult'], data['Mswxult'], data['My'], data['Mbyult'], data['Mswyult'])
        data.update(rez_coeff)

    return data


