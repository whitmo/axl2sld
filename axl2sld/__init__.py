# todo:
# TRUETYPEMARKER     -- pointsymbolizer for graphics later
# RASTERMARKERSYMBOL --
# xsi:SchemaLocation
# ns0:
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


ABSTRACT = "styles for the alachua project" #@@
curdir = os.path.abspath(os.curdir)

nsmap = dict(sld="http://www.opengis.net/sld",
             ogc="http://www.opengis.net/ogc",
             xlink="http://www.w3.org/1999/xlink",
             xsi="http://www.w3.org/2001/XMLSchema-instance")


def emaker(prefix):
    nsmap2 = copy(nsmap)
    ns = nsmap2[prefix]
    return ElementMaker(namespace=ns, nsmap=nsmap2)


SLD = emaker('sld')
OGC = emaker('ogc')
LITERAL = OGC.Literal

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


def pretty(ele):
    print tostring(ele, pretty_print=True)



def transform_to_sldtree(layer):
    layer_name = "alachua:%s" %layer.attrib['id'].split('.')[1]
    sldtree = SLD.StyledLayerDescriptor(
        SLD.NamedLayer(SLD.Name(layer_name),
                       SLD.UserStyle(make_fts(layer, layer_name))),
        {"schemaLocation":"http://www.opengis.net/sld StyledLayerDescriptor.xsd",
         "version":'1.0.0'})
    return sldtree

def make_fts(layer, layer_name):
    fts = SLD.FeatureTypeStyle(
        SLD.Name(layer_name),
        SLD.Title(layer.attrib['name']),
        SLD.Abstract(ABSTRACT),
        SLD.FeatureTypeName(layer_name)
        )
    add_rules(fts, layer)
    return fts

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
        if sld_sym.tag.endswith('PointSymbolizer'):
            populate_point_symbolizer(sld_sym, axl_sym)
        if axl_sym.tag not in ("TRUETYPEMARKERSYMBOL", "TEXTSYMBOL"):
            filters = make_filters(rule, axl_sym)
        else:
            make_text(sld_sym, axl_sym)


geometry_map = dict(point='circle')

def populate_point_symbolizer(sld_sym, axl_sym):
    layer = axl_sym.xpath("ancestor::LAYER")[0]
    atype = layer.xpath("./DATASET")[0].attrib['type']
    if atype == 'point':
        geo = SLD.Geometry(OGC.PropertyName("SHAPE"))
        graphic = SLD.Graphic(
            SLD.Mark(SLD.WellKnownName('circle'),
                     SLD.Fill(SLD.CssParameter('',dict(name=""))),
                     ),
            SLD.Size(),
            )
        sld_sym.extend((geo, graphic))


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
    ele.append(SLD.PropertyName(aquire_attr(axl, 'lookupfield')))
    ele.append(LITERAL(unicode(litval)))


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


def make_text(text, axl_sym): 
    "creates ts" 
    pass 


def add_stroke_params(stroke, axl_sym):
    strokecolor = axl_sym.attrib['boundarycolor']
    strokewidth = axl_sym.attrib['boundarywidth']
    strokeopacity = axl_sym.attrib['boundarytransparency']
    strokecolor = axl_sym.attrib['boundarycolor']
    digits = strokecolor.split(',')
    hexcolor = "#%s%s%s" %tuple([convert_to_hex_letter(int(dig)) for dig in digits])
    stroke.extend((
        SLD.CssParameter(OGC.Literal(hexcolor), dict(name='stroke')),
        SLD.CssParameter(OGC.Literal(strokewidth), dict(name='stroke')),
        SLD.CssParameter(OGC.Literal(strokeopacity), dict(name='stroke'))
        ))

def cssparam(name, value, parent=None):
    css = SLD.CssParameter(OGC.Literal(value), dict(name=name))
    if parent is not None:
        parent.append(css)
    return css

def add_fill_params(sld_sym, axl_sym):
    fillcolor = axl_sym.attrib['fillcolor']
    digits = fillcolor.split(',')
    hexcolor = "#%s%s%s" %tuple([convert_to_hex_letter(int(dig)) for dig in digits])
    cssparam('fill', hexcolor, sld_sym)
    opacity = axl_sym.attrib.get('filltransparency', None)
    if opacity is not None:
        cssparam('fill-opacity', opacity, sld_sym)
        
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
    filepaths = dict()
    for tree in sld_trees:
        assert len(tree)
        res = findname(tree)
        assert len(res), ValueError(tostring(tree, pretty_print=True))
        dummy, name = res[0].text.split(":")
        filepath = os.path.join(options.output_dir, name)
        if filepaths.has_key(filepath):
            filepaths[filepath] += 1
            filepath = filepath + str(filepaths[filepath])
        else:
            filepaths[filepath]=1                            
        fh = open(filepath, 'w+')
        fh.write(tostring(tree, pretty_print=True))
    #pprint([(x, y) for x, y in filepaths.items() if y>1])




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


