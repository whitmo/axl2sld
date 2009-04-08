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

def sld_subelement(parent, name):
    ele = SLD(name)
    parent.append(ele)
    return ele


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
    

rule_map = dict(SHIELDSYMBOL=None,
                RASTERMARKERSYMBOL=None,
                SIMPLEPOLYGONSYMBOL='PolygonSymbolizer',
                SIMPLELINESYMBOL='LineSymbolizer',
                TEXTSYMBOL='TextSymbolizer',
                TRUETYPEMARKERSYMBOL='TextSymbolizer',
                SIMPLEMARKERSYMBOL='PointSymbolizer')


def add_rules(ele, layer):
    "add rules to fts 'ele'"
    gr = layer.xpath("./GROUPRENDERER")
    if not len(gr):
        return
    gr = gr.pop()

    symbols = [gr.xpath('.//%s' %tag) for tag in rule_map.keys() if rule_map[tag]]

    for sym in itertools.chain(*symbols):
        # tags.update((x, None) for x in sym.attrib.keys()) # debug
        tag = sym.getparent().tag
        rule_handler.get(tag, normal_rule)(sym, ele, layer)

def filter_rule(ele, symbol, layer):
    "build rule with filter ala RANGE"
    rule = normal_rule(ele, symbol)
    return rule

def normal_rule(ele, symbol, layer=None):
    "nothing fancy rule"
    rule = sld_subelement(ele, "Rule")
    parent = symbol.getparent()
    title = parent.attrib.get('label', None)
    if title is not None:
        sld_subelement(rule, "Title").text = title
    sld_sym = sld_subelement(rule, rule_map[ele.tag])
    
    return rule



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
