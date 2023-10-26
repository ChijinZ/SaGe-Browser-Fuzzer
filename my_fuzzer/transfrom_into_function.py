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
import os
import re
import random
import sys
import json
from grammar import Grammar


def get_option(option_name):
    for i in range(len(sys.argv)):
        if (sys.argv[i] == option_name) and ((i + 1) < len(sys.argv)):
            return sys.argv[i + 1]
        elif sys.argv[i].startswith(option_name + '='):
            return sys.argv[i][len(option_name) + 1:]
    return None

def _get_tag_name(jsgrammar, string):
    return jsgrammar._parse_tag_and_attributes(string)["tagname"]
        
       

def transform(path, output_path):
    err=0
    jsgrammar = Grammar(True)
    jsgrammar.parse_from_file('./domato/js2.txt')
    if '.txt' in path:
        rules = jsgrammar._all_rules
        key_string = "original_line"
    else:
        with open(path, 'r') as f:
            rules = json.load(f)
        key_string = "origin_line"
    if err > 0:
        print('There were errors parsing grammar')
        return
    # Add it as import
    arguments_regex = re.compile("<([^>)]*)>")  # <a>,<b>,<c>
    
    constructor_regex = re.compile(
        "^<(?:new )?(.*?)> = new[^\(]*?\((.*)\)")  # <X> = new constructor(<a>, ..)
    method_with_return_regex = re.compile(
        "^<(?:new )?(.*?)> = <(.*?)>\.([^=\(]*)\((.*)\)")  # <Y> = <X>.func(<a>, ..)
    method_wo_return_regex = re.compile("^<(?:new )?(.*?)>\.([^=\(]*)\((.*)\)")  # <X>.func(<a>, ..)
    var_read_regex = re.compile("^<(?:new )?(.*?)> = <(.*?)>\.(.*);")  # <Y> = <X>.var
    var_write_regex = re.compile(
        "^<(?:new )?(.*?)>.(.*) = (.*?)$")  # <X>.var = <Y> or <X>.var = "aa" or <X> = <Y>
    # transition_regex = re.compile("^<(.*?)>\..* = .*?")  # <X> = <Y> or <X> = {<a>: <b>}
    
    all_functions=[]
    for rule in rules:
        line = rule[key_string]

        if 'missed' in rule and rule['missed'] == False:
            all_functions.append(rule)
            continue
        function_name = []
        
        if (r := constructor_regex.match(line)) is not None:
            left_name = _get_tag_name(jsgrammar, r.group(1))
            # function_name +=['js'+left_name+'Constructor']
            function_name += ["WebCore::JSDOMConstructor<WebCore::JS%s>::construct(JSC::JSGlobalObject*, JSC::CallFrame*)" % left_name]
            function_name += ["WebCore::JSDOMBuiltinConstructor<WebCore::JS%s>::construct(JSC::JSGlobalObject*, JSC::CallFrame*)" % left_name]

            # arg_splited = arguments_regex.split(r.group(2))
            
        elif (r := method_with_return_regex.match(line)) is not None:
            left_name = _get_tag_name(jsgrammar, r.group(1))
            right_obj_name = _get_tag_name(jsgrammar, r.group(2))
            method_name = r.group(3).strip()
            function_name += ['js'+ right_obj_name + 'ConstructorFunction_' + method_name]
            function_name +=  ['js'+ right_obj_name + 'PrototypeFunction_' + method_name]
            function_name += [right_obj_name+method_name+"CodeGenerator"]
            # function_name +=  ['jsDOMWindow_'+ obj_name + 'Constructor' + method_name]
            function_name +=  ['js'+ right_obj_name + 'InstanceFunction_' + method_name]     
            # arg_splited = argu ments_regex.split(r.group(4))
            
        elif (r := method_wo_return_regex.match(line)) is not None:
            obj_name = _get_tag_name(jsgrammar, r.group(1))
            method_name = r.group(2).strip()
            # arg_splited = arguments_regex.split(r.group(3))
            function_name += ['js'+ obj_name + 'ConstructorFunction_' + method_name]
            function_name +=  ['js'+ obj_name + 'PrototypeFunction_' + method_name]
            # function_name +=  ['jsDOMWindow_'+ obj_name + 'Constructor' + method_name]
            function_name +=  ['js'+ obj_name + 'InstanceFunction_' + method_name]
            function_name += [obj_name+method_name+"CodeGenerator"]  #readableByteStreamControllerCloseCodeGenerator   
        elif (r := var_read_regex.match(line)) is not None:
            left_name = _get_tag_name(jsgrammar, r.group(1))
            right_obj_name = _get_tag_name(jsgrammar, r.group(2))
            attribute_name = r.group(3).strip() #setJSAudioBufferSourceNode_buffer
            function_name += ['js'+ right_obj_name + '_' + attribute_name]  #jsAudioListener_positionX
            function_name += [right_obj_name+attribute_name+"CodeGenerator"] #writableStreamDefaultWriterClosedCodeGenerator
            #<new GLenum> = <WebGL2RenderingContext>.UNPACK_SKIP_PIXELS;

        elif (r := var_write_regex.match(line)) is not None:
            left_name = _get_tag_name(jsgrammar, r.group(1))
            attribute_name = r.group(2).strip()
            # arg_splited = arguments_regex.split(r.group(3))
            function_name += ['setJS'+ left_name + '_' + attribute_name]
        else:
            # pass
            print("not handle rule:", line)

        all_functions.append({
            'CFunction' : function_name,
            'origin_line': line,
            'missed': True
        })
    with open(output_path, 'w') as f:
        json.dump(all_functions, f)
    
    return all_functions




def main():
    # grammar_path = os.path.join('./domato/js2.txt')
    grammar_path = os.path.join('./temp/CFunction.json')
    if not os.path.exists(grammar_path):
        print('grammar file not exists')
        exit(1)
    save_path = os.path.join('./temp/CFunction.json')
    transform(grammar_path,save_path)
    


if __name__ == '__main__':
    main()
