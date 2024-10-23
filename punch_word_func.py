import docx
from docx import Document
from docx.shared import Pt
from docx.oxml import parse_xml
from docx.shared import Mm
from docx.shared import RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import typing
import latex2mathml.converter
import mathml2omml


def formula_latex(latex_string: str) -> typing.Any:
    mathml_output = latex2mathml.converter.convert(latex_string)
    omml_output = mathml2omml.convert(mathml_output)
    xml_output = (
        f'<p xmlns:m="http://schemas.openxmlformats.org/officeDocument'
        f'/2006/math">{omml_output}</p>'
    )
    return parse_xml(xml_output)[0]

def add_math(p, latex_string) -> None:
    p._p.append(formula_latex(latex_string))

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
    if '$' in string:
        string_text, string_latex = divide_latex(string)
        for i in range(len(string_text)):
            if string_text[i] != 'NONE':
                p.add_run(string_text[i])
            else: add_math(p, string_latex[i])
    else: p.add_run(string)

def delete_paragraph(paragraph):
    p = paragraph._element
    p.getparent().remove(p)
    paragraph._p = paragraph._element = None
