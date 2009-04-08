from copy import copy
from lxml import etree
from lxml.builder import ElementMaker
from lxml.etree import tostring
from pprint import pprint
from utils import arg_parser
import itertools
import optparse
import os
import string

curdir = os.path.abspath(os.curdir)

nsmap = dict(sld="http://www.opengis.net/sld",
             ogc="http://www.opengis.net/ogc",
             xlink="http://www.w3.org/1999/xlink",
             xsi="http://www.w3.org/2001/XMLSchema-instance")


def emaker(prefix):
    nsmap2 = copy(nsmap)
    ns = nsmap2.pop(prefix)
    return ElementMaker(namespace=ns, nsmap=nsmap2)


SLD = emaker('sld')

def sld_subelement(parent, name, attrib=dict()):
    ele = SLD(name, attrib)
    parent.append(ele)
    return ele

sld_sub = sld_subelement

def build_sld_trees(axls):
    for axl in axls:
        axltree = etree.parse(axl)
        for layer in axltree.xpath(".//LAYER"):
            yield transform_to_sldtree(layer)


def transform_to_sldtree(layer):
    sldtree = SLD('StyledLayerDescriptor',
                  {"schemaLocation":"http://www.opengis.net/sld StyledLayerDescriptor.xsd",
                   "version":'1.0.0'})
    namedlayer = sld_subelement(sldtree, 'NamedLayer')
    name = sld_subelement(namedlayer, "Name")
    layer_name = name.text = "alachua:%s" %layer.attrib['id'].split('.')[1]

    userstyle = sld_subelement(namedlayer, "UserStyle")
    fts = sld_subelement(userstyle, "FeatureTypeStyle")
    sld_subelement(fts, "Name").text = layer_name
    sld_subelement(fts, "Title").text = layer.attrib['name']
    sld_subelement(fts, "Abstract").text = "styles for the alachua project"
    sld_subelement(fts, "FeatureTypeName").text = layer_name
    add_rules(fts, layer)
    return sldtree
    

symbol_map = dict(
    RASTERMARKERSYMBOL=None,
    SHIELDSYMBOL=None,
    SIMPLELINESYMBOL='LineSymbolizer',
    SIMPLEMARKERSYMBOL='PointSymbolizer',
    SIMPLEPOLYGONSYMBOL='PolygonSymbolizer',
    TEXTSYMBOL='TextSymbolizer',
    TRUETYPEMARKERSYMBOL='TextSymbolizer'
    )


def add_rules(ele, layer):
    "add rules to fts 'ele'"
    gr = layer.xpath("./GROUPRENDERER")
    if not len(gr):
        return
    gr = gr.pop()

    symbols = [gr.xpath('.//%s' %tag) for tag in symbol_map.keys() if symbol_map[tag]]

    for axl_sym in itertools.chain(*symbols):
        # tags.update((x, None) for x in axl_sym.attrib.keys()) # debug
        #parent = axl_sym.getparent()
        rule = make_rule(axl_sym, ele)
        sld_sym = make_symbol(rule, axl_sym)
        if axl_sym.tag not in ("TRUETYPEMARKERSYMBOL", "TEXTSYMBOL"):
            filters = make_filters(rule, axl_sym)
        else:
            print axl_sym.text
        #rule_handler.get(parent.tag, normal_rule)(rule, axl_sym)

def make_rule(axl_ele, fts):
    rule = sld_subelement(fts, "Rule")
    parent = axl_ele.getparent()
    title = parent.attrib.get('label', None)
    if title is not None:
        sld_subelement(rule, "Title").text = title
    return rule

_axl = ("OTHER", "RANGE", "EXACT")

eq_map = dict(upper=dict(high='PropertyIsLessThanOrEqualTo',
                         low='PropertyIsGreaterThan'),
              lower=dict(high='PropertyIsLessThan',
                         low='PropertyIsGreaterThanOrEqualTo',
                         )
              )
eq_map[None] = dict(high='PropertyIsLessThan',
                    low='PropertyIsLessThanOrEqualTo')

def make_filters(rule, axl_sym):
    "build rule with filter ala RANGE"
    parent = axl_sym.getparent()
    tag = parent.tag
    if tag not in _axl or tag == _axl[0]:
        return

    filt = sld_sub(rule, "Filter")

    if tag == _axl[1]:
        equality = aquire_attr(axl_sym, "equality", _axl[1])

        lt = sld_sub(filt, eq_map[equality]['high'])
        top = float(aquire_attr(axl_sym, "upper", _axl[1]))
        name_and_literal(lt, axl_sym, top)
        
        gt = sld_sub(filt, eq_map[equality]['low'])
        bot = float(aquire_attr(axl_sym, "lower", _axl[1]))
        name_and_literal(gt, axl_sym, bot)
    else:
        try:
            val = int(aquire_attr(axl_sym, "value", _axl[2]))
            eq = sld_sub(filt, 'PropertyIsEqualTo')
            name_and_literal(eq, axl_sym, val)
        except ValueError:
            #@@ exact + geometry, catch before?
            pass

    return rule
filter_rule = make_filters 


def aquire_attr(ele, attr, tag=None, strict=True):
    found = None
    orig = ele
    while found == None and ele is not None:
        parent = ele.getparent()
        ele = parent
        if ele is None:
            if strict:
                raise ValueError(orig)
            continue
        if tag is not None and parent.tag != tag:
            continue
        found = ele.attrib.get(attr, None)
    return found


def name_and_literal(ele, axl, litval):
    sld_sub(ele, "PropertyName").text = aquire_attr(axl, 'lookupfield')
    sld_sub(ele, "Literal").text = unicode(litval)


def normal_rule(rule, axl_sym):
    "nothing fancy rule"
    sld_sym = sld_subelement(rule, symbol_map[axl_sym.tag])
    filltype = axl_sym.attrib.get("filltype")
    if filltype and filltype == 'solid':
        fill = sld_subelement(sld_sym, "Fill")
        add_fill_params(fill, axl_sym)
    if axl_sym.attrib.get("boundary") is not None:
        stroke = sld_subelement(sld_sym, "Stroke")
        add_stroke_params(stroke, axl_sym)
    return sld_sym

make_symbol = normal_rule

def normal_text(text, axl_sym): 
    "creates ts" 
    pass 


make_text = normal_text 


def add_stroke_params(stroke, axl_sym):
    strokecolor = axl_sym.attrib['boundarycolor']
    strokewidth = axl_sym.attrib['boundarywidth']
    strokeopacity = axl_sym.attrib['boundarytransparency']
    strokecolor = axl_sym.attrib['boundarycolor']
    digits = strokecolor.split(',')
    hexcolor = "#%s%s%s" %tuple([convert_to_hex_letter(int(dig)) for dig in digits])
    sld_sub(stroke, "CssParameter", dict(name='stroke')).text = hexcolor
    sld_sub(stroke, "CssParameter", dict(name='stroke-width')).text = strokewidth
    sld_sub(stroke, "CssParameter", dict(name='stroke-opacity')).text = strokeopacity





def add_fill_params(sld_sym, axl_sym):
    fillcolor = axl_sym.attrib['fillcolor']
    digits = fillcolor.split(',')
    hexcolor = "#%s%s%s" %tuple([convert_to_hex_letter(int(dig)) for dig in digits])
    sld_sub(sld_sym, "CssParameter", dict(name='fill')).text = hexcolor
    opacity = axl_sym.attrib.get('filltransparency', None)
    if opacity is not None:
        sld_sub(sld_sym, "CssParameter", dict(name='fill-opacity')).text = opacity
        
hex_seq = [16*x for x in range(len(string.hexdigits))]

def convert_to_hex_letter(num):
    first = string.hexdigits[num / 16]
    mod = string.hexdigits[num % 16]
    return "%s%s" %(first, mod)
        


rule_handler = dict(RANGE=filter_rule,
                    EXACT=normal_rule,
                    OTHER=normal_rule)

# main script

usage = "usage: %prog [options] inputdir [inputdir, etc]"
main_parser = optparse.OptionParser(usage=usage)

main_parser.add_option('-o', '--output',
                  help="Output directory",
                  action="store",
                  dest="output_dir",
                  default=curdir)

@arg_parser(main_parser)
def main(args=None, options=None, parser=None):
    listdir = os.listdir(args[1]) # multiples?
    axls = [x for x in listdir if x.endswith('.axl')]
    sld_trees = build_sld_trees(axls)
    if not os.path.exists(options.output_dir):
        os.mkdir(options.output_dir)
    findname = etree.ETXPath("//{http://www.opengis.net/sld}NamedLayer/{http://www.opengis.net/sld}Name")
    for tree in sld_trees:
        assert len(tree)
        res = findname(tree)
        assert len(res), ValueError(tostring(tree, pretty_print=True))
        dummy, name = res[0].text.split(":")
        fh = open(os.path.join(options.output_dir, name), 'w+')
        fh.write(tostring(tree, pretty_print=True))



# explorer script

usage = "usage: %prog [options] inputdir"
explorer_parser = optparse.OptionParser(usage=usage)

explorer_parser.add_option('-x', '--xpath',
                           help="Xpath Expression",
                           action="store",
                           dest="xpath",
                           default="")

explorer_parser.add_option('-e', '--extension',
                           help="file extension",
                           action="store",
                           dest="file_ext",
                           default='.sld')

# debugging globals for data exploration
ATTRIBS = dict()
tags = dict()

@arg_parser(explorer_parser)
def explorer(args=None, options=None, parser=None):
    opdir = args[1]
    listdir = os.listdir(opdir) # multiples?
    for fp in [fp for fp in listdir if fp.endswith(options.file_ext)]:
        tree = etree.parse(os.path.join(opdir, fp))
        #import pdb;pdb.set_trace()
        find = etree.ETXPath(options.xpath)
        for res in find(tree):
            tags[res.tag]=None
            ATTRIBS.update((x, None) for x in res.attrib.values())
    pprint(tags.keys())
    pprint(ATTRIBS.keys())



# we need to create a mapping between attributes in axl symbols
# and resulting CssParameter names

# empty "#" beside resolved mappings

# INCOMPLETE
arc_attrib_to_css_map = dict(font='font-family',
                             fontstyle='font-style',
                             fontsize='font-size',
                             boundary=None,
                             boundarywidth='stroke-width',
                             boundarycolor='stroke',
                             boundarytransparency='stroke-opacity',
                             fillcolor='fill',
                             filltransparency='fill-opacity')

arc_attribs = [
    'angle',
    'antialiasing',
    'boundary',#
    'boundarycaptype',
    'boundarycolor',#
    'boundaryjointype',
    'boundarytransparency',#
    'boundarytype',
    'boundarywidth',#
    'captype',
    'character',
    'color',
    'fillcolor',#
    'fillinterval',
    'filltransparency',
    'filltype'
    'font', # done
    'fontcolor',
    'fontsize',#
    'fontstyle',#
    'glowing',
    'jointype',
    'outline',
    'overlap',
    'rotatemethod',
    'transparency',
    'type',
    'usecentroid',
    'width',
    ]

css_param = [
    'fill',#
    'fill-opacity',#
    'font-family', #
    'font-size',#
    'font-style',#
    'font-weight'
    'stroke',
    'stroke-dasharray',
    'stroke-dashoffset',
    'stroke-linecap',
    'stroke-linejoin',
    'stroke-opacity',
    'stroke-width',#
    ]
