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


def find_contour_geometry (V, M, Rbt, h0, F, Mx, My, deltaMx,  deltaMy, xcol, ycol):
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
    #Присваеваем максимум и минимум координат
    #в соответствии с координатами первой точки первой линии
    xmin0, xmax0 = V[:,0].min(), V[:,0].max()
    ymin0, ymax0 = V[:,1].min(), V[:,1].max()
    j = 0
    for i in V:
        #Извлекаем координаты начала и конца i-го участка
        x1, x2 = i[0]
        y1, y2 = i[1]
        #Вычисляем длину i-го участка
        L_i = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
        #Добавляем его длину в суммарную
        Lsum = Lsum + L_i
        #Вычисляем координаты центра i-го участка
        center_i = ((x2 - x1)/2 + x1, (y2 - y1)/2 + y1)
        #Вычисляем статические моменты i-го участка
        Sx_i = L_i*center_i[0]
        Sx_arr.append(Sx_i)
        Sy_i = L_i*center_i[1]
        Sy_arr.append(Sy_i)
        #Добавляем их в суммарные
        Sx = Sx + Sx_i
        Sy = Sy + Sy_i
        j += 1
    #Предельная сила, воспринимаемая бетоном
    Fbult = Lsum*Rbt*h0
    #Коэффициент использования по продольной силе
    kF= F/Fbult
    #Вычисляем координаты центра тяжести всего контура
    xc, yc = Sx/Lsum, Sy/Lsum
    ex, ey = xc - xcol, yc - ycol
    #Расчет характеристик "без масс"
    for i in V:
        #Вычисляем координаты минимума и максимума относительно геометрического центра тяжести
        xL, xR = xmin0 - xc, xmax0 - xc
        yB, yT = ymin0 - yc, ymax0 - yc
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
        Ix0_i = Lx_i**3/12
        Iy0_i = Ly_i**3/12
        Ix0_arr.append(Ix0_i)
        Iy0_arr.append(Iy0_i)
        #Моменты инерции относительно центра тяжести
        Ix_i = Ix0_i + L_i*x0**2
        Iy_i = Iy0_i + L_i*y0**2
        Ix_arr.append(Ix_i)
        Iy_arr.append(Iy_i)
        Ix = Ix + Ix_i
        Iy = Iy + Iy_i
    Wxl, Wxr = Ix/abs(xL), Ix/xR
    Wxmin = min(Wxl, Wxr)
    Wyb, Wyt = Iy/abs(yB), Iy/yT
    Wymin = min(Wyb, Wyt)
    Mbxult = Wxmin*h0*Rbt/100
    Mbyult = Wymin*h0*Rbt/100
    Mxexc = -F*ex/100
    Myexc = -F*ey/100
    Mxloc = Mx + Mxexc
    Myloc = My + Myexc
    kM = abs(Mxloc)/Mbxult*deltaMx + abs(Myloc)/Mbyult*deltaMy
    kM = min(kM, kF/2)
    k = kF + kM 
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
            'Mxloc': Mxloc, 'Myloc': Myloc,
            'Fbult': Fbult, 'Mbxult': Mbxult, 'Mbyult': Mbyult,
            'kF': kF, 'kM': kM, 'k': k}

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
        contour_x = [-cL0/2, -cL0/2]
        contour_y = [-cB0/2, h+cT0/2]
        if not is_cT: contour_y[1] = h+cT
        if not is_cB: contour_y[0] = -cB
        contour_gamma.append(round(h0/cL0,2))
        contour.append([contour_x, contour_y])
        contour_sides.append('левый')
        L = ((contour_x[1]-contour_x[0])**2 + (contour_y[1]-contour_y[0])**2)**0.5
        contour_len.append(L)
        contour_xc = contour_x[0]
        contour_yc = contour_y[0] + 0.5*L
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
    add = 0.75*h0
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
                red_contours, blue_contours, center):
    fig = go.Figure()
    #Добавляем колонну
    xx = [0, b, b, 0, 0]
    yy = [0, 0, h, h, 0]
    hatch = dict(fillpattern=dict(fgcolor='black', size=10, fillmode='replace', shape="/"))
    #**hatch
    fig.add_trace(go.Scatter(x=xx, y=yy, showlegend=False, fill='toself', fillcolor = 'rgba(128, 128, 128, 0.3)', mode='lines', line=dict(color='black')))
    fig.add_trace(go.Scatter(x=[0, b], y=[h/2, h/2], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[b/2, b/2], y=[0, h], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=xx, y=yy, showlegend=False, mode='lines', line=dict(color='black')))
    
    arrows_props = dict(arrowcolor="black", arrowsize=3, arrowwidth=0.5, arrowhead=3, axref='x', ayref='y', xref='x', yref='y', arrowside='end')
    arrows_axes = dict(arrowcolor="red", arrowsize=3, arrowwidth=0.7, arrowhead=3, axref='x', ayref='y', xref='x', yref='y', arrowside='end')
    text_props = dict(font=dict(color='black',size=14), showarrow=False, bgcolor="#ffffff")
    text_props_axes = dict(font=dict(color='red',size=16), showarrow=False)
    for contour in red_contours:
        fig.add_trace(go.Scatter(x=contour[0], y=contour[1], showlegend=False, mode='lines', line=dict(color='red')))
    for contour in blue_contours:
        fig.add_trace(go.Scatter(x=contour[0], y=contour[1], showlegend=False, mode='lines', line=dict(color='blue')))
    for i in range(len(blue_contours)):
        cont =  blue_contours[i]
        cx = cont[0][0] + (cont[0][1]-cont[0][0])/2
        cy = cont[1][0] + (cont[1][1]-cont[1][0])/2
        lx = (cont[0][1]-cont[0][0])
        ly = (cont[1][1]-cont[1][0])
        l = (lx**2+ly**2)**0.5
        if cont[1][0] == cont[1][1]:
            ang = 0
            yan = 'bottom'
            yan2 = 'top'
            if cy<=0:
                yan = 'top'
                yan2 = 'bottom'
            xan = 'center'
            xan2 = 'center'
            cx = b/2
        else:
            ang = 270
            yan = 'middle'
            yan2 = 'middle'
            xan = 'right'
            xan2 = 'left'
            if cx>=0:
                xan = 'left'
                xan2 = 'right'
            cy = h/2
        fig.add_annotation(dict(x=cx, y=cy, text=f'{float(l):g}', textangle=ang, yanchor=yan2, xanchor=xan2, **text_props))
        if cx<=0.0 and lx == 0.0:
            fig.add_annotation(dict(x=cx/2, y=0, text=f'{float(abs(cx)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
            fig.add_annotation(x=0, ax=-h0/2, y=0, ay=0, **arrows_props)
            fig.add_annotation(x=-h0/2, ax=0, y=0, ay=0, **arrows_props)
        if cx>=0.0 and lx == 0.0:
            fig.add_annotation(dict(x=b+(cx-b)/2, y=0, text=f'{float(abs(cx-b)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
            fig.add_annotation(x=b, ax=b+h0/2, y=0, ay=0, **arrows_props)
            fig.add_annotation(x=b+h0/2, ax=b, y=0, ay=0, **arrows_props)
        if cy<=0.0 and ly == 0.0:
            fig.add_annotation(dict(x=b, y=cy/2, text=f'{float(abs(cy)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
            fig.add_annotation(x=b, ax=b, y=0, ay=-h0/2, **arrows_props)
            fig.add_annotation(x=b, ax=b, y=-h0/2, ay=0, **arrows_props)
        if cy>=0.0 and ly == 0.0:
            fig.add_annotation(dict(x=b, y=h+(cy-h)/2, text=f'{float(abs(cy-h)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
            fig.add_annotation(x=b, ax=b, y=h, ay=h+h0/2, **arrows_props)
            fig.add_annotation(x=b, ax=b, y=h+h0/2, ay=h, **arrows_props)
    #Ширина колонны
    fig.add_annotation(dict(x=b/2, y=h, text=f'{float(b):g}', textangle=0, yanchor='top',xanchor='center', **text_props))
    #Высота колонны
    fig.add_annotation(dict(x=b, y=h/2, text=f'{float(h):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Начальные оси
    fig.add_annotation(x=min(0.5*b,0.5*h), ax=0, y=0, ay=0, **arrows_axes)
    fig.add_annotation(dict(x=min(0.5*b,0.5*h), y=0, text='x0', textangle=0, yanchor='top',xanchor='center', **text_props_axes))
    fig.add_annotation(x=0, ax=0, y=min(0.5*b,0.5*h), ay=0, **arrows_axes)
    fig.add_annotation(dict(x=0, y=min(0.5*b,0.5*h), text='y0', textangle=0, yanchor='middle',xanchor='right', **text_props_axes))
    
    #Расстояние до левой грани
    if not is_cL:
        if cL>0:
            fig.add_annotation(x=0, ax=-cL, y=0, ay=0, **arrows_props)
            fig.add_annotation(x=-cL, ax=0, y=0, ay=0, **arrows_props)
            fig.add_annotation(dict(x=-cL/2, y=0, text=f'{float(cL):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Расстояние до правой грани
    if not is_cR:
        if cR>0:
            fig.add_annotation(x=b, ax=b+cR, y=0, ay=0, **arrows_props)
            fig.add_annotation(x=b+cR, ax=b, y=0, ay=0, **arrows_props)
            fig.add_annotation(dict(x=b+cR/2, y=0, text=f'{float(cR):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Расстояние до нижней грани
    if not is_cB:
        if cB>0:
            fig.add_annotation(x=b, ax=b, y=0, ay=-cB, **arrows_props)
            fig.add_annotation(x=b, ax=b, y=-cB, ay=0, **arrows_props)
            fig.add_annotation(dict(x=b, y=-cB/2, text=f'{float(cB):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Расстояние до верхней грани
    if not is_cT:
        if cT>0:
            fig.add_annotation(x=b, ax=b, y=h, ay=h+cT, **arrows_props)
            fig.add_annotation(x=b, ax=b, y=h+cT, ay=h, **arrows_props)
            fig.add_annotation(dict(x=b, y=h+cT/2, text=f'{float(cT):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
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
    st.write('$b$ и $h$ - ширина и высота поперечного сечения сечения колонны, см;')
    st.write('$h_0$ - приведенная рабочая высота поперечного сечения плиты, см;')
    st.write('$c_L$ и $c_R$ - расстояние в свету до левой и правой грани плиты от грани колонны, см;')
    st.write('$c_B$ и $c_T$ - расстояние в свету до нижней и верхней грани плиты от грани колонны, см;')
    st.write('$R_{bt}$ - расчетное сопротивление на растяжение материала плиты, МПа;')
    st.write('$\\gamma_{bt}$ - коэффициент, вводимый к расчетному сопротивлению бетона на растяжение;')
    st.write('$R_{sw}$ - расчетное сопротивление поперечного армирования, МПа;')
    st.write('$n_{sw}$ - число стержней поперечного армирования в одном ряду, пересекающих пирамиду продавливания, шт.;')
    st.write('$s_{w}$ - шаг рядов поперечного армирования вдоль расчетного контура, мм;')
    st.write('$d_{sw}$ - диаметр поперечного армирования, мм;')
    st.write('$F$ - продавливающее усилие, тс; ''')
    st.write('$M_x$ - сосредоточенные момент в ПЛОСКОСТИ оси $x$ (относительно оси $y$), тсм;')
    st.write('$M_y$ - сосредоточенные момент в ПЛОСКОСТИ оси $y$ (относительно оси $x$), тсм;')
    st.write('$\\delta_{Mx}$ - понижающий коэффициент к сосредоточенным моментам в плоскости оси $x$.')
    st.write('$\\delta_{My}$ - понижающий коэффициент к сосредоточенным моментам в плоскости оси $y$.')

cols = st.columns([1, 0.5])

cols2_size = [1, 1, 1]
cols2 = cols[1].columns(cols2_size)
##cols2 = cols[1].columns(cols2_size)
##cols2 = cols[1].columns(cols2_size)
##cols2 = cols[1].columns(cols2_size)
##cols2 = cols[1].columns(cols2_size)
cols2[0].write('$b$, см')
b = cols2[1].number_input(label='$b$, см', step=5.0, format="%.1f", value=20.0, min_value=1.0, max_value=500.0, label_visibility="collapsed")

cols2 = cols[1].columns(cols2_size)
cols2[0].write('$h$, см')
h = cols2[1].number_input(label='$h$, см', step=5.0, format="%.1f", value=40.0, min_value=1.0, max_value=500.0, label_visibility="collapsed")

cols2 = cols[1].columns(cols2_size)
cols2[0].write('$h_0$, см')
h0 = cols2[1].number_input(label='$h_0$, см', step=5.0, format="%.1f", value=20.0, min_value=1.0, max_value=500.0, label_visibility="collapsed")

cols2 = cols[1].columns(cols2_size)
cols2[0].write('$c_L$, см')
is_cL = cols2[2].toggle('Контур_слева', value=True, label_visibility="collapsed")
cL = cols2[1].number_input(label='$c_L$, см', step=5.0, format="%.1f", value=10.0, disabled=is_cL, min_value=0.0, max_value=500.0, label_visibility="collapsed")


cols2 = cols[1].columns(cols2_size)
cols2[0].write('$c_R$, см')
is_cR = cols2[2].toggle('Контур_справа', value=True, label_visibility="collapsed")
cR = cols2[1].number_input(label='$c_R$, см', step=5.0, format="%.1f", value=10.0, disabled=is_cR, min_value=0.0, max_value=500.0, label_visibility="collapsed")


cols2 = cols[1].columns(cols2_size)
cols2[0].write('$c_B$, см')
is_cB = cols2[2].toggle('Контур_снизу', value=True, label_visibility="collapsed")
cB = cols2[1].number_input(label='$c_B$, см', step=5.0, format="%.1f", value=10.0, disabled=is_cB, min_value=0.0, max_value=500.0, label_visibility="collapsed")


cols2 = cols[1].columns(cols2_size)
cols2[0].write('$c_T$, см')
is_cT = cols2[2].toggle('Контур_сверху', value=True, label_visibility="collapsed")
cT = cols2[1].number_input(label='$c_T$, см', step=5.0, format="%.1f", value=10.0, disabled=is_cT, min_value=0.0, max_value=500.0, label_visibility="collapsed")

##cols3 = st.columns([1, 0.5])
cols2 = st.columns([1,0.8,0.8,0.8,0.8,0.8,0.7,0.7])
ctype = cols2[0].selectbox(label='Бетон', options=available_concretes, index=5, label_visibility="visible")
selected_concrete_data = table_concretes_data.loc[table_concretes_data['Class'] == ctype]
selected_concrete_data = selected_concrete_data.to_dict('records')[0]
Rbt0 = selected_concrete_data['Rbt']
gammabt = cols2[1].number_input(label='$\\gamma_{bt}$', step=0.05, format="%.2f", value=1.0, min_value=0.1, max_value=1.0, label_visibility="visible")
Rbt01 = Rbt0*gammabt
RbtMPA = cols2[2].number_input(label='$R_{bt}$, МПа', step=0.05, format="%.2f", value=Rbt01, min_value=0.1, max_value=2.2, label_visibility="visible", disabled=True)
Rbt = 0.01019716213*RbtMPA
#st.write(Rbt)
#Rbt = 0.01*Rbt
F = cols2[3].number_input(label='$F$, тс', step=0.5, format="%.1f", value=28.0, min_value=1.0, max_value=50000.0, label_visibility="visible")
Mx = cols2[4].number_input(label='$M_x$, тсм', step=0.5, format="%.1f", value=4.0, label_visibility="visible")
My = cols2[5].number_input(label='$M_y$, тсм', step=0.5, format="%.1f", value=7.0, label_visibility="visible")
deltaMx = cols2[6].number_input(label='$\\delta_{Mx}$', step=0.1, format="%.2f", value=0.5, min_value=0.0, max_value=2.0, label_visibility="visible")
deltaMy = cols2[7].number_input(label='$\\delta_{My}$', step=0.1, format="%.2f", value=0.5, min_value=0.0, max_value=2.0, label_visibility="visible")

is_sw = st.toggle('Поперечное армирование', value=False)
cols2 = st.columns([1,1,1,1,1])

rtype = cols2[0].selectbox(label='Арматура', options=['A240', 'A400', 'A500'], index=0, label_visibility="visible")
selected_reinf_data = table_reinf_data.loc[table_reinf_data['Class'] == rtype]
selected_reinf_data = selected_reinf_data.to_dict('records')[0]
Rsw0 = selected_reinf_data['Rsw']
Rsw = cols2[1].number_input(label='$R_{sw}$, МПа', value=Rsw0, label_visibility="visible", disabled=True)
Rsw = 0.01019716213*Rsw
nsw = cols2[2].number_input(label='$n_{sw}$, шт.', step=1, format="%i", value=2, min_value=1, max_value=10, label_visibility="visible")
sw = cols2[3].number_input(label='$s_w$, см', step=5.0, format="%.2f", value=6.0, min_value=0.0, max_value=100.0, label_visibility="visible")
dsw = cols2[4].selectbox(label='$d_{sw}$, мм', options=[6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32], index=0, label_visibility="visible")





red_contours = generate_red_contours(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
blue_contours, contour_gamma, contour_sides, contour_len, contour_center, contour_len_pr = generate_blue_contours(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
num_elem = len(blue_contours)
rez = 0
if num_elem>=2:
    rez = find_contour_geometry(blue_contours, contour_gamma, Rbt, h0, F, Mx, My, deltaMx, deltaMy, b/2, h/2)
    center = [rez['xc'], rez['yc']]
    #st.write(rez)

fig, image_stream, image_stream2 = draw_scheme(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT,
                  red_contours, blue_contours, center)
#, use_container_width=True
cols[0].plotly_chart(fig)

if num_elem<2:
    st.write('В расчете должно быть минимум два участка!')
    st.stop()



with st.expander('Расчетные предпосылки'):
    doc = Document('Template_punch.docx')
    doc.core_properties.author = 'Автор'
    p = doc.paragraphs[-1]
    delete_paragraph(p)
   
    string = 'Расчет на продавливание при действии сосредоточенной силы и изгибающих моментов.'
    doc.add_heading(string, level=0)
    st.subheader(string)

    string = 'Расчетные предпосылки.'
    doc.add_heading(string, level=1)
    st.subheader(string)

    string = 'Расчет производится согласно СП 63.13330.2018 п. 8.1.46 – 8.1.52. Поперечная арматура принимается равномерно расположенной по периметру расчетного контура.'
    st.write(string)
    doc.add_paragraph().add_run(string)
    string = 'Проверка прочности в общем случае выполняется из условия (8.96):'
    st.write(string)
    doc.add_paragraph().add_run(string)
    string = '$\\dfrac{F}{F_{b,ult}+F_{sw,ult}} + \\dfrac{\\delta_{Mx} \\cdot M_x}{M_{bx,ult} + M_{sw,x,ult}} + \\dfrac{\\delta_{My} \\cdot M_y}{M_{by,ult}+ M_{sw,y,ult} }  \\le 1.$'
    st.write(string)
    add_math(doc.add_paragraph(), string.replace('$',''))

    string = 'Здесь $F_{b,ult}$, $M_{bx,ult}$ и $M_{by,ult}$ – предельные сосредоточенная сила и изгибающие моменты, которые могут быть восприняты бетоном в расчетном поперечном сечении.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = '$F_{sw,ult}$, $M_{sw,x,ult}$ и $M_{sw,y,ult}$ – предельные сосредоточенная сила и изгибающие моменты, которые могут быть восприняты арматурой в расчетном поперечном сечении.'
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
    string += ' расположенной в пределах расстояния $0.5 h_0$ по обе стороны от контура расчетного сечения'
    st.write(string)
    p = doc.add_paragraph()
    add_text_latex(p, string)
    p.paragraph_format.first_line_indent = Mm(0)

    string = '$q_{sw} = \\dfrac{R_{sw} \\cdot A_{sw} }{s_w};$'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = '$A_{sw}$ – площадь сечения поперечной арматуры с шагом $s_w$, расположенная в пределах расстояния $0.5 h_0$ по обе'
    string += ' стороны от контура расчетного поперечного сечения по периметру контура расчетного поперечного сечения;'
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
    string += ' расположенной равномерно вдоль контура расчетного сечения, определяют при действии изгибающего момента'
    string += ' соответственно в направлении осей $x$ и $y$ по формуле:'
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

    string = '$k_{sw} = \\dfrac{0.8 \\cdot q_{sw}}{R_{bt} \\cdot h_0}.$'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = 'C учетом данного коэффициента и предыдущих выкладок условие прочности (8.96) можно переписать в виде:'
    st.write(string)
    doc.add_paragraph().add_run(string)
    string = '$\\dfrac{F}{F_{b,ult} \\cdot (1+k_{sw})} + \\dfrac{\\delta_{Mx} \\cdot M_x}{M_{bx,ult} \\cdot (1+k_{sw})} + \\dfrac{\\delta_{My} \\cdot M_y}{M_{by,ult} \\cdot (1+k_{sw}) }  \\le 1.$'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    
    string = 'В случае, если поперечная арматура не учитывается в расчете, $k_{sw}=0$.'
    string += ' В противном случае, если поперечная арматура учитывается в расчете, на коэффициент $k_{sw}$ накладываются следующие ограничения:'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = '$0.25 \\le k_{sw} \\le 1.$'
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

    string = 'Введем дополнительно коэффициенты $k_{b,F}$ и $k_{b,M}$ следующим образом:'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = '$k_{b,F} = \\dfrac{F}{F_{b,ult}}; \\quad'
    string += ' k_{b,M} = \\dfrac{\\delta_{Mx} \\cdot M_x}{M_{bx,ult}} + \\dfrac{\\delta_{My} \\cdot M_y}{M_{by,ult}}.$'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = 'В результате, условие прочности примет вид:'
    st.write(string)
    doc.add_paragraph().add_run(string)
    string = '$\\dfrac{k_{b,F} + k_{b,M}}{1+k_{sw}} \\le 1.$'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = 'Здесь $k_{b,F}$ и $k_{b,M}$ – коэффициенты использования прочности бетона расчетного поперечного сечения по силе и моментам соответственно.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    string = 'В соответствии с п. 8.1.46 при действии сосредоточенных моментов и силы в условиях прочности соотношение между действующими'
    string += ' сосредоточенными моментами $M$, учитываемыми при продавливании, и предельными $M_{ult}$ принимают не более'
    string += ' половины соотношения между действующим сосредоточенным усилием $F$ и предельным $F_{ult}$.'
    string += ' Следовательно, $k_{b,M} \\le 0.5 \\cdot k_{b,F}$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)

    #string = '$\\dfrac{F}{F_{b,ult}+{F_{sw,ult}} + \\left(\\dfrac{\\delta_{Mx} \\cdot M_x}{M_{bx,ult}+M_{sw,x,ult}} + \\dfrac{\\delta_{My} \\cdot M_y}{M_{by,ult}+M_{sw,y,ult}} \\right) = k_F + k_M \\le 1.$'

    string = 'Геометрические характеристики, такие как статические моменты, осевые моменты инерции, моменты сопротивления для расчетного контура вычисляются в НАПРАВЛЕНИИ соответствующих осей.'
    if is_sw:
        string += ' Поперечная арматура принимается равномерно расположенной по периметру расчетного контура.'
    st.write(string)
    doc.add_paragraph().add_run(string)
    string = 'Положение центра тяжести расчетного контура вычисляется относительно нижнего левого угла площадки передачи нагрузки.'
    st.write(string)
    doc.add_paragraph().add_run(string)

with st.expander('Расчетные выкладки'):
    string = 'Исходные данные.'
    doc.add_heading(string, level=1)
    st.subheader(string)

    string = 'Ширина зоны передачи нагрузки $b=' + str(round(b,1)) + 'см$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Высота зоны передачи нагрузки $h=' + str(round(h,1)) + 'см$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Приведенная рабочая высота сечения плиты $h_0=' + str(round(h0,1)) + 'см$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Класс бетона по прочности на сжатие ' + str(ctype) + '.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Расчетное сопротивление бетона на растяжение $R_{bt}=' + str(round(Rbt0,2)) + 'МПа$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Коэффициент, вводимый к расчетному сопротивлению бетона на растяжение $\\gamma_{bt}=' + str(round(gammabt,2)) + '$.'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string = 'Расчетное сопротивление бетона на растяжение, учитываемое в расчете:'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)
    string =  '$R_{bt}=R_{bt} \\cdot \\gamma_{bt} = ' + str(round(Rbt0,3)) + '\\cdot' + str(round(gammabt,2))
    string += '=' + str(round(RbtMPA,3)) + '\\cdot МПа='
    string += str(round(Rbt,6)) + '\\cdot тс/см^2'
    string += '.$'
    st.write(string)
    add_text_latex(doc.add_paragraph(), string)




    string = 'Эскиз расчетного конута.'
    doc.add_heading(string, level=1)
    doc.add_picture(image_stream, width=Mm(80))
    #doc.add_picture('test.svg', width=Mm(80))
    p = doc.paragraphs[-1]
    p.paragraph_format.first_line_indent = Mm(0)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    string = 'Расчет геометрических характеристик расчетного контура.'
    doc.add_heading(string, level=1)
    if True: #Длины участков
        string = 'Длины участков расчетного контура $L_i$, а также длины их проекций $L_{x,i}$ и $L_{y,i}$ в соответствии с эскизом приведены в таблице ниже.'

        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
    
        contours_lens = {'Li, см':[], 'Lxi, см':[], 'Lyi, см':[]}
        contours_lens_names = []
        for i in range(len(contour_len)):
            contours_lens_names.append(contour_sides[i])
            contours_lens['Li, см'].append(f'{float(round(contour_len[i],3)):g}')
            contours_lens['Lxi, см'].append(f'{float(round(contour_len_pr[i][0],3)):g}')
            contours_lens['Lyi, см'].append(f'{float(round(contour_len_pr[i][1],3)):g}')
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
        string = 'Вычисляем периметр расчетного контура:'
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
    
    if True: #Предельная продавливающая сила
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
        string = 'Статические моменты $S_{x,0,i}$ и $S_{y,0,i}$ каждого из участков расчетного контура относительно левого нижнего угла колонны вычисляются по формулам:'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
        string = '$S_{x,0,i} = L_{i} \\cdot x_{c,0,i} ; \\quad S_{y,0,i} = L_{i} \\cdot y_{c,0,i}.$'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
        string = 'Результаты расчета статических моментов участков расчетного контура по указанным выше приведены в таблице ниже.'
        st.write(string)
        doc.add_paragraph().add_run(string)
        contours_S = {'Sx0i, см2':[], 'Sy0i, см2':[]}
        contours_S_names = []
        for i in range(len(contour_sides)):
            contours_S_names.append(contour_sides[i])
            contours_S['Sx0i, см2'].append(f'{float(round(rez["Sx_arr"][i],1)):g}')
            contours_S['Sy0i, см2'].append(f'{float(round(rez["Sy_arr"][i],1)):g}')
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
        add_math(p, 'S_{x,0,i}, см^2')
        p.add_run(' ')
        p.paragraph_format.first_line_indent = Mm(0)
        #p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p = table.cell(2,0).paragraphs[0]
        add_math(p, 'S_{y,0,i}, см^2')
        p.add_run(' ')
        p.paragraph_format.first_line_indent = Mm(0)
        #p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    if True: #Статический момент инерции всего сечения
        string = 'Статические моменты инерции всего расчетного контура относительно левого нижнего угла колонны вычисляем как сумму статических моментов инерции каждого из участков.'
        st.write(string)
        doc.add_paragraph().add_run(string)
        string = '$ S_{x,0} = \\sum_i S_{x,0,i}= '
        string += f'{float(round(rez["Sx_arr"][0],2)):g}'
        for i in range(1, len(rez["Sx_arr"])):
            if rez["Sx_arr"][i] > 0:
                string += '+'
            string += f'{float(round(rez["Sx_arr"][i],2)):g}'
        string += f'={float(round(rez["Sx"],2)):g} \\cdot см^2.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))

        string = '$ S_{y,0} = \\sum_i S_{y,0,i}= '
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
        string = '$ x_c = \\dfrac{S_{x,0}}{u} = '
        string += '\\dfrac{' + f'{float(round(rez["Sx"],2)):g}' + '}{' + f'{float(round(rez["Lsum"],3)):g}' + '}='
        string += f'{float(round(rez["xc"],3)):g} \\cdot см.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))

        string = '$ y_c = \\dfrac{S_{y,0}}{u} = '
        string += '\\dfrac{' + f'{float(round(rez["Sy"],2)):g}' + '}{' + f'{float(round(rez["Lsum"],3)):g}' + '}='
        string += f'{float(round(rez["yc"],3)):g} \\cdot см.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))

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
        string = '$I_{x,0,i} = \\dfrac{L_{x,i}^3}{12}; \\quad I_{y,0,i} = \\dfrac{L_{y,i}^3}{12}.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))
        string = 'Результаты расчета собственных моментов по указанным выше формулам приведены в таблице ниже.'
        st.write(string)
        doc.add_paragraph().add_run(string)
        contours_I0 = {'Ix0i, см3':[], 'Iy0i, см3':[]}
        contours_I0_names = []
        for i in range(len(contour_sides)):
            contours_I0_names.append(contour_sides[i])
            #contours_I0['Ix0i, см3'].append(f'{float(round())}')
            #contours_I0['Ix0i, см3'].append(n_number(rez["Ix0_arr"][i],2))
            #contours_I0['Ix0i, см3'].append(Decimal(round(rez["Ix0_arr"][i],2)).normalize())
            contours_I0['Ix0i, см3'].append(f'{float(round(rez["Ix0_arr"][i],2))}')
            contours_I0['Iy0i, см3'].append(f'{float(round(rez["Iy0_arr"][i],2))}')
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
        add_math(p, 'I_{x,0,i}, см^3')
        p.add_run(' ')
        p.paragraph_format.first_line_indent = Mm(0)
        #p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p = table.cell(2,0).paragraphs[0]
        add_math(p, 'I_{y,0,i}, см^3')
        p.add_run(' ')
        p.paragraph_format.first_line_indent = Mm(0)

    if True: #Вычисление моментов инерции участков
        string = 'Для вычисления моментов инерции участков контура относительно геометрического центра всего контура используются формулы переноса осей, приведенные ниже.'
        st.write(string)
        doc.add_paragraph().add_run(string)
        string = '$I_{x,i} = I_{x,0,i} +  L_i \\cdot x_{c,i}^2; \\quad I_{y,i} = I_{y,0,i} +  L_i \\cdot y_{c,i}^2.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))
        string = 'Результаты расчета моментов инерции участков контура относительно геометрического центра всего контура по указанным выше формулам приведены в таблице ниже.'
        st.write(string)
        doc.add_paragraph().add_run(string)
        contours_I = {'Ixi, см3':[], 'Iyi, см3':[]}
        contours_I_names = []
        #st.write(rez["Ix_arr"])
        for i in range(len(contour_sides)):
            contours_I_names.append(contour_sides[i])
            #contours_I['Ixi, см3'].append(f'{float(round(rez["Ix_arr"][i],2)):g}')
            #contours_I['Iyi, см3'].append(f'{float(round(rez["Iy_arr"][i],2)):g}')
            contours_I['Ixi, см3'].append(f'{float(round(rez["Ix_arr"][i],2))}')
            contours_I['Iyi, см3'].append(f'{float(round(rez["Iy_arr"][i],2))}')
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
        add_math(p, 'I_{x,i}, см^3')
        p.add_run(' ')
        p.paragraph_format.first_line_indent = Mm(0)
        #p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p = table.cell(2,0).paragraphs[0]
        add_math(p, 'I_{y,i}, см^3')
        p.add_run(' ')
        p.paragraph_format.first_line_indent = Mm(0)

    if True: #Моменты инерции всего сечения
        string = 'Моменты инерции всего расчетного контура вычисляем как сумму моментов инерции каждого из участков.'
        st.write(string)
        doc.add_paragraph().add_run(string)
        string = '$ I_{x} = \\sum_i{I_{x,i}}= '
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

        string = '$ I_{y} = \\sum_i{I_{y,i}}= '
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
        string = '$ W_{x} = \\dfrac{I_x}{x_{\\max}} = \\dfrac{'
        #string += f'{float(round(rez["Ix_arr"][0],2)):g}'
        string += f'{float(round(rez["Ix"],2))}'
        string += '}{'
        string += f'{float(round(rez["xmax"],3))}'
        string += '} = '
        string += f'{float(round(rez["Wxmin"],2))}'
        string += '\\cdot см^2.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))

        string = '$ W_{y} = \\dfrac{I_y}{y_{\\max}} = \\dfrac{'
        #string += f'{float(round(rez["Ix_arr"][0],2)):g}'
        string += f'{float(round(rez["Iy"],2))}'
        string += '}{'
        string += f'{float(round(rez["ymax"],3))}'
        string += '} = '
        string += f'{float(round(rez["Wymin"],2))}'
        string += '\\cdot см^2.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))

    if True: #Предельные моменты, воспринимаемые бетонным сечением
        string = 'Предельные моменты, воспринимаемые бетоном в расчетном поперечном сечении, вычисляются по формулам (8.94):'
        st.write(string)
        doc.add_paragraph().add_run(string)
        string = '$ M_{bx,ult} = R_{bt} \\cdot h_0 \\cdot W_{x} = '
        #string += f'{float(round(rez["Ix_arr"][0],2)):g}'
        string += f'{float(round(Rbt,6)):g} \\cdot {float(round(h0,5)):g} \\cdot  {float(round(rez["Wxmin"],2))} / 100 ='
        string += f'{float(round(rez["Mbxult"],2))} \\cdot тс \\cdot м.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))

        string = '$ M_{by,ult} = R_{bt} \\cdot h_0 \\cdot W_{y} = '
        #string += f'{float(round(rez["Ix_arr"][0],2)):g}'
        string += f'{float(round(Rbt,6)):g} \\cdot {float(round(h0,5)):g} \\cdot  {float(round(rez["Wymin"],2))} / 100 ='
        string += f'{float(round(rez["Mbyult"],2))} \\cdot тс \\cdot м.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))

        string = 'Примечание. Деление на 100 в данных формулах необходимо для перевода сантиметров в метры.'
        st.write(string)
        doc.add_paragraph().add_run(string)

    
    if True: #Условие прочности
        string = 'Проверка прочности выполняется из условия:'
        st.write(string)
        doc.add_paragraph().add_run(string)
        string = '$\\dfrac{F}{F_{b,ult}} + \\left(\\dfrac{\\delta_{Mx} \\cdot M_x}{M_{x,ult}} + \\dfrac{\\delta_{My} \\cdot M_y}{M_{y,ult}} \\right) = k_F + k_M \\le 1.$'
        st.write(string)
        add_math(doc.add_paragraph(), string.replace('$',''))
        string = 'Здесь $k_F$ и $k_M$ - коэффициенты использования по силе и моментам соответственно.'
        string += ' При действии сосредоточенных моментов и силы в условиях прочности соотношение между действующими'
        string += ' сосредоточенными моментами $M$, учитываемыми при продавливании, и предельными $M_{ult}$ принимают не более'
        string += ' половины соотношения между действующим сосредоточенным усилием $F$ и предельным $F_{ult}$.'
        string += ' Следовательно, $k_M \\le 0.5 \\cdot k_F$.'
        string += ' Коэффициенты $\\delta_{Mx} \\le 1$ и $\\delta_{My} \\le 1$ также учитывают положения п. 8.1.46, a именно:'
        string += ' при действии момента в месте приложения сосредоточенной нагрузки половину этого момента учитывают при расчете на продавливание.'
        st.write(string)
        add_text_latex(doc.add_paragraph(), string)
        



    




    file_stream = io.BytesIO()
    doc.save(file_stream)
    st.sidebar.download_button('Сохранить исходные данные', file_name='1.docx', data=file_stream)


    st.write('В результате подстановки значений найдем $F_{b,ult}='+ str(round(rez['Fbult'])) + '$тс; $F_{b,ult}/1.5=' + str(round(rez['Fbult']/1.5)) + '$тс.' )

    st.write('Положение центров тяжести каждого из участков контура относительно левого нижнего угла колонны:')
    x0cL, x0cR, x0cB, x0cT = 0, 0, 0, 0
    y0cL, y0cR, y0cB, y0cT = 0, 0, 0, 0
    string = ''
    for i in range(len(contour_sides)):
        if contour_sides[i] == 'левый':
            x0cL, y0cL = contour_center[i]
            string += 'левый: $x_{0,c,L}=' + f'{float(x0cL):g}' + 'см; \\quad y_{0,c,L}=' + f'{float(y0cL):g}' + 'см$'
            if i == len(contour_sides) - 1:
                string += '.'
            else:
                string += ''';
                \n'''
        if contour_sides[i] == 'правый':
            x0cR, y0cR = contour_center[i]
            string += 'правый: $x_{0,c,R}=' + f'{float(x0cR):g}' + 'см; \\quad y_{0,c,R}=' + f'{float(y0cR):g}' + 'см$'
            if i == len(contour_sides) - 1:
                string += '.'
            else:
                string += ''';
                \n'''
        if contour_sides[i] == 'нижний':
            x0cB, y0cB = contour_center[i]
            string += 'нижний: $x_{0,c,B}=' + f'{float(x0cB):g}' + 'см; \\quad y_{0,c,B}=' + f'{float(y0cB):g}' + 'см$'
            if i == len(contour_sides) - 1:
                string += '.'
            else:
                string += ''';
                \n'''
        if contour_sides[i] == 'верхний':
            x0cT, y0cT = contour_center[i]
            string += 'верхний: $x_{0,c,T}=' + f'{round(x0cT,2):g}' + 'см; \\quad y_{0,c,T}=' + f'{round(y0cT,2):g}' + 'см$.'
    
    st.write(string)


    st.write('Положение геометрического центра тяжести контура относительно левого нижнего угла колонны вычисляем по формуле:')

    st.latex('''
    x_c = \\dfrac{\\sum_i S_{x,i}}{\\sum_i L_{i}} = \\dfrac{\\sum_i L_{i} \\cdot x_{0,c,i}}{\\sum_i L_{i}}; \\quad
    y_c = \\dfrac{\\sum_i S_{y,i}}{\\sum_i L_{i}} = \\dfrac{\\sum_i L_{i} \\cdot y_{0,c,i}}{\\sum_i L_{i}}.
    ''')
    
    st.write('В результате подстановки значений найдем $x_{c}='+ f'''{round(rez['xc'],2):g}'''+ '$см; $y_{c}='+ f'''{round(rez['yc'],2):g}$см.''')

    st.write('Таким образом координаты центров тяжести каждого из элементов контура относительно центра тяжести всего контура составляют:')

    st.write('Положение центров тяжести каждого из участков контура относительно центра тяжести колонны:')
    xcL, xcR, xcB, xcT = 0, 0, 0, 0
    ycL, ycR, ycB, ycT = 0, 0, 0, 0
    string = ''
    for i in range(len(contour_sides)):
        if contour_sides[i] == 'левый':
            xcL = x0cL - rez['xc']
            ycL = y0cL - rez['yc']
            string += 'левый: $x_{c,L}=' + f'{float(round(xcL,2)):g}' + 'см; \\quad y_{c,L}=' + f'{float(round(ycL,2)):g}' + 'см$'
            if i == len(contour_sides) - 1:
                string += '.'
            else:
                string += ''';
                \n'''
        if contour_sides[i] == 'правый':
            xcR = x0cR - rez['xc']
            ycR = y0cR - rez['yc']
            string += 'правый: $x_{c,R}=' + f'{float(round(xcR,2)):g}' + 'см; \\quad y_{c,R}=' + f'{float(round(ycR,2)):g}' + 'см$'
            if i == len(contour_sides) - 1:
                string += '.'
            else:
                string += ''';
                \n'''
        if contour_sides[i] == 'нижний':
            xcB = x0cB - rez['xc']
            ycB = y0cB - rez['yc']
            string += 'нижний: $x_{c,B}=' + f'{float(round(xcB,2)):g}' + 'см; \\quad y_{c,B}=' + f'{float(round(ycB,2)):g}' + 'см$'
            if i == len(contour_sides) - 1:
                string += '.'
            else:
                string += ''';
                \n'''
        if contour_sides[i] == 'верхний':
            xcT = x0cT - rez['xc']
            ycT = y0cT - rez['yc']
            string += 'верхний: $x_{c,T}=' + f'{float(round(xcT,2)):g}' + 'см; \\quad y_{c,T}=' + f'{float(round(ycT,2)):g}' + 'см.$'
    
    
    st.write(string)

  

    I0xL, I0xR, I0xB, I0xT = 0, 0, 0, 0
    I0yL, I0yR, I0yB, I0yT = 0, 0, 0, 0
    st.write('Собственные моменты инерции участков контура в направлении осей $x$ и $y$ вычисляются по формулам:')
    st.latex('''I_{0,x,i} = \\dfrac{L_{x,i}^3}{12}; \\quad
    I_{0,y,i} = \\dfrac{L_{y,i}^3}{12},
    ''')
    st.write('где $L_{x,i}$ и $L_{y,i}$ длины проекций соответствующего участка на оси $x$ и $y$.')

    st.write('Длины проекций и собственные моменты инерции в направлении осей $x$ и $y$ участков контура составляют: ')
    
    for i in range(len(contour_sides)):
        string = ''
        if contour_sides[i] == 'левый':
            LL = contour_len[i]
            I0yL = LL**3/12
            string += 'левый: '
            string += r'$L_{x,L}=0; I_{0,x,L}=0; L_{y,L}=' + f'{round(LL,2):g}' + '$см$' '; I_{0,y,L}=\\dfrac{' + f'{round(LL,2):g}' + '^3}{12}='  +f'{round(I0yL):g}' + '$см$^3$; '
        if contour_sides[i] == 'правый':
            LR = contour_len[i]
            I0yR = LR**3/12
            string += 'правый: '
            string += r'$L_{x,R}=0; I_{0,x,R}=0; L_{y,R}=' + f'{round(LR,2):g}' + '$см$' '; I_{0,y,R}=\\dfrac{' + f'{round(LR,2):g}' + '^3}{12}=' +f'{round(I0yR):g}' + '$см$^3$; '
            
        if contour_sides[i] == 'нижний':
            LB = contour_len[i]
            Ix0B = LB**3/12
            string += 'нижний: '
            string += r'$L_{x,B}=' + f'{round(LB,2):g}' + '$см$; I_{0,x,B}=\\dfrac{' + f'{round(LB,2):g}' + '^3}{12}=' + f'{round(Ix0B):g}' + '$см$^4; L_{y,B}=0; I_{0,y,B}=0$; '
            
        if contour_sides[i] == 'верхний':
            LT = contour_len[i]
            Ix0T = LT**3/12
            string += 'верхний: '
            string += r'$L_{x,T}=' + f'{round(LT,2):g}' + '$см$; I_{0,x,T}=\\dfrac{' + f'{round(LT,2):g}' + '^3}{12}=' + f'{round(Ix0T):g}' + '$см$^4; L_{y,T}=0; I_{0,y,T}=0$; '
        
        if i == len(contour_sides)-1:
            string = string[:-2]
            string += '.'
        st.write(string)

    st.write('Моменты инерции всего контура в направлении осей $x$ и $y$ вычисляются по формулам:')
    st.latex('''I_{x} = \\sum_i \\left[ I_{0,x,i} + L_i \\cdot \\left( x_{c,i} \\right)^2   \\right]; \\quad
    I_{y} = \\sum_i \\left[ I_{0,y,i} + L_i \\cdot \\left( y_{c,i} \\right)^2   \\right].
    ''')
    
    st.write('В результате подстановки значений найдем $I_{bx}='+ f'''{round(rez['Ix'])}'''+ '$см$^3$; $I_{y}='+ f'''{round(rez['Iy'])}$см$^3$.''')

    st.write('Расстояния до наиболее удаленных точек от центра тяжести контура:')
    st.write('$|x_{\\min}|=' + f'''{round(abs(rez['xL']),2):g}''' + 'см; x_{\\max}='+ f'''{round(abs(rez['xR']),2):g}''' + 'см; |y_{\\min}|=' + f'''{round(abs(rez['yB']),2):g}''' + 'см; y_{\\max}=' + f'''{round(abs(rez['yT']),2):g}'''+   'см.$' )

    st.write('Минимальные значения моментов сопротивления расчетного контура в направлении осей $x$ и $y$ вычисляются по формуле:')

    st.latex('W_{bx} = \\dfrac{I_{bx}}{x_{\\max}}; \\quad W_{by} = \\dfrac{I_{by}}{y_{\\max}}.')

    st.write('В результате расчета найдем: $W_{bx}=' + f'''{round(abs(rez['Wxmin'])):g}''' + 'см^2; W_{by}=' + f'''{round(abs(rez['Wymin'])):g}''' + 'см^2.$')

    st.write('Предельные моменты, воспринимаемые расчетным контуром в плоскости осей $x$ и $y$ вычисляются по формулам:')
    st.latex('''M_{bx,ult}=\\gamma \\cdot R_{bt} \\cdot h_0 \\cdot W_{bx}; \\quad
     M_{by,ult}=\\gamma \\cdot R_{bt} \\cdot h_0 \\cdot W_{by}.''')
    gamma_min = min(contour_gamma)

    st.write('''Здесь $\\gamma='''+ str(gamma_min) + '''$ - минимальное значение повышающего коэффициента к прочности бетона, из найденных ранее.''')

    st.write('В результате расчета найдем: $M_{bx,ult}=' + f'''{round(abs(rez["Mbxult"]),1):g}''' + 'тсм; M_{by,ult}=' + f'''{round(abs(rez["Mbyult"]),1):g}''' + 'тсм.$')
    
    st.write('Проверка прочности выполняется из условия:')

    st.latex('\\dfrac{F}{F_{b,ult}} + \\left(\\dfrac{\\delta_M \\cdot M_x}{M_{bx,ult}} + \\dfrac{\\delta_M \\cdot M_y}{M_{by,ult}}\\right) = k_F + k_M \\le 1.')
    st.write('Здесь $k_F$ и $k_M$ - коэффициенты использования сечения по силе и моментам соответственно, причем $k_M \\le 0.5 \\cdot k_F$.')

   

    st.write('Коэффициенты использования составляют:')
    st.write('$k_F=\\dfrac{F}{F_{b,ult}}=\\dfrac{' + f'''{round(F):g}''' + '}{' f'''{round(rez["Fbult"]):g}''' + '}=' + f'''{round(rez["kF"],3):g}''' + ';$')
    st.write('$k_M=\\dfrac{\\delta_M \\cdot M_x}{M_{bx,ult}} + \\dfrac{\\delta_M \\cdot M_y}{M_{by,ult}} =\\dfrac{' 
             + str(deltaMx) + '\\cdot' + f'''{round(rez["Mxloc"],1):g}''' +  '}{' f'''{round(rez["Mbxult"],1):g}''' + '}+' +
              '\\dfrac{' + str(deltaMy) + '\\cdot' + f'''{round(rez["Myloc"],1):g}'''  + '}{' f'''{round(rez["Mbyult"],1):g}''' + '}=' +
            f'''{round(rez["kM"],3):g}''' + ';$')
    st.write('$k=k_F+k_M=' + str(round(rez['kF'],3)) + '+' + str(round(rez['kM'],3)) + '=' + str(round(rez['k'],3)) + '$.')

st.write('Коэффициент использования по продольной силе $k_F=' + str(round(rez['kF'],3)) + '$.')
st.write('Коэффициент использования по моментам $k_М=' + str(round(rez['kM'],3)) + '$.')
st.write('Суммарный коэффициент использования $k=' + str(round(rez['k'],3)) + '$.')







