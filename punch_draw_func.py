import plotly.graph_objects as go
import io

  
def draw_geometry(data):
    x_min, x_max, y_min, y_max, dx, dy = data['xmin0'], data['xmax0'], data['ymin0'], data['ymax0'],  data['dx'], data['dy']
    b, h = data['b'], data['h']
    xc, yc = data['xc'], data['yc']
    arrows_props = dict(arrowcolor="black", arrowsize=2.5, arrowwidth=0.5, arrowhead=5, axref='x', ayref='y', xref='x', yref='y', arrowside='end')
    #, bgcolor="#ffffff"
    text_props = dict(font=dict(color='black',size=14), showarrow=False)
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
    for contour in data['bounds']:
        fig.add_trace(go.Scatter(x=contour[0], y=contour[1], showlegend=False, mode='lines', line=dict(color='red', width=1.5)))
    #Линии контура
    for contour in data['contours']:
        fig.add_trace(go.Scatter(x=contour[0], y=contour[1], showlegend=False, mode='lines', line=dict(color='blue', width=3)))

    #НИЖНЯЯ РАЗМЕРНАЯ ЦЕПОЧКА
    #Добавляем ширину колонны
    add = 0.1*smax
    fig.add_annotation(x=0, ax=b, y=y_min-add, ay=y_min-add, **arrows_props)
    fig.add_annotation(x=b, ax=0, y=y_min-add, ay=y_min-add, **arrows_props)
    fig.add_trace(go.Scatter(x=[0, 0], y=[0, y_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[b, b], y=[0, y_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=b/2, y=y_min-0.95*add, text=f'{float(b):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Добавляем ширину контура
    fig.add_annotation(x=x_min, ax=x_max, y=y_min-2*add, ay=y_min-2*add, **arrows_props)
    fig.add_annotation(x=x_max, ax=x_min, y=y_min-2*add, ay=y_min-2*add, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_min, x_min], y=[0, y_min-2.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[x_max, x_max], y=[0, y_min-2.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_max+x_min)/2, y=y_min-1.95*add, text=f'{float(abs(x_max-x_min)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Размер от колонны до левой грани контура
    if abs(x_min)>0:
        fig.add_annotation(x=0, ax=x_min, y=y_min-add, ay=y_min-add, **arrows_props)
        fig.add_annotation(x=x_min, ax=0, y=y_min-add, ay=y_min-add, **arrows_props)
        fig.add_trace(go.Scatter(x=[x_min, x_min], y=[0, y_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=x_min/2, y=y_min-0.95*add, text=f'{float(abs(x_min)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Размер от колонны до правой грани контура
    if abs(x_max)>b:
        fig.add_annotation(x=b, ax=x_max, y=y_min-add, ay=y_min-add, **arrows_props)
        fig.add_annotation(x=x_max, ax=b, y=y_min-add, ay=y_min-add, **arrows_props)
        fig.add_trace(go.Scatter(x=[x_max, x_max], y=[0, y_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=(x_max+b)/2, y=y_min-0.95*add, text=f'{float(abs(x_max-b)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))

    #Добавляем высоту колонны
    fig.add_annotation(x=x_min-add, ax=x_min-add, y=0, ay=h, **arrows_props)
    fig.add_annotation(x=x_min-add, ax=x_min-add, y=h, ay=0, **arrows_props)
    fig.add_trace(go.Scatter(x=[0, x_min-1.1*add], y=[0, 0], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[0, x_min-1.1*add], y=[h, h], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=x_min-1.05*add, y=h/2, text=f'{float(h):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Добавляем высоту контура
    fig.add_annotation(x=x_min-2*add, ax=x_min-2*add, y=y_min, ay=y_max, **arrows_props)
    fig.add_annotation(x=x_min-2*add, ax=x_min-2*add, y=y_max, ay=y_min, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_min, x_min-2.1*add], y=[y_min, y_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[x_min, x_min-2.1*add], y=[y_max, y_max], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=x_min-2.05*add, y=(y_max+y_min)/2, text=f'{float(abs(y_max-y_min)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Размер от колонны до нижней грани контура
    if abs(y_min)>0:
        fig.add_annotation(x=x_min-add, ax=x_min-add, y=0, ay=y_min, **arrows_props)
        fig.add_annotation(x=x_min-add, ax=x_min-add, y=y_min, ay=0, **arrows_props)
        fig.add_trace(go.Scatter(x=[0, x_min-1.1*add], y=[y_min, y_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=x_min-1.05*add, y=(y_min)/2, text=f'{float(abs(y_min)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Размер от колонны до верхней грани контура
    if abs(y_max)>h:
        fig.add_annotation(x=x_min-add, ax=x_min-add, y=h, ay=y_max, **arrows_props)
        fig.add_annotation(x=x_min-add, ax=x_min-add, y=y_max, ay=h, **arrows_props)
        fig.add_trace(go.Scatter(x=[0, x_min-1.1*add], y=[y_min, y_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=x_min-1.05*add, y=(y_max+h)/2, text=f'{float(abs(y_max-h)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
      
    arrows_axes_props = dict(arrowcolor="red", arrowsize=3, arrowwidth=0.7, arrowhead=3, axref='x', ayref='y', xref='x', yref='y', arrowside='end')
    text_props_axes = dict(font=dict(color='red',size=16), showarrow=False)
    #Оси колонны
    fig.add_annotation(x=x_max+2*add, ax=b/2, y=h/2, ay=h/2, **arrows_axes_props)
    fig.add_annotation(x=b/2, ax=b/2, y=y_max+2.5*add, ay=h/2, **arrows_axes_props)

    if round(yc,3)!=round(h/2,3): #Если ось х контура не совпадает с центом колонны, то дополнительно рисуем оси контура
        fig.add_annotation(x=x_max+2*add, ax=xc, y=yc, ay=yc, **arrows_axes_props)
        fig.add_annotation(dict(x=x_max+2*add, y=h/2, text='x', textangle=0, yanchor='middle',xanchor='left', **text_props_axes))
        fig.add_annotation(dict(x=x_max+2*add, y=yc, text='xc', textangle=0, yanchor='middle',xanchor='left', **text_props_axes))
        #Добавляем эксцентриситет
        fig.add_annotation(x=x_max, ax=x_max, y=h/2, ay=yc, **arrows_props)
        fig.add_annotation(x=x_max, ax=x_max, y=yc, ay=h/2, **arrows_props)
        fig.add_annotation(dict(x=x_max-0.05*add, y=(yc+h/2)/2, text=f'{float(round(abs(yc-h/2),2)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    else:
        fig.add_annotation(dict(x=x_max+2*add, y=yc, text='x, xc', textangle=0, yanchor='middle',xanchor='left', **text_props_axes))
    
    if round(xc,3)!=round(b/2,3):  #Если ось y контура не совпадает с центом колонны, то дополнительно рисуем оси контура
        fig.add_annotation(x=xc, ax=xc, y=y_max+2.5*add, ay=yc, **arrows_axes_props)
        fig.add_annotation(dict(x=b/2, y=y_max+2.5*add, text='y', textangle=0, yanchor='bottom',xanchor='center', **text_props_axes))
        fig.add_annotation(dict(x=xc, y=y_max+2.5*add, text='yc', textangle=0, yanchor='bottom',xanchor='center', **text_props_axes))
        #Добавляем эксцентриситет
        fig.add_annotation(x=b/2, ax=xc, y=y_max, ay=y_max, **arrows_props)
        fig.add_annotation(x=xc, ax=b/2, y=y_max, ay=y_max, **arrows_props)
        fig.add_annotation(dict(x=(xc+b/2)/2, y=y_max+0.05*add, text=f'{float(round(abs(xc-b/2),2)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    else:
        fig.add_annotation(dict(x=xc, y=y_max+2.5*add, text='y, yc', textangle=0, yanchor='bottom',xanchor='center', **text_props_axes))

    #Расстояние до наиболее удаленных точек
    #Вдоль оси x (подписи сверху)
    fig.add_annotation(x=x_min, ax=xc, y=y_max+add, ay=y_max+add, **arrows_props)
    fig.add_annotation(x=xc, ax=x_min, y=y_max+add, ay=y_max+add, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_min, x_min], y=[y_max, y_max+1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_min+xc)/2, y=(y_max+1.05*add), text=f'{float(round(abs((x_min-xc)),2)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    fig.add_annotation(x=x_max, ax=xc, y=y_max+add, ay=y_max+add, **arrows_props)
    fig.add_annotation(x=xc, ax=x_max, y=y_max+add, ay=y_max+add, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_max, x_max], y=[y_max, y_max+1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_max+xc)/2, y=(y_max+1.05*add), text=f'{float(round(abs((x_max-xc)),2)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))

    #Вдоль оси y (подписи справа)
    fig.add_annotation(x=x_max+add, ax=x_max+add, y=y_max, ay=yc, **arrows_props)
    fig.add_annotation(x=x_max+add, ax=x_max+add, y=yc, ay=y_max, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_max, x_max+1.1*add], y=[y_max, y_max], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_max+0.95*add), y=(y_max+yc)/2, text=f'{float(round(abs(y_max-yc),2)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    fig.add_annotation(x=x_max+add, ax=x_max+add, y=y_min, ay=yc, **arrows_props)
    fig.add_annotation(x=x_max+add, ax=x_max+add, y=yc, ay=y_min, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_max, x_max+1.1*add], y=[y_min, y_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_max+0.95*add), y=(y_min+yc)/2, text=f'{float(round(abs(y_min-yc),2)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))

    
    fig.add_trace(go.Scatter(x=[xc], y=[yc], showlegend=False, mode="markers", marker_symbol=4, marker_size=15, line=dict(color='green')))
    fig.update_yaxes(scaleanchor="x",scaleratio=1,title="y")
    fig.update_xaxes(dict(title="x", visible=False))
    fig.update_yaxes(visible=False)
    #autosize=True,
    fig.update_layout(margin={'l': 0, 'r': 0, 't': 0, 'b': 0})
    #*dx/smax *dy/smax
    fig.update_layout(height=400, width=400)
    file_stream = io.BytesIO()
    fig.write_image(file_stream, format='png', width=400, height=400, scale=8)
##    fig.write_image(file_stream2, format='svg', width=400, height=400, scale=8)
##    fig.write_image('test.svg', format='svg', width=400, height=400, scale=8)
    return fig, file_stream


def draw_Aq(data):
    x_min, x_max, y_min, y_max, dx, dy = data['xmin0b'], data['xmax0b'], data['ymin0b'], data['ymax0b'],  data['dxb'], data['dyb']
    b, h = data['b'], data['h']
    xc, yc = data['xc'], data['yc']
    arrows_props = dict(arrowcolor="black", arrowsize=2.5, arrowwidth=0.5, arrowhead=5, axref='x', ayref='y', xref='x', yref='y', arrowside='end')
    #, bgcolor="#ffffff"
    text_props = dict(font=dict(color='black',size=14), showarrow=False)
    smax = max(dx, dy)
    fig = go.Figure()
    #Добавляем колонну
    xx = [0, b, b, 0, 0]
    yy = [0, 0, h, h, 0]
    #hatch = dict(fillpattern=dict(fgcolor='black', size=10, fillmode='replace', shape="/"))
    #**hatch
    fig.add_trace(go.Scatter(x=xx, y=yy, showlegend=False, fill='toself', fillcolor = 'rgba(128, 128, 128, 0.3)', mode='lines', line=dict(color='black', width=1.5)))
    fig.add_trace(go.Scatter(x=xx, y=yy, showlegend=False, mode='lines', line=dict(color='black')))

    #Красные линии
    for contour in data['bottom_bounds']:
        fig.add_trace(go.Scatter(x=contour[0], y=contour[1], showlegend=False, mode='lines', line=dict(color='red', width=1.5)))
    #Линии контура отпора
    for contour in data['bottom_contours']:
        fig.add_trace(go.Scatter(x=contour[0], y=contour[1], showlegend=False, mode='lines', line=dict(color='magenta', width=3)))
    #Линии контура
    for contour in data['contours']:
        fig.add_trace(go.Scatter(x=contour[0], y=contour[1], showlegend=False, mode='lines', line=dict(color='blue', width=1.5)))

    #НИЖНЯЯ РАЗМЕРНАЯ ЦЕПОЧКА
    #Добавляем ширину колонны
    add = 0.2*smax
    fig.add_annotation(x=0, ax=b, y=y_min-add, ay=y_min-add, **arrows_props)
    fig.add_annotation(x=b, ax=0, y=y_min-add, ay=y_min-add, **arrows_props)
    fig.add_trace(go.Scatter(x=[0, 0], y=[0, y_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[b, b], y=[0, y_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=b/2, y=y_min-0.95*add, text=f'{float(b):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Добавляем ширину контура
    fig.add_annotation(x=x_min, ax=x_max, y=y_min-2*add, ay=y_min-2*add, **arrows_props)
    fig.add_annotation(x=x_max, ax=x_min, y=y_min-2*add, ay=y_min-2*add, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_min, x_min], y=[0, y_min-2.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[x_max, x_max], y=[0, y_min-2.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=(x_max+x_min)/2, y=y_min-1.95*add, text=f'{float(abs(x_max-x_min)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Размер от колонны до левой грани контура
    if abs(x_min)>0:
        fig.add_annotation(x=0, ax=x_min, y=y_min-add, ay=y_min-add, **arrows_props)
        fig.add_annotation(x=x_min, ax=0, y=y_min-add, ay=y_min-add, **arrows_props)
        fig.add_trace(go.Scatter(x=[x_min, x_min], y=[0, y_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=x_min/2, y=y_min-0.95*add, text=f'{float(abs(x_min)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))
    #Размер от колонны до правой грани контура
    if abs(x_max)>b:
        fig.add_annotation(x=b, ax=x_max, y=y_min-add, ay=y_min-add, **arrows_props)
        fig.add_annotation(x=x_max, ax=b, y=y_min-add, ay=y_min-add, **arrows_props)
        fig.add_trace(go.Scatter(x=[x_max, x_max], y=[0, y_min-1.1*add], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=(x_max+b)/2, y=y_min-0.95*add, text=f'{float(abs(x_max-b)):g}', textangle=0, yanchor='bottom',xanchor='center', **text_props))

    #Добавляем высоту колонны
    fig.add_annotation(x=x_min-add, ax=x_min-add, y=0, ay=h, **arrows_props)
    fig.add_annotation(x=x_min-add, ax=x_min-add, y=h, ay=0, **arrows_props)
    fig.add_trace(go.Scatter(x=[0, x_min-1.1*add], y=[0, 0], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[0, x_min-1.1*add], y=[h, h], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=x_min-1.05*add, y=h/2, text=f'{float(h):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Добавляем высоту контура
    fig.add_annotation(x=x_min-2*add, ax=x_min-2*add, y=y_min, ay=y_max, **arrows_props)
    fig.add_annotation(x=x_min-2*add, ax=x_min-2*add, y=y_max, ay=y_min, **arrows_props)
    fig.add_trace(go.Scatter(x=[x_min, x_min-2.1*add], y=[y_min, y_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_trace(go.Scatter(x=[x_min, x_min-2.1*add], y=[y_max, y_max], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
    fig.add_annotation(dict(x=x_min-2.05*add, y=(y_max+y_min)/2, text=f'{float(abs(y_max-y_min)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Размер от колонны до нижней грани контура
    if abs(y_min)>0:
        fig.add_annotation(x=x_min-add, ax=x_min-add, y=0, ay=y_min, **arrows_props)
        fig.add_annotation(x=x_min-add, ax=x_min-add, y=y_min, ay=0, **arrows_props)
        fig.add_trace(go.Scatter(x=[0, x_min-1.1*add], y=[y_min, y_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=x_min-1.05*add, y=(y_min)/2, text=f'{float(abs(y_min)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
    #Размер от колонны до верхней грани контура
    if abs(y_max)>h:
        fig.add_annotation(x=x_min-add, ax=x_min-add, y=h, ay=y_max, **arrows_props)
        fig.add_annotation(x=x_min-add, ax=x_min-add, y=y_max, ay=h, **arrows_props)
        fig.add_trace(go.Scatter(x=[0, x_min-1.1*add], y=[y_min, y_min], showlegend=False, mode='lines', line=dict(color='black', width=0.5)))
        fig.add_annotation(dict(x=x_min-1.05*add, y=(y_max+h)/2, text=f'{float(abs(y_max-h)):g}', textangle=270, yanchor='middle',xanchor='right', **text_props))
      
    arrows_axes_props = dict(arrowcolor="red", arrowsize=3, arrowwidth=0.7, arrowhead=3, axref='x', ayref='y', xref='x', yref='y', arrowside='end')
    text_props_axes = dict(font=dict(color='red',size=16), showarrow=False)
   

    
    fig.update_yaxes(scaleanchor="x",scaleratio=1,title="y")
    fig.update_xaxes(dict(title="x", visible=False))
    fig.update_yaxes(visible=False)
    #autosize=True,
    fig.update_layout(margin={'l': 0, 'r': 0, 't': 0, 'b': 0})
    fig.update_layout(height=200, width=200)
    file_stream = io.BytesIO()
    fig.write_image(file_stream, format='png', width=200, height=200, scale=8)
##    fig.write_image(file_stream2, format='svg', width=400, height=400, scale=8)
##    fig.write_image('test.svg', format='svg', width=400, height=400, scale=8)
    return fig, file_stream

