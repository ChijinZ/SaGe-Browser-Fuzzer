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


from __future__ import barry_as_FLUFL, print_function
from cgi import parse
import os
import re
import random
import sys
import json
from types import new_class
from grammar import Grammar
from enum import unique
import logging
def get_option(option_name):
    for i in range(len(sys.argv)):
        if (sys.argv[i] == option_name) and ((i + 1) < len(sys.argv)):
            return sys.argv[i + 1]
        elif sys.argv[i].startswith(option_name + '='):
            return sys.argv[i][len(option_name) + 1:]
    return None

def _get_tag_name(jsgrammar, string):
    return jsgrammar._parse_tag_and_attributes(string)["tagname"]
        
       
replace_list = []
def combine(new_grammar_file, old_grammar_file):
    err=0
    OGra = Grammar(True)
    err = OGra.parse_from_file(old_grammar_file)
    with open(old_grammar_file, 'r') as f:
        Orules = f.readlines()
        Orules = parse_rules(Orules, OGra)
    if err > 0:
        logging.error('There were errors parsing grammar')
        return

    NGra = Grammar(True)
    err = NGra.parse_from_file(new_grammar_file) 
    with open(new_grammar_file, 'r') as f:
        Nrules = f.readlines()
        Nrules = parse_rules(Nrules, NGra)
    if err > 0:
        logging.error('There were errors parsing grammar')
        return

    tags = buid_keyset()
    co_Orules=[]
    co_Nrules=[]
    output_copy_rules = []
    ignored_all_rules = []
    Object_name = None
    i=0
    while i<len(Orules):
        orule = Orules[i]['origin_line'].strip()
        if orule == '':
            # output_copy_rules.append(Orules[i])
            pass
        elif '# ' in orule or orule == '#' or\
             '#tod' in orule:
            pass
            # output_copy_rules.append(orule)
        elif '#' == orule[0]:
            Object_name = orule[1:]
            output_copy_rules.append({"origin_line": ""})
            output_copy_rules.append(Orules[i])
            i+=1
            while i<len(Orules) and Orules[i]['origin_line']!='' \
                             and Orules[i]['origin_line'][0]!='#':
                co_Orules.append(Orules[i])
                i+=1
            i-=1
            co_Nrules, _ = filter_new_rules(Nrules, Object_name)
            combined_rule, ignore_rule = combine_cor_rules(co_Nrules, co_Orules, tags)
            output_copy_rules += combined_rule
            ignored_all_rules += ignore_rule
            co_Nrules = []
            co_Orules = []
            Object_name = None
        
        else:
            # output_copy_rules.append(Orules[i])
            if Orules[i]['method'] is not None and ('setAttribute' in Orules[i]['method'] \
                                     and 'SVGElement' == Orules[i]['right_object'] or \
                                    "CSSStyleDeclaration" == Orules[i]['right_object'] \
                                        and "setProperty" in Orules[i]['method']):
                output_copy_rules.append(Orules[i])
            else:
                logging.warning("ungroup line: " + orule.strip())
        i+=1

    rules = [rule['origin_line'] + '\n' for rule in output_copy_rules]

    rules += [
        "<new svg_href_path> = \"<hash>\" + <SVGPathElement>.id;\n",
        "<new svg_url_clippath> = \"url(<hash>\" + <SVGClipPathElement>.id + \")\";\n",
        "<new svg_url_filter> = \"url(<hash>\" + <SVGFilterElement>.id + \")\";\n",
        "<new svg_url_marker> = \"url(<hash>\" + <SVGMarkerElement>.id + \")\";\n",
        "<new svg_url_mask> = \"url(<hash>\" + <SVGMaskElement>.id + \")\";\n",
        "<new svg_url_fill> = \"url(<hash>\" + <SVGLinearGradientElement>.id + \")\";\n",
        "<new svg_url_fill> = \"url(<hash>\" + <SVGPatternElement>.id + \")\";\n"
        "<new svg_url_fill> = \"url(<hash>\" + <SVGRadialGradientElement>.id + \")\";\n"
    ]
    rules += ["document.all[<int min=0 max=100>%document.all.length].appendChild(<Element>);\n" for i in range(40)]
    rules += ['<new CSSStyleDeclaration> = <Element>.style;\n' for i in range(19)]
    with open(new_grammar_file, 'r') as f:
        existed_rules = f.readlines()
    rules = existed_rules + rules
    with open('domato/js2.txt', 'w') as f:
        f.writelines(rules)
    
        
        
constructor_regex = re.compile(
    "^<(?:new )?(.*?)> = new ([^\(]*)\((.*)\)")  # <X> = new constructor(<a>, ..)
method_with_return_regex = re.compile(
    "^<(?:new )?(.*?)> = <(.*?)>\.([^=\(]*)\((.*)\)")  # <Y> = <X>.func(<a>, ..)
method_wo_return_regex = re.compile("^<(?:new )?(.*?)>\.([^=\(]*)\((.*)\)")  # <X>.func(<a>, ..)
var_read_regex = re.compile("^<(?:new )?(.*?)> = <(.*?)>\.(.*);")  # <Y> = <X>.var
var_write_regex = re.compile(
    "^<(?:new )?(.*?)>.(.*) = (.*?)$")  # <X>.var = <Y> or <X>.var = "aa" or <X> = <Y>
# transition_regex = re.compile("^<(.*?)>\..* = .*?")  # <X> = <Y> or <X> = {<a>: <b>}  
extend_regex = re.compile(
    '!extends ([^ ]*) ([^ ]*);?')



def parse_rules(rules, grammar):
    # Add it as import

    all_parsed_rules = []
    for rule in rules:
        res =     {
            'type': None,
            "letf_tag": None,
            "right_object": None,
            "attribute": None,
            "method": None,
            "arguements" : [],
        }
        if (r :=extend_regex.match(rule)) is not None:
            res['left_tag'] = _get_tag_name(grammar, r.group(2))
            res['right_object'] = _get_tag_name(grammar, r.group(1))
            res['type'] = 'extends'
        elif '#' == rule[0]:
            res['type'] = 'comment'
        elif (r := constructor_regex.match(rule)) is not None:
            res['left_tag'] = _get_tag_name(grammar, r.group(1))
            res['right_object'] = _get_tag_name(grammar, r.group(2))
            res['arguements'] = get_arguements(r.group(3))
            res['type'] = 'constructor'
            
        elif (r := method_with_return_regex.match(rule)) is not None:
            res['left_tag'] = _get_tag_name(grammar, r.group(1))
            res['right_object'] = _get_tag_name(grammar, r.group(2))
            res['method'] = r.group(3).strip()
            res['arguements'] = get_arguements(r.group(4))
            res['type'] = 'return_func'
            
        elif (r := method_wo_return_regex.match(rule)) is not None:
            res['right_object'] = _get_tag_name(grammar, r.group(1))
            res['method'] = r.group(2).strip()
            res['arguements'] = get_arguements(r.group(3))
            res['type'] = 'no_return_func'
            
        elif (r := var_read_regex.match(rule)) is not None:
            res['left_tag'] = _get_tag_name(grammar, r.group(1))
            res['right_object'] = _get_tag_name(grammar, r.group(2))
            res['attribute'] = r.group(3).strip() #setJSAudioBufferSourceNode_buffer
            res['type'] = 'read_attr'

        elif (r := var_write_regex.match(rule)) is not None:
            res['right_object'] = _get_tag_name(grammar, r.group(1))
            res['attribute'] = r.group(2).strip()
            res['left_tag'] = _get_tag_name(grammar, r.group(3))
            res['type'] = 'write_attr'
        else:
            # pass
            res['type'] = 'unknown'
            if len(rule) > 0 and rule != '\n':
                # logging.warning("not handle rule: "+rule.strip())
                pass
        res['origin_line'] = rule.strip()
        all_parsed_rules.append(res)
    
    return all_parsed_rules

arguments_regex = re.compile(', *')  # <a>,<b>,<c>

def get_arguements(line):
    if line == '':
        return []
    arg = arguments_regex.split(line)
    return [i for i in arg if len(i)>0]


def filter_new_rules(Nrules, obj_name):
    co = []
    noco = []

    for rule in Nrules:
        if rule['right_object'] == obj_name and \
                ('func' in rule['type'] or 'write' in rule['type']):
            co.append(rule)
        else:
            noco.append(rule)
    if len(co) == 0:
        obj_name = 'DOM'+obj_name
        noco = []
        for rule in Nrules:
            if rule['right_object'] == obj_name and \
                    ('func' in rule['type'] or 'write' in rule['type']):
                co.append(rule)
            else:
                noco.append(rule)
        if len(co) > 0:
            replace_list.append(obj_name)    
    return co, noco

tag_regex = re.compile('<(new )?(.*)> =(.*)')
tag_name_regex = re.compile("[A-Za-z\-_]*")
def buid_keyset():
    files = ['jshelpers.txt', 'webkit_helper.txt', 'common.txt', 'attributevalues.txt', 'svgattrvalues.txt', 'cssproperties.txt']
    all_tags = set()
    for fi in files:
        fpath = os.path.join('./domato', fi)
        with open(fpath, 'r') as f:
            rules = f.readlines()
        for rule in rules:
            if (r := tag_regex.match(rule)):
                tag_name = r.group(2).strip()
                if 'new ' in r.group(3):
                    continue
                elif tag_name_regex.match(tag_name) is not None:
                    all_tags.add(tag_name)
                else:
                    logging.warning('unknown tag type: '+rule.strip())
            else:
                if len(rule.strip()) > 0 and '#' not in rule and '!' not in rule:
                    logging.warning("cannot handle addition rules: "+rule.strip())
    del_list = ['DOMString', 'boolean', "Element", "HTMLTableSectionElement", "Window", "Function"]
    for na in del_list:
        if na in all_tags:
            all_tags.remove(na)
    all_tags.add("htmlstring")
    return all_tags

# string_regex = re.compile("\"([^<^>]*)\"")
lower_tag_regex = re.compile("\"?<([A-Za-z_\-]*)>\"?")
def combine_cor_rules(Nrules, ORules, kset):
    output_ORules = []
    ignore_rule = []
    for rule in ORules:
        flag=False
        if 'func' in rule['type']:
            if 'execCommand' == rule['method'] and 'Document' == rule['right_object']:
                flag=True
            elif 'setProperty' == rule['method'] and 'CSSStyleDeclaration' == rule['right_object']:
                flag=True
            # elif "GlobalEventHandlers" == rule['right_object']:
            #     flag=True
            else:
                for arg in rule['arguements']:
                    if (r := lower_tag_regex.match(arg)) is not None \
                                    and r.group(1) in kset:
                        flag = True
                        break
        elif rule['type'] == 'write_attr':
            if (r := lower_tag_regex.match(rule['left_tag'])) is not None \
                     and r.group(1) in kset:
                flag = True
        if flag:
            output_ORules.append(rule)
            continue
            matched = False
            for idx,nrule in enumerate(Nrules):
                if rule['type'] != nrule['type']:
                    continue
                elif rule['attribute'] is not None and rule['attribute'] == nrule['attribute']:
                    matched=True
                elif rule['method'] is not None and rule['method'] == nrule['method']:
                    attr1 = rule['arguements']
                    attr2 = nrule['arguements']
                    if len(attr1) != len(attr2):
                        continue
                    matched = True
                    # for (a1,a2) in zip(attr1, attr2):
                    #     if a1 == a2 or ("\"" in a1 and a2 == "<DOMString>") \
                    #         or ("fuzzint"==a1 and a2=='<float>'):
                    #         continue
                    #     else:
                    #         matched = False
                    #         break
                if matched:
                    output_ORules.append(rule)
                    break
            if not matched:
                logging.warning('unmatched old rule: '+rule['origin_line'].strip())
        elif 'func' in rule['type'] or rule['type'] == 'write_attr':
            logging.warning('ignored old rules: '+rule['origin_line'].strip())
            ignore_rule.append(rule)
    
    # ignore_rule.append("")
    return output_ORules, ignore_rule  
    



def main():
    new_grammar_path = os.path.join('./temp/js2_bak.txt')
    old_grannar_path = os.path.join('./domato/js.txt')
    if not os.path.exists(new_grammar_path):
        logging.error('new grammar file not exists')
        exit(1)
    if not os.path.exists(new_grammar_path):
        logging.error('new grammar file not exists')
        exit(1)
    combine(new_grammar_path,old_grannar_path)

if __name__ == '__main__':
    main()
