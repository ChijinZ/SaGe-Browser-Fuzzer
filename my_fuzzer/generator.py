#   Domato - main generator script
#   -------------------------------
#
#   Written and maintained by Ivan Fratric <ifratric@google.com>
#
#   Copyright 2017 Google Inc. All Rights Reserved.
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


from __future__ import print_function

import json
import os
import re
import random
import sys
import pickle
import time

from grammar import Grammar, OneGramSelector, GlobalInfo, DerivationTree, DerivationTreeNode, InvalidNode
from typing import List, Dict, Tuple

from graph_analyzer import divide_into_groups, Graph

_N_MAIN_LINES = 1000
_N_EVENTHANDLER_LINES = 500

if "EXPERIMENT_FOR_SPEED" in os.environ:
    _N_MAIN_LINES = 200
    _N_EVENTHANDLER_LINES = 100




_N_ADDITIONAL_HTMLVARS = 5

# A map from tag name to corresponding type for HTML tags
_HTML_TYPES = {
    "html": "HTMLHtmlElement",
    "head": "HTMLHeadElement",
    "title": "HTMLTitleElement",
    "base": "HTMLBaseElement",
    "link": "HTMLLinkElement",
    "meta": "HTMLMetaElement",
    "style": "HTMLStyleElement",
    "body": "HTMLBodyElement",
    "article": "HTMLElement",
    "section": "HTMLElement",
    "nav": "HTMLElement",
    "aside": "HTMLElement",
    "h1": "HTMLHeadingElement",
    "h2": "HTMLHeadingElement",
    "h3": "HTMLHeadingElement",
    "h4": "HTMLHeadingElement",
    "h5": "HTMLHeadingElement",
    "h6": "HTMLHeadingElement",
    "hgroup": "HTMLElement",
    "header": "HTMLElement",
    "footer": "HTMLElement",
    "address": "HTMLElement",
    "p": "HTMLParagraphElement",
    "hr": "HTMLHRElement",
    "pre": "HTMLPreElement",
    "blockquote": "HTMLQuoteElement",
    "ol": "HTMLOListElement",
    "ul": "HTMLUListElement",
    "menu": "HTMLMenuElement",
    "li": "HTMLLIElement",
    "dl": "HTMLDListElement",
    "dt": "HTMLElement",
    "dd": "HTMLElement",
    "figure": "HTMLElement",
    "figcaption": "HTMLElement",
    "main": "HTMLElement",
    "div": "HTMLDivElement",
    "a": "HTMLAnchorElement",
    "em": "HTMLElement",
    "strong": "HTMLElement",
    "small": "HTMLElement",
    "s": "HTMLElement",
    "cite": "HTMLElement",
    "q": "HTMLQuoteElement",
    "dfn": "HTMLElement",
    "abbr": "HTMLElement",
    "ruby": "HTMLElement",
    "rt": "HTMLElement",
    "rp": "HTMLElement",
    "data": "HTMLDataElement",
    "time": "HTMLTimeElement",
    "code": "HTMLElement",
    "var": "HTMLElement",
    "samp": "HTMLElement",
    "kbd": "HTMLElement",
    "sub": "HTMLElement",
    "sup": "HTMLElement",
    "i": "HTMLElement",
    "b": "HTMLElement",
    "u": "HTMLElement",
    "mark": "HTMLElement",
    "bdi": "HTMLElement",
    "bdo": "HTMLElement",
    "span": "HTMLSpanElement",
    "br": "HTMLBRElement",
    "wbr": "HTMLElement",
    "ins": "HTMLModElement",
    "del": "HTMLModElement",
    "picture": "HTMLPictureElement",
    "source": "HTMLSourceElement",
    "img": "HTMLImageElement",
    "iframe": "HTMLIFrameElement",
    "embed": "HTMLEmbedElement",
    "object": "HTMLObjectElement",
    "video": "HTMLVideoElement",
    "audio": "HTMLAudioElement",
    "track": "HTMLTrackElement",
    "map": "HTMLMapElement",
    "area": "HTMLAreaElement",
    "table": "HTMLTableElement",
    "caption": "HTMLTableCaptionElement",
    "colgroup": "HTMLTableColElement",
    "col": "HTMLTableColElement",
    "tbody": "HTMLTableSectionElement",
    "thead": "HTMLTableSectionElement",
    "tfoot": "HTMLTableSectionElement",
    "tr": "HTMLTableRowElement",
    "td": "HTMLTableCellElement",
    "th": "HTMLTableCellElement",
    "form": "HTMLFormElement",
    "label": "HTMLLabelElement",
    "input": "HTMLInputElement",
    "button": "HTMLButtonElement",
    "select": "HTMLSelectElement",
    "datalist": "HTMLDataListElement",
    "optgroup": "HTMLOptGroupElement",
    "option": "HTMLOptionElement",
    "textarea": "HTMLTextAreaElement",
    "output": "HTMLOutputElement",
    "progress": "HTMLProgressElement",
    "meter": "HTMLMeterElement",
    "fieldset": "HTMLFieldSetElement",
    "legend": "HTMLLegendElement",
    "details": "HTMLDetailsElement",
    "summary": "HTMLElement",
    "dialog": "HTMLDialogElement",
    "script": "HTMLScriptElement",
    "noscript": "HTMLElement",
    "template": "HTMLTemplateElement",
    "slot": "HTMLSlotElement",
    "canvas": "HTMLCanvasElement",
    "applet": "HTMLUnknownElement",
    "acronym": "HTMLElement",
    "bgsound": "HTMLUnknownElement",
    "dir": "HTMLDirectoryElement",
    "frame": "HTMLFrameElement",
    "frameset": "HTMLFrameSetElement",
    "noframes": "HTMLElement",
    "isindex": "HTMLUnknownElement",
    "keygen": "HTMLUnknownElement",
    "listing": "HTMLPreElement",
    "menuitem": "HTMLElement",
    "nextid": "HTMLUnknownElement",
    "noembed": "HTMLElement",
    "param": "HTMLParamElement",
    "plaintext": "HTMLElement",
    "rb": "HTMLElement",
    "rtc": "HTMLElement",
    "strike": "HTMLElement",
    "xmp": "HTMLPreElement",
    "basefont": "HTMLElement",
    "big": "HTMLElement",
    "blink": "HTMLUnknownElement",
    "center": "HTMLElement",
    "font": "HTMLFontElement",
    "marquee": "HTMLMarqueeElement",
    "multicol": "HTMLUnknownElement",
    "nobr": "HTMLElement",
    "spacer": "HTMLUnknownElement",
    "tt": "HTMLElement",
    "model": "HTMLModelElement",
    "portal": "HTMLPortalElement",
    "discard": "HTMLUnknownElement",
}

# A map from tag name to corresponding type for SVG tags
_SVG_TYPES = {
    "svg": "SVGSVGElement",
    "g": "SVGGElement",
    "defs": "SVGDefsElement",
    "desc": "SVGDescElement",
    "title": "SVGTitleElement",
    "symbol": "SVGSymbolElement",
    "use": "SVGUseElement",
    "image": "SVGImageElement",
    "switch": "SVGSwitchElement",
    "style": "SVGStyleElement",
    "path": "SVGPathElement",
    "rect": "SVGRectElement",
    "circle": "SVGCircleElement",
    "ellipse": "SVGEllipseElement",
    "line": "SVGLineElement",
    "polyline": "SVGPolylineElement",
    "polygon": "SVGPolygonElement",
    "text": "SVGTextElement",
    "tspan": "SVGTSpanElement",
    "textPath": "SVGTextPathElement",
    "marker": "SVGMarkerElement",
    "linearGradient": "SVGLinearGradientElement",
    "radialGradient": "SVGRadialGradientElement",
    "stop": "SVGStopElement",
    "pattern": "SVGPatternElement",
    "clipPath": "SVGClipPathElement",
    "mask": "SVGMaskElement",
    "filter": "SVGFilterElement",
    "feDistantLight": "SVGFEDistantLightElement",
    "fePointLight": "SVGFEPointLightElement",
    "feSpotLight": "SVGFESpotLightElement",
    "feBlend": "SVGFEBlendElement",
    "feColorMatrix": "SVGFEColorMatrixElement",
    "feComponentTransfer": "SVGFEComponentTransferElement",
    "feFuncR": "SVGFEFuncRElement",
    "feFuncG": "SVGFEFuncGElement",
    "feFuncB": "SVGFEFuncBElement",
    "feFuncA": "SVGFEFuncAElement",
    "feComposite": "SVGFECompositeElement",
    "feConvolveMatrix": "SVGFEConvolveMatrixElement",
    "feDiffuseLighting": "SVGFEDiffuseLightingElement",
    "feDisplacementMap": "SVGFEDisplacementMapElement",
    "feFlood": "SVGFEFloodElement",
    "feGaussianBlur": "SVGFEGaussianBlurElement",
    "feImage": "SVGFEImageElement",
    "feMerge": "SVGFEMergeElement",
    "feMergeNode": "SVGFEMergeNodeElement",
    "feMorphology": "SVGFEMorphologyElement",
    "feOffset": "SVGFEOffsetElement",
    "feSpecularLighting": "SVGFESpecularLightingElement",
    "feTile": "SVGFETileElement",
    "feTurbulence": "SVGFETurbulenceElement",
    "a": "SVGAElement",
    "view": "SVGViewElement",
    "script": "SVGScriptElement",
    "animate": "SVGAnimateElement",
    "set": "SVGSetElement",
    "animateMotion": "SVGAnimateMotionElement",
    "mpath": "SVGMPathElement",
    "animateTransform": "SVGAnimateTransformElement",
    "metadata": "SVGMetadataElement",
    "foreignObject": "SVGForeignObjectElement",
    "feDropShadow": "SVGFEDropShadowElement",

}


def generate_html_elements(ctx, n):
    for i in range(n):
        tag = random.choice(list(_HTML_TYPES))
        tagtype = _HTML_TYPES[tag]
        ctx['htmlvarctr'] += 1
        varname = 'htmlvar%05d' % ctx['htmlvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': tagtype})
        ctx[
            'htmlvargen'] += '/* newvar{' + varname + ':' + tagtype + '} */ var ' + varname + ' = document.createElement(\"' + tag + '\"); //' + tagtype + '\n'


def add_html_ids(matchobj, ctx, original_line=None):
    # print(matchobj, ctx)
    tagname = matchobj.group(0)[1:-1]
    if tagname in _HTML_TYPES:
        ctx['htmlvarctr'] += 1
        varname = 'htmlvar%05d' % ctx['htmlvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': _HTML_TYPES[tagname]})
        ctx['htmlvargen'] += f"/* newvar{{ {varname}: {_HTML_TYPES[tagname]} }} */ " \
                             f"var {varname} = document.getElementById(\"{varname}\"); " \
                             f"if({varname} == null) {{ {varname} = document.createElement(\"{tagname}\");}}" \
                             f"\n"
        return matchobj.group(0) + 'id=\"' + varname + '\" '
    elif tagname in _SVG_TYPES:
        ctx['svgvarctr'] += 1
        varname = 'svgvar%05d' % ctx['svgvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': _SVG_TYPES[tagname]})
        ctx['htmlvargen'] += f"/* newvar{{ {varname}: {_SVG_TYPES[tagname]} }} */ " \
                             f"var {varname} = document.getElementById(\"{varname}\"); " \
                             f"if({varname} == null) {{ {varname} = " \
                             f"document.createElementNS(\"http://www.w3.org/2000/svg\",\"{tagname}\");}}" \
                             f"\n"
        return matchobj.group(0) + 'id=\"' + varname + '\" '
    else:
        return matchobj.group(0)


def generate_function_body(jsgrammar, htmlctx, num_lines,
                           tree_list: List[DerivationTree],
                           statement_map: Dict[str, DerivationTreeNode]):
    js = ''
    js += 'var fuzzervars = {};\n\n'
    js += "SetVariable(fuzzervars, window, 'Window');\nSetVariable(fuzzervars, document, 'Document');\nSetVariable(fuzzervars, document.body.firstChild, 'Element');\n\n"
    js += '//beginjs\n'
    js += htmlctx['htmlvargen']
    js += jsgrammar._generate_code(num_lines, tree_list, statement_map, htmlctx['htmlvars'])
    js += '\n//endjs\n'
    js += 'var fuzzervars = {};\nfreememory()\n'
    return js


def check_grammar(grammar):
    """Checks if grammar has errors and if so outputs them.

    Args:
      grammar: The grammar to check.
    """

    for rule in grammar._all_rules:
        for part in rule['parts']:
            if part['type'] == 'text':
                continue
            tagname = part['tagname']
            # print tagname
            if tagname not in grammar._creators:
                print('No creators for type ' + tagname)


def generate_new_sample(template, htmlgrammar, cssgrammar, jsgrammar,
                        tree_list: List[DerivationTree],
                        statement_map: Dict[str, DerivationTreeNode]):
    """Parses grammar rules from string.

    Args:
      template: A template string.
      htmlgrammar: Grammar for generating HTML code.
      cssgrammar: Grammar for generating CSS code.
      jsgrammar: Grammar for generating JS code.

    Returns:
      A string containing sample data.
    """

    result = template

    cssgrammar.derivation_tree = DerivationTree()
    css = cssgrammar.generate_symbol('rules', statement_map)

    html = ""
    for _ in range(10):
        htmlgrammar.derivation_tree = DerivationTree()
        html += htmlgrammar.generate_symbol('line', statement_map)

    htmlctx = {
        'htmlvars': [],
        'htmlvarctr': 0,
        'svgvarctr': 0,
        'htmlvargen': ''
    }

    # for line in html:
    #

    html = re.sub(
        r'<[a-zA-Z0-9_-]+ ',
        lambda match: add_html_ids(match, htmlctx),
        html
    )
    generate_html_elements(htmlctx, _N_ADDITIONAL_HTMLVARS)

    result = result.replace('<cssfuzzer>', css)
    result = result.replace('<htmlfuzzer>', html)

    handlers = False
    while '<jsfuzzer>' in result:
        numlines = _N_MAIN_LINES
        if handlers:
            numlines = _N_EVENTHANDLER_LINES
        else:
            handlers = True
        result = result.replace(
            '<jsfuzzer>',
            generate_function_body(jsgrammar, htmlctx, numlines, tree_list, statement_map),
            1
        )

    return result


def get_option(option_name):
    for i in range(len(sys.argv)):
        if (sys.argv[i] == option_name) and ((i + 1) < len(sys.argv)):
            return sys.argv[i + 1]
        elif sys.argv[i].startswith(option_name + '='):
            return sys.argv[i][len(option_name) + 1:]
    return None


class Generator:
    def __init__(self, selector: OneGramSelector, global_info: GlobalInfo):
        self.grammar_dir = os.path.dirname(__file__)
        f = open(os.path.join(self.grammar_dir, 'template.html'))
        self.template = f.read()
        f.close()

        self.dump_tree_dir = None

        self.selector = selector
        self.global_info = global_info

        self.derivation_tree_list: List[DerivationTree] = []
        self.statement_to_tree: Dict[str, DerivationTreeNode] = {}

        self.htmlgrammar = Grammar(selector=selector, global_info=global_info, grammar_type="html")
        err = self.htmlgrammar.parse_from_file(os.path.join(self.grammar_dir, 'html.txt'))
        print("html parsed")
        # CheckGrammar(htmlgrammar)
        if err > 0:
            print('There were errors parsing html grammar')
            return

        self.cssgrammar = Grammar(selector=selector, global_info=global_info, grammar_type="css")
        err = self.cssgrammar.parse_from_file(os.path.join(self.grammar_dir, 'css.txt'))
        print("css parsed")
        # CheckGrammar(cssgrammar)
        if err > 0:
            print('There were errors parsing css grammar')
            return

        self.collect_tree_info = False
        if os.getenv("COLLECT_TREE_INFO") is not None:
            print("collect tree info")
            self.collect_tree_info = True
        self.use_invalid_tree = False
        if os.getenv("USE_INVALID_TREE") is not None:
            print("use invalid tree")
            self.use_invalid_tree = True

        self.jsgrammar = Grammar(selector=selector, global_info=global_info, grammar_type="js",
                                 should_remove_redundant=True,
                                 collect_tree_info=self.collect_tree_info,
                                 use_invalid_tree=self.use_invalid_tree)
        browser_grammar = os.getenv("BROWSER_GRAMMAR")
        if browser_grammar is None:
            print("not set BROWSER_GRAMMAR, default webref_js")
        if browser_grammar == "CHROME":
            err = self.jsgrammar.parse_from_file(os.path.join(self.grammar_dir, 'webref_js.txt'))
        elif browser_grammar == "FIREFOX":
            err = self.jsgrammar.parse_from_file(os.path.join(self.grammar_dir, 'webref_js.txt'))
        elif browser_grammar == "WEBKIT":
            err = self.jsgrammar.parse_from_file(os.path.join(self.grammar_dir, 'webref_js.txt'))
        elif browser_grammar == "ORIGINAL_DOMATO":
            err = self.jsgrammar.parse_from_file(os.path.join(self.grammar_dir, 'js.txt'))
        elif browser_grammar == "WEBREF":
            err = self.jsgrammar.parse_from_file(os.path.join(self.grammar_dir, 'webref_js.txt'))
        else:
            print(f"BROWSER_GRAMMAR is invalid: {browser_grammar}, default webref_js")
            err = self.jsgrammar.parse_from_file(os.path.join(self.grammar_dir, 'webref_js.txt'))
        # CheckGrammar(jsgrammar)

        if err > 0:
            print('There were errors parsing js grammar')
            return
        print("js parsed")

        # JS and HTML grammar need access to CSS grammar.
        # Add it as import
        self.htmlgrammar.add_import('cssgrammar', self.cssgrammar)
        self.jsgrammar.add_import('cssgrammar', self.cssgrammar)

    def handle_feedback(self, feedback: List[Tuple[str, bool]]):
        # for line in feedback:
        #     statement = line[0]
        #     is_semantic_error = line[1]
        #     try:
        #         tree = self.statement_to_tree[statement]
        #         # self.selector.update_stats("js", tree, is_semantic_error)
        #     except KeyError as e:
        #         print(e)
        #         print(f"statement: {statement}")
        if self.dump_tree_dir is None:
            print("dump_tree_dir is None")
            return
        if not self.use_invalid_tree:
            # when we use invalid tree, we don't need to dump derivation tree
            with open(f"{self.dump_tree_dir}/{random.getrandbits(128)}.pickle", "wb") as f:
                pickle.dump((self.derivation_tree_list, self.statement_to_tree, feedback), f)
        self.derivation_tree_list.clear()
        self.statement_to_tree.clear()

    def handle_update_probs(self):
        self.selector.update_probs()

    def load_selector_and_info(self, pickle_path: str):
        with open(pickle_path, "rb") as f:
            selector, info = pickle.load(f)
            self.selector = selector
            self.global_info = info

    def store_selector_and_info(self, pickle_path: str):
        with open(pickle_path, "wb") as f:
            pickle.dump((self.selector, self.global_info), f)

    def generate_one(self) -> str:
        result = generate_new_sample(self.template, self.htmlgrammar, self.cssgrammar,
                                     self.jsgrammar, self.derivation_tree_list, self.statement_to_tree)

        # for tree in self.derivation_tree_list:
        #     print(tree)
        #     print("\n")

        return result

    def _get_tag_name(self, string):
        return self.jsgrammar._parse_tag_and_attributes(string)["tagname"]

    def generate_sample_of_two_apis(self, original_line_1, original_line_2):
        pass

    def build_graph(self):
        graph = Graph()
        arguments_regex = re.compile("<([^>)]*)>")  # <a>,<b>,<c>
        constructor_regex = re.compile(
            "^<(?:new )?(.*?)> = new.*?\((.*)\)")  # <X> = new constructor(<a>, ..)
        method_with_return_regex = re.compile(
            "^<(?:new )?(.*?)> = <(.*?)>\.[^=]*\((.*)\)")  # <Y> = <X>.func(<a>, ..)
        method_wo_return_regex = re.compile("^<(?:new )?(.*?)>\.[^=]*\((.*)\)")  # <X>.func(<a>, ..)
        var_read_regex = re.compile("^<(?:new )?(.*?)> = <(.*?)>\..*")  # <Y> = <X>.var
        var_write_regex = re.compile(
            "^<(?:new )?(.*?)>.* = (.*?)$")  # <X>.var = <Y> or <X>.var = "aa" or <X> = <Y>
        # transition_regex = re.compile("^<(.*?)>\..* = .*?")  # <X> = <Y> or <X> = {<a>: <b>}
        rules = self.jsgrammar._all_rules
        for rule in rules:
            rule_id = graph.add_rule(rule)
            line = rule["original_line"]

            if (r := constructor_regex.match(line)) is not None:
                left_name = self._get_tag_name(r.group(1))
                graph.add_node(left_name)
                arg_splited = arguments_regex.split(r.group(2))
                for i in range(0, len(arg_splited)):
                    if i % 2 == 0:
                        continue
                    else:
                        assert arg_splited[i] != "", f"{arg_splited}, {line}"
                        arg_name = self._get_tag_name(arg_splited[i])
                        graph.add_node(arg_name)
                        graph.add_edge(left_name, arg_name, rule_id)
            elif (r := method_with_return_regex.match(line)) is not None:
                left_name = self._get_tag_name(r.group(1))
                right_obj_name = self._get_tag_name(r.group(2))
                graph.add_node(left_name)
                graph.add_node(right_obj_name)
                graph.add_edge(left_name, right_obj_name, rule_id)
                arg_splited = arguments_regex.split(r.group(3))
                for i in range(0, len(arg_splited)):
                    if i % 2 == 0:
                        continue
                    else:
                        assert arg_splited[i] != "", f"{arg_splited}, {line}"
                        arg_name = self._get_tag_name(arg_splited[i])
                        graph.add_node(arg_name)
                        # graph.add_edge(left_name, arg_name, rule_id)
                        graph.add_edge(right_obj_name, arg_name, rule_id)
            elif (r := method_wo_return_regex.match(line)) is not None:
                obj_name = self._get_tag_name(r.group(1))
                graph.add_node(obj_name)
                arg_splited = arguments_regex.split(r.group(2))
                for i in range(0, len(arg_splited)):
                    if i % 2 == 0:
                        continue
                    else:
                        assert arg_splited[i] != "", f"{arg_splited}, {line}"
                        arg_name = self._get_tag_name(arg_splited[i])
                        graph.add_node(arg_name)
                        graph.add_edge(obj_name, arg_name, rule_id)
            elif (r := var_read_regex.match(line)) is not None:
                left_name = self._get_tag_name(r.group(1))
                right_name = self._get_tag_name(r.group(2))
                graph.add_node(left_name)
                graph.add_node(right_name)
                graph.add_edge(left_name, right_name, rule_id)
            elif (r := var_write_regex.match(line)) is not None:
                left_name = self._get_tag_name(r.group(1))
                graph.add_node(left_name)
                arg_splited = arguments_regex.split(r.group(2))
                for i in range(0, len(arg_splited)):
                    if i % 2 == 0:
                        continue
                    else:
                        assert arg_splited[i] != "", f"{arg_splited}, {line}"
                        arg_name = self._get_tag_name(arg_splited[i])
                        graph.add_node(arg_name)
                        graph.add_edge(left_name, arg_name, rule_id)
            else:
                pass
                # print("not handle rule:", line)

        something_left = set(graph.nodes.keys()) - set(self.jsgrammar._creators.keys()) if len(
            graph.nodes.keys()) > len(self.jsgrammar._creators.keys()) else set(
            self.jsgrammar._creators.keys()) - set(graph.nodes.keys())
        # if len(something_left) > 0:
        #     print("something left:", something_left)
        return graph

def check_if_semantic_error(s: str) -> bool:
    for error_type in ["TypeError", "ReferenceError", "NotSupportedError"]:
        if error_type in s:
            return True

    return False


def main():
    selector = OneGramSelector()
    global_info = GlobalInfo()
    generator = Generator(selector, global_info)
    target_file = ""
    while True:
        msg = sys.stdin.readline().strip()
        if msg == "generate":
            seed = generator.generate_one()
            try:
                f = open(target_file, 'w')
                f.write(seed)
                f.close()
            except IOError as e:
                print(f'Error writing to output: {e}')
            print("done")
            sys.stdout.flush()
        elif msg == "exit":
            return
        elif msg == "update":
            generator.handle_update_probs()
            print("done")
            sys.stdout.flush()
        elif msg.startswith("init"):
            target_file = msg.split(" ")[1]
            print("target file path: ", target_file)
            print("received")
            sys.stdout.flush()
        elif msg.startswith("load"):
            pickle_path = msg.split(" ")[1]
            print("load info from ", pickle_path)
            generator.load_selector_and_info(pickle_path)
            print("loaded")
            sys.stdout.flush()
        elif msg.startswith("store"):
            pickle_path = msg.split(" ")[1]
            print("store info into ", pickle_path)
            generator.store_selector_and_info(pickle_path)
            print("stored")
            sys.stdout.flush()
        elif msg.startswith("dumptree"):
            dump_tree_dir = msg.split(" ")[1]
            generator.dump_tree_dir = dump_tree_dir
            print("dump tree directory: ", dump_tree_dir)
            print("received")
            sys.stdout.flush()
        elif msg.startswith("feedback"):
            try:
                if generator.collect_tree_info:
                    space_index = msg.index(" ")
                    feedback_str = msg[space_index + 1:]
                    feedback_raw = json.loads(feedback_str)
                    feedback: List[Tuple[str, bool]] = []
                    total_num = 0
                    error_num = 0
                    for line in feedback_raw:
                        if not isinstance(line, list):
                            continue
                        if len(line) != 2:
                            continue
                        if "GetVariable" in line[0] or "SetVariable" in line[0]:
                            continue
                        error = check_if_semantic_error(line[1])
                        feedback.append((line[0], error))
                        total_num += 1
                        error_num += 1 if error else 0
                    if total_num != 0:
                        print(f"error rate: {error_num / total_num} ({error_num}/{total_num}) ({time.time()})")
                        generator.handle_feedback(feedback)
            except BaseException as e:
                print(f"error during process feedback: {e}")
            print("received")
            sys.stdout.flush()


if __name__ == '__main__':
    main()
