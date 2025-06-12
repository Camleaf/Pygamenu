from ..utils.logging import log, LogLevel, reset_log
class Error:
    def __init__(self,text:str='Error'):
        log(text,LogLevel.FATAL)


class IllegalCharError(Error):
    def __init__(self, line_number:int=None, line:str='', char:str='', message='IllegalCharError: Illegal character'):
        text = f"\n\n\nLine {line_number}| \"    {line}    \"    >> {message} `{char}`"
        super().__init__(text)

class StringNotEnded(Error):
    def __init__(self, line_number:int=None, line:str=''):
        text = f"\n\n\nLine {line_number}| \"    {line}    \"    >>  String not Ended"
        super().__init__(text)

class SyntaxIncorrect(Error):
    def __init__(self, line_number:int=None, line:str='', message='Syntax Error'):
        text = f"\n\n\nLine {line_number}| \"    {line}    \"    >>  {message}"
        super().__init__(text)

class ImportFailed(Error):
    def __init__(self, line_number:int=None, line:str='', path:str=''):
        text = f"\n\n\nLine {line_number}| \"    {line}    \"    >>  Import Error: Import of `{path}` failed. Try using absolute imports from the CWD"
        super().__init__(text)

class NameSpaceError(Error):
    def __init__(self, line_number:int=None, line:str='', namevalue=''):
        text = f"\n\n\nLine {line_number}| \"    {line}    \"    >>  NamespaceError: {namevalue} not a valid name"
        super().__init__(text)

class ScopeError(Error):
    def __init__(self, line_number:int=None, line:str=''):
        text = f"\n\n\nLine {line_number}| \"    {line}    \"    >>  ScopeError: Identifier not allowed in current scope"
        super().__init__(text)

class FrameRequiredError(Error):
    def __init__(self, line_number:int=None, line:str='', type_:str=''):
        text = f"\n\n\nLine {line_number}| \"    {line}    \"    >>  FrameRequiredError: Element {type_} requires a frame to be under Global scope"
        super().__init__(text)

class StateImplementError(Error):
    def __init__(self, line_number:int=None, line:str='', message='State can not be applied in element with previous values'):
        text = f"\n\n\nLine {line_number}| \"    {line}    \"    >>  StateImplementError: {message}"
        super().__init__(text)

class StateTypeError(Error):
    def __init__(self):
        text = f"StateTypeError: State only accepts types STR | INT | FLOAT"
        super().__init__(text=text)

class StateNotInitializedError(Error):
    def __init__(self,name):
        text = f"StateTypeError: State {name} not initialized upon first usage"
        super().__init__(text=text)

class StyleError(Error):
    def __init__(self, line_number:int=None, line:str='', message='Style does not exist'):
        text = f"\n\n\nLine {line_number}| \"    {line}    \"    >>  StyleError : {message}"
        super().__init__(text=text)