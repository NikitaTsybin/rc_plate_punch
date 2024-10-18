from math import pi
from PIL import Image
import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from decimal import Decimal
import docx
from docx import Document
from docx.shared import Pt
##import docx_svg_patch
from docx.shared import Mm
from docx.shared import RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import typing
import latex2mathml.converter
import mathml2omml
from docx.oxml import parse_xml
import io

st.header('Расчет на продавливание плиты')



is_init_help = st.sidebar.toggle('Расчетные предпосылки', value=False)
is_geom_help = st.sidebar.toggle('Геом. характеристики подробно', value=False)


##pile_punch_dir = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
##+ '/pages/pile_punch/')
##sys.path.append(pile_punch_dir)

def _formula(latex_string: str) -> typing.Any:
    mathml_output = latex2mathml.converter.convert(latex_string)
    omml_output = mathml2omml.convert(mathml_output)
    xml_output = (
        f'<p xmlns:m="http://schemas.openxmlformats.org/officeDocument'
        f'/2006/math">{omml_output}</p>'
    )
    return parse_xml(xml_output)[0]

def add_math(p, latex_string) -> None:
    p._p.append(_formula(latex_string))

def divide_latex(string):
    string_text, string_latex = [[]], [[]]
    if string[0] == '$': cursor = 1
    else: cursor = -1
    if cursor == 1 and string[0] != '$':
        string_latex[-1].append(string[0])
    else: string_text[-1].append(string[0])
    for i in range(1, len(string)):
        if string[i] == '$':
            cursor = cursor*(-1)
            string_latex.append([])
            string_text.append([])
        if cursor == 1 and string[i] != '$':
            string_latex[-1].append(string[i])
            string_text[-1] = 'NONE'
        if cursor == -1 and string[i] != '$':
            string_text[-1].append(string[i])
            string_latex[-1] = 'NONE'
    for i in range(len(string_text)):
        temp = ''
        for j in string_text[i]: temp += j
        string_text[i] = temp
    for i in range(len(string_latex)):
        temp = ''
        for j in string_latex[i]: temp += j
        string_latex[i] = temp
    return string_text, string_latex

def add_text_latex (p, string):
    string_text, string_latex = divide_latex(string)
    for i in range(len(string_text)):
        if string_text[i] != 'NONE':
            p.add_run(string_text[i])
        else: add_math(p, string_latex[i])

def n_number(number,rnd):
    return '{:.{deci}f}'.format(number, deci=rnd)

def delete_paragraph(paragraph):
    p = paragraph._element
    p.getparent().remove(p)
    paragraph._p = paragraph._element = None

table_concretes_data = pd.read_excel('RC_data.xlsx', sheet_name="Concretes_SP63", header=[0])
table_reinf_data = pd.read_excel('RC_data.xlsx', sheet_name="Reinforcement_SP63", header=[0])
available_concretes = table_concretes_data['Class'].to_list()

center = [25.0, 50.0]

def find_contour_geometry (V, M, Rbt, Rsw, h0, F, Mxloc, Myloc, deltaMx,  deltaMy, xcol, ycol, M_abs, delta_M_exc, F_dir, is_sw, qsw, sw_mode):
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
    kM0_check = Mx/(Mbxult+Mswxult_check) + My/(Mbyult+Mswyult_check)
    kM0_check = round(kM0_check, 3)
    kM_check = round(min(kM0_check, kF_check/2), 3)
    kb = round(kbF + kbM, 3)
    swAsw_sol = Rbt*h0*(kb-1)/(0.8*Rsw)
    k_check = round(kF_check + kM_check, 3)

    #print(is_sw, qsw, sw_mode)
    #print(Fswult_check, Mswxult_check, Mswyult_check)
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
            'kF_check': kF_check, 'kM0_check': kM0_check, 'kM_check': kM_check, 'k_check': k_check
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
    
def draw_scheme(b, h, h0,
                cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT,
                red_contours, blue_contours, center, sizes):
    x_cont_min, x_cont_max,y_cont_min, y_cont_max, dx, dy = sizes
    arrows_props = dict(arrowcolor="black", arrowsize=2.5, arrowwidth=0.5, arrowhead=5, axref='x', ayref='y', xref='x', yref='y', arrowside='end')
    text_props = dict(font=dict(color='black',size=14), showarrow=False, bgcolor="#ffffff")
    smax = max(dx, dy)
    fig = go.Figure()
    #Добавляем колонну
    xx = [0, b, b, 0, 0]
    yy = [0, 0, h, h, 0]
    #hatch = dict(fillpattern=dict(fgcolor='black', size=10, fillmode='replace', shape="/"))
    #**hatch
    fig.add_trace(go.Scatter(x=xx, y=yy, showlegend=False, fill='toself', fillcolor = 'rgba(128, 128, 128, 0.3)', mode='lines', line=dict(color='black', width=1.5)))
    fig.add_trace(go.Scatter(x=[0, b], y=[h/2, h/2], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[b/2, b/2], y=[0, h], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=xx, y=yy, showlegend=False, mode='lines', line=dict(color='black')))

    #Красные линии
    for contour in red_contours:
        fig.add_trace(go.Scatter(x=contour[0], y=contour[1], showlegend=False, mode='lines', line=dict(color='red', width=1.5)))
    #Линии контура
    for contour in blue_contours:
        fig.add_trace(go.Scatter(x=contour[0], y=contour[1], showlegend=False, mode='lines', line=dict(color='blue', width=3)))

    #НИЖНЯЯ РАЗМЕРНАЯ ЦЕПОЧКА
    #Добавляем ширину колонны
    add = 0.1*smax
    fig.add_annotation(x=0, ax=b, y=y_cont_min-add, ay=y_cont_min-add, **arrows_props)
    fig.add_annotation(x=b, ax=0, y=y_cont_min-add, ay=y_cont_min-add, **arrows_props)
    fig.add_trace(go.Scatter(x=[0, 0], y=[0, y_cont_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[b, b], y=[0, y_cont_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=b/2, y=y_cont_min-0.95*add, text=f'{float(b):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Добавляем ширину контура
    fig.add_annotation(x=x_cont_min, ax=x_cont_max, y=y_cont_min-2*add, ay=y_cont_min-2*add, **arrows_props)
    fig.add_annotation(x=x_cont_max, ax=x_cont_min, y=y_cont_min-2*add, ay=y_cont_min-2*add, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_cont_min, x_cont_min], y=[0, y_cont_min-2.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[x_cont_max, x_cont_max], y=[0, y_cont_min-2.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_cont_max+x_cont_min)/2, y=y_cont_min-1.95*add, text=f'{float(abs(x_cont_max-x_cont_min)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Размер от колонны до левой грани контура
    if abs(x_cont_min)>0:
        fig.add_annotation(x=0, ax=x_cont_min, y=y_cont_min-add, ay=y_cont_min-add, **arrows_props)
        fig.add_annotation(x=x_cont_min, ax=0, y=y_cont_min-add, ay=y_cont_min-add, **arrows_props)
        fig.add_trace(go.Scatter(x=[x_cont_min, x_cont_min], y=[0, y_cont_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=x_cont_min/2, y=y_cont_min-0.95*add, text=f'{float(abs(x_cont_min)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Размер от колонны до правой грани контура
    if abs(x_cont_max)>b:
        fig.add_annotation(x=b, ax=x_cont_max, y=y_cont_min-add, ay=y_cont_min-add, **arrows_props)
        fig.add_annotation(x=x_cont_max, ax=b, y=y_cont_min-add, ay=y_cont_min-add, **arrows_props)
        fig.add_trace(go.Scatter(x=[x_cont_max, x_cont_max], y=[0, y_cont_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=(x_cont_max+b)/2, y=y_cont_min-0.95*add, text=f'{float(abs(x_cont_max-b)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))

    #Добавляем высоту колонны
    fig.add_annotation(x=x_cont_min-add, ax=x_cont_min-add, y=0, ay=h, **arrows_props)
    fig.add_annotation(x=x_cont_min-add, ax=x_cont_min-add, y=h, ay=0, **arrows_props)
    fig.add_trace(go.Scatter(x=[0, x_cont_min-1.1*add], y=[0, 0], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[0, x_cont_min-1.1*add], y=[h, h], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=x_cont_min-1.05*add, y=h/2, text=f'{float(h):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Добавляем высоту контура
    fig.add_annotation(x=x_cont_min-2*add, ax=x_cont_min-2*add, y=y_cont_min, ay=y_cont_max, **arrows_props)
    fig.add_annotation(x=x_cont_min-2*add, ax=x_cont_min-2*add, y=y_cont_max, ay=y_cont_min, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_cont_min, x_cont_min-2.1*add], y=[y_cont_min, y_cont_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[x_cont_min, x_cont_min-2.1*add], y=[y_cont_max, y_cont_max], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=x_cont_min-2.05*add, y=(y_cont_max+y_cont_min)/2, text=f'{float(abs(y_cont_max-y_cont_min)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Размер от колонны до нижней грани контура
    if abs(y_cont_min)>0:
        fig.add_annotation(x=x_cont_min-add, ax=x_cont_min-add, y=0, ay=y_cont_min, **arrows_props)
        fig.add_annotation(x=x_cont_min-add, ax=x_cont_min-add, y=y_cont_min, ay=0, **arrows_props)
        fig.add_trace(go.Scatter(x=[0, x_cont_min-1.1*add], y=[y_cont_min, y_cont_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=x_cont_min-1.05*add, y=(y_cont_min)/2, text=f'{float(abs(y_cont_min)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Размер от колонны до верхней грани контура
    if abs(y_cont_max)>h:
        fig.add_annotation(x=x_cont_min-add, ax=x_cont_min-add, y=h, ay=y_cont_max, **arrows_props)
        fig.add_annotation(x=x_cont_min-add, ax=x_cont_min-add, y=y_cont_max, ay=h, **arrows_props)
        fig.add_trace(go.Scatter(x=[0, x_cont_min-1.1*add], y=[y_cont_min, y_cont_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=x_cont_min-1.05*add, y=(y_cont_max+h)/2, text=f'{float(abs(y_cont_max-h)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
      
    arrows_axes_props = dict(arrowcolor="red", arrowsize=3, arrowwidth=0.7, arrowhead=3, axref='x', ayref='y', xref='x', yref='y', arrowside='end')
    text_props_axes = dict(font=dict(color='red',size=16), showarrow=False)
    #Оси колонны
    fig.add_annotation(x=x_cont_max+2*add, ax=b/2, y=h/2, ay=h/2, **arrows_axes_props)
    fig.add_annotation(x=b/2, ax=b/2, y=y_cont_max+2.5*add, ay=h/2, **arrows_axes_props)

    if round(center[1],3)!=round(h/2,3): #Если ось х контура не совпадает с центом колонны, то дополнительно рисуем оси контура
        fig.add_annotation(x=x_cont_max+2*add, ax=center[0], y=center[1], ay=center[1], **arrows_axes_props)
        fig.add_annotation(dict(x=x_cont_max+2*add, y=h/2, text='x', textangle=0, yanchor='middle',xanchor='left', **text_props_axes))
        fig.add_annotation(dict(x=x_cont_max+2*add, y=center[1], text='xc', textangle=0, yanchor='middle',xanchor='left', **text_props_axes))
        #Добавляем эксцентриситет
        fig.add_annotation(x=x_cont_max, ax=x_cont_max, y=h/2, ay=center[1], **arrows_props)
        fig.add_annotation(x=x_cont_max, ax=x_cont_max, y=center[1], ay=h/2, **arrows_props)
        fig.add_annotation(dict(x=x_cont_max-0.05*add, y=(center[1]+h/2)/2, text=f'{float(round(abs(center[1]-h/2),2)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    else:
        fig.add_annotation(dict(x=x_cont_max+2*add, y=center[1], text='x, xc', textangle=0, yanchor='middle',xanchor='left', **text_props_axes))
    
    if round(center[0],3)!=round(b/2,3):  #Если ось y контура не совпадает с центом колонны, то дополнительно рисуем оси контура
        fig.add_annotation(x=center[0], ax=center[0], y=y_cont_max+2.5*add, ay=center[1], **arrows_axes_props)
        fig.add_annotation(dict(x=b/2, y=y_cont_max+2.5*add, text='y', textangle=0, yanchor='bottom',xanchor='center', **text_props_axes))
        fig.add_annotation(dict(x=center[0], y=y_cont_max+2.5*add, text='yc', textangle=0, yanchor='bottom',xanchor='center', **text_props_axes))
        #Добавляем эксцентриситет
        fig.add_annotation(x=b/2, ax=center[0], y=y_cont_max, ay=y_cont_max, **arrows_props)
        fig.add_annotation(x=center[0], ax=b/2, y=y_cont_max, ay=y_cont_max, **arrows_props)
        fig.add_annotation(dict(x=(center[0]+b/2)/2, y=y_cont_max+0.05*add, text=f'{float(round(abs(center[0]-b/2),2)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    else:
        fig.add_annotation(dict(x=center[0], y=y_cont_max+2.5*add, text='y, yc', textangle=0, yanchor='bottom',xanchor='center', **text_props_axes))

    #Расстояние до наиболее удаленных точек
    #Вдоль оси x (подписи сверху)
    fig.add_annotation(x=x_cont_min, ax=center[0], y=y_cont_max+add, ay=y_cont_max+add, **arrows_props)
    fig.add_annotation(x=center[0], ax=x_cont_min, y=y_cont_max+add, ay=y_cont_max+add, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_cont_min, x_cont_min], y=[y_cont_max, y_cont_max+1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_cont_min+center[0])/2, y=(y_cont_max+1.05*add), text=f'{float(round(abs((x_cont_min-center[0])),2)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    fig.add_annotation(x=x_cont_max, ax=center[0], y=y_cont_max+add, ay=y_cont_max+add, **arrows_props)
    fig.add_annotation(x=center[0], ax=x_cont_max, y=y_cont_max+add, ay=y_cont_max+add, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_cont_max, x_cont_max], y=[y_cont_max, y_cont_max+1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_cont_max+center[0])/2, y=(y_cont_max+1.05*add), text=f'{float(round(abs((x_cont_max-center[0])),2)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))

    #Вдоль оси y (подписи справа)
    fig.add_annotation(x=x_cont_max+add, ax=x_cont_max+add, y=y_cont_max, ay=center[1], **arrows_props)
    fig.add_annotation(x=x_cont_max+add, ax=x_cont_max+add, y=center[1], ay=y_cont_max, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_cont_max, x_cont_max+1.1*add], y=[y_cont_max, y_cont_max], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_cont_max+0.95*add), y=(y_cont_max+center[1])/2, text=f'{float(round(abs(y_cont_max-center[1]),2)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    fig.add_annotation(x=x_cont_max+add, ax=x_cont_max+add, y=y_cont_min, ay=center[1], **arrows_props)
    fig.add_annotation(x=x_cont_max+add, ax=x_cont_max+add, y=center[1], ay=y_cont_min, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_cont_max, x_cont_max+1.1*add], y=[y_cont_min, y_cont_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_cont_max+0.95*add), y=(y_cont_min+center[1])/2, text=f'{float(round(abs(y_cont_min-center[1]),2)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))

    
    fig.add_trace(go.Scatter(x=[center[0]], y=[center[1]], showlegend=False, mode="markers", marker_symbol=4, marker_size=15, line=dict(color='green')))
    fig.update_yaxes(scaleanchor="x",scaleratio=1,title="y")
    fig.update_xaxes(dict(title="x", visible=False))
    fig.update_yaxes(visible=False)
    #autosize=True,
    fig.update_layout(margin={'l': 0, 'r': 0, 't': 0, 'b': 0})
    fig.update_layout(height=400, width=400)
    file_stream = io.BytesIO()
    file_stream2 = 0
    fig.write_image(file_stream, format='png', width=400, height=400, scale=8)
##    fig.write_image(file_stream2, format='svg', width=400, height=400, scale=8)
##    fig.write_image('test.svg', format='svg', width=400, height=400, scale=8)
    return fig, file_stream, file_stream2

with st.expander('Описание исходных данных'):
    st.write('$b$ и $h$ – ширина и высота поперечного сечения сечения колонны, см;')
    st.write('$h_0$ – приведенная рабочая высота поперечного сечения плиты, см;')
    st.write('$c_L$ и $c_R$ – расстояние в свету до левой и правой грани плиты от грани колонны, см. Вводится если левая или правая граница контура отключена;')
    st.write('$c_B$ и $c_T$ – расстояние в свету до нижней и верхней грани плиты от грани колонны, см. Вводится если верхняя или нижняя граница контура отключена;')
    st.write('$R_{bt}$ – расчетное сопротивление на растяжение бетона, МПа;')
    st.write('''$\\gamma_{bt}$ – коэффициент, вводимый к расчетному сопротивлению бетона на растяжение.
    Например, в соответствии с п. 6.1.12 (а) СП 63.13330.2018 при продолжительном действии нагрузки величина данного коэффициента принимается равной 0.9;''')
    st.write('$R_{sw}$ – расчетное сопротивление поперечного армирования, МПа;')
    st.write('$n_{sw}$ – число стержней поперечного армирования в одном ряду, пересекающих пирамиду продавливания, шт.;')
    st.write('$s_{w}$ – шаг рядов поперечного армирования вдоль расчетного контура, мм;')
    st.write('$d_{sw}$ – диаметр поперечного армирования, мм;')
    st.write('$k_{sw}, %$ – вклад поперечного армирования в несущую способность в процентах от максимально допустимого;')
    st.write('''$F$ – сосредоточенная продавливающая сила, тс.
    Значение сосредоточенной силы следует принимать за вычетом сил, действующих в пределах основания
    пирамиды продавливания в противоположном направлении; ''')
    st.write('$M_{x,loc}$ – сосредоточенный момент в месте приложения сосредоточенной нагрузки в ПЛОСКОСТИ оси $x$ (относительно оси $y$), тсм. Положительное значение "сжимает" правую грань расчетного контура (см. "положительные направления нагрузок");')
    st.write('$M_{y,loc}$ – сосредоточенный момент в месте приложения сосредоточенной нагрузки в ПЛОСКОСТИ оси $y$ (относительно оси $x$), тсм. Положительное значение "сжимает" верхнюю грань расчетного контура (см. "положительные направления нагрузок");')
    st.write('$\\delta_{Mx}$ – понижающий коэффициент к моментам в плоскости оси $x$;')
    st.write('$\\delta_{My}$ – понижающий коэффициент к моментам в плоскости оси $y$;')
    st.write('''Параметр "учитывать знак $F \\cdot e$".
    Если данный параметр включен, то момент от внецентренного приложения сосредоточенной силы,
    в зависимости от величины эксцентриситета, может догружать или разгружать расчетный контур.
    В противном случае момент от эксцентриситета всегда догружает расчетный контур;''')
    st.write('''Параметр "направление $F$". Данный параметр влияет на результаты расчета, только если активирован параметр "учитывать знак $F \\cdot e$". При положительном
    значении эксцентриситета и силе направленной вверх, момент от эксцентриситета $F \\cdot e$ будет положительным.
    Если сила направлена вниз – отрицательным. Более наглядно этот факт понятен из рисунка "положительные направления нагрузок";''')
    st.write('''Параметр "$\\delta_{M}$ для $F \\cdot e$". Данный параметр указывает, учитывать ли понижающие коэффициенты $\\delta_{M}$ для моментов от эксцентриситета.
    В соответствии с п. 8.1.46 указания по снижению момента представлены только в абзаце, содержащем $M_{loc}$.''')

if True: #Ввод исходных данных
    cols = st.columns([1, 0.5])
    cols2_size = [1, 1, 1]
    cols2 = cols[1].columns(cols2_size)
    ##cols2 = cols[1].columns(cols2_size)
    ##cols2 = cols[1].columns(cols2_size)
    ##cols2 = cols[1].columns(cols2_size)
    ##cols2 = cols[1].columns(cols2_size)
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
    cL = cols2[1].number_input(label='$c_L$, см', step=5.0, format="%.1f", value=10.0, disabled=is_cL, min_value=0.0, max_value=500.0, label_visibility="collapsed")
    cL = round(cL,2)


    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$c_R$, см')
    is_cR = cols2[2].toggle('Контур_справа', value=True, label_visibility="collapsed")
    cR = cols2[1].number_input(label='$c_R$, см', step=5.0, format="%.1f", value=10.0, disabled=is_cR, min_value=0.0, max_value=500.0, label_visibility="collapsed")
    cR = round(cR,2)


    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$c_B$, см')
    is_cB = cols2[2].toggle('Контур_снизу', value=True, label_visibility="collapsed")
    cB = cols2[1].number_input(label='$c_B$, см', step=5.0, format="%.1f", value=10.0, disabled=is_cB, min_value=0.0, max_value=500.0, label_visibility="collapsed")
    cB = round(cB,2)


    cols2 = cols[1].columns(cols2_size)
    cols2[0].write('$c_T$, см')
    is_cT = cols2[2].toggle('Контур_сверху', value=True, label_visibility="collapsed")
    cT = cols2[1].number_input(label='$c_T$, см', step=5.0, format="%.1f", value=10.0, disabled=is_cT, min_value=0.0, max_value=500.0, label_visibility="collapsed")
    cT = round(cT,2)

    ##cols3 = st.columns([1, 0.5])
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
    Rbt = round(Rbt,4)
    #st.write(Rbt)
    #Rbt = 0.01*Rbt
    F = cols2[3].number_input(label='$F$, тс', step=0.5, format="%.1f", value=28.0, min_value=1.0, max_value=50000.0, label_visibility="visible")
    Mxloc = cols2[4].number_input(label='$M_{x,loc}$, тсм', step=0.5, format="%.2f", value=4.0, label_visibility="visible")
    Myloc = cols2[5].number_input(label='$M_{y,loc}$, тсм', step=0.5, format="%.2f", value=7.0, label_visibility="visible")
    deltaMx = cols2[6].number_input(label='$\\delta_{Mx}$', step=0.1, format="%.2f", value=0.5, min_value=0.0, max_value=2.0, label_visibility="visible")
    deltaMy = cols2[7].number_input(label='$\\delta_{My}$', step=0.1, format="%.2f", value=0.5, min_value=0.0, max_value=2.0, label_visibility="visible")
    cols2 = st.columns([1.1, 1.1, 1.1, 1, 1])
    delta_M_exc = cols2[-1].selectbox(label='$\\delta_{M}$ для $F \\cdot e$', options=['да', 'нет'], index=0, label_visibility="visible")
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
    is_sw = cols2[0].selectbox(label='Поперечное арм.', options=['да', 'нет'], index=1, label_visibility="visible")
    if is_sw == 'да': is_sw=True
    else: is_sw=False
    sw_mode = cols2[1].selectbox(label='Режим арм.', options=['подбор','проверка'], index=0, label_visibility="visible")
    if sw_mode == 'подбор': sw_block=True
    else: sw_block=False

    qsw = 0.0
    Rsw = 1.734
    if is_sw:
        cols2 = st.columns([1,1,1,1,1,1])
        
        rtype = cols2[0].selectbox(label='Арматура', options=['A240', 'A400', 'A500'], index=0, label_visibility="visible")
        selected_reinf_data = table_reinf_data.loc[table_reinf_data['Class'] == rtype]
        selected_reinf_data = selected_reinf_data.to_dict('records')[0]
        Rsw0 = selected_reinf_data['Rsw']
        Rsw = cols2[1].number_input(label='$R_{sw}$, МПа', value=Rsw0, label_visibility="visible", disabled=True)
        Rsw = 0.01019716213*Rsw
        Rsw = round(Rsw,3)
        nsw = cols2[2].number_input(label='$n_{sw}$, шт.', step=1, format="%i", value=2, min_value=1, max_value=10, label_visibility="visible", disabled=sw_block)
        nsw = round(nsw)
        sw = cols2[3].number_input(label='$s_w$, см', step=5.0, format="%.2f", value=6.0, min_value=0.0, max_value=100.0, label_visibility="visible", disabled=sw_block)
        sw = round(sw,2)
        dsw = cols2[4].selectbox(label='$d_{sw}$, мм', options=[6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32], index=0, label_visibility="visible", disabled=sw_block)
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
        if sw_mode == 'проверка':
            cols2[5].number_input(label='$k_{sw}$, %', step=5.0, format="%.1f", value=ksw0*100, label_visibility="visible", disabled=True)
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
    

    red_contours = generate_red_contours(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
    blue_contours, contour_gamma, contour_sides, contour_len, contour_center, contour_len_pr = generate_blue_contours(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
    num_elem = len(blue_contours)
    rez = 0
    cont_arr = np.array(blue_contours)
    x_cont_min = cont_arr[:,0,:].min()
    x_cont_max = cont_arr[:,0,:].max()
    y_cont_min = cont_arr[:,1,:].min()
    y_cont_max = cont_arr[:,1,:].max()
    dx = x_cont_max - x_cont_min
    dy = y_cont_max - y_cont_min
    sizes = [x_cont_min, x_cont_max,y_cont_min, y_cont_max, dx, dy]

if num_elem>=2:
    rez = find_contour_geometry(blue_contours, contour_gamma, Rbt, Rsw, h0, F, Mxloc, Myloc, deltaMx, deltaMy, b/2, h/2, M_abs, delta_M_exc, F_dir, is_sw, qsw0, sw_mode)
    center = [rez['xc'], rez['yc']]
    #st.write(rez)

fig, image_stream, image_stream2 = draw_scheme(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT,
                  red_contours, blue_contours, center, sizes)
#, use_container_width=True
cols[0].plotly_chart(fig)

if num_elem<2:
    st.write('В расчете должно быть минимум два участка!')
    st.stop()

doc = Document('Template_punch.docx')
doc.core_properties.author = 'Автор'
p = doc.paragraphs[-1]
delete_paragraph(p)
string = 'Расчет на продавливание при действии сосредоточенной силы и изгибающих моментов.'
doc.add_heading(string, level=0)
#st.subheader(string)

string = 'Расчет производится согласно СП 63.13330.2018 п. 8.1.46 – 8.1.52.'
if is_sw: string += ' Поперечная арматура принимается равномерно расположенной по периметру расчетного контура.'
doc.add_paragraph().add_run(string)


if is_init_help: #Расчетные предпосылки
    with st.expander('Расчетные предпосылки'):
        string = 'Расчетные предпосылки.'
        doc.add_heading(string, level=1)
        st.subheader(string)

        string = 'Расчет производится согласно СП 63.13330.2018 п. 8.1.46 – 8.1.52.'
        if is_sw: string += ' Поперечная арматура принимается равномерно расположенной по периметру расчетного контура.'
        st.write(string)
        
        string = 'Проверка прочности в общем случае выполняется из условия (8.96):'
        st.write(string)
        doc.add_paragraph().add_run(string)
        string = '$\\dfrac{F}{F_{b,ult}+F_{sw,ult}} + \\dfrac{M_x}{M_{bx,ult} + M_{sw,x,ult}} + \\dfrac{M_y}{M_{by,ult}+ M_{sw,y,ult} }  \\le 1.0.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))

        string = 'Здесь $F$, $M_{x}$ и $M_{y}$ – сосредоточенная сила и изгибающие моменты от внешней нагрузки, учитываемые при расчете на продавливание, определяемые в соответствии с п. 8.1.46;'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$F_{b,ult}$, $M_{bx,ult}$ и $M_{by,ult}$ – предельные сосредоточенная сила и изгибающие моменты, которые могут быть восприняты бетоном в расчетном поперечном сечении;'
        st.write(string)
        p = doc.add_paragraph()
        add_text_latex(p, string)
        p.paragraph_format.first_line_indent = Mm(0)

        string = '$F_{sw,ult}$, $M_{sw,x,ult}$ и $M_{sw,y,ult}$ – предельные сосредоточенная сила и изгибающие моменты, которые могут быть восприняты арматурой в расчетном поперечном сечении.'
        st.write(string)
        p = doc.add_paragraph()
        add_text_latex(p, string)
        p.paragraph_format.first_line_indent = Mm(0)

        string = 'Сосредоточенные моменты от внешней нагрузки $M_{x}$ и $M_{y}$, учитываемые при расчете на продавливание, определяются в соответствии указаниями с п. 8.1.46.'
        string += ' В общем случае, при расположении сосредоточенной силы $F$ внецентренно относительно центра тяжести контура расчетного поперечного сечения'
        string += ' с эксцентриситетами $e_x$ и $e_y$ по формуле:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        if M_abs:
            if delta_M_exc:
                string = '$M_x = (|M_{x,loc}| +  F \\cdot | e_x |) \\cdot \\delta_{Mx}; \\quad'
                string += ' M_y = (|M_{y,loc}| +  F \\cdot | e_y |) \\cdot \\delta_{My}.$'
            else:
                string = '$M_x = |M_{x,loc}| \\cdot \\delta_{Mx} +  F \\cdot | e_x| ; \\quad'
                string += ' M_y =|M_{y,loc}| \\cdot \\delta_{My} +  F \\cdot | e_y|.$'
        else:
            if F_dir == 'вверх': znak = '+'
            else: znak = '-'
            if delta_M_exc:
                string = '$M_x = |M_{x,loc}' + znak + 'F \\cdot e_x| \\cdot \\delta_{Mx}; \\quad'
                string += ' M_y = |M_{y,loc} ' + znak + ' F \\cdot e_y| \\cdot \\delta_{My}.$'
            else:
                string = '$M_x = |M_{x,loc} \\cdot \\delta_{Mx} ' + znak + ' F \\cdot e_x| ; \\quad'
                string += ' M_y = |M_{y,loc} \\cdot \\delta_{My} ' + znak + ' F \\cdot e_y| .$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'В данных формулах $M_{loc}$ – действующий момент в месте приложения сосредоточенной нагрузки.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Коэффициенты $\\delta_{Mx} \\le 1$ и $\\delta_{My} \\le 1$ учитывают положения п. 8.1.46:'
        string += ' при действии момента в месте приложения сосредоточенной нагрузки половину этого момента учитывают при расчете на продавливание, а другую половину – при расчете по нормальным сечениям.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Предельная продавливающая сила, воспринимаемая бетоном $F_{b,ult}$, вычисляется по формуле (8.88) с учетом формулы (8.89):'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
        string = '$F_{b,ult} = R_{bt} \\cdot h_0 \\cdot u.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Здесь $u$ и $h_0$ – периметр контура расчетного поперечного сечения и приведенная рабочая высота сечения, вычисляемая по формуле:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$h_0 = 0.5 \\cdot (h_{0x} + h_{0y}),$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'где $h_{0x}$ и $h_{0y}$ – рабочая высота сечения для продольной арматуры, расположенной в направлении осей $x$ и $y$.'
        st.write(string)
        p = doc.add_paragraph()
        add_text_latex(p, string)
        p.paragraph_format.first_line_indent = Mm(0)

        string = 'Предельная продавливающая сила, воспринимаемая арматурой $F_{sw,ult}$, при равномерном расположении арматуры вдоль контура расчетного поперечного сечения вычисляется по формуле (8.91):'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
        string = '$F_{sw,ult} = 0.8 \\cdot q_{sw} \\cdot u,$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'где $q_{sw}$ – усилие в поперечной арматуре на единицу длины контура расчетного поперечного сечения,'
        string += ' расположенной в пределах расстояния $0.5 \\cdot h_0$ по обе стороны от контура расчетного сечения'
        st.write(string)
        p = doc.add_paragraph()
        add_text_latex(p, string)
        p.paragraph_format.first_line_indent = Mm(0)

        string = '$q_{sw} = \\dfrac{R_{sw} \\cdot A_{sw} }{s_w};$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$A_{sw}$ – площадь сечения всей поперечной арматуры расположенная в пределах расстояния $0.5 \\cdot h_0$ по обе'
        string += ' стороны от контура расчетного поперечного сечения по периметру контура расчетного поперечного сечения (площадь поперечной арматуры в одном каркасе);'
        st.write(string)
        p = doc.add_paragraph()
        add_text_latex(p, string)
        p.paragraph_format.first_line_indent = Mm(0)

        string = '$s_w$ – шаг поперечной арматуры (шаг каркасов);'
        st.write(string)
        p = doc.add_paragraph()
        add_text_latex(p, string)
        p.paragraph_format.first_line_indent = Mm(0)

        string = '$u$ – периметр контура расчетного поперечного сечения.'
        st.write(string)
        p = doc.add_paragraph()
        add_text_latex(p, string)
        p.paragraph_format.first_line_indent = Mm(0)

        string = 'Предельный изгибающий момент, воспринимаемый бетоном $M_{b,ult}$, вычисляется по формуле (8.94):'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
        string = '$M_{b,ult} = R_{bt} \\cdot W_b \\cdot h_0.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
        string = 'где $W_b$ – момент сопротивления расчетного поперечного сечения, определяемый в соответствии с п. 8.1.51.'
        st.write(string)
        p = doc.add_paragraph()
        add_text_latex(p, string)
        p.paragraph_format.first_line_indent = Mm(0)

        string = 'Усилия $M_{sw,x,ult}$ и $M_{sw,y,ult}$, воспринимаемые поперечной арматурой, нормальной к продольной оси элемента и'
        string += ' расположенной равномерно вдоль контура расчетного сечения, определяются при действии изгибающего момента'
        string += ' соответственно в направлении осей $x$ и $y$ по формуле (8.97):'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$M_{sw,ult} = 0.8 \\cdot q_{sw} \\cdot W_{sw}.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'В дальнейших расчетах, в соответствии с п. 8.1.52, предполагаем, что'
        string += ' поперечная арматура расположена равномерно вдоль расчетного контура продавливания в пределах зоны, границы'
        string += ' которой отстоят на расстоянии $h_0/2$ в каждую сторону от контура продавливания бетона.'
        string += ' В этом случае значения моментов сопротивления поперечной арматуры при продавливании $W_{sw,x(y)}$ принимают равными соответствующим значениям $W_{bx}$ и $W_{by}$.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Введем следующей коэффициент:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$k_{sw} = \\dfrac{F_{sw,ult}}{F_{b,ult}} = \\dfrac{M_{sw,ult}}{M_{b,ult}} = \\dfrac{0.8 \\cdot q_{sw}}{R_{bt} \\cdot h_0}.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Данный коэффициент можно интерпретировать, как вклад поперечного армирования в несущую способность. C учетом данного коэффициента и предыдущих выкладок условие прочности (8.96) можно переписать в виде:'
        st.write(string)
        doc.add_paragraph().add_run(string)
        string = '$\\dfrac{F}{F_{b,ult} \\cdot (1+k_{sw})} + \\dfrac{M_x}{M_{bx,ult} \\cdot (1+k_{sw})} + \\dfrac{M_y}{M_{by,ult} \\cdot (1+k_{sw}) }  \\le 1.0.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
    
        string = 'В случае, если поперечная арматура не учитывается в расчете, $k_{sw}=0.0$.'
        string += ' В противном случае, если поперечная арматура учитывается в расчете, на коэффициент $k_{sw}$ накладываются следующие ограничения:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$0.25 \\le k_{sw} \\le 1.0.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Нижняя и верхняя граница $k_{sw}$ связаны со ограничениями, приведенными в п. 8.1.48 и 8.1.50.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Во-первых, поперечную арматуру можно учитывать в расчете при выполнении условия $F_{sw,ult} \\ge 0.25 \\cdot F_{b,ult}$.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Во-вторых, усилия, воспринимаемые поперечной арматурой, не могут превышать усилия, воспринимаемые бетоном, т.е.'
        string += ' $F_{b,ult} + F_{sw,ult} \\le 2 \\cdot F_{b,ult}$,'
        string += ' $M_{bx,ult} + M_{sw,x,ult} \\le 2 \\cdot M_{bx,ult}$,'
        string += ' $M_{by,ult} + M_{sw,y,ult} \\le 2 \\cdot M_{by,ult}$.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Введем дополнительно коэффициенты $k_{b,F}$, $k_{b,M}$ и $k_b$ следующим образом:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$k_{b,F} = \\dfrac{F}{F_{b,ult}}; \\quad'
        string += ' k_{b,M} = \\dfrac{M_x}{M_{bx,ult}} + \\dfrac{M_y}{M_{by,ult}}; \\quad k_b = k_{b,F} + k_{b,M}$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'В результате, условие прочности примет вид:'
        st.write(string)
        doc.add_paragraph().add_run(string)
        string = '$\\dfrac{k_{b,F} + k_{b,M}}{1+k_{sw}} \\le 1.0.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Здесь $k_{b,F}$, $k_{b,M}$ и $k_b$ – коэффициенты использования прочности бетона расчетного поперечного сечения по силе, моментам и суммарный соответственно.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)


        string = 'В соответствии с п. 8.1.46 при действии сосредоточенных моментов и силы в условиях прочности соотношение между действующими'
        string += ' сосредоточенными моментами $M$, учитываемыми при продавливании, и предельными $M_{ult}$ принимают не более'
        string += ' половины соотношения между действующим сосредоточенным усилием $F$ и предельным $F_{ult}$.'
        string += ' Следовательно, $k_{b,M} \\le 0.5 \\cdot k_{b,F}$. В случае нарушения данного условия значение $k_{b,M}$ принимается равным $k_{b,M}=0.5 \\cdot k_{b,F}$.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Условие прочности, в случае $k_{b,M} \\ge 0.5 \\cdot k_{b,F}$ примет вид:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$\\dfrac{1.5 \\cdot k_{b,F}}{1+k_{sw}} \\le 1.0.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Из данного неравенства можно получить условие прочности, справедливое для любого значения моментов:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$k_{b,F} \\le \\dfrac{1+k_{sw}}{1.5} \\Rightarrow F \\le \\dfrac{F_{b,ult} \\cdot (1+k_{sw})}{1.5}.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Аналогично при отсутствии поперечной арматуры ($k_{sw}=0.0$):'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$k_{b,F} \\le \\dfrac{1}{1.5} \\Rightarrow F \\le \\dfrac{F_{b,ult}}{1.5}.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = 'Для расчета используется следующая последовательность.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '1. Выполняется расчет геометрических характеристик контура расчетного поперечного сечения.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '2. Выполняется расчет предельных усилий, воспринимаемых бетоном расчетного поперечного сечения.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '3. Вычисление коэффициентов $k_{b,F}$ и $k_{b,M}$.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '4. Проверка условия $k_{b,M} \\le 0.5 \\cdot k_{b,F}$. Если условие не выполняется, коэффициент $k_{b,M}$ принимается равным $k_{b,M} = 0.5 \\cdot k_{b,F}$.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '5. Вычисление коэффициента использования прочности бетона расчетного поперечного сечения $ k_{b} = k_{b,F} + k_{b,M}$.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '6. В случае, если $k_{b} \\le 1.0 $ прочность обеспечена без установки поперечной арматуры.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '7. В случае, если $k_{b} > 2.0 $ прочность не может быть обеспечена, необходимо увеличение габаритов площадки передачи нагрузки, либо толщины плиты, либо класса бетона.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '8. В случае, если $1.0 < k_{b} \\le 2.0 $ требуется установка поперечной арматуры.'
        string += ' В этом случае требуемое соотношение $A_{sw}/s_w$, с учетом выражений для $k_{sw}$ и $q_{sw}$ определяется по формуле:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string = '$\\dfrac{A_{sw}}{s_w} \\ge \\dfrac{R_{bt} \\cdot h_0 \\cdot (k_{b} - 1)}{0.8 \\cdot R_{sw}}.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        #string = '$\\dfrac{F}{F_{b,ult}+{F_{sw,ult}} + \\left(\\dfrac{\\delta_{Mx} \\cdot M_x}{M_{bx,ult}+M_{sw,x,ult}} + \\dfrac{\\delta_{My} \\cdot M_y}{M_{by,ult}+M_{sw,y,ult}} \\right) = k_F + k_M \\le 1.$'

with st.expander('Исходные данные'):
    string = 'Исходные данные.'
    doc.add_heading(string, level=1)
    st.subheader(string)

    string = 'Геометрия.'
    doc.add_heading(string, level=2)
    st.subheader(string)

    string = 'Ширина зоны передачи нагрузки $b=' + str(round(b,2)) + '\\cdot см$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Высота зоны передачи нагрузки $h=' + str(round(h,2)) + '\\cdot см$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Приведенная рабочая высота сечения плиты $h_0=' + str(round(h0,2)) + '\\cdot см$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = 'Приложенные усилия.'
    doc.add_heading(string, level=2)
    st.subheader(string)

    string = 'Принятое положительное направление усилий.'
    if F_dir == 'вверх':
        image_f_dir = "F_up.png"
    if F_dir == 'вниз':
        image_f_dir = "F_down.png"
    add_text_latex(doc.add_paragraph(), string)
    doc.add_picture(image_f_dir, width=Mm(60))
    #doc.add_picture('test.svg', width=Mm(80))
    p = doc.paragraphs[-1]
    p.paragraph_format.first_line_indent = Mm(0)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    string = 'Сосредоточенная сила $F=' + str(F) + '\\cdot тс$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Направление действия силы $F$ – ' + F_dir + '.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Изгибающий момент в плоскости оси $x$ в месте приложения силы $M_{x,loc}=' + str(Mxloc) + '\\cdot тсм$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Понижающий коэффициент для'
    if delta_M_exc:
        string += ' всех моментов в плоскости оси $x$, '
    else: string += ' момента $M_{x,loc}$ в плоскости оси $x$, '
    string += '$\\delta_{Mx}=' + str(deltaMx) + '$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = 'Изгибающий момент в плоскости оси $y$ в месте приложения силы $M_{y,loc}=' + str(Myloc) + '\\cdot тсм$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Понижающий коэффициент для'
    if delta_M_exc:
        string += ' всех моментов в плоскости оси $y$, '
    else: string += ' момента $M_{y,loc}$ в плоскости оси $y$, '
    string += '$\\delta_{My}=' + str(deltaMy) + '$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)


    string = 'Материалы.'
    doc.add_heading(string, level=2)
    st.subheader(string)
    string = 'Класс бетона по прочности на сжатие ' + str(ctype) + '.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Расчетное сопротивление бетона на растяжение $R_{bt}=' + str(Rbt0) + '\\cdot МПа$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Коэффициент, вводимый к расчетному сопротивлению бетона на растяжение $\\gamma_{bt}=' + str(gammabt) + '$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Расчетное сопротивление бетона на растяжение, учитываемое в расчете:'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string =  '$R_{bt}=R_{bt} \\cdot \\gamma_{bt} = ' + str(Rbt0) + '\\cdot' + str(gammabt)
    string += '=' + str(RbtMPA) + '\\cdot МПа='
    string += str(Rbt) + '\\cdot тс/см^2'
    string += '.$'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    if is_sw:
        string = 'Класс поперечной арматуры ' + str(rtype) + '.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
        string = 'Расчетное сопротивление поперечной арматуры, учитываемое в расчете:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

        string =  '$R_{sw}= ' + str(Rsw0) +  '\\cdot МПа='
        string += str(Rsw) + '\\cdot тс/см^2'
        string += '.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
    
    if is_sw:
        if sw_mode == 'проверка':
            string = 'Параметры заданного поперечного армирования.'
            doc.add_heading(string, level=2)
            st.subheader(string)
            string = 'Число стержней в одном ряду, пересекающих пирамиду продавливания ' + '$n_{sw}='  + str(nsw) + 'шт$.'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = 'Шаг рядов поперечного армирования вдоль расчетного контура ' + '$s_{w}='  +  str(sw) + '\\cdot см$.'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = 'Диаметр стержней поперечного армирования ' + '$d_{sw}=' + str(dsw) + '\\cdot мм$.'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = 'Площадь стержней поперечного армирования одного ряда, пересекающих пирамиду продавливания:'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = '$A_{sw} = \\dfrac{\\pi \\cdot d_{sw}^2 \\cdot n_{sw}}{4} = '
            string += '\\dfrac{\\pi \\cdot ' + str(dsw) + '^2 \\cdot' + str(nsw) + '}{4 \\cdot 100} =' 
            string += str(Asw) + '\\cdot см^2.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = 'Примечание. Деление на 100 в данной формуле необходимо для перевода $мм^2$ в $см^2$.'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = 'Усилие в поперечной арматуре на единицу длины контура расчетного поперечного сечения:'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = '$q_{sw} = \\dfrac{R_{sw} \\cdot A_{sw} }{s_w} = \\dfrac{' + str(Rsw) + '\\cdot' + str(Asw)
            string += '}' + '{' +  str(sw) +  '}=' + str(qsw0) + '\\cdot тс/см.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = 'Вклад поперечного армирования в несущую способность:'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)
            string = '$k_{sw} = \\dfrac{0.8 \\cdot q_{sw}}{R_{bt} \\cdot h_0} = \\dfrac{0.8 \\cdot'
            string += str(qsw0) + '}{' + str(Rbt) + '\\cdot' + str(h0) +  '}='
            string += str(ksw0) + '.$'
            st.write(string)
            add_text_latex(doc.add_paragraph(), string)

            #if 0.25<=ksw0<=1.0:
            #    string = 'Так как условие $0.25 \\le k_{sw} \\le 1.0$ выполняется, в расчете принимаем $k_{sw}=' + str(ksw) + '$ и $q_{sw}=' + str(qsw) + '\\cdot тс/см$.'
            #    st.write(string)
            #    add_text_latex(doc.add_paragraph(), string)
            #if ksw0<0.25:
            #    string = 'Так как условие $k_{sw} \\ge 0.25$ НЕ выполняется, поперечное армирование НЕ учитываем, в расчете принимаем $k_{sw}='  + str(ksw) + '$ и $q_{sw}=' + str(qsw) + '$.'
            #    st.write(string)
            #    add_text_latex(doc.add_paragraph(), string)
            #    string = 'Максимальное значение шага рядов поперечного армирования для учета поперечной арматуры в расчете составляет $s_{w, \\max}=' + str(sw_max) + '\\cdot см$.'
            #    st.write(string)
            #if ksw0>1.0:
            #    string = 'Так как условие $k_{sw} \\le 1.0$ НЕ выполняется, вклад поперечного армирования ограничивается, в расчете принимаем $k_{sw}='
            #    string += str(ksw) + '$ и $q_{sw}=' + str(qsw) + '\\cdot тс/см$.'
            #    st.write(string)
            #    add_text_latex(doc.add_paragraph(), string)

        string = 'Примечание. Поперечная арматура принимается равномерно расположенной по периметру расчетного контура.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)

if True: #Добавление эскиза расчетного контура в docx
    string = 'Эскиз расчетного контура.'
    doc.add_heading(string, level=1)
    doc.add_picture(image_stream, width=Mm(80))
    #doc.add_picture('test.svg', width=Mm(80))
    p = doc.paragraphs[-1]
    p.paragraph_format.first_line_indent = Mm(0)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

with st.expander('Геометрические характеристики контура'):
    string = 'Геометрические характеристики контура.'
    st.subheader(string)
    doc.add_heading(string, level=1)
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
                if qsw0>qsw:
                    string = 'Так как $F_{sw,ult} \\ge F_{b,ult}$, вклад поперечного армирования ограничиваем. В расчете принимаем:'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)
                    string = '$F_{sw,ult} = F_{b,ult}=' + str(rez['Fbult']) +  '\\cdot тс.$'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)
                

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
            if True: #Результаты проверки прочности по бетону
                if rez['k_check'] <= 1:
                    string = 'Так как $k=' + str(rez['k_check'])+ '<1$ прочность обеспечена.'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)
                if rez['k_check'] > 1:
                    string = 'Так как $k=' + str(rez['k_check'])+ '>1$ прочность не обеспечена, необходимо увеличение поперечного армирования.'
                    st.write(string)
                    add_text_latex(doc.add_paragraph(), string)


        if sw_mode == 'подбор':
            if rez['kb'] <= 1: #Если прочность может быть обеспечена
                string = 'Поперечная арматура не требуется.'
                st.write(string)
                add_text_latex(doc.add_paragraph(), string)


cols = st.columns([1,1,1])

#cols[0].write()

#st.write('Коэффициент использования по продольной силе $k_{bF}=' + str(rez['kbF']) + '$.')
#st.write('Коэффициент использования по моментам $k_{bМ}=' + str(rez['kbM']) + '$.')
#st.write('Суммарный коэффициент использования $k_b=' + str(rez['kb']) + '$.')

file_stream = io.BytesIO()
doc.save(file_stream)
st.sidebar.download_button('Сохранить исходные данные', file_name='1.docx', data=file_stream)







