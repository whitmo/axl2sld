#
from lxml import etree
from lxml.etree import tostring
import optparse
import os
from utils import arg_parser
from lxml.builder import ElementMaker
from copy import copy
from pprint import pprint
import itertools
curdir = os.path.abspath(os.curdir)

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
    for tree in sld_trees:
        continue
    pprint(tags.keys())

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


ATTRIBS = dict()

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


def build_sld_trees(axls):
    for axl in axls:
        axltree = etree.parse(axl)
        for layer in axltree.xpath(".//LAYER"):
            yield transform_to_sldtree(layer)

def transform_to_sldtree(layer):
    sldtree = SLD('StyledLayerDescriptor',
                  {"schemaLocation":"http://www.opengis.net/sld StyledLayerDescriptor.xsd",
                   "version":'1.0.0'})
    namedlayer = SLD.subElement(sldtree, 'NamedLayer')
    name = SLD.subElement(namedlayer, "Name")
    layer_name = name.text = "alachua:%s" %layer.attrib['id'].split('.')[1]

    userstyle = SLD.subElement(namedlayer, "UserStyle")
    fts = SLD.subElement(userstyle, "FeatureTypeStyle")
    SLD.subElement(fts, "Name").text = layer_name
    SLD.subElement(fts, "Title").text = layer.attrib['name']
    SLD.subElement(fts, "Abstract").text = "styles for the alachua project"
    SLD.subElement(fts, "FeatureTypeName").text = layer_name
    add_rules(fts, layer)
    return sldtree
    

rule_map = dict(SHIELDSYMBOL=None,
                RASTERMARKERSYMBOL=None,
                SIMPLEPOLYGONSYMBOL='PolygonSymbolizer',
                SIMPLELINESYMBOL='LineSymbolizer',
                TEXTSYMBOL='TextSymbolizer',
                TRUETYPEMARKERSYMBOL='TextSymbolizer',
                SIMPLEMARKERSYMBOL='PointSymbolizer')

tags = dict()


def add_rules(ele, layer):
    gr = layer.xpath("./GROUPRENDERER")
    if not len(gr):
        return
    gr = gr.pop()


    symbols = [gr.xpath('.//%s' %tag) for tag in rule_map.keys() if rule_map[tag]]

    for sym in itertools.chain(*symbols):
        tags.update((x, None) for x in sym.attrib.keys())
#         tag = sym.getparent().tag
#         #rule_handler.get(tag, normal_rule)(sym, ele)

def filter_rule(ele, symbol):
    "build rule with filter"
    rule = normal_rule(ele, symbol)
    return rule

def normal_rule(ele, symbol):
    "nothing fancy rule"
    rule = SLD.subElement(ele, "Rule")
    parent = symbol.getparent()
    title = parent.attrib.get('label', None)
    if title is not None:
        SLD.subElement(rule, "Title").text = title
    sld_sym = SLD.subElement(rule, rule_map[symbol.tag])
    
    return rule

import string

def convert_to_hex_letter(num):
    dl = string.hexdigits
    dn = [16*x for x in range(len(string.hexdigits))]
    for val in dn:
        if num == val:
            return "%s0" %dl[num/16]
        if num > val:
            last = val
            continue
        else:
            return "%s%s" %(dl[last], dl[num - last])
        
        

rule_handler = dict(RANGE=filter_rule,
                    EXACT=normal_rule,
                    OTHER=normal_rule)

css_param_map = dict()

# we need to create a mapping between attributes in axl symbols
# and resulting CssParameter names

arc_attribs = [
    'angle',
    'antialiasing',
    'boundary',
    'boundarycaptype',
    'boundarycolor',
    'boundaryjointype',
    'boundarytransparency',
    'boundarytype',
    'boundarywidth',
    'captype',
    'character',
    'color',
    'fillcolor',
    'fillinterval',
    'filltransparency',
    'filltype'
    'font',
    'fontcolor',
    'fontsize',
    'fontstyle',
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

css_param = ['stroke-linejoin',
             'font-size',
             'fill-opacity',
             'stroke',
             'stroke-linecap',
             'font-family',
             'font-style',
             'fill',
             'stroke-width',
             'stroke-opacity',
             'stroke-dashoffset',
             'stroke-dasharray',
             'font-weight']


nsmap = dict(sld="http://www.opengis.net/sld",
             ogc="http://www.opengis.net/ogc",
             xlink="http://www.w3.org/1999/xlink",
             xsi="http://www.w3.org/2001/XMLSchema-instance")

def emaker(prefix):
    return ElementMaker(namespace=nsmap[prefix], nsmap={prefix:nsmap[prefix]})



SLD = emaker('sld')

