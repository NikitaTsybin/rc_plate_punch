from math import pi, ceil, floor
from PIL import Image
import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
import docx
from docx import Document
from docx.shared import Pt
from docx.shared import Mm
from docx.shared import RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import typing
import latex2mathml.converter
import mathml2omml
from docx.oxml import parse_xml
import io
import os
import sys
##punch_dir = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
##+ '/pages/punch/')
##sys.path.append(punch_dir)

from punch_word_func import *
from punch_draw_func import *
from punch_text_func import *
from punch_solve_func import *

dias = [6, 8, 10, 12, 14, 16, 18, 20, 22, 25]
qsw = 0.0
qsw0 = 0.0
Rsw = 1.734
sw = 6.0
nsw = 2
center = [25.0, 50.0]
kh0 = 1.5

st.header('Расчет на продавливание плиты')


is_report = st.sidebar.toggle('Формировать отчет', value=False)

if is_report:
    is_init_help = st.sidebar.toggle('Расчетные предпосылки', value=False)
    is_geom_help = st.sidebar.toggle('Геом. характеристики подробно', value=False)
table_concretes_data = pd.read_excel('RC_data.xlsx', sheet_name="Concretes_SP63", header=[0])
table_reinf_data = pd.read_excel('RC_data.xlsx', sheet_name="Reinforcement_SP63", header=[0])
available_concretes = table_concretes_data['Class'].to_list()

init_data_help()




def solve_arm (Asw_sw, h0, Lx, Ly):
    nswmin = 1
    nswmax = round(h0/5)
    if nswmax>10: nswmax = 10
    if nswmax < 3: nswmax = 3
    nsw_arr = [round(nswmin + i) for i in range(nswmax-nswmin+1)]
    sw_min = 5
    sw_max = min(Lx/4, Ly/4)
    sw_num = 6
    sw_step = round((sw_max-sw_min)/sw_num,2)
    sw_arr = [round(sw_min + i*sw_step,1) for i in range(sw_num+1)]
    dsw_arr = [[] for i in range(len(nsw_arr))]
    for i in range(len(nsw_arr)):
        for j in range(len(sw_arr)):
            tmp = round((Asw_sw*sw_arr[j]*4/(nsw_arr[i]*pi))**0.5*10,2)
            if tmp>25: tmp = '-'
            dsw_arr[i].append(tmp)
    return nsw_arr, sw_arr, dsw_arr

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

def generate_blue_contours (b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT):
    contour = []
    cL0 = round(max(min(cL,h0), h0),1)
    cR0 = round(max(min(cR,h0), h0),1)
    cT0 = round(max(min(cT,h0), h0),1)
    cB0 = round(max(min(cB,h0), h0),1)
    contour_gamma = []
    contour_colour = []
    contour_sides = []
    contour_len = []
    contour_len_pr = []
    contour_center = []
    if is_cL:
        contour_x = [round(-cL0/2, 2), round(-cL0/2, 2)]
        contour_y = [round(-cB0/2, 2), round(h+cT0/2, 2)]
        if not is_cT: contour_y[1] = round(h+cT, 2)
        if not is_cB: contour_y[0] = round(-cB, 2)
        contour_gamma.append(round(h0/cL0,2))
        contour.append([contour_x, contour_y])
        contour_sides.append('левый')
        L = round(((contour_x[1]-contour_x[0])**2 + (contour_y[1]-contour_y[0])**2)**0.5,2)
        contour_len.append(L)
        contour_xc = round(contour_x[0],2)
        contour_yc = round(contour_y[0] + 0.5*L,2)
        contour_center.append([contour_xc, contour_yc])
        contour_len_pr.append([contour_x[1] - contour_x[0], contour_y[1] - contour_y[0]])
    if is_cR:
        contour_x = [b+cR0/2, b+cR0/2]
        contour_y = [-cB0/2, h+cT0/2]
        if not is_cT: contour_y[1] = h+cT
        if not is_cB: contour_y[0] = -cB
        contour_gamma.append(round(h0/cR0,2))
        contour.append([contour_x, contour_y])
        contour_sides.append('правый')
        L = ((contour_x[1]-contour_x[0])**2 + (contour_y[1]-contour_y[0])**2)**0.5
        contour_len.append(L)
        contour_xc = contour_x[0]
        contour_yc = contour_y[0] + 0.5*L
        contour_center.append([contour_xc, contour_yc])
        contour_len_pr.append([contour_x[1] - contour_x[0], contour_y[1] - contour_y[0]])
    if is_cB:
        contour_x = [-cL0/2, b+cR0/2]
        contour_y = [-cB0/2, -cB0/2]
        if not is_cL: contour_x[0] = -cL
        if not is_cR: contour_x[1] = b+cR
        contour_gamma.append(round(h0/cB0,2))
        contour.append([contour_x, contour_y])
        contour_sides.append('нижний')
        L = ((contour_x[1]-contour_x[0])**2 + (contour_y[1]-contour_y[0])**2)**0.5
        contour_len.append(L)
        contour_yc = contour_y[0]
        contour_xc = contour_x[0] + 0.5*L
        contour_center.append([contour_xc, contour_yc])
        contour_len_pr.append([contour_x[1] - contour_x[0], contour_y[1] - contour_y[0]])
    if is_cT:
        contour_x = [-cL0/2, b+cR0/2]
        contour_y = [h+cT0/2, h+cT0/2]
        if not is_cL: contour_x[0] = -cL
        if not is_cR: contour_x[1] = b+cR
        contour_gamma.append(round(h0/cT0,2))
        contour.append([contour_x, contour_y])
        contour_sides.append('верхний')
        L = ((contour_x[1]-contour_x[0])**2 + (contour_y[1]-contour_y[0])**2)**0.5
        contour_len.append(L)
        contour_yc = contour_y[0]
        contour_xc = contour_x[0] + 0.5*L
        contour_center.append([contour_xc, contour_yc])
        contour_len_pr.append([contour_x[1] - contour_x[0], contour_y[1] - contour_y[0]])
        
    return contour, contour_gamma, contour_sides, contour_len, contour_center, contour_len_pr

def generate_red_contours (b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT):
    add = 0.5*h0
    contour = []
    if not is_cL:
        contour_x = [-cL, -cL]
        contour_y = [-add, h+add]
        if not is_cB:
            contour_y[0] = -cB
        if not is_cT:
            contour_y[1] = h+cT
        contour.append([contour_x, contour_y])
    if not is_cR:
        contour_x = [b+cR, b+cR]
        contour_y = [-add, h+add]
        if not is_cB:
            contour_y[0] = -cB
        if not is_cT:
            contour_y[1] = h+cT
        contour.append([contour_x, contour_y])
    if not is_cB:
        contour_x = [-add, b+add]
        contour_y = [-cB, -cB]
        if not is_cL:
            contour_x[0] = -cL
        if not is_cR:
            contour_x[1] = b+cR
        contour.append([contour_x, contour_y])
    if not is_cT:
        contour_x = [-add, b+add]
        contour_y = [h+cT, h+cT]
        if not is_cL:
            contour_x[0] = -cL
        if not is_cR:
            contour_x[1] = b+cR
        contour.append([contour_x, contour_y])
    return contour

if True: #Ввод исходных данных
    cols = st.columns([1, 0.5])
    cols2_size = [1, 1, 1]
    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$b$, см')
    b = cols2[1].number_input(label='$b$, см', step=5.0, format="%.1f", value=20.0, min_value=1.0, max_value=500.0, label_visibility="collapsed")
    b = round(b,2)

    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$h$, см')
    h = cols2[1].number_input(label='$h$, см', step=5.0, format="%.1f", value=40.0, min_value=1.0, max_value=500.0, label_visibility="collapsed")
    h = round(h,2)

    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$h_0$, см')
    h0 = cols2[1].number_input(label='$h_0$, см', step=5.0, format="%.1f", value=20.0, min_value=1.0, max_value=500.0, label_visibility="collapsed")
    h0 = round(h0,2)

    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$c_L$, см')
    is_cL = cols2[2].toggle('Контур_слева', value=True, label_visibility="collapsed")
    cL = cols2[1].number_input(label='$c_L$, см', step=5.0, format="%.1f", value=0.0, disabled=is_cL, min_value=0.0, max_value=500.0, label_visibility="collapsed")
    cL = round(cL,2)


    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$c_R$, см')
    is_cR = cols2[2].toggle('Контур_справа', value=True, label_visibility="collapsed")
    cR = cols2[1].number_input(label='$c_R$, см', step=5.0, format="%.1f", value=0.0, disabled=is_cR, min_value=0.0, max_value=500.0, label_visibility="collapsed")
    cR = round(cR,2)


    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$c_B$, см')
    is_cB = cols2[2].toggle('Контур_снизу', value=True, label_visibility="collapsed")
    cB = cols2[1].number_input(label='$c_B$, см', step=5.0, format="%.1f", value=0.0, disabled=is_cB, min_value=0.0, max_value=500.0, label_visibility="collapsed")
    cB = round(cB,2)


    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$c_T$, см')
    is_cT = cols2[2].toggle('Контур_сверху', value=True, label_visibility="collapsed")
    cT = cols2[1].number_input(label='$c_T$, см', step=5.0, format="%.1f", value=0.0, disabled=is_cT, min_value=0.0, max_value=500.0, label_visibility="collapsed")
    cT = round(cT,2)

    cols2 = st.columns([1,0.6,0.6,0.7,0.7,0.7,0.5,0.5])
    ctype = cols2[0].selectbox(label='Бетон', options=available_concretes, index=5, label_visibility="visible")
    selected_concrete_data = table_concretes_data.loc[table_concretes_data['Class'] == ctype]
    selected_concrete_data = selected_concrete_data.to_dict('records')[0]
    Rbt0 = selected_concrete_data['Rbt']
    Rbt0 = round(Rbt0,4)
    gammabt = cols2[1].number_input(label='$\\gamma_{bt}$', step=0.05, format="%.2f", value=1.0, min_value=0.1, max_value=1.0, label_visibility="visible")
    gammabt = round(gammabt,2)
    Rbt01 = Rbt0*gammabt
    RbtMPA = cols2[2].number_input(label='$R_{bt}$, МПа', step=0.05, format="%.2f", value=Rbt01, min_value=0.1, max_value=2.2, label_visibility="visible", disabled=True)
    RbtMPA = round(RbtMPA,4)
    Rbt = 0.01019716213*RbtMPA
    Rbt = round(Rbt,5)
    F = cols2[3].number_input(label='$F$, тс', step=1.0, format="%.1f", value=49.0, min_value=1.0, max_value=50000.0, label_visibility="visible")
    Mxloc = cols2[4].number_input(label='$M_{x,loc}$, тсм', step=0.5, format="%.2f", value=4.0, label_visibility="visible")
    Myloc = cols2[5].number_input(label='$M_{y,loc}$, тсм', step=0.5, format="%.2f", value=7.0, label_visibility="visible")
    deltaMx = cols2[6].number_input(label='$\\delta_{Mx}$', step=0.1, format="%.2f", value=0.5, min_value=0.0, max_value=2.0, label_visibility="visible")
    deltaMy = cols2[7].number_input(label='$\\delta_{My}$', step=0.1, format="%.2f", value=0.5, min_value=0.0, max_value=2.0, label_visibility="visible")
    cols2 = st.columns([1.1, 1.1, 1.1, 1, 1])
    delta_M_exc = cols2[-1].selectbox(label='$\\delta_{M}$ для $F \\cdot e$', options=['нет','да'], index=0, label_visibility="visible")
    if delta_M_exc == 'да': delta_M_exc=True
    else: delta_M_exc=False
    M_abs = cols2[-3].selectbox('Учитывать знак $F \\cdot e$', options=['нет', 'да'], index=0)
    if M_abs == 'да': M_abs=False
    else: M_abs=True
    F_dir = cols2[-2].selectbox('Направление $F$', options=['вверх','вниз'], index=0)
    if F_dir == 'вверх':
        image_f_dir = Image.open("F_up.png")
    if F_dir == 'вниз':
        image_f_dir = Image.open("F_down.png")
    st.sidebar.write("Положительные направления нагрузок")
    st.sidebar.image(image_f_dir)
    is_sw = cols2[0].selectbox(label='Поперечное арм.', options=['да', 'нет'], index=0, label_visibility="visible")
    if is_sw == 'да': is_sw=True
    else: is_sw=False
    sw_mode = cols2[1].selectbox(label='Режим арм.', options=['подбор','проверка'], index=0, label_visibility="visible")
    if sw_mode == 'подбор': sw_block=True
    else: sw_block=False


    if is_sw:
        cols2 = st.columns([1,0.8,1,1,1,1,1])
        rtype = cols2[0].selectbox(label='Арматура', options=['A240', 'A400', 'A500'], index=0, label_visibility="visible")
        selected_reinf_data = table_reinf_data.loc[table_reinf_data['Class'] == rtype]
        selected_reinf_data = selected_reinf_data.to_dict('records')[0]
        Rsw0 = selected_reinf_data['Rsw']
        Rsw = cols2[1].number_input(label='$R_{sw}$, МПа', value=Rsw0, label_visibility="visible", disabled=True)
        Rsw = 0.01019716213*Rsw
        Rsw = round(Rsw,3)
        nsw = cols2[3].number_input(label='$n_{sw}$, шт.', step=1, format="%i", value=2, min_value=1, max_value=10, label_visibility="visible")
        nsw = round(nsw)
        sw = cols2[5].number_input(label='$s_w$, см', step=5.0, format="%.2f", value=6.0, min_value=0.0, max_value=100.0, label_visibility="visible", disabled=sw_block)
        sw = round(sw,2)
        dsw = cols2[4].selectbox(label='$d_{sw}$, мм', options=dias, index=0, label_visibility="visible")
        dsw = round(dsw)
        Asw = pi*dsw*dsw/4*nsw/10/10
        Asw= round(Asw,3)
        qsw0 = Rsw*Asw/sw
        qsw0 = round(qsw0,5)
        qsw_max = (Rbt*h0)/0.8
        qsw_max = round(qsw_max,5)
        qsw_min = 0.25*Rbt*h0/0.8
        #qsw_min = round(qsw_min,3)
        #st.write(qsw_max)
        ksw0 = 0.8*qsw0/(Rbt*h0)
        ksw0 = round(ksw0,3)
        cols2[6].number_input(label='$k_{sw}$, %', step=5.0, format="%.1f", value=ksw0*100, label_visibility="visible", disabled=True)
        kh0 = cols2[2].number_input(label='$k \\cdot h_0$', step=0.1, format="%.1f", value=1.5, label_visibility="visible")
        ksw = 0.0
        if ksw0<0.25:
            ksw = 0.0
            qsw = 0
            sw_max = Rsw*pi*dsw*dsw*nsw/4/100/qsw_min
            sw_max = round(sw_max,1)
        if ksw0>1.0:
            ksw = 1.0
            qsw = qsw_max
        if 0.25<=ksw0<=1:
            ksw = ksw0
            qsw = qsw0
        ksw = round(ksw,3)
    
if True: #Генерация контуров
    red_contours = generate_red_contours(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
    blue_contours, contour_gamma, contour_sides, contour_len, contour_center, contour_len_pr = generate_blue_contours(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
    red_contours_sw = generate_red_contours(b, h, 2*kh0*h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
    blue_contours_sw, contour_gamma_sw, contour_sides_sw, contour_len_sw, contour_center_sw, contour_len_pr_sw = generate_blue_contours(b, h, 2*kh0*h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
    num_elem = len(blue_contours)
    rez = 0
    cont_arr = np.array(blue_contours)
    cont_arr_sw = np.array(blue_contours_sw)
    x_cont_min = cont_arr[:,0,:].min()
    x_cont_min_sw = cont_arr_sw[:,0,:].min()
    x_cont_max = cont_arr[:,0,:].max()
    x_cont_max_sw = cont_arr_sw[:,0,:].max()
    y_cont_min = cont_arr[:,1,:].min()
    y_cont_min_sw = cont_arr_sw[:,1,:].min()
    y_cont_max = cont_arr[:,1,:].max()
    y_cont_max_sw = cont_arr_sw[:,1,:].max()
    dx = x_cont_max - x_cont_min
    dx_sw = x_cont_max_sw - x_cont_min_sw
    dy = y_cont_max - y_cont_min
    dy_sw = y_cont_max_sw - y_cont_min_sw
    sizes = [x_cont_min, x_cont_max,y_cont_min, y_cont_max, dx, dy]
    sizes_sw = [x_cont_min_sw, x_cont_max_sw, y_cont_min_sw, y_cont_max_sw, dx_sw, dy_sw]

if num_elem>=2:
    rez = find_contour_geometry(blue_contours, contour_gamma, Rbt, Rsw, h0, F, Mxloc, Myloc, deltaMx, deltaMy, b/2, h/2, M_abs, delta_M_exc, F_dir, is_sw, qsw0, sw_mode, sw, nsw)
    #rez2 = solve_geom_props(blue_contours)
    #colls = st.columns([1,1])
    #colls[0].write(rez)
    #colls[1].write(rez2)
    if sw_mode == 'подбор':
        sw_min, sw_min_code = solve_sw_min(rez['kb'], h0, Rbt, Rsw, Asw, dx, dy)
        qsw = round(Rsw*Asw/sw_min,5)
        rez = find_contour_geometry(blue_contours, contour_gamma, Rbt, Rsw, h0, F, Mxloc, Myloc, deltaMx, deltaMy, b/2, h/2, M_abs, delta_M_exc, F_dir, is_sw, qsw0, sw_mode, sw, nsw)
    rez_sw = find_contour_geometry(blue_contours_sw, contour_gamma_sw, Rbt, Rsw, h0, F, Mxloc, Myloc, deltaMx, deltaMy, b/2, h/2, M_abs, delta_M_exc, F_dir, is_sw, qsw0, sw_mode, sw, nsw)
    center = [rez['xc'], rez['yc']]
    center_sw = [rez_sw['xc'], rez_sw['yc']]
    #st.write(rez)

fig, image_stream, image_stream2 = draw_scheme(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT,
                  red_contours, blue_contours, center, sizes)
fig_sw, image_stream_sw, image_stream2_sw = draw_scheme(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT,
                  red_contours_sw, blue_contours_sw, center_sw, sizes_sw)
#, use_container_width=True
cols[0].plotly_chart(fig)

if num_elem<2:
    st.write('В расчете должно быть минимум два участка!')
    st.stop()

if True: #Быстрый вывод основных результатов
    st.write('Предельные усилия, воспринимаемые бетоном контура расчетного поперечного сечения:')
    string = '$F_{b,ult} = ' + str(rez["Fbult"]) +  '\\cdot тс; '
    string += '\\quad M_{bx,ult} = ' + str(rez["Mbxult"])+  '\\cdot тсм; '
    string += '\\quad M_{by,ult} = ' + str(rez["Mbyult"])+  '\\cdot тсм.$'
    st.write(string)
    st.write('Коэффициенты использования бетона по силе $k_{b,F}$, по моментам $k_{b,M}$ и суммарный $k_{b}$:')
    string = '$k_{b,F}='  + str(rez['kbF'])
    string += '; \\quad k_{b,M}='  + str(rez['kbM'])
    string += '; \\quad k_{b}='  + str(rez['kb']) + '$.'
    if rez['kbM0'] != rez['kbM']:
        string += ' :blue[Вклад моментов ограничен.]'
    st.write(string)
    if rez['kb'] > 2:
        string = ':red[Прочность не может быть обеспечена, необходимо увеличение габаритов площадки колонны, толщины плиты или класса бетона.]'
        st.write(string)
    if rez['kb'] <= 1:
        string = ':green[Прочность обеспечена. Поперечное армирование не требуется.]'
        st.write(string)
    if 2>= rez['kb'] > 1:
        string = ':orange[Требуется поперечное армирование.]'
        st.write(string)
    if is_sw:
        if 2>= rez['kb'] > 1:
            if sw_mode == 'подбор':
                sw_min, sw_min_code = solve_sw_min(rez['kb'], h0, Rbt, Rsw, Asw, dx, dy)
                string = 'Максимальный шаг, при заданном $A_{sw} = ' + str(Asw) + '\\cdot см^2$, составляет $s_w = ' + str(sw_min) + '\\cdot см$.'
                if sw_min_code == 1:
                    string += ' :blue[Учтено ограничение на максимальный шаг.]'
                string += ' При данном шаге $q_{sw} = ' + str(qsw) + '\\cdot тс/см$.'
                st.write(string)
        if 2>= rez['kb'] > 1:
            st.subheader('Проверка за зоной установки поперечной арматуры')
            string = 'Коэффициенты для расчетного контура на расстоянии $' + str(kh0) + '\\cdot h_0=' + str(round(kh0*h0,1)) +  '\\cdot см$:'
            st.write(string)
            string = '$k_{b,F}='  + str(rez_sw['kbF'])
            string += '; \\quad k_{b,M}='  + str(rez_sw['kbM'])
            string += '; \\quad k_{b}='  + str(rez_sw['kb']) + '$.'
            if rez_sw['kbM0'] != rez_sw['kbM']:
                string += ' :blue[Вклад моментов ограничен.]'
            st.write(string)
            if rez_sw['kb'] <= 1:
                string = ':green[Прочность за зоной поперечного армирования обеспечена.]'
                st.write(string)
            if rez_sw['kb'] > 1:
                string = ':orange[Требуется увеличение зоны поперечного армирования.]'
                st.write(string)

if is_report:
    doc = Document('Template_punch.docx')
    styles_element = doc.styles.element
    rpr_default = styles_element.xpath('./w:docDefaults/w:rPrDefault/w:rPr')[0]
    lang_default = rpr_default.xpath('w:lang')[0]
    lang_default.set(docx.oxml.shared.qn('w:val'),'ru-RU')
    doc.core_properties.author = 'Автор'
    p = doc.paragraphs[-1]
    delete_paragraph(p)
    string = 'Расчет на продавливание при действии сосредоточенной силы и изгибающих моментов.'
    doc.add_heading(string, level=0)
    #st.subheader(string)

    string = 'Расчет производится согласно СП 63.13330.2018 п. 8.1.46 – 8.1.52.'
    if is_sw: string += ' Поперечная арматура принимается равномерно расположенной по периметру расчетного контура.'
    doc.add_paragraph().add_run(string)


    if is_init_help:
        solve_help_text(doc, is_sw, M_abs, delta_M_exc, F_dir)

    init_data_text(doc, b, h, h0,
                   ctype, Rbt0, gammabt, RbtMPA, Rbt,
                   is_sw, rtype, Rsw0, Rsw,
                   nsw, dsw, sw, Asw, sw_mode, qsw0, ksw0,
                   F, F_dir, Mxloc, Myloc,
                   delta_M_exc, deltaMx, deltaMy)


    if True: #Добавление эскиза расчетного контура в docx
        string = 'Эскиз расчетного контура.'
        doc.add_heading(string, level=2)
        doc.add_picture(image_stream, width=Mm(80))
        #doc.add_picture('test.svg', width=Mm(80))
        p = doc.paragraphs[-1]
        p.paragraph_format.first_line_indent = Mm(0)
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    with st.expander('Геометрические характеристики контура'):
        string = 'Геометрические характеристики контура.'
        st.subheader(string)
        doc.add_heading(string, level=2)
        if is_geom_help: #Подробный расчет
            if True: #Длины участков
                string = 'Геометрические характеристики, такие как статические моменты, осевые моменты инерции, моменты сопротивления для расчетного контура вычисляются в НАПРАВЛЕНИИ соответствующих осей.'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = 'Длины участков расчетного контура $L_i$, а также длины их проекций $L_{x,i}$ и $L_{y,i}$ в соответствии с эскизом приведены в таблице ниже.'

                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
    
                contours_lens = {'Li, см':[], 'Lxi, см':[], 'Lyi, см':[]}
                contours_lens_names = []
                for i in range(len(contour_len)):
                    contours_lens_names.append(contour_sides[i])
                    contours_lens['Li, см'].append(f'{float(contour_len[i]):g}')
                    contours_lens['Lxi, см'].append(f'{float(contour_len_pr[i][0]):g}')
                    contours_lens['Lyi, см'].append(f'{float(contour_len_pr[i][1]):g}')
                contours_lens = pd.DataFrame.from_dict(contours_lens, orient='index', columns=contours_lens_names)
                st.dataframe(contours_lens, use_container_width=True)

                table = doc.add_table(contours_lens.shape[0]+1, contours_lens.shape[1]+1)
                table.style = 'Стиль_таблицы'
                for j in range(contours_lens.shape[-1]):
                    table.cell(0,j+1).text = contours_lens.columns[j]
                    table.cell(0,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                for i in range(contours_lens.shape[0]):
                    for j in range(contours_lens.shape[-1]):
                        table.cell(i+1,j+1).text = str(contours_lens.values[i,j])
                        table.cell(i+1,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                table.cell(0,0).text = 'Участок'
                table.cell(0,0).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                p = table.cell(1,0).paragraphs[0]
                add_text_latex(p, '$L_i$, см')
                p.paragraph_format.first_line_indent = Mm(0)
                p = table.cell(2,0).paragraphs[0]
                add_text_latex(p, '$L_{x,i}$, см')
                p.paragraph_format.first_line_indent = Mm(0)
                p = table.cell(3,0).paragraphs[0]
                add_text_latex(p, '$L_{y,i}$, см')
                p.paragraph_format.first_line_indent = Mm(0)
        
            if True: #Периметр расчетного контура
                string = 'Вычисляем периметр расчетного контура как сумму длин каждого из участков:'
                st.write(string)
                doc.add_paragraph().add_run(string)

                string = '$u = \\sum_i L_i = '
                string += f'{float(round(contour_len[0],3)):g}'
                for i in range(1, len(contour_len)):
                    string += '+'
                    string += f'{float(round(contour_len[i],3)):g}'
                string += f'={float(round(sum(contour_len),3)):g} \\cdot см.$'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
    
            if True: #Центры тяжести участков
                string = 'Положения центров тяжести $x_{c,0,i}$ и $y_{c,0,i}$ каждого из участков расчетного контура относительно левого нижнего угла колонны приведены в таблице ниже.'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
                contours_cent = {'xc0i, см':[], 'yc0i, см':[]}
                contours_cent_names = []
                for i in range(len(contour_sides)):
                    contours_cent_names.append(contour_sides[i])
                    contours_cent['xc0i, см'].append(f'{float(round(contour_center[i][0],3)):g}')
                    contours_cent['yc0i, см'].append(f'{float(round(contour_center[i][1],3)):g}')
                contours_cent = pd.DataFrame.from_dict(contours_cent, orient='index', columns=contours_cent_names)
                st.dataframe(contours_cent, use_container_width=True)
                table = doc.add_table(contours_cent.shape[0]+1, contours_cent.shape[1]+1)
                table.style = 'Стиль_таблицы'
                for j in range(contours_cent.shape[-1]):
                    table.cell(0,j+1).text = contours_cent.columns[j]
                    table.cell(0,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                for i in range(contours_cent.shape[0]):
                    for j in range(contours_cent.shape[-1]):
                        table.cell(i+1,j+1).text = str(contours_cent.values[i,j])
                        table.cell(i+1,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                table.cell(0,0).text = 'Участок'
                table.cell(0,0).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                p = table.cell(1,0).paragraphs[0]
                add_math(p, 'x_{c,0,i}, см')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)
                p = table.cell(2,0).paragraphs[0]
                add_math(p, 'y_{c,0,i}, см')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)

            if True: #Статические моменты инерции
                string = 'Статические моменты $S_{bx,0,i}$ и $S_{by,0,i}$ каждого из участков расчетного контура относительно левого нижнего угла колонны вычисляются по формулам:'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
                string = '$S_{bx,0,i} = L_{i} \\cdot x_{c,0,i} ; \\quad S_{by,0,i} = L_{i} \\cdot y_{c,0,i}.$'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
                string = 'Результаты расчета статических моментов участков расчетного контура по указанным выше приведены в таблице ниже.'
                st.write(string)
                doc.add_paragraph().add_run(string)
                contours_S = {'Sbx0i, см2':[], 'Sby0i, см2':[]}
                contours_S_names = []
                for i in range(len(contour_sides)):
                    contours_S_names.append(contour_sides[i])
                    contours_S['Sbx0i, см2'].append(f'{float(round(rez["Sx_arr"][i],1)):g}')
                    contours_S['Sby0i, см2'].append(f'{float(round(rez["Sy_arr"][i],1)):g}')
                contours_S = pd.DataFrame.from_dict(contours_S, orient='index', columns=contours_S_names)
                st.dataframe(contours_S, use_container_width=True)
                table = doc.add_table(contours_S.shape[0]+1, contours_S.shape[1]+1)
                table.style = 'Стиль_таблицы'
                for j in range(contours_S.shape[-1]):
                    table.cell(0,j+1).text = contours_S.columns[j]
                    table.cell(0,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                for i in range(contours_S.shape[0]):
                    for j in range(contours_S.shape[-1]):
                        table.cell(i+1,j+1).text = str(contours_S.values[i,j])
                        table.cell(i+1,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                table.cell(0,0).text = 'Участок'
                table.cell(0,0).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                p = table.cell(1,0).paragraphs[0]
                add_math(p, 'S_{bx,0,i}, см^2')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)
                #p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p = table.cell(2,0).paragraphs[0]
                add_math(p, 'S_{by,0,i}, см^2')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)
                #p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

            if True: #Статический момент инерции всего сечения
                string = 'Статические моменты инерции всего расчетного контура относительно левого нижнего угла колонны вычисляем как сумму статических моментов инерции каждого из участков.'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = '$ S_{bx,0} = \\sum_i S_{bx,0,i}= '
                string += f'{float(round(rez["Sx_arr"][0],2)):g}'
                for i in range(1, len(rez["Sx_arr"])):
                    if rez["Sx_arr"][i] > 0:
                        string += '+'
                    string += f'{float(round(rez["Sx_arr"][i],2)):g}'
                string += f'={float(round(rez["Sx"],2)):g} \\cdot см^2.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))

                string = '$ S_{by,0} = \\sum_i S_{by,0,i}= '
                string += f'{float(round(rez["Sy_arr"][0],2)):g}'
                for i in range(1, len(rez["Sy_arr"])):
                    if rez["Sy_arr"][i] > 0:
                        string += '+'
                    string += f'{float(round(rez["Sy_arr"][i],2)):g}'
                string += f'={float(round(rez["Sy"],2)):g} \\cdot см^2.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))

            if True: #Вычисление центра тяжести
                string = 'Вычисляем положение геометрического центра тяжести контура относительно левого нижнего угла колонны.'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = '$ x_c = \\dfrac{S_{bx,0}}{u} = '
                string += '\\dfrac{' + f'{float(round(rez["Sx"],2)):g}' + '}{' + f'{float(round(rez["Lsum"],3)):g}' + '}='
                string += f'{float(round(rez["xc"],3)):g} \\cdot см.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))

                string = '$ y_c = \\dfrac{S_{by,0}}{u} = '
                string += '\\dfrac{' + f'{float(round(rez["Sy"],2)):g}' + '}{' + f'{float(round(rez["Lsum"],3)):g}' + '}='
                string += f'{float(round(rez["yc"],3)):g} \\cdot см.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))

            if True: #Эксцентриситет продольной силы
                if rez["ex"] !=0 or rez["ex"] !=0:
                    string = 'Вычисляем эксцентриситет центра тяжести расчетного контура относительно центра колонны.'
                    st.write(string)
                    doc.add_paragraph().add_run(string)
                    if rez["ex"] !=0:
                        string = 'Вдоль оси $x$:'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = '$e_x = x_c - b/2= '
                        string += f'{float(rez["xc"]):g} -'
                        string += f'{float(round(b/2,2)):g} = {float(rez["ex"]):g} \\cdot см.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                    if rez["ey"] !=0:
                        string = 'Вдоль оси $y$:'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = '$e_y = y_c - h/2= '
                        string += f'{float(rez["yc"]):g} -'
                        string += f'{float(round(h/2,2)):g} = {float(rez["ey"]):g} \\cdot см.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)

            if True: #Вычисление центров тяжести участков
                string = 'Вычисляем координаты центров тяжести каждого из элементов расчетного контура относительно центра тяжести всего расчетного контура по формулам:'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = '$x_{c,i} = x_{c,0,i} - x_c; \\quad y_{c,i} = y_{c,0,i} - y_c.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))
                string = 'Результаты расчета по указанным выше формулам приведены в таблице ниже.'
                st.write(string)
                doc.add_paragraph().add_run(string)
                contours_cent = {'xci, см':[], 'yci, см':[]}
                contours_cent_names = []
                for i in range(len(contour_sides)):
                    contours_cent_names.append(contour_sides[i])
                    contours_cent['xci, см'].append(f'{float(round(contour_center[i][0] - rez["xc"],3)):g}')
                    contours_cent['yci, см'].append(f'{float(round(contour_center[i][1] - rez["yc"],3)):g}')
                contours_cent = pd.DataFrame.from_dict(contours_cent, orient='index', columns=contours_cent_names)
                st.dataframe(contours_cent, use_container_width=True)
                table = doc.add_table(contours_cent.shape[0]+1, contours_cent.shape[1]+1)
                table.style = 'Стиль_таблицы'
                for j in range(contours_cent.shape[-1]):
                    table.cell(0,j+1).text = contours_cent.columns[j]
                    table.cell(0,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                for i in range(contours_cent.shape[0]):
                    for j in range(contours_cent.shape[-1]):
                        table.cell(i+1,j+1).text = str(contours_cent.values[i,j])
                        table.cell(i+1,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                table.cell(0,0).text = 'Участок'
                table.cell(0,0).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                p = table.cell(1,0).paragraphs[0]
                add_math(p, 'x_{c,i}, см')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)
                p = table.cell(2,0).paragraphs[0]
                add_math(p, 'y_{c,i}, см')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)

            if True: #Вычисление наиболее удаленных точек
                string = 'Расстояние до наиболее удаленных от геометрического центра тяжести точек (левой, $x_L$; правой, $x_R$; нижней, $y_B$; верхней, $y_T$) расчетного контура приведено в таблице ниже:'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
                max_values = [f'{float(round(rez["xL"],3)):g}',
                                                f'{float(round(rez["xR"],3)):g}',
                                                f'{float(round(rez["yB"],3)):g}',
                                                f'{float(round(rez["yT"],3)):g}']
                max_points = {'Расстояние, см':max_values}
                max_points = pd.DataFrame.from_dict(max_points, orient='index', columns=['Левая','Правая','Нижняя','Верхняя'])
                st.dataframe(max_points, use_container_width=True)
                table = doc.add_table(2, 5)
                table.style = 'Стиль_таблицы'
                table.cell(1,0).text = 'Расстояние, см'
                table.cell(1,0).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                p = table.cell(0,1).paragraphs[0]
                add_math(p, 'x_{L}')
                p.paragraph_format.first_line_indent = Mm(0)
                p = table.cell(0,2).paragraphs[0]
                add_math(p, 'x_{R}')
                p.paragraph_format.first_line_indent = Mm(0)
                p = table.cell(0,3).paragraphs[0]
                add_math(p, 'y_{B}')
                p.paragraph_format.first_line_indent = Mm(0)
                p = table.cell(0,4).paragraphs[0]
                add_math(p, 'y_{T}')
                p.paragraph_format.first_line_indent = Mm(0)
                for i in range(len(max_values)):
                    p = table.cell(1,i+1).paragraphs[0]
                    add_math(p, max_values[i])
                    p.paragraph_format.first_line_indent = Mm(0)
        
                string = 'Расстояние до наиболее удаленных от центра тяжести точек расчетного контура составляет:'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = '$x_{\\max} = \\max(|x_{L}|,x_{R})='
                string += str(round(rez["xmax"],3))
                string += 'см; \\quad y_{\\max} = \\max(|y_{B}|,y_{T})='
                string += str(round(rez["ymax"],3))
                string += 'см.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))

            if True: #Вычисление собственных моментов инерции участков
                string = 'Собственные моменты инерции участков расчетного контура вычисляются по формулам:'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = '$I_{bx,0,i} = \\dfrac{L_{x,i}^3}{12}; \\quad I_{by,0,i} = \\dfrac{L_{y,i}^3}{12}.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))
                string = 'Результаты расчета собственных моментов по указанным выше формулам приведены в таблице ниже.'
                st.write(string)
                doc.add_paragraph().add_run(string)
                contours_I0 = {'Ibx0i, см3':[], 'Iby0i, см3':[]}
                contours_I0_names = []
                for i in range(len(contour_sides)):
                    contours_I0_names.append(contour_sides[i])
                    #contours_I0['Ix0i, см3'].append(f'{float(round())}')
                    #contours_I0['Ix0i, см3'].append(n_number(rez["Ix0_arr"][i],2))
                    #contours_I0['Ix0i, см3'].append(Decimal(round(rez["Ix0_arr"][i],2)).normalize())
                    contours_I0['Ibx0i, см3'].append(f'{float(round(rez["Ix0_arr"][i],2))}')
                    contours_I0['Iby0i, см3'].append(f'{float(round(rez["Iy0_arr"][i],2))}')
                contours_I0 = pd.DataFrame.from_dict(contours_I0, orient='index', columns=contours_I0_names)
                st.dataframe(contours_I0, use_container_width=True)
                table = doc.add_table(contours_I0.shape[0]+1, contours_I0.shape[1]+1)
                table.style = 'Стиль_таблицы'
                for j in range(contours_I0.shape[-1]):
                    table.cell(0,j+1).text = contours_I0.columns[j]
                    table.cell(0,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                for i in range(contours_I0.shape[0]):
                    for j in range(contours_I0.shape[-1]):
                        table.cell(i+1,j+1).text = str(contours_I0.values[i,j])
                        table.cell(i+1,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                table.cell(0,0).text = 'Участок'
                table.cell(0,0).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                p = table.cell(1,0).paragraphs[0]
                add_math(p, 'I_{bx,0,i}, см^3')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)
                #p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p = table.cell(2,0).paragraphs[0]
                add_math(p, 'I_{by,0,i}, см^3')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)

            if True: #Вычисление моментов инерции участков
                string = 'Для вычисления моментов инерции участков контура относительно геометрического центра всего контура используются формулы переноса осей, приведенные ниже.'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = '$I_{bx,i} = I_{bx,0,i} +  L_i \\cdot x_{c,i}^2; \\quad I_{by,i} = I_{by,0,i} +  L_i \\cdot y_{c,i}^2.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))
                string = 'Результаты расчета моментов инерции участков контура относительно геометрического центра всего контура по указанным выше формулам приведены в таблице ниже.'
                st.write(string)
                doc.add_paragraph().add_run(string)
                contours_I = {'Ibxi, см3':[], 'Ibyi, см3':[]}
                contours_I_names = []
                #st.write(rez["Ix_arr"])
                for i in range(len(contour_sides)):
                    contours_I_names.append(contour_sides[i])
                    #contours_I['Ixi, см3'].append(f'{float(round(rez["Ix_arr"][i],2)):g}')
                    #contours_I['Iyi, см3'].append(f'{float(round(rez["Iy_arr"][i],2)):g}')
                    contours_I['Ibxi, см3'].append(f'{float(round(rez["Ix_arr"][i],2))}')
                    contours_I['Ibyi, см3'].append(f'{float(round(rez["Iy_arr"][i],2))}')
                contours_I = pd.DataFrame.from_dict(contours_I, orient='index', columns=contours_I_names)
                st.dataframe(contours_I, use_container_width=True)
                table = doc.add_table(contours_I.shape[0]+1, contours_I.shape[1]+1)
                table.style = 'Стиль_таблицы'
                for j in range(contours_I.shape[-1]):
                    table.cell(0,j+1).text = contours_I.columns[j]
                    table.cell(0,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                for i in range(contours_I.shape[0]):
                    for j in range(contours_I.shape[-1]):
                        table.cell(i+1,j+1).text = str(contours_I.values[i,j])
                        table.cell(i+1,j+1).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                table.cell(0,0).text = 'Участок'
                table.cell(0,0).paragraphs[0].paragraph_format.first_line_indent = Mm(0)
                p = table.cell(1,0).paragraphs[0]
                add_math(p, 'I_{bx,i}, см^3')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)
                #p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p = table.cell(2,0).paragraphs[0]
                add_math(p, 'I_{by,i}, см^3')
                p.add_run(' ')
                p.paragraph_format.first_line_indent = Mm(0)

            if True: #Моменты инерции всего сечения
                string = 'Моменты инерции всего расчетного контура вычисляем как сумму моментов инерции каждого из участков.'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = '$ I_{bx} = \\sum_i{I_{bx,i}}= '
                #string += f'{float(round(rez["Ix_arr"][0],2)):g}'
                string += f'{float(round(rez["Ix_arr"][0],2))}'
                for i in range(1, len(rez["Ix_arr"])):
                    if rez["Ix_arr"][i] > 0:
                        string += '+'
                    #string += f'{float(round(rez["Ix_arr"][i],2)):g}'
                    string += f'{float(round(rez["Ix_arr"][i],2))}'
                #string += f'={float(round(rez["Ix"],2)):g} \\cdot см^3.$'
                string += f'={float(round(rez["Ix"],2))} \\cdot см^3.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))

                string = '$ I_{by} = \\sum_i{I_{by,i}}= '
                #string += f'{float(round(rez["Iy_arr"][0],2)):g}'
                string += f'{float(round(rez["Iy_arr"][0],2))}'
                for i in range(1, len(rez["Iy_arr"])):
                    if rez["Iy_arr"][i] > 0:
                        string += '+'
                    #string += f'{float(round(rez["Iy_arr"][i],2)):g}'
                    string += f'{float(round(rez["Iy_arr"][i],2))}'
                #string += f'={float(round(rez["Iy"],2)):g} \\cdot см^3.$'
                string += f'={float(round(rez["Iy"],2))} \\cdot см^3.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))

            if True: #Моменты сопротивления расчетного контура
                string = 'Моменты сопротивления расчетного контура вычисляются по формулам (8.98):'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = '$ W_{bx} = \\dfrac{I_{bx}}{x_{\\max}} = \\dfrac{'
                #string += f'{float(round(rez["Ix_arr"][0],2)):g}'
                string += f'{float(round(rez["Ix"],2))}'
                string += '}{'
                string += f'{float(round(rez["xmax"],3))}'
                string += '} = '
                string += f'{float(round(rez["Wxmin"],2))}'
                string += '\\cdot см^2.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))

                string = '$ W_{by} = \\dfrac{I_{by}}{y_{\\max}} = \\dfrac{'
                #string += f'{float(round(rez["Ix_arr"][0],2)):g}'
                string += f'{float(round(rez["Iy"],2))}'
                string += '}{'
                string += f'{float(round(rez["ymax"],3))}'
                string += '} = '
                string += f'{float(round(rez["Wymin"],2))}'
                string += '\\cdot см^2.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))
    
        else: #Краткий расчет
            if True: #Периметр расчетного контура
                string = 'Геометрические характеристики, такие как осевые моменты инерции и моменты сопротивления для расчетного контура вычисляются в НАПРАВЛЕНИИ соответствующих осей.'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
                string = 'Периметр расчетного контура:'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
                string = f'$u = {float(round(sum(contour_len),3)):g} \\cdot см.$'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)

            if True: #Центра тяжести
                string = 'Координаты центра тяжести контура относительно левого нижнего угла колонны:'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = f'$ x_c =  {float(round(rez["xc"],3)):g} \\cdot см; \\quad  y_c = {float(round(rez["yc"],3)):g} \\cdot см.$'
                st.write(string)
                add_math(doc.add_paragraph(), string.replace('$',''))
        
            if True: #Эксцентриситет продольной силы
                if rez["ex"] !=0 or rez["ey"] !=0:
                    string = 'Эксцентриситеты продольной силы:'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)
                    string = '$'
                    if rez["ex"] !=0:
                        string += f'e_x = {float(rez["ex"]):g} \\cdot см'
                    if rez["ey"] !=0:
                        if rez["ex"] !=0:
                            string += '; \\quad '
                        string += f'e_y = {float(rez["ey"]):g} \\cdot см'
                    string += '.$'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)

            if True: #Вычисление наиболее удаленных точек
                string = 'Расстояние до наиболее удаленных от центра тяжести точек расчетного контура составляет:'
                st.write(string)
                doc.add_paragraph().add_run(string)
                string = '$x_{\\max} = '
                string += str(rez["xmax"])
                string += 'см; \\quad y_{\\max} ='
                string += str(rez["ymax"])
                string += 'см.$'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)

            if True: #Моменты инерции всего сечения
                string = 'Моменты инерции расчетного контура:'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
                string = '$ I_{bx} = '
                string += f'{rez["Ix"]} \\cdot см^3; \\quad'
                string += ' I_{by} = '
                string += f'{rez["Iy"]} \\cdot см^3.$'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)

            if True: #Моменты сопротивления расчетного контура
                string = 'Моменты сопротивления расчетного контура:'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
                string = '$ W_{bx} = ' + str(rez["Wxmin"]) + '\\cdot см^2; \\quad'
                string += ' W_{by} = ' + str(rez["Wymin"]) + '\\cdot см^2.$'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)

    with st.expander('Предельные усилия, воспринимаемые бетоном'):
        if True: #Предельная продавливающая сила, воспринимаемая бетоном
            string = 'Предельные усилия, воспринимаемые бетоном.'
            st.subheader(string)
            doc.add_heading(string, level=1)
            string = 'Предельную продавливающую силу, воспринимаемую бетоном $F_{b,ult}$, вычисляем по формуле (8.88) с учетом формулы (8.89):'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = '$F_{b,ult} = R_{bt} \\cdot h_0 \\cdot u = '
            string += f'{float(round(Rbt,6)):g} \\cdot {float(round(h0,5)):g} \\cdot  {float(sum(contour_len)):g} ='
            string += f'{float(round(rez["Fbult"],1)):g} \\cdot тс.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

            string = 'Предельно допустимое значение продавливающей силы (с учетом положений п. 8.1.46), при которой допускается не учитывать изгибающие моменты:'
            st.write(string)
            doc.add_paragraph().add_run(string)
            string = '$F_{b,ult}/1.5 = '
            string += f'{float(round(rez["Fbult"]/1.5,1)):g} \\cdot тс.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

        if True: #Предельные моменты, воспринимаемые бетонным сечением
            string = 'Предельные моменты, воспринимаемые бетоном в расчетном поперечном сечении, вычисляются по формулам (8.94):'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = '$ M_{bx,ult} = R_{bt} \\cdot h_0 \\cdot W_{bx} = '
            #string += f'{float(round(rez["Ix_arr"][0],2)):g}'
            string += f'{float(round(Rbt,6)):g} \\cdot {float(round(h0,5)):g} \\cdot  {float(round(rez["Wxmin"],2))} / 100 ='
            string += f'{float(round(rez["Mbxult"],2))} \\cdot тсм.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

            string = '$ M_{by,ult} = R_{bt} \\cdot h_0 \\cdot W_{by} = '
            #string += f'{float(round(rez["Ix_arr"][0],2)):g}'
            string += f'{float(round(Rbt,6)):g} \\cdot {float(round(h0,5)):g} \\cdot  {float(round(rez["Wymin"],2))} / 100 ='
            string += f'{float(round(rez["Mbyult"],2))} \\cdot тсм.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

            string = 'Примечание. Деление на 100 в данных формулах необходимо для перевода сантиметров в метры.'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

    with st.expander('Вычисление усилий, учитываемых в расчете'):
        string = 'Усилия, учитываемые в расчете.'
        st.subheader(string)
        doc.add_heading(string, level=1)
        string = 'Сосредоточенная сила, направленная ' + str(F_dir) + ' $F=' + str(F) + '\\cdot тс$.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Сосредоточенные моменты.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        if rez["ex"] !=0: #Если есть эксцентриситет вдоль х
            if M_abs: #Если считаем момент от эксцентриситета всегда догружающим
                if delta_M_exc: #Если учитываем дельта к эксцентриситету
                    string = '$M_x = (|M_{x,loc}| + F \\cdot |e_x|) \\cdot \\delta_{Mx} = '
                    string += '(|' + str(Mxloc) + '| + ' + str(F) + '\\cdot |' + str(rez['ex']) + '/100|) \\cdot ' + str(deltaMx) +  ' =  ' + str(rez['Mx']) 
                else:  #Если не учитываем дельта к эксцентриситету
                    string = '$M_x = |M_{x,loc}| \\cdot \\delta_{Mx} + F \\cdot |e_x|  = '
                    string += '|' + str(Mxloc) + '| \\cdot'  + str(deltaMx) + ' + ' + str(F) + '\\cdot |' + str(rez['ex']) + '/100| '  ' =  ' + str(rez['Mx']) 
            else: #Если учитываем знаки моментов
                if F_dir == 'вверх': znak = '+'
                if F_dir == 'вниз': znak = '-'
                if delta_M_exc: #Если учитываем дельта к эксцентриситету
                    string = '$M_x = |M_{x,loc}' + znak +  'F \\cdot e_x| \\cdot \\delta_{Mx} = '
                    string += '|' + str(Mxloc) + znak + str(F) + '\\cdot ' 
                    if rez['ex'] <0: string += '(' +  str(rez['ex'])  + ')'
                    else: string += str(rez['ex'])
                    string += '/100| \\cdot ' + str(deltaMx) +  ' =  ' + str(rez['Mx']) 
                else:  #Если не учитываем дельта к эксцентриситету
                    string = '$M_x = |M_{x,loc} \\cdot \\delta_{Mx}' + znak +  'F \\cdot e_x|  = '
                    string += '|' + str(Mxloc) + ' \\cdot'  + str(deltaMx) + znak + str(F) + '\\cdot '
                    if rez['ex'] <0: string += '(' +  str(rez['ex'])  + ')'
                    else: string += str(rez['ex'])
                    string +=  '/100| '  ' =  ' + str(rez['Mx']) 
            string +=  '\\cdot тсм.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

        if rez["ey"] !=0: #Если есть эксцентриситет вдоль х
            if M_abs: #Если считаем момент от эксцентриситета всегда догружающим
                if delta_M_exc: #Если учитываем дельта к эксцентриситету
                    string = '$M_y = (|M_{y,loc}| + F \\cdot |e_y|) \\cdot \\delta_{My} = '
                    string += '(|' + str(Myloc) + '| + ' + str(F) + '\\cdot |' + str(rez['ey']) + '/100|) \\cdot ' + str(deltaMy) +  ' =  ' + str(rez['My']) 
                else:  #Если не учитываем дельта к эксцентриситету
                    string = '$M_y = |M_{y,loc}| \\cdot \\delta_{My} + F \\cdot |e_y|  = '
                    string += '|' + str(Myloc) + '| \\cdot'  + str(deltaMy) + ' + ' + str(F) + '\\cdot |' + str(rez['ey']) + '/100| '  ' =  ' + str(rez['My']) 
            else: #Если учитываем знаки моментов
                if F_dir == 'вверх': znak = '+'
                if F_dir == 'вниз': znak = '-'
                if delta_M_exc: #Если учитываем дельта к эксцентриситету
                    string = '$M_y = |M_{y,loc}' + znak +  'F \\cdot e_y| \\cdot \\delta_{My} = '
                    string += '|' + str(Myloc) + znak + str(F) + '\\cdot ' 
                    if rez['ey'] <0: string += '(' +  str(rez['ey'])  + ')'
                    else: string += str(rez['ey'])
                    string += '/100| \\cdot ' + str(deltaMy) +  ' =  ' + str(rez['My']) 
                else:  #Если не учитываем дельта к эксцентриситету
                    string = '$M_y = |M_{y,loc} \\cdot \\delta_{My}' + znak +  'F \\cdot e_y|  = '
                    string += '|' + str(Myloc) + ' \\cdot'  + str(deltaMy) + znak + str(F) + '\\cdot '
                    if rez['ey'] <0: string += '(' +  str(rez['ey'])  + ')'
                    else: string += str(rez['ey'])
                    string +=  '/100| '  ' =  ' + str(rez['My']) 
            string +=  '\\cdot тсм.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
    
        if rez["ex"] !=0 or rez["ey"] !=0:
            string = 'Примечание. Деление на 100 необходимо для перевода сантиметров в метры.'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

        if rez["ex"] == 0:
            string = '$M_x = |M_{x,loc}| \\cdot \\delta_{Mx} = | ' + str(Mxloc) +'| \\cdot ' + str(deltaMx) + '=' + str(rez['Mx']) +  '\\cdot тсм.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

        if rez["ey"] == 0:
            string = '$M_y = |M_{y,loc}| \\cdot \\delta_{My} = | ' + str(Myloc) +'| \\cdot ' + str(deltaMy) + '=' + str(rez['My']) +  '\\cdot тсм.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

    with st.expander('Проверка прочности по бетону'):
        string = 'Проверка прочности бетона расчетного поперечного сечения.'
        st.subheader(string)
        doc.add_heading(string, level=1)
        if True: #Проверка по продольной силе
            string = 'Коэффициент использования прочности бетона расчетного поперечного сечения по силе:'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = '$k_{b,F}=\\dfrac{F}{F_{b,ult}}=\\dfrac{'
            string += str(F) + '}{' + str(rez['Fbult']) + '} = ' + str(rez['kbF']) + '.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
        if True: #Проверка по моментам
            string = 'Коэффициент использования прочности бетона расчетного поперечного сечения по моментам:'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = '$k_{b,M}=\\dfrac{M_x}{M_{bx,ult}} + \\dfrac{M_y}{M_{by,ult}} =\\dfrac{'
            string += str(rez['Mx']) + '}{' + str(rez['Mbxult']) + '} +  \\dfrac{' + str(rez['My']) + '}{' + str(rez['Mbyult'])
            string += '}=' + str(rez['kbM0']) + '.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            if rez['kbM0'] != rez['kbM']:
                string = 'Условие $k_{b,M} \\le 0.5 \\cdot k_{b,F}$ не выполняется. Вклад моментов ограничивается в соответствии с указаниями п. 8.1.46.'
                string += ' В расчете принимаем:'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)
                string = '$k_{b,M} = 0.5 \\cdot k_{b,F} =' + str(rez['kbM']) + '.$'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)

        if True: #Суммарно
            string = 'Суммарный (по силе и моментам) коэффициент использования прочности бетона расчетного поперечного сечения:'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = '$k_b=k_{b,F}+k_{b,M}=' + str(rez['kbF']) + '+' + str(rez['kbM']) + '=' + str(rez['kb']) + '.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

        st.write()

    if True: #Результаты проверки прочности по бетону
        if rez['kb'] <= 1:
            string = 'Так как $k_{b}=' + str(rez['kb'])+ '<1$ прочность обеспечена без установки поперечной арматуры.'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
        if rez['kb'] > 2:
            string = 'Так как $k_{b}=' + str(rez['kb'])+ '>2$ прочность не может быть обеспечена, необходимо увеличение габаритов площадки передачи нагрузки, либо толщины плиты, либо класса бетона.'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
        if 1 < rez['kb'] <= 2:
            string = 'Так как $1< k_{b}=' + str(rez['kb'])+  ' \\le 2$ требуется установка поперечной арматуры.'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

    if rez['kb'] <=2: #Если прочность может быть обеспечена
        if is_sw: #Предельные усилия, воспринимаемые заданной арматурой
            if sw_mode == 'проверка':
                with st.expander('Предельные усилия, воспринимаемые арматурой'):
                    string = 'Предельные усилия, воспринимаемые поперечной арматурой.'
                    st.subheader(string)
                    doc.add_heading(string, level=1)
                    string = 'Предельная продавливающая сила, воспринимаемая поперечной арматурой $F_{sw,ult}$, вычисляется по формуле (8.91):'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)
                
                    string = '$F_{sw,ult} = 0.8 \\cdot q_{sw} \\cdot u = '
                    string += '0.8 \\cdot' + str(qsw0) + '\\cdot' + str(rez['Lsum']) + '='
                    string += str(rez['Fswult_check0']) + '\\cdot тс.$'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)

                    if rez['Fswult_check0'] >= 0.25*rez['Fbult']:
                        string = 'Условие $F_{sw,ult}  = ' + str(rez['Fswult_check0']) +  ' \\ge 0.25 \\cdot F_{b,ult} =' + str(round(0.25*rez['Fbult'],1)) +  ' $ выполняется.'
                        string += ' Поперечная арматура учитывается в расчете.'
                        if rez['Fswult_check0']<rez['Fbult']:
                            string += ' Условие $F_{sw,ult}  = ' + str(rez['Fswult_check0']) +  ' \\le F_{b,ult} =' + str(rez['Fbult']) +  ' $ выполняется.'
                            string += ' Вклад поперечного армирования не ограничивается.'
                        
                        if rez['Fswult_check0']>rez['Fbult']:
                            string += ' Условие $F_{sw,ult} \\le F_{b,ult}$ не выполняется, вклад поперечного армирования ограничиваем. В расчете принимаем: '
                            string += '$F_{sw,ult} = F_{b,ult}=' + str(rez['Fswult_check']) +  '\\cdot тс.$'

                    if rez['Fswult_check0']<0.25*rez['Fbult']:
                        string = 'Так как $F_{sw,ult} \\le 0.25 \\cdot F_{b,ult} = ' + str(round(0.25*rez['Fbult'],1)) + '$ , поперечную арматуру не учитываем в расчете. В расчете принимаем:'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = '$F_{sw,ult} = M_{sw,x,ult} = M_{sw,y,ult} = 0.$'

                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)

                    if rez['Fswult_check0']>=0.25*rez['Fbult']:
                        string = 'Предельные моменты, воспринимаемые поперечной арматурой, вычисляются по формуле (8.97):'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)

                        string = '$M_{sw,ult}= 0.8 \\cdot q_{sw} \\cdot W_{sw}.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)

                        string = 'В соответствии с п. 8.1.52, принято, что поперечная арматура расположена равномерно вдоль расчетного контура продавливания, т.е. $W_{sw}=W_b$. В результате:'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)

                        string = '$M_{sw,x,ult}= 0.8 \\cdot q_{sw} \\cdot W_{bx} = '
                        string += '0.8 \\cdot' + str(qsw0) + '\\cdot' + str(rez['Wxmin']) + '/100='
                        string += str(rez['Mswxult_check0']) + '\\cdot тсм;$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = '$ M_{sw,y,ult}= 0.8 \\cdot q_{sw} \\cdot W_{by} = '
                        string += '0.8 \\cdot' + str(qsw0) + '\\cdot' + str(rez['Wymin']) + '/100='
                        string += str(rez['Mswyult_check0']) + '\\cdot тсм.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = 'Примечание. Деление на 100 в данных формулах необходимо для перевода сантиметров в метры.'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)

                        if qsw0>qsw:
                            string = 'Так как $M_{sw,x,ult} \\ge M_{bx,ult}$ и $M_{sw,y,ult} \\ge M_{by,ult}$, вклад поперечного армирования ограничиваем. В расчете принимаем:'
                            st.write(string)
                            add_text_latex(doc.add_paragraph(), string)
                            string = '$M_{sw,x,ult} = M_{bx,ult}=' + str(rez['Mswxult_check']) +  '\\cdot тсм; \\quad'
                            string += ' M_{sw,y,ult} = M_{by,ult}=' + str(rez['Mswyult_check'])
                            string += '\\cdot тсм.$'
                            st.write(string)
                            add_text_latex(doc.add_paragraph(), string)

                with st.expander('Проверка прочности с поперечной арматурой'):
                    string = 'Проверка прочности бетона расчетного поперечного сечения.'
                    st.subheader(string)
                    doc.add_heading(string, level=1)
                    if True: #Проверка по продольной силе
                        string = 'Коэффициент использования прочности расчетного поперечного сечения по силе:'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = '$k_{F}=\\dfrac{F}{F_{b,ult} + F_{sw,ult}}=\\dfrac{'
                        string += str(F) + '}{' + str(rez['Fbult']) + '+' + str(rez['Fswult_check']) + '} = ' + str(rez['kF_check']) + '.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                    if True: #Проверка по моментам
                        string = 'Коэффициент использования прочности расчетного поперечного сечения по моментам:'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = '$k_{M}=\\dfrac{M_x}{M_{bx,ult} + M_{sw,x,ult}} + \\dfrac{M_y}{M_{by,ult} + M_{sw,y,ult}} =\\dfrac{'
                        string += str(rez['Mx']) + '}{' + str(rez['Mbxult']) + '+' + str(rez['Mswxult_check']) + '} +  \\dfrac{' + str(rez['My']) + '}{' + str(rez['Mbyult'])  + '+' + str(rez['Mswyult_check'])
                        string += '}=' + str(rez['kM0_check']) + '.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        if rez['kM0_check'] != rez['kM_check']:
                            string = 'Условие $k_{M} \\le 0.5 \\cdot k_{F}$ не выполняется. Вклад моментов ограничивается в соответствии с указаниями п. 8.1.46.'
                            string += ' В расчете принимаем:'
                            st.write(string)
                            add_text_latex(doc.add_paragraph(), string)
                            string = '$k_{M} = 0.5 \\cdot k_{F} =' + str(rez['kM_check']) + '.$'
                            st.write(string)
                            add_text_latex(doc.add_paragraph(), string)

                    if True: #Суммарно
                        string = 'Суммарный (по силе и моментам) коэффициент использования прочности расчетного поперечного сечения:'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = '$k=k_{F}+k_{M}=' + str(rez['kF_check']) + '+' + str(rez['kM_check']) + '=' + str(rez['k_check']) + '.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                if True: #Результаты проверки прочности с арматурой
                    if rez['k_check'] <= 1:
                        string = 'Так как $k=' + str(rez['k_check'])+ '<1$ прочность обеспечена.'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                    if rez['k_check'] > 1:
                        string = 'Так как $k=' + str(rez['k_check'])+ '>1$ прочность не обеспечена, необходимо увеличение поперечного армирования.'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = 'Минимальное значение $A_{sw}/s_{w}=' + str(rez['sw_Asw_min']) + ' \\cdot см^2 / см.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = 'При заданном шаге рядов поперечного армирования и числе стержней, пересекающих пирамиду продавливания, минимальный диаметр стержня составляет $' + str(rez['dsw_min']) + ' \\cdot мм.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                    string = 'При заданном шаге рядов поперечного армирования и числе стержней, пересекающих пирамиду продавливания, максимальный диаметр стержня составляет $' + str(rez['dsw_max']) + ' \\cdot мм.$'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)


            if sw_mode == 'подбор':
                if rez['kb'] <= 1: #Если поперечная арматура не требуется
                    string = 'Поперечная арматура не требуется.'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)
                if rez['kb'] > 1: #Если поперечная арматура требуется
                    with st.expander('Расчет требуемого поперечного армирования'):
                        string = 'Требуемая интенсивность поперечного армирования.'
                        st.subheader(string)
                        doc.add_heading(string, level=1)
                        string = 'Минимальное значение $A_{sw}/s_{w}$ вычисляется по формуле:'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        string = '$\\dfrac{A_{sw}}{s_{w}} = \\dfrac{R_{bt} \\cdot h_0 \\cdot (k_b - 1)}{0.8 \\cdot R_{sw}}='
                        string += ' \\dfrac{' + str(Rbt)  + ' \\cdot ' +  str(h0) + ' \\cdot (' + str(rez['kb']) +  '- 1)}{0.8 \\cdot ' + str(Rsw) +'}=' + str(rez['sw_Asw_min'])
                        string += ' \\cdot см^2 / см.$'
                        st.write(string)
                        add_text_latex(doc.add_paragraph(), string)
                        solve_d = solve_arm(rez['sw_Asw_min'], h0, dx, dy)
                        col_names = solve_d[1]
                        row_names = solve_d[0]
                        for i in range(len(col_names)):
                            col_names[i] = 'sw=' + str(col_names[i]) + 'см'
                        for i in range(len(row_names)):
                            row_names[i] = 'nsw=' + str(row_names[i]) + 'шт'
                        st.write(pd.DataFrame(solve_d[2],index=row_names,columns=col_names))
                        #st.write(rez)

            st.plotly_chart(fig_sw)



    cols = st.columns([1,1,1])

    #cols[0].write()

    #st.write('Коэффициент использования по продольной силе $k_{bF}=' + str(rez['kbF']) + '$.')
    #st.write('Коэффициент использования по моментам $k_{bМ}=' + str(rez['kbM']) + '$.')
    #st.write('Суммарный коэффициент использования $k_b=' + str(rez['kb']) + '$.')

    file_stream = io.BytesIO()
    doc.save(file_stream)
    st.sidebar.download_button('Отчет *.docx', file_name='продавливание_колонна_' + str(round(b))+'x'+str(round(h))+'_h0='+str(round(h0)) +'.docx', data=file_stream)







