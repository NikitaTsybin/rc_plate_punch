##from turtle import width
import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
import plotly.graph_objects as go

##pile_punch_dir = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
##+ '/pages/pile_punch/')
##sys.path.append(pile_punch_dir)
st.header('Расчет на продавливание фундаментной плиты, опирающейся на сваи')


center = [25.0, 50.0]
centerM = [25.0, 50.0]


def find_contour_geometry (V, M, Rbt, h0, F, Mx, My, deltaM, xcol, ycol):
    #V - массив координат линий контура [   [[x1,x2], [y1,y2]],    [[x1,x2], [y1,y2]], ...   ]
    #M - вектор масс линий
    #Объявляем нулевыми суммарные длину и моменты инерции
    V = np.array(V)
    M = np.array(M)
    #print(V1)
    Lsum, Sx, Sy, Ix, Iy = 0, 0, 0, 0, 0
    LsumM, SxM, SyM, IxM, IyM = 0, 0, 0, 0, 0
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
        Lsum, LsumM = Lsum + L_i, LsumM + L_i*M[j]
        #Вычисляем координаты центра i-го участка
        center_i = ((x2 - x1)/2 + x1, (y2 - y1)/2 + y1)
        #Вычисляем статические моменты i-го участка
        Sx_i = L_i*center_i[0]
        Sy_i = L_i*center_i[1]
        #Добавляем их в суммарные
        Sx, SxM = Sx + Sx_i, SxM + Sx_i*M[j]
        Sy, SyM = Sy + Sy_i, SyM + Sy_i*M[j]
        j += 1
    #Длина контура и весовая длина контура
    Lsum, LsumM = round(Lsum, 2), round(LsumM,2)
    #Предельная сила, воспринимаемая бетоном
    Fbult = LsumM*Rbt*h0
    #Коэффициент использования по продольной силе
    kF= F/Fbult
    #Вычисляем координаты центра тяжести всего контура
    xc, xcM = Sx/Lsum, SxM/LsumM
    yc, ycM = Sy/Lsum, SyM/LsumM
    ex, exM = xc - xcol, xcM - xcol
    ey, eyM = yc - ycol, ycM - ycol
    #Расчет характеристик "без масс"
    for i in V:
        #Вычисляем координаты минимума и максимума относительно геометрического центра тяжести
        xmin, xmax = xmin0 - xc, xmax0 - xc
        ymin, ymax = ymin0 - yc, ymax0 - yc
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
        #Моменты инерции относительно центра тяжести
        Ix_i = Ix0_i + L_i*x0**2
        Iy_i = Iy0_i + L_i*y0**2
        Ix = Ix + Ix_i
        Iy = Iy + Iy_i
    Wxl, Wxr = Ix/abs(xmin), Ix/xmax
    Wxmin = min(Wxl, Wxr)
    Wyb, Wyt = Iy/abs(ymin), Iy/ymax
    Wymin = min(Wyb, Wyt)
    Mbxult = Wxmin*h0*Rbt*M.min()/100
    Mbyult = Wymin*h0*Rbt*M.min()/100
    Mxexc = -F*ex/100
    Myexc = -F*ey/100
    MxexcM = -F*exM/100
    MyexcM = -F*eyM/100
    Mxloc = Mx + Mxexc
    Myloc = My + Myexc
    MxlocM = Mx + MxexcM
    MylocM = My + MyexcM
    Mxlocmax = max(abs(Mxloc), abs(MxlocM))
    Mylocmax = max(abs(Myloc), abs(MylocM))
    kM = (abs(Mxloc)/Mbxult + abs(Myloc)/Mbyult)*deltaM
    kMM = (abs(MxlocM)/Mbxult + abs(MylocM)/Mbyult)*deltaM
    kM = min(kM, kF/2)
    kMM = min(kMM, kF/2)
    kMmax = max(kM, kMM) 
    k = kF + max(kM, kMM) 
    return {'Lsum': Lsum, 'xc': xc, 'yc': yc, 'xcM': xcM, 'ycM': ycM, 
                                     'ex': ex, 'ey': ey, 'exM': exM, 'eyM': eyM,
                                     'Ibx': Ix, 'Iby': Iy, 'xmin': xmin, 'xmax': xmax, 'ymin': ymin, 'ymax': ymax,
                                     'Wxmin': Wxmin, 'Wymin': Wymin,
                                     'Mxexc': Mxexc, 'Myexc': Myexc, 'MxexcM': MxexcM, 'MyexcM': MyexcM,
                                     'Mxloc': Mxloc, 'Myloc': Myloc, 'MxlocM': MxlocM, 'MylocM': MylocM, 
                                     'Mxlocmax': Mxlocmax, 'Mylocmax': Mylocmax,
                                     'Fbult': Fbult, 'Mbxult': Mbxult, 'Mbyult': Mbyult,
                                     'kF': kF, 'kM': kM, 'kMM': kMM, 'kMmax': kMmax , 'k': k}

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
    return contour, contour_gamma, contour_sides, contour_len, contour_center

def generate_red_contours (b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT):
    add = 0.75*h0
    contour = []
    if not is_cL:
        contour_x = [-cL, -cL]
        contour_y = [-add, h+add]
        contour.append([contour_x, contour_y])
    if not is_cR:
        contour_x = [b+cR, b+cR]
        contour_y = [-add, h+add]
        contour.append([contour_x, contour_y])
    if not is_cB:
        contour_x = [-add, b+add]
        contour_y = [-cB, -cB]
        contour.append([contour_x, contour_y])
    if not is_cT:
        contour_x = [-add, b+add]
        contour_y = [h+cT, h+cT]
        contour.append([contour_x, contour_y])
    return contour
    
def draw_scheme(b, h, h0,
                cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT,
                red_contours, blue_contours, center, centerM):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[center[0]], y=[center[1]], showlegend=False, mode="markers", marker_symbol=4, marker_size=10, line=dict(color='green')))
    fig.add_trace(go.Scatter(x=[centerM[0]], y=[centerM[1]], showlegend=False, mode="markers", marker_symbol=4, marker_size=10, line=dict(color='red')))
    #Добавляем колонну
    xx = [0, b, b, 0, 0]
    yy = [0, 0, h, h, 0]
    fig.add_trace(go.Scatter(x=[0, b], y=[h/2, h/2], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[b/2, b/2], y=[0, h], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=xx, y=yy, showlegend=False, mode='lines', line=dict(color='black')))
    fig.add_trace(go.Scatter(x=xx, y=yy, showlegend=False, fill='toself', mode='lines', line=dict(color='black'), fillpattern=dict(fgcolor='black', size=10, fillmode='replace', shape="/")))
    arrows_props = dict(arrowcolor="black", arrowsize=3, arrowwidth=0.5, arrowhead=3, axref='x', ayref='y', xref='x', yref='y', arrowside='end')
    text_props = dict(font=dict(color='black',size=14), showarrow=False, bgcolor="#ffffff")
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
    fig.add_annotation(dict(x=b/2, y=0, text=f'{float(b):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
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
    #Высота колонны
    fig.add_annotation(dict(x=b, y=h/2, text=f'{float(h):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
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
##            fig.add_annotation(x=b, y=h, ax=0, ay=-k_l*cT, **arrows_props)
##            fig.add_annotation(x=b, y=h+cT, ax=0, ay=k_l*cT, **arrows_props)
            fig.add_annotation(dict(x=b, y=h+cT/2, text=f'{float(cT):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    fig.update_yaxes(scaleanchor="x",scaleratio=1,title="y")
    fig.update_xaxes(dict(title="x", visible=False))
    fig.update_yaxes(visible=False)
    fig.update_layout(autosize=True, margin={'l': 0, 'r': 0, 't': 0, 'b': 0})
    return fig



with st.expander('Описание исходных данных'):
    st.write(''' $b$ и $h$ - ширина и высота поперечного сечения сечения колонны, см; ''')
    st.write(''' $h_0$ - рабочая высота поперечного сечения фундаментной плиты, см; ''')
    st.write(''' $c_L$ и $c_R$ - расстояние в свету до левой и правой сваи (грани плиты) от грани колонны, см; ''')
    st.write(''' $c_B$ и $c_T$ - расстояние в свету до нижней и верхней сваи (грани плиты) от грани колонны, см; ''')
    st.write(''' $R_{bt}$ - расчетное сопротивление на растяжение материала фундаментной плиты, МПа; ''')
    st.write(''' $F$ - продавливающее усилие, тс; ''')
    st.write(''' $M_x$ - сосредоточенные момент в ПЛОСКОСТИ оси $x$ (относительно оси $y$), тсм; ''')
    st.write(''' $M_y$ - сосредоточенные момент в ПЛОСКОСТИ оси $y$ (относительно оси $x$), тсм; ''')
    st.write(''' $\delta_M$ - понижающий коэффициент к сосредоточенным моментам. ''')

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
cols2 = st.columns([1,1,1,1,1])
Rbt = cols2[0].number_input(label='$R_{bt}$, МПа', step=0.05, format="%.2f", value=1.4, min_value=0.1, max_value=5.0, label_visibility="visible")
#Rbt = 0.01019716213*Rbt
Rbt = 0.01*Rbt
F = cols2[1].number_input(label='$F$, тс', step=0.5, format="%.1f", value=1400.0, min_value=1.0, max_value=50000.0, label_visibility="visible")
Mx = cols2[2].number_input(label='$M_x$, тсм', step=0.5, format="%.1f", value=90.0, label_visibility="visible")
My = cols2[3].number_input(label='$M_y$, тсм', step=0.5, format="%.1f", value=120.0, label_visibility="visible")
deltaM = cols2[4].number_input(label='$\delta_M$', step=0.1, format="%.2f", value=0.5, min_value=0.0, max_value=2.0, label_visibility="visible")




red_contours = generate_red_contours(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
blue_contours, contour_gamma, contour_sides, contour_len, contour_center = generate_blue_contours(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT)
num_elem = len(blue_contours)
rez = 0
if num_elem>=2:
    rez = find_contour_geometry(blue_contours, contour_gamma, Rbt, h0, F, Mx, My, deltaM, b/2, h/2)
    center = [rez['xc'], rez['yc']]
    centerM = [rez['xcM'], rez['ycM']]
    #st.write(rez)

fig = draw_scheme(b, h, h0, cL, is_cL, cR, is_cR, cB, is_cB, cT, is_cT,
                  red_contours, blue_contours, center, centerM)
cols[0].plotly_chart(fig, use_container_width=True)

if num_elem<2:
    st.write('В расчете должно быть минимум два участка!')
    st.stop()



with st.expander('Расчетные выкладки'):

    LL, LR, LT, LB = 0, 0, 0, 0
    string = 'Длины участков контура приведены в таблице ниже:'
    contours_lens = {'Li, см':[]}
    contours_lens_names = []
    for i in range(len(contour_sides)):
        contours_lens_names.append(contour_sides[i])
        contours_lens['Li, см'].append(contour_len[i])
    string = string[:-2]
    string += '.'
    st.write(string)
    contours_lens = pd.DataFrame.from_dict(contours_lens, orient='index', columns=contours_lens_names)
    st.write(contours_lens)
    
    st.write('Предельную продавливаюшую силу, воспринимаемую бетоном, вычисляем по формуле:')

    st.latex('''
    F_{b,ult} = R_{bt} \\cdot h_0 \\cdot \\sum_i L_i .
    ''')

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
            string += 'левый: $x_{c,L}=' + f'{float(round(xcL,2)):g}' + 'см; \quad y_{c,L}=' + f'{float(round(ycL,2)):g}' + 'см$'
            if i == len(contour_sides) - 1:
                string += '.'
            else:
                string += ''';
                \n'''
        if contour_sides[i] == 'правый':
            xcR = x0cR - rez['xc']
            ycR = y0cR - rez['yc']
            string += 'правый: $x_{c,R}=' + f'{float(round(xcR,2)):g}' + 'см; \quad y_{c,R}=' + f'{float(round(ycR,2)):g}' + 'см$'
            if i == len(contour_sides) - 1:
                string += '.'
            else:
                string += ''';
                \n'''
        if contour_sides[i] == 'нижний':
            xcB = x0cB - rez['xc']
            ycB = y0cB - rez['yc']
            string += 'нижний: $x_{c,B}=' + f'{float(round(xcB,2)):g}' + 'см; \quad y_{c,B}=' + f'{float(round(ycB,2)):g}' + 'см$'
            if i == len(contour_sides) - 1:
                string += '.'
            else:
                string += ''';
                \n'''
        if contour_sides[i] == 'верхний':
            xcT = x0cT - rez['xc']
            ycT = y0cT - rez['yc']
            string += 'верхний: $x_{c,T}=' + f'{float(round(xcT,2)):g}' + 'см; \quad y_{c,T}=' + f'{float(round(ycT,2)):g}' + 'см.$'
    
    
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
    
    st.write('В результате подстановки значений найдем $I_{bx}='+ f'''{round(rez['Ibx'])}'''+ '$см$^3$; $I_{y}='+ f'''{round(rez['Iby'])}$см$^3$.''')

    st.write('Расстояния до наиболее удаленных точек от центра тяжести контура:')
    st.write('$|x_{\\min}|=' + f'''{round(abs(rez['xmin']),2):g}''' + 'см; x_{\\max}='+ f'''{round(abs(rez['xmax']),2):g}''' + 'см; |y_{\\min}|=' + f'''{round(abs(rez['ymin']),2):g}''' + 'см; y_{\\max}=' + f'''{round(abs(rez['ymax']),2):g}'''+   'см.$' )

    st.write('Минимальные значения моментов сопротивления расчетного контура в направлении осей $x$ и $y$ вычисляются по формуле:')

    st.latex('W_{bx} = \dfrac{I_{bx}}{x_{\\max}}; \\quad W_{by} = \dfrac{I_{by}}{y_{\\max}}.')

    st.write('В результате расчета найдем: $W_{bx}=' + f'''{round(abs(rez['Wxmin'])):g}''' + 'см^2; W_{by}=' + f'''{round(abs(rez['Wymin'])):g}''' + 'см^2.$')

    st.write('Предельные моменты, воспринимаемые расчетным контуром в плоскости осей $x$ и $y$ вычисляются по формулам:')
    st.latex('''M_{bx,ult}=\\gamma \cdot R_{bt} \cdot h_0 \cdot W_{bx}; \\quad
     M_{by,ult}=\\gamma \cdot R_{bt} \cdot h_0 \cdot W_{by}.''')
    gamma_min = min(contour_gamma)

    st.write('''Здесь $\\gamma='''+ str(gamma_min) + '''$ - минимальное значение повышающего коэффициента к прочности бетона, из найденных ранее.''')

    st.write('В результате расчета найдем: $M_{bx,ult}=' + f'''{round(abs(rez["Mbxult"]),1):g}''' + 'тсм; M_{by,ult}=' + f'''{round(abs(rez["Mbyult"]),1):g}''' + 'тсм.$')
    
    st.write('Проверка прочности выполняется из условия:')

    st.latex('\\dfrac{F}{F_{b,ult}} + \\left(\\dfrac{\delta_M \\cdot M_x}{M_{bx,ult}} + \\dfrac{\\delta_M \cdot M_y}{M_{by,ult}}\\right) = k_F + k_M \\le 1.')
    st.write('Здесь $k_F$ и $k_M$ - коэффициенты использования сечения по силе и моментам соответственно, причем $k_M \le 0.5\cdot k_F$.')

    if abs(rez["ex"]) != 0.0 or abs(rez["ey"]) != 0.0:
        st.write('Так как положение центра расчетного контура не совпадает с точкой приложения нагрузки, корректируем величину действующих моментов с учетом эксцентриситета.')
        st.write('Значения эксцентриситетов продольной силы относительно геометрического центра расчетного контура составляют:')
        st.write('$e_x = x_c - b/2=' + f'''{round(rez["ex"],2):g}''' + 'см; \\quad e_y = y_c - h/2=' f'''{round(rez["ey"],2):g}''' 'см.$')
        st.write('Таким образом дополнительные моменты от эксцентриситета геометрического центра составляют:')
        st.write('$M_{x,e} =  - F \\cdot e_x=' + f'''{round(rez["Mxexc"],1):g}''' + 'тсм; \\quad M_{y,e} = - F \\cdot e_y=' f'''{round(rez["Myexc"],1):g}''' 'тсм.$')
    
        st.write('Положение центра прочности контура относительно левого нижнего угла колонны вычисляем по формуле:')
        st.latex('''
        x_{c,\\gamma} = \\dfrac{\\sum_i \\gamma_i \\cdot S_{x,i}}{\\sum_i \\gamma_i \\cdot L_{i}} = \\dfrac{\\sum_i \\gamma_i \\cdot L_{i} \\cdot x_{0,i}}{\\sum_i \\gamma_i \\cdot L_{i}}; \\quad
        y_{c,\\gamma} = \\dfrac{\\sum_i \\gamma_i \\cdot S_{y,i}}{\\sum_i \\gamma_i \\cdot L_{i}} = \\dfrac{\\sum_i \\gamma_i \\cdot L_{i} \\cdot y_{0,i}}{\\sum_i \\gamma_i \\cdot L_{i}}.
        ''')
        st.write('В результате подстановки значений найдем $x_{c,\\gamma}='+ f'''{round(rez['xcM'],2):g}'''+ '$см; $y_{c,\\gamma}='+ f'''{round(rez['ycM'],2):g}$см.''')
        
        st.write('Значения эксцентриситетов продольной силы относительно центра прочности расчетного контура составляют:')
        st.write('$e_{x,\\gamma} = x_{c,\\gamma} - b/2=' + f'''{round(rez["exM"],2):g}''' + 'см; \\quad e_{y,\\gamma} = y_{c,\\gamma} - h/2=' f'''{round(rez["eyM"],2):g}''' 'см.$')
        st.write('Таким образом дополнительные моменты от эксцентриситета центра прочности составляют:')
        st.write('$M_{x,e,\\gamma} =  - F \\cdot e_{x,\\gamma}=' + f'''{round(rez["MxexcM"],1):g}''' + 'тсм; \\quad M_{y,e,\\gamma} = - F \\cdot e_{y,\\gamma}=' f'''{round(rez["MyexcM"],1):g}''' 'тсм.$')
        st.write('Величины действующих моментов с учетом эксцентриситета для расчета принимаем следующие:')
        st.latex('M_x = \\max(|M_x + M_{x,e}|; |M_x + M_{x,e,\\gamma}|); M_y = \\max(|M_y + M_{y,e}|; |M_y + M_{y,e,\\gamma}|)')
        st.write('В результате найдем $M_x = '+ f'''{round(rez["Mxlocmax"],1):g}''' + 'тсм; M_y='+ f'''{round(rez["Mylocmax"],1):g}'''+ 'тсм.$')

    st.write('Коэффициенты использования составляют:')
    st.write('$k_F=\\dfrac{F}{F_{b,ult}}=\\dfrac{' + f'''{round(F):g}''' + '}{' f'''{round(rez["Fbult"]):g}''' + '}=' + f'''{round(rez["kF"],3):g}''' + ';$')
    st.write('$k_M=\\dfrac{\\delta_M \cdot M_x}{M_{bx,ult}} + \\dfrac{\\delta_M \cdot M_y}{M_{by,ult}} =\\dfrac{' 
             + str(deltaM) + '\\cdot' + f'''{round(rez["Mxlocmax"],1):g}''' +  '}{' f'''{round(rez["Mbxult"],1):g}''' + '}+' +
              '\\dfrac{' + str(deltaM) + '\\cdot' + f'''{round(rez["Mylocmax"],1):g}'''  + '}{' f'''{round(rez["Mbyult"],1):g}''' + '}=' +
            f'''{round(rez["kM"],3):g}''' + ';$')
    st.write('$k=k_F+k_M=' + str(round(rez['kF'],3)) + '+' + str(round(rez['kMmax'],3)) + '=' + str(round(rez['k'],3)) + '$.')

st.write('Коэффициент использования по продольной силе $k_F=' + str(round(rez['kF'],3)) + '$.')
st.write('Коэффициент использования по моментам $k_М=' + str(round(rez['kMmax'],3)) + '$.')
st.write('Суммарный коэффициент использования $k=' + str(round(rez['k'],3)) + '$.')


#string = ''
#string += '''принимаем $$a+b+c$$ 
#\n'''
#string += '''принимаем $$b+c+d$$
#\n'''
#string += '$aaa$'
#st.write(string)

#from pylatex import *

#def gen_pdf(text):
#    # initialize a Document
#    doc = Document('tmppdf')

#    # this is a sample of a document, you could add more sections
#    with doc.create(Section('Пример')):
#        doc.append(text)
#    doc.generate_pdf("tmppdf", clean_tex=True, compiler = "XeLaTeX ")
    
#    with open("tmppdf.pdf", "rb") as pdf_file:
#        PDFbyte = pdf_file.read()
  
#    return PDFbyte

## the download button will get the generated file stored in Streamlit server side, and download it at the user's side
#st.download_button(label="Download PDF Report",
#                   key='download_pdf_btn',
#                   data=gen_pdf(string),
#                   file_name='name_of_your_file.pdf', # this might be changed from browser after pressing on the download button
#                   mime='application/octet-stream',)





