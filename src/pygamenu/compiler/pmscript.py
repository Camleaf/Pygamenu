from typing import Self, Any
import pygame as pg
import json
from ..utils.logging import log, LogLevel, reset_log
from .errors import *
# just as a reminder for future me to set editor font to consolas monospace

##################
# Constants
##################

EXIT = False
CONTINUE = True

##################
# TOKENS
##################

ILLEGAL_DATA_NAMESPACES = [">",";","{","}","\'","\"","=","#","<"]
KEYWORDS = ['class','id','style','role']
RESERVED_NAMEVALUES = ['GLOBAL']

T_ADVANCE = 'T_ADVANCE'
T_SEMICOLON = 'T_SEMICOLON'
T_NAMEVALUE = 'T_NAMEVALUE'
T_DATAVALUE = 'T_DATAVALUE'
T_LBRCK = 'T_LBRCK'
T_RBRCK = 'T_RBRCK'
T_FSLASH = 'T_FSLASH'
T_EQ = 'T_EQ'
T_KW = 'T_KW'
T_BACK = 'T_BACK'
T_DOLLAR = 'T_DOLLAR'

class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value
    
    def __repr__(self):
        if self.value: return f'{self.type}:{self.value}'
        return f'{self.type}'

    def get_type(self):
        return self.type
    
STYLES = {
    "position":{"types":['text'], "default":"relative", "accepted":["relative","absolute","block"]},
    "height":{"types":['number', 'percentage'], "default":0,"max":"parentheight"},
    "width":{"types":['number', 'percentage'], "default":0,"max":"parentwidth"},
    "top":{"types":['number', 'percentage'], "default":0,"max":"parentheight"},
    "left":{"types":['number', 'percentage'], "default":0,"max":"parentwidth"},
    "rotation":{"types":['number'], "default":0},
    "background":{"types":['rgbvalue'], "default":None},
    "opacity":{"types":['number', 'percentage'], "default":255, "max":255},
    "corner-radius":{"types":['number'], "default":0},
    "border-width":{"types":['number'], "default":0},
    "border-color":{"types":['rgbvalue'], "default":None},
    "font":{"types":['text'],"default":"verdana", "accepted":[]},
    "font-color":{"types":['rgbvalue'],'default':(255,255,255)},
    "font-size":{"types":['number'],"default":10},
    "cx": {"types":['number','percentage'], "default":0, "max":"parentwidth"},
    "cy": {"types":['number','percentage'], "default":0, "max":"parentheight"},
}

##################
# Syntax Tree
##################


    # Structure of syntax elements. Token sep by $. Repeatable options keywords by ? then sep by /

    # Options can be filled with 'IGNORE', 'ANY', 'NONE' for keywords

    # For options, ASSIGN keyword can be used to take a datavalue and assign to a namevalue

SYNTAX_TREE = { 
    
    ##############################################################
    "OPEN_ELEMENT":"T_ADVANCE$T_NAMEVALUE?T_NAMEVALUE$T_EQ$T_DATAVALUE",
    "CLOSE_ELEMENT":"T_ADVANCE$T_FSLASH$T_NAMEVALUE?NONE",
    "COMMENT":"T_FSLASH$T_FSLASH?ANY",
    "IMPORT":"T_SEMICOLON$T_SEMICOLON$T_NAMEVALUE$T_BACK$T_DATAVALUE?NONE",
    "STATE":"T_SEMICOLON$T_DOLLAR$T_NAMEVALUE$T_BACK$T_DATAVALUE?NONE"
}
##################
# ELEMENTS
##################
_past_ids = []

class Element: 
    # So I'm mostly done with state stuff I just need to add comprehension.
    # Comprehension is not executed here. It will be executed upon compilation at render time, where the stuff needs to be iterated over anyways. 
    # Once a state is found in place of a value, the comprehension code will find the value currently stored in the object the namespace is representing, and serve that to the user. 
    # it will also serve to computed styles so that it is accessible by scripting code through the element
    type:str
    parent_id:str
    children:list[Self]
    style: dict[str,str]
    scoped_styles:dict
    children_allowed:bool
    required={}
    onclick:list[str]
    surf:pg.Surface
    surf_rect:pg.Rect
    computed_styles:dict
    callback_hook:Any
    clickable:bool
    mask:pg.Mask

    def __init__(self, type_:str, parent_id:str|None, style:dict[str,str]={}, id_:str=None, scoped_styles:dict={}, children_allowed:bool=True, onclick=[]):
        self.type = type_
        self.id = id_
        self.parent_id:str = parent_id
        self.children = []
        self.computed_styles = {}
        self.style = style
        self.scoped_styles = scoped_styles
        self.children_allowed = children_allowed
        self.onclick = onclick
        self.clickable = True if len(onclick) > 0 else False
        self.mask = None

        if not self.id:
            self.id = _create_id(self)
        else:
            if self.id in _past_ids:
                log(f"ID {self.id} already exists. This overwrites the previous element.", LogLevel.WARNING)
            _past_ids.append(self.id)

    def __repr__(self):
        return f'ID: `{self.id}` ; TYPE: `{self.type}` ; Parent_ID: `{str(self.parent_id)}` ; STYLE_TAGS: `{self.style}`;'
        # return f'{self.type}'

    def __str__(self):
        return f'ID: `{self.id}` ; TYPE: `{self.type}` ; Parent_ID: `{str(self.parent_id)}` ; STYLE_TAGS: `{self.style}`;'

    def get_surface(self) -> pg.Surface: 
        # Render functions will be stored outside of this element, 
        #I just thought it would be easier to store the surface data with the rest of the data
        if not self.surf:
            raise Error(f"Element of ID {self.id} gets surface called before defined")
        return {'surf':self.surf,'rect':self.surf_rect,'mask':self.mask}
    
    def set_surface(self, surface:pg.Surface, surf_rect:pg.Rect,mask:pg.Mask=None):
        self.surf = surface
        self.surf_rect = surf_rect
        self.mask = mask

    def get_computed_styles(self):
        if len(list(self.computed_styles.keys())) == 0:
            raise SyntaxError(msg="Computed styles accessed before initialized")
        else:
            return self.computed_styles
    
    def setstyleblock(self,styles:dict[str,str]):
        self.style = styles
        self.__oncallback__()

    def setstyleattribute(self,attr:str,val:str):
        if attr in STYLES:
            self.style[attr]  =val.strip()
        else:
            log(f'Name {attr} not a valid style. Skipping operation',LogLevel.WARNING)
        
        self.__oncallback__()

    def getstyleattribute(self,attr:str):
        if attr in STYLES:
            return self.style[attr]
        else:
            log(f'Name {attr} not a valid style. Skipping operation',LogLevel.WARNING)

    def setattribute(self,attr:str,val:Any):
        if attr in self.__dict__:
            self.__dict__[attr] = val
        else:
            log(f'Name {attr} not a valid attribute. Skipping operation', LogLevel.WARNING)
        self.__oncallback__()


    def getattribute(self,attr:str):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            log(f'Name {attr} not a valid attribute. Skipping operation', LogLevel.WARNING)


    def set_callback_hook(self,method):
        self.callback_hook = method

    def __oncallback__(self):
        # execute the current callback hook
        self.callback_hook(self)

#####################################

class ImageElement(Element):
    image_path:str
    required={
        "src":[]
    }
    def __init__(self, parent_id:str, style:dict[str,str]={},id_:str=None,onclick=[],src:str=''):
        super().__init__('image',parent_id,style,id_,{},False,onclick)
        self.src = src


class TextElement(Element):
    text:str
    modifiable:bool
    required={
        "text":[],
        "modifiable":["True", "False"]
    }
    def __init__(self, parent_id:str,style:dict[str,str]={},id_:str=None,onclick=[],text:str='',modifiable:str="False",):
        super().__init__('text',parent_id,style,id_,{},False,onclick)
        self.text = text
        self.modifiable = eval(modifiable)
        self.cursor = None
    def __str__(self):
        return f'ID: `{self.id}` ; TYPE: `{self.type}` ; Parent_ID: `{str(self.parent_id)}` ; STYLE_TAGS: `{self.style}`;\n Text: `{self.text}`\n'

class DivElement(Element):
    required={}
    def __init__(self, parent_id:str,style:dict[str,str]={},id_:str=None,onclick=[]):
        super().__init__('div',parent_id,style,id_,{},True,onclick)

class FrameElement(Element):
    required={}
    def __init__(self,parent_id:str,style:dict[str,str]={},id_:str=None, onclick=[]):
        super().__init__('frame', parent_id, style, id_, {}, True,onclick)

class PolygonElement(Element):
    required={
        'points':[]
    }
    def __init__(self,parent_id:str,style:dict[str,str]={},id_:str=None, onclick=[],points=''):
        super().__init__('polygon', parent_id, style, id_, {}, True,onclick)
        split_points = points.split('/')
        self.points = []
        if split_points == ['']:
            self.set_shape([(0,0),(0,0),(0,0)])
        else:
            if len(split_points) < 3:
                log(f"Polygon {self.id} has less than three points. Setting surface to blank", LogLevel.WARNING)
                self.set_shape([(0,0),(0,0),(0,0)])
            try:
                
                for pair in split_points:
                    self.points.append(tuple(map(float,pair.split(','))))
            except TypeError:
                log(f"Polygon {self.id} has an error with points format. Setting surface to blank", LogLevel.WARNING)
                self.set_shape([(0,0),(0,0),(0,0)])
    
    def set_shape(self,points:list[tuple[int,int]]):
        self.points = points
        if len(points) < 3:
            log(f"Polygon {self.id} has less than three points. Setting surface to blank", LogLevel.WARNING)
            self.points = [(0,0),(0,0),(0,0)]
    
#############################

class State: 
    # So this state function will work by being defined inside of the compiledfiles with an initial value
    # Then it will act as an object which supplies values to it's dependencies
    # It will share its pointers with Python variables through a function which grabs it
    # Whenever those variables update the object, the changes propogate
    # This allows me to restrict state and check for errors if it isn't defined
    # It also allows me to build the dependency trees as the code compiles, as it is defined in code
    # All states will be hoisted to GLOBAL scope

    value:str|int|float
    name:str
    dependents:list[str]
    callback_hook:Any

    def __init__(self,name, initial_value:str=None):
        self.dependents = []
        self.name = name
        self.value = initial_value
    
    def get_dependents(self):
        return self.dependents

    def set(self,value):
        if type(value) not in [str,int,float]:
            raise StateTypeError()
        self.value = value
        self.__oncallback__()
    
    def get(self):
        if not self.value:
            raise StateNotInitializedError(self.name)
        return self.value
    def set_callback_hook(self,method):
        self.callback_hook = method

    def __oncallback__(self):
        # execute the current callback hook
        self.callback_hook(self)


    
    



def _create_id(object:Element):

    id_suffix = 0
    object_type = object.type

    while (id := object_type+str(id_suffix)) in _past_ids: 
        id_suffix += 1
    _past_ids.append(id)
    return id
#############################################################

ELEMENTS:list[Element] = {
    "div":DivElement,
    "frame":FrameElement,
    "image":ImageElement,
    "text":TextElement,
    "polygon":PolygonElement
}

##############################################################


##################
# LEXER
##################

# For parent/ Children, use a stack showing what the current parent is, so that switching back and forth is easy


class Lexer:
    text:str
    current_char:str
    current_build:str
    mode:list[Any]
    tokens:list[Token] = []
    parent:Element

    def __init__(self):
        ...
    
    def new_line(self,line:str, index:int, parent:Element = None):
        self.text = line.strip()
        self.parent = parent
        self.index = index
        self.current_build = ''
        self.mode = [self.default_search] # A stack for me to easily switch between different search patterns
        self.tokens = []
        if self.text: 
            self.make_tokens()
    
    def make_tokens(self):
        for i, char in enumerate(self.text):
            
            self.mode[-1](char) # The top of the stack is the capture method that is executed

        
        ####### To clear up any escaped builds #######

        if self.mode[-1] == self.value_search: # This logic is to capture any components at the end of the string
            raise StringNotEnded(self.index, self.text)
        
        elif self.current_build != '':
            self.tokens.append(Token(T_NAMEVALUE,self.current_build.strip()))

    ##############################################################

    def flush_build(self):
        if self.current_build != '':
            self.tokens.append(Token(T_NAMEVALUE,self.current_build.strip()))
        self.current_build = ''

    def default_search(self,char:str):
        if char == ' ' or char == '\t':
            self.flush_build()

        
        elif char == '\'':
            self.current_build = ''
            self.mode.append(self.value_search)
        

        elif char == '>': # In The future I could probably make this way more concise but for now it works
            self.flush_build()
            self.tokens.append(Token(T_ADVANCE,char))
            
        
        elif char == ';':
            self.flush_build()
            self.tokens.append(Token(T_SEMICOLON,char))


        elif char == '[':
            self.flush_build()
            self.tokens.append(Token(T_LBRCK,char))


        elif char == ']':
            self.flush_build()
            self.tokens.append(Token(T_RBRCK,char))


        elif char == '=':
            self.flush_build()
            self.tokens.append(Token(T_EQ,char))


        elif char == '/':
            self.flush_build()
            self.tokens.append(Token(T_FSLASH,char))

        elif char == '<':
            self.flush_build()
            self.tokens.append(Token(T_BACK,char))

        elif char == '$':
            self.flush_build()
            self.tokens.append(Token(T_DOLLAR,char))
        else:
            self.current_build += char

    ##############################################################

    def value_search(self, char:str):
        if char == '\'':
            self.tokens.append(Token(T_DATAVALUE,self.current_build.strip()))
            self.current_build = ''
            self.mode.pop()
        # elif char in ILLEGAL_DATA_NAMESPACES:
        #     raise IllegalCharError(self.index,self.text, char)
        else:
            self.current_build += char
            
##################
# Compiler
##################

# Uses lexer as subcategory
class Compiler:
    lexer:Lexer
    parent_stack:list[Element]
    compiled:list[Element]
    states:dict[str,State]
    frames:dict[str,list[State]]

    def __init__(self, path:str): # Use token patterns to figure out what type the line is
        self.lexer = Lexer()
        self.global_scope = Element(type_="global",id_="global", parent_id=None,style={'width:100%/height:100%;'})
        self.parent_stack = [self.global_scope]
        self.compiled:dict[str,Element] = {"global":self.global_scope}
        self.path = path
        self.states = {}
        self.frames = {}
        self.uncompiled = []
        self.index = 0
        self.syntax_tree = dict()
        self.parse_syntax_tree()
        # print(self.syntax_tree)
        self.extract_path(path,0, '')
        self.compile()
        # print(*self.uncompiled,sep='\n')

    ##############################################################

    def parse_syntax_tree(self):

        syntax_keys = list(SYNTAX_TREE.keys())
        for key in syntax_keys:
            raw_syntax = SYNTAX_TREE[key]
            temp = raw_syntax.split('?')
            if len(temp) == 1:
                raw_identifier, raw_options = temp[0],''
            elif len(temp) > 2:
                raise Error('? Identifier found multiple times in syntax Tree')
            else:
                raw_identifier, raw_options = temp
            identifier_structure = raw_identifier.split('$')
            options_structure = raw_options.split('$')
            if len(options_structure) == 1 and options_structure[0] == '':
                options_structure = []
            self.syntax_tree[key] = {
                "identifier":identifier_structure,
                "options":options_structure
            }
            



    def extract_path(self,path:str, insert_index:0,line):
        try:
            with open(path,'r') as f:
                self.uncompiled = self.uncompiled[:insert_index+1] + f.read().split('\n') + self.uncompiled[insert_index+1:]
        except FileNotFoundError:
            raise ImportFailed(self.index, line)
            
    ##############################################################

    def compile(self):
        while self.index < len(self.uncompiled):
            line:str = self.uncompiled[self.index].strip()



            self.lexer.new_line(line,self.index+1)
            if not self.lexer.tokens: 
                self.index += 1
                continue

            syntax_type = self.match_tokens(self.lexer.tokens,line)
            
            if self.parent_stack[-1].type == 'text' and syntax_type != "CLOSE_ELEMENT":
                self.handle_text(self.lexer.tokens,line,syntax_type)

            elif syntax_type == "COMMENT":
                ...
            
            elif syntax_type == "IMPORT":
                self.handle_import(self.lexer.tokens,line)
            
            elif syntax_type == "OPEN_ELEMENT":
                self.handle_open_element(self.lexer.tokens,line,syntax_type)
            
            elif syntax_type == "CLOSE_ELEMENT":
                self.handle_close_element(self.lexer.tokens,line,syntax_type)
            elif syntax_type == "STATE":
                self.handle_state(self.lexer.tokens,line,syntax_type)
            else:
                raise SyntaxIncorrect(self.index,line,"Syntax Error. Perhaps you forgot an identifier?")
            # print(self.parent_stack, "\n",) For checking scope

            self.index += 1
        if len(self.parent_stack) > 1:
            raise SyntaxIncorrect(self.index, line, f"At least one Element not closed. Try checking if you forgot a call of type CLOSE ELEMENT")
    
    ##############################################################

    def match_tokens(self, tokens:list[Token],line):

        syntax_type = ''
        for key in self.syntax_tree:

            for i,tok_type in enumerate(self.syntax_tree[key]['identifier']):
                
                if tokens[i].get_type() != tok_type:
                    
                    break

                if i == len(self.syntax_tree[key]['identifier'])-1:
                    syntax_type = key


        # print(syntax_type)
        return syntax_type
    
    ##############################################################

    def handle_import(self,tokens:list[Token],line):
        import_type = tokens[2]
        path = tokens[4]

        if not self.parent_stack[-1].children_allowed:
            raise ScopeError(self.index,line)
        # import type and path are static always so I can assign them like that

        self.uncompiled[self.index] = ''
        if import_type.value == "markdown":
            self.extract_path(path.value,self.index,line)

        elif import_type.value == "styles":
            try:
                with open(path.value,'r') as f:
                    raw_styles = json.load(f)
            except FileNotFoundError:
                raise ImportFailed(self.index, line)

            # This is to scope classes to their specific zones, so that styles can be overwritten in certain scopes
            for key in raw_styles:
                self.parent_stack[-1].scoped_styles[key] = raw_styles[key]
                if any(i not in STYLES.keys() for i in raw_styles[key]):
                    raise StyleError(self.index,line,f"One or more styles from file `{path.value}` does not exist")
                
    ##############################################################

    
    def handle_open_element(self,tokens:list[Token],line:str,syntax_type:str):

        if not self.parent_stack[-1].children_allowed:
            raise ScopeError(self.index,line)

        tok_types = []
        for tok in tokens:
            tok_types.append(tok.get_type())
        
        # some basic reserved namespace stuff
        type_ = tokens[1].value
        
        if type_ not in ELEMENTS.keys(): # Check to make sure the user only uses predefined elements
            raise NameSpaceError(self.index,line,type_)
        
        # special handling for frame element
        if type_ == 'frame' and not self.parent_stack[-1].type=='global':
            raise ScopeError(self.index,line)
        elif type_ != 'frame' and self.parent_stack[-1].type == 'global':
            raise FrameRequiredError(self.index,line,type_)

        options_structure = self.syntax_tree[syntax_type]['options']
        type_search_index = 0
        seen_keywords = []

        datapoints = { # this is for hardcoded stuff with a lot of searching
            "class":'',
            "style":'',
            "id":'',
            "onclick":'',
        }
        required_operands = ELEMENTS[type_].required # this is for element-specific datapoints with little formatting
        
        operands = {}
        operand_restrict = {x:required_operands[x] for x in required_operands.keys()} # to restrict what kind of inputs are valid format
        
        cur_kw:str = ''
        cur_val:str = ''
        for i,tok in enumerate(tokens[2:]): # past the element declaration
            if tok.get_type() != options_structure[type_search_index]: # Raise error if structure is not followed
                raise SyntaxIncorrect(self.index, line, f"Syntax Error. {tok.get_type()} not in right place or not supported in OPTIONS structure {options_structure}.")
            
            # Keyword checking
            if tok.get_type() == T_NAMEVALUE:
                if tok.value in seen_keywords: 
                    raise SyntaxIncorrect(self.index, line, f"Syntax Error: {tok.value} used twice.")
                elif tok.value not in datapoints.keys() and tok.value not in required_operands:
                    raise SyntaxIncorrect(self.index, line, f"Syntax Error: {tok.value} not a valid operand.")
                cur_kw = tok.value
                seen_keywords.append(tok.value)

            # Datavalue checking
            if tok.get_type() == T_DATAVALUE:
                cur_val = tok.value.strip()

            # structure completion / increment
            type_search_index += 1 # increment structure
            type_search_index %= len(options_structure) # repeat structure on completion

            if type_search_index == 0:
                if not cur_kw or not cur_val:
                    raise SyntaxIncorrect(self.index,line,f"Syntax Error: Error with operand values")
                if cur_kw in datapoints.keys(): # If its a hardcoded datapoint
                    datapoints[cur_kw] = cur_val
                elif cur_kw in operand_restrict.keys(): # If its a element-specific datapoint
                    
                    if len(operand_restrict[cur_kw]) != 0:
                        
                        if cur_val not in operand_restrict[cur_kw]:
                            raise SyntaxIncorrect(self.index,line,f"Syntax Error: {cur_val} not valid assignment to {cur_kw}")
                        

                    operands[cur_kw] = cur_val
                
                cur_kw,cur_val = '',''

        
        if type_search_index != 0: # Raise error if structure is unfinished
            raise SyntaxIncorrect(self.index, line, f"Syntax Error. Operand structure {options_structure} not completed, missing elements {options_structure[type_search_index:]}.")
        # print(datapoints)


        style = {}
        if datapoints["class"]: #state declaration is illegal here
            if '$' in datapoints["class"]:
                IllegalCharError(self.index,line,'$', "IllegalCharError: State definition not allowed in class value")

            for element in self.parent_stack[::-1]: # reverse iterate to find the most recently scope version of the class
                if datapoints["class"] in element.scoped_styles:
                    
                    scoped_class = element.scoped_styles[datapoints['class']]
                    for item in scoped_class:
                        style[item] = scoped_class[item]
                    break
        contains_state = False
        states = []
        if datapoints["style"]: # split up the styles into keypairs
            for item in datapoints["style"].split('/'):
                raw = item.split(':')

                if len(raw) > 2 or len(raw) < 2:
                    raise SyntaxIncorrect(self.index,line,f"`:` Symbol must act as a divider between key:value pairs, and must exist.")

                key,value = raw
                style[key] = value
                # check for state errors
                if '$' in value:
                    
                    if not value.startswith('$$'):
                        raise IllegalCharError(self.index,value,'$',f"IllegalCharError: Symbol reserved for reactive state usage applied incorrectly")
                    elif not value.count('$') == 2:
                        raise IllegalCharError(self.index,value,'$',f"IllegalCharError: Symbol reserved for reactive state usage applied incorrectly")


                    if value[2:] not in self.states.keys(): # make the error for this
                        raise StateImplementError(self.index,value,"State referenced which does not exist")
                    contains_state = True
                    states.append(value[2:])
                else:
                    if key not in STYLES.keys():
                        raise StyleError(self.index,line,f"Style `{key}` does not exist")
        
        if not datapoints['id']:
            if '$' in datapoints["id"]: #state declaration is illegal here
                IllegalCharError(self.index,line,'$', "IllegalCharError: State definition not allowed in id value")
            datapoints['id'] = None
        
        funcs = []
        if datapoints['onclick'].strip() != '':
            funcs = datapoints['onclick'].split('/')


        method = ELEMENTS[type_] # grab the specific element type based on type index
        
        current:Element = method(self.parent_stack[-1].id,style,datapoints['id'],funcs,**operands) # ah yes dictionary unpacking gotta love how useful that is
        self.parent_stack[-1].children.append(current)
        self.parent_stack.append(current)
        self.compiled[current.id] = current
        if contains_state:
            for state_id in states:
                self.states[state_id].dependents.append(current.id)

        if type_ == 'frame':
            self.frames[current.id] = []
        else:
            self.frames[list(self.frames.keys())[-1]].append(current)
 
    ##############################################################
        
        
    def handle_close_element(self,tokens:list[Token],line:str,syntax_type:str):
        if len(tokens) > 3:
            return SyntaxIncorrect(self.index,line,f"CLOSE_ELEMENT argument does not take options")
        
        type_ = tokens[2].value

        if type_ in RESERVED_NAMEVALUES: # Check to make sure the user isn't overwriting global or something
            raise NameSpaceError(self.index,line,type_)

        if self.parent_stack[-1].type != type_:
            raise SyntaxIncorrect(self.index, line, f"CLOSE ELEMENT argument in wrong scope. Try checking if another element is still open during this call.")
        
        self.parent_stack.pop()

    ##############################################################

    def handle_state(self,tokens:list[Token],line:str,syntax_type:str):

        if len(tokens) > 5:
            return SyntaxIncorrect(self.index,line,f"CREATE_STATE argument does not take options")
        
        name = tokens[2].value
        initial_value = tokens[4].value

        current = State(name,initial_value.strip())
        self.states[name] = current

    ##############################################################

    def handle_text(self, tokens:list[Token], line:str, syntax_type:str):
        contains_state = False

        if '$' in line: # handles if any state was found inside of a text element. If it is, it should overwrite the entire text element because I'm lazy
            
            if not line.startswith('$$'):
                raise IllegalCharError(self.index,line,'$',f"IllegalCharError: Symbol reserved for reactive state usage applied incorrectly")
            elif not line.count('$') == 2:
                raise IllegalCharError(self.index,line,'$',f"IllegalCharError: Symbol reserved for reactive state usage applied incorrectly")

            if line[2:] not in self.states.keys(): # make the error for this
                raise StateImplementError(self.index,line,"State referenced which does not exist. States inside text objects must only exist on individual lines, did you try to put it in text?")
            contains_state = True


        if self.parent_stack[-1].text: # make the error for this
            self.parent_stack[-1].text +=  '\n'
        
        # i want it to add the line regardless, as it will get compiled in the element, most of this function is for checking state errors
        self.parent_stack[-1].text +=  line 
        
        # add state to deps
        if contains_state and self.parent_stack[-1].id not in self.states[line[2:]].dependents:
            self.states[line[2:]].dependents.append(self.parent_stack[-1].id)

# Todo. Add rendering (don't forget to compile reactive state at that time)
