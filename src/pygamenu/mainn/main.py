from ..compiler import *
from ..utils.logging import LogLevel, log, reset_log
from .eventlistener import EventListener
import re
from collections import deque
import pygame as pg
import os, threading as th
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
class View:
    
    elements:dict[str,Element]
    states:dict[str,State]
    surf: pg.Surface
    size: list[int,int]
    frames:dict[str,list[Element]]
    frame_stack:list[str]
    eventlistener: EventListener
    activated_text: list[TextElement]
    flags: dict[str,bool]

    def __init__(self, elements:dict[str,Element], states:dict[str,State], size:list[int,int], frames:dict[str,list[State]]):
        
        self.elements = elements
        self.states = states
        self.frames = frames
        self.surf = pg.Surface(size,pg.SRCALPHA)
        self.surf.fill((0,0,0,255))
        self.width = size[0]
        self.height = size[1]
        self.size = size
        self.frame_stack = []
        self.eventlistener = EventListener()
        self.activated_text = []
        self.flags = {
            'noRender':False
        }
        self.factory = self.ContextFactory(self)

        self.addEventListener('mousedown',self.__mouseDown__)
        self.addEventListener('keydown',self.__keyDown__)
        # In the compiler, also make something which organizes the elements into their respective frames
        # Both the total elements group and frames group will modify each other because they are just pointing
        # to the same object

        # add state callbacks
        for state_id in self.states:
            self.states[state_id].set_callback_hook(self.__state_modify_callback__)

        # add element callbacks
        for element_id in self.elements:
            self.elements[element_id].set_callback_hook(self.__element_modify_callback__)
            if self.elements[element_id].type == 'text': # If it's text we just want to add this
                if self.elements[element_id].modifiable:
                    self.elements[element_id].clickable = True
                    self.elements[element_id].onclick.append(self.__activateTextbox__)

        
        self.__create_initial_objects__('global')
    
    ####################
    # event listener stuff
    ####################

    def addEventListener(self,event:str,callback):
        self.eventlistener.add_callback(event,callback)


    def __mouseDown__(self,event, global_dict):
        # 
        # do collision here 
        # For collision check from highest rendered object first (so highest rendered frame down)
        # not sure how laggy this is but now I just need to add text stuff
        self.activated_text = []
        end = False
        mouse = pg.Mask((1,1))
        mouse = pg.sprite.Sprite()
        mouse.image = pg.Surface((1, 1), pg.SRCALPHA)
        mouse.image.fill((0, 0, 0,255))
        mouse.rect = mouse.image.get_rect(topleft=pg.mouse.get_pos())
        mouse.mask = pg.mask.from_surface(mouse.image)

        for frame_id in self.frame_stack[::-1]:
            print(frame_id)
            # this stuff still gets repeated but I need do do it twice for frams
            cur_frame = self.getElementById(frame_id)
            el_surf = cur_frame.get_surface()

            boundary = pg.mask.from_surface(el_surf['mask'])
            bound_rect = boundary.get_rect(center=el_surf['rect'].center)
            offset_x = mouse.rect.x - bound_rect.x
            offset_y = mouse.rect.y - bound_rect.y
            offset = (offset_x, offset_y)


            if pg.mask.Mask.overlap(boundary,mouse.mask,offset):
                elements = self.frames[frame_id][::-1]
                elements.append(cur_frame)
                # iterate backwards to find the top
                for el in elements:
                    if not el.clickable: continue
                    el_surf = el.get_surface() # I know this is repeated I'm just being lazy
                    boundary = el_surf['surf']
      
                    boundary = pg.mask.from_surface(boundary)
                    bound_rect = boundary.get_rect(center=el_surf['rect'].center)
                    offset_x = mouse.rect.x - bound_rect.x
                    offset_y = mouse.rect.y - bound_rect.y
                    offset = (offset_x, offset_y)
                    if el.type == 'text': # If it's text, it has a clear background and needs a different way for collision
                        boundary = pg.mask.from_surface(el_surf['mask'])
                    
                    if pg.mask.Mask.overlap(boundary,mouse.mask,offset):
                        
                        for callback_id in el.onclick:
                            if not callable(callback_id):
                                # If it is not callable, it is a string and we have to see if it can 
                                # be found within global scope
                                callback = global_dict.get(callback_id,None)
                                if callback is not None and callable(callback):
                                    callback(el)
                            else:
                                callback_id(el)
                        self.__recalc_rendered_frames__()
                        end = True
                        break
            if end:
                break


    ################################
    def __activateTextbox__(self,element:TextElement):
        if element.modifiable:
            self.activated_text.append(element)
            element.cursor = len(element.text)
            self.__create_image_individual__(element)
            self.__recalc_rendered_frames__()

        # this activates

    def __keyDown__(self,event:pg.event.Event,global_dict):
        key = event.dict['key']

        for element in self.activated_text:
            #use some of the code for the old thing. Also may need to add a keyheld thing for this
            if key == pg.K_RIGHT:
                element.cursor += 1
                if element.cursor >= len(element.text):
                    element.cursor = len(element.text) - 1
            elif key == pg.K_LEFT:
                element.cursor -= 1
                if element.cursor < -1:
                    element.cursor = -1
            elif key == pg.K_BACKSPACE:
                if element.cursor != -1:
                    element.text = element.text[:element.cursor] + element.text[element.cursor+1:]
                    element.cursor -= 1
            elif key == pg.K_RETURN:
                element.text = element.text[:element.cursor+1] + '\r' + element.text[element.cursor+1:]
                element.cursor += 1

            elif key == pg.K_ESCAPE:
                self.activated_text = []
                element.cursor = None
            else:
                if event.dict['unicode'].lower() in " abcdefghijklmnopqrstuvwxyz1234567890!@#$%^&*()-_=+[]{}\|;:\'\",.<>?/`~" \
                or event.dict['unicode'] in ['\t']:
                    element.text = element.text[:element.cursor+1] + event.dict['unicode'] + element.text[element.cursor+1:]
                    element.cursor += 1

            self.__create_image_individual__(element)
        self.__recalc_rendered_frames__()

    #####################
    # Frame operations
    #####################
    def append_frame(self,id_:str):
        
        if id_ in self.frame_stack:
            log(f'Frame {id_} already in frame stack, skipping operation',LogLevel.WARNING)
            return
        elif id_ not in self.frames:
            log(f'Frame {id_} doesn\'t exist, skipping operation', LogLevel.WARNING)
            return
        
        self.frame_stack.append(id_)
        self.__recalc_rendered_frames__()
    

    def remove_frame(self,id_:str):
        if id_ not in self.frame_stack:
            log(f'Frame {id_} not in frame stack, skipping operation', LogLevel.WARNING)
            return
        self.frame_stack.remove(id_)
        self.__recalc_rendered_frames__()
    

    def pop_frame(self,index:int):
        if len(self.frame_stack) > index+1:
            log(f'Index {index} greater than length of frame stack, skipping operation', LogLevel.WARNING)
            return
        self.frame_stack.pop(index)
        self.__recalc_rendered_frames__()
    
    def clear_frames(self):
        self.frame_stack = []
        self.__recalc_rendered_frames__()

    def insert_frame(self,id_:str,index:int):
        if id_ in self.frame_stack:
            log(f'Frame {id_} already in frame stack, skipping operation',LogLevel.WARNING)
            return
        elif id_ not in self.frames:
            log(f'Frame {id_} doesn\'t exist, skipping operation', LogLevel.WARNING)
            return
        elif len(self.frame_stack) > index+1:
            log(f'Index {index} greater than length of frame stack, skipping operation', LogLevel.WARNING)
            return
        
        self.frame_stack.insert(index,id_)
        self.__recalc_rendered_frames__()
    
    def __recalc_rendered_frames__(self):
        if self.flags['noRender']:
            return
        self.surf = pg.Surface(self.size,pg.SRCALPHA)
        self.surf.fill((0,0,0,255))
        for frame in self.frame_stack:
            self.__render_frame__(frame)

    ######################################
    ######################################

    def __create_initial_objects__(self,id_:str):
        self.__execute_down_scope__(id_,self.__create_image_individual__)

    def __render_frame__(self,id_:str):
        self.__execute_down_scope__(id_,self.__render_element__)

    def __execute_down_scope__(self,id_:str,function):
        """Re-renders the object of the ID provided and all of it's children, 
        nothing else. Useful for only re-rendering a small scope"""
        initial_object = self.getElementById(id_)

        element_stack:deque[Element] = deque()
        element_stack.append(initial_object)
        
        # test to make sure this does not trigger an infinite loop
        while element_stack: # add sibling stuff for block view later
            el = element_stack.popleft()
            function(el)
            
            if el.children_allowed:
                for child_el in el.children:
                    element_stack.append(child_el)

        # remove rendering in this function, this is meant to re-create images.
        # Will need to make a function that is dedicated to turning on and off frames

        # for block style I could make a sibling counter tally, however for now it is just me manually typing ig
        # I think that function should be implemented in the image creation step

    ###############################################


    def __create_image_individual__(self, element:Element,sibling_height:int = 0):
        """Re-renders the styles for an individual element"""

        # set defaults for computed styles
        computed_styles = {
            'width':0,
            'height':0,
            'rotation':0,
            'x':0,
            'y':0,
            'cx':0,
            'cy':0,
            'background':None,
            'corner-radius':0,
            'border':False,
            'border-color':None,
            'border_width':0,
            'font-size':0,
            'font-color':(0,0,0,0)
        }
        element.computed_styles = {x:computed_styles[x] for x in computed_styles}
        if element.type == 'global':
            element.computed_styles['width'] = self.width
            element.computed_styles['height'] = self.height
            element.computed_styles['cx'] = self.width / 2
            element.computed_styles['cy'] = self.height / 2
            gbsurf = pg.Surface([self.width,self.height],pg.SRCALPHA)
            element.set_surface(gbsurf,gbsurf.get_rect())
            return
        buffer = {}
        for style in STYLES.keys():
            # This code is not meant to add to computed styles at all, rather to verify that all styles contain proper
            # types, structure, and attributes
            if style not in element.style: # grab default style instead of regular if not in element.style
                val = STYLES[style]['default']
                buffer[style] = val
                continue
            
            else:
                val:str = element.style[style].strip()
            
            acceptable_types = STYLES[style]['types']


            # Whether in or out continue with regular parsing
            if val.startswith('$$'): 
                # happily this is just about everything I need to do right here for state parsing.
                # There will be a bit more in the text comprehension section but for now yippee
                val:str = self.states[val[2:]].get()
                    

            not_chosen = 0
            if "number" in acceptable_types :
                try:
                    buffer[style] = float(val)
                except ValueError:
                    not_chosen += 1
            
            if "percentage" in acceptable_types:
                try:
                    if val[-1] != '%':
                        not_chosen += 1
                    else:
                        maximum = STYLES[style]['max']
                        
                        if maximum in ['parentwidth','parentheight']: # If it depends on parent get that
                            
                            if buffer['position'] == 'absolute':
                                parent = self.getElementById('global')
                            else:
                                parent = self.getElementById(element.parent_id) 

                            if maximum == 'parentwidth':
                                maximum = parent.computed_styles['width']

                            elif maximum == 'parentheight':
                                maximum = parent.computed_styles['height']
                        
                        buffer[style] = (float(val[:-1]) /100 ) * maximum
                except ValueError:
                    not_chosen += 1
            
            if "rgbvalue" in acceptable_types: # rgb val
                if len(re.findall("(\d+)",val)) != 3:
                    not_chosen += 1
                else:
                    colour = tuple(map(int,re.findall("(\d+)",val)))
                    buffer[style] = colour
                    

            
            if "text" in acceptable_types:
                if val not in STYLES[style]['accepted']:
                    not_chosen += 1
                else:
                    buffer[style] = val

            if not_chosen == len(acceptable_types):
                log(f"{style} value {val} not valid",LogLevel.FATAL)
            


        if element.type in ['div', 'frame']:
            self.__create_div_image__(element, buffer)
        
        elif element.type in ['image']:
            self.__create_image_element(element,buffer)

        elif element.type in ['text']:
            self.__create_text_element__(element,buffer)
        elif element.type in ['polygon']:
            self.__create_polygon_element__(element,buffer)


        self.__common_image_creation__(element,buffer, sibling_height)

    ###############################################
    def __common_image_creation__(self,element:Element,buffer, sibling_height:int):
        # get parent for parent calcs
        if buffer['position'] == 'absolute':
            parent = self.getElementById('global')
        else:
            parent = self.getElementById(element.parent_id) 
        # common - shared between all elements
        element.computed_styles['width'] = buffer['width']
        element.computed_styles['height'] = buffer['height']
        if buffer['width'] < 0 or buffer['height'] < 0:
            log(f"Element {element.id}; {element.type} has height smaller than 0")
        element.computed_styles['position'] = buffer['position']

        if buffer['position'] == 'block':
            buffer['top'] = sibling_height

        element.computed_styles['y'] = parent.computed_styles['y']+buffer['top'] 
        element.computed_styles['x'] = parent.computed_styles['x']+buffer['left']
        element.computed_styles['cx'] = parent.computed_styles['x']+ buffer['left'] + buffer['width'] / 2
        element.computed_styles['cy'] = parent.computed_styles['y']+buffer['top'] + buffer['height'] / 2
        
        if buffer['cx'] != 0:
            element.computed_styles['cx'] = parent.computed_styles['x'] + buffer['cx']
            element.computed_styles['x'] = element.computed_styles['cx'] - buffer['width'] / 2
        if buffer['cy'] != 0:
            element.computed_styles['cy'] = parent.computed_styles['y'] + buffer['cy']
            element.computed_styles['y'] = element.computed_styles['cy'] - buffer['height'] / 2

        element.computed_styles['rotation'] = parent.computed_styles['rotation']+buffer['rotation']
        # end adding to  computed styles

        # get the surface
        c_surf = element.get_surface()['surf']

        # filled mask_surf is only used for text elment collison
        filled_mask_surf = c_surf.copy()
        filled_mask_surf.fill((255,255,255))
        filled_mask_surf = pg.transform.rotate(filled_mask_surf,buffer['rotation'])
        ##############
        # rotate orig surface
        c_surf = pg.transform.rotate(c_surf,buffer['rotation'])
        ##################

        if parent.computed_styles['rotation'] % 360 != 0 and buffer['position'] in ['relative','block']:
            # How I factor in parent rotation is I make an empty bog the size of the parent box, then blit the subject to it and rotate around the parent origin, then use that box as a placeholder
            surf:pg.Surface = pg.Surface([parent.computed_styles['width'], parent.computed_styles['height']],pg.SRCALPHA)
            
            c_surf_rect = c_surf.get_rect(center = (
                buffer['left'] + buffer['width'] / 2,
                buffer['top'] + buffer['height'] / 2
            ))
            
            filled_surf = surf.copy()
            filled_surf.blit(filled_mask_surf,c_surf_rect)
    
            surf.blit(c_surf,c_surf_rect)
            surf = pg.transform.rotate(surf,parent.computed_styles['rotation'])
            surf_rect = surf.get_rect(center = (
                parent.computed_styles['cx'],
                parent.computed_styles['cy']
            ))

            filled_surf = pg.transform.rotate(filled_surf,parent.computed_styles['rotation'])
            

           

        else:
            c_surf_rect = c_surf.get_rect(center = (
                element.computed_styles['cx'],
                element.computed_styles['cy']
            ))
            surf = c_surf
            surf_rect = c_surf_rect

            # filled mask stuff
            filled_surf = filled_mask_surf

        # set the surface to the rotated version
        element.set_surface(surf,surf_rect,filled_surf)

        

    ##################################################

    def __render_element__(self,el:Element):
        surf = el.get_surface()['surf']
        surf_rect = el.get_surface()['rect']
        self.blit_to_surf(surf,surf_rect)

    def blit_to_surf(self,new_surf:pg.Surface,surf_rect:pg.Rect):

        self.surf.blit(new_surf,surf_rect)

    ###################################################

    def __create_div_image__(self, element:DivElement, buffer):
        # empty stuff to put out of the way
        element.computed_styles['font-size'] = 0
        element.computed_styles['font-color'] = (0,0,0,0)
        # border
        border_space = 0
        border_color = (0,0,0,0)
        border = False
        if buffer['border-width'] != 0 and buffer['border-color'] is not None:
            border_space = buffer['border-width']
            border_color = [x for x in buffer['border-color']] + [buffer['opacity']]
            element.computed_styles['border'] = True
            border = True
        
        element.computed_styles['border-width'] = border_space
        element.computed_styles['border-color'] = border_color


        
        # background
        background_color = (0,0,0,0)
        if buffer['background'] is not None:
            background_color = [x for x in buffer['background']] + [buffer['opacity']]

        element.computed_styles['background'] = background_color
        element.computed_styles['corner-radius'] = buffer['corner-radius']
        # misc move misc to common function

        # surface images
        surf = pg.Surface([buffer['width'],buffer['height']],pg.SRCALPHA)
        surf.fill((0,0,0,0))
        if border:
            pg.draw.rect(surf,border_color,(0,0,buffer['width'],buffer['height']),border_radius=int(buffer['corner-radius']))
        
        pg.draw.rect(surf,background_color,
                     (border_space,border_space,
                      buffer['width']-(2*border_space),
                      buffer['height']-(2*border_space)
                      ),
                      border_radius=int(buffer['corner-radius'])
                     )
        surf_rect = surf.get_rect()
        element.set_surface(surf, surf_rect)
    
    ##############################################################

    def __create_polygon_element__(self, element:PolygonElement, buffer):
         # empty stuff to put out of the way
        element.computed_styles['font-size'] = 0
        element.computed_styles['font-color'] = (0,0,0,0)
        # border


        
        # background
        background_color = (0,0,0,0)
        if buffer['background'] is not None:
            background_color = [x for x in buffer['background']] + [buffer['opacity']]

        element.computed_styles['background'] = background_color
        element.computed_styles['corner-radius'] = 0
        # misc move misc to common function

        # surface images
        surf = pg.Surface([buffer['width'],buffer['height']],pg.SRCALPHA)
        surf.fill((0,0,0,0))

        pg.draw.polygon(surf,background_color,element.points)
        
        surf_rect = surf.get_rect()
        element.set_surface(surf, surf_rect)

    ##############################################################

    def __create_text_element__(self,element:TextElement,buffer):
        if buffer['font-size'] <= 0: buffer['font-size'] = 10
        if buffer['height'] <= 0: buffer['height'] = buffer['font-size']
        if buffer['width'] <= 0: buffer['width'] = 500



        element.computed_styles['border-width'] = 0
        element.computed_styles['border-color'] = (0,0,0,0)
        element.computed_styles['background'] = (0,0,0,0)
        element.computed_styles['corner-radius'] = 0
        element.computed_styles['font-size'] = buffer['font-size']
        element.computed_styles['font-color'] = [x for x in buffer['font-color']] + [buffer['opacity']]
        
        if buffer['font'] == 'verdana':
            font = pg.font.SysFont('verdana',size=int(buffer['font-size']))
        else:
            font_file = buffer['font']
            font = pg.Font(font_file,size=int(buffer['font-size']))

        # I could use some of the font code from the previous thing for this
        surf = pg.Surface([buffer['width'],buffer['height']],pg.SRCALPHA)
        surf.fill((0,0,0,0))
        

        # check for reactive state
        # WARNING: using state with user input could result in unexpected behaviour

        textsplit = element.text.split('\n')
        state_in_text = False
        if not element.modifiable:
            for i, text in enumerate(textsplit):
                
                if (k:=text[2:].strip()) in self.states.keys():
                    textsplit[i] = str(self.states[k].get())
                    state_in_text =True
        text = '\n'.join(textsplit)
        if element.cursor is not None:
            text = text[:element.cursor+1] + '|' + text[element.cursor+1:]

        text_surf = self.__create_text__(font,buffer['width'],buffer['font-color'],text)

        if not state_in_text: # Only run this is no state is in place otherwise will probably break
            while text_surf.height > buffer['height']:

                element.text = element.text[:-1]
                if element.cursor is not None:
                    if element.cursor > len(element.text)-1:
                        element.cursor = len(element.text)-1
                    text = element.text[:element.cursor+1] + '|' + element.text[element.cursor+1:]
                else:
                    text = element.text
                if len(element.text) == 0: break
                text_surf = self.__create_text__(font,buffer['width'],buffer['font-color'],text)



        surf.blit(text_surf,(0,0))
        surf_rect = surf.get_rect()
        element.set_surface(surf, surf_rect)
    
    def __create_text__(self,font:pg.Font,width:int,color,text:str) -> pg.Surface:
        surf = font.render(text,True, color, wraplength=int(width))
        return surf

    ##############################################

    def __create_image_element(self,element:ImageElement,buffer):
        # empty stuff to put out of the way
        element.computed_styles['font-size'] = 0
        element.computed_styles['font-color'] = (0,0,0,0)
        # border
        border_space = 0
        border_color = (0,0,0,0)
        border = False
        if buffer['border-width'] != 0 and buffer['border-color'] is not None:
            border_space = buffer['border-width']
            border_color = [x for x in buffer['border-color']] + [buffer['opacity']]
            element.computed_styles['border'] = True
            border = True
        
        element.computed_styles['border-width'] = border_space
        element.computed_styles['border-color'] = border_color
        element.computed_styles['background'] = (0,0,0,0)
        element.computed_styles['corner-radius'] = buffer['corner-radius']

        try:
            pg.image.load(element.src)
        except:
            log(f"FileNotFoundError: Image element {element.id} path {element.src} not found.", LogLevel.FATAL)

        # no clue what this code does I kind of just copied it from my old Pymenu version where I apparently forgot to comment it
        # I just changed variable name to the equivalent of this project and hope it works
        surf = pg.Surface([buffer['width'],buffer['height']],pg.SRCALPHA)
        surf.fill((0,0,0,0))

        im_surf = pg.Surface([buffer['width']-buffer['border-width']*2,buffer['height']-buffer['border-width']*2], pg.SRCALPHA)
        im_surf.blit(pg.transform.scale(pg.image.load(element.src),[buffer['width']-buffer['border-width']*2,buffer['height']-buffer['border-width']*2]))

        img_size = im_surf.get_size()
        rect_img = pg.Surface(img_size,pg.SRCALPHA)
        pg.draw.rect(rect_img, (255,255,255), (0, 0, *img_size), border_radius=int(buffer['corner-radius']))

        im_surf.blit(rect_img,(0,0),None, pg.BLEND_RGBA_MIN)

        temp_surf = surf.copy()
        surf.blit(im_surf, (0,0))

        if buffer['border-width']> 0:
            pg.draw.rect(temp_surf, border_color, (0,0,*img_size), border_radius=int(buffer['corner-radius']))
            pg.draw.rect(temp_surf, (0,0,0,0),(buffer['border-width'],buffer['border-width'],img_size[0]-buffer['border-width']*2, img_size[1]-buffer['border-width']*2), border_radius=int(buffer['corner-radius']))
            #add a alpha in the centre to make a border
            surf.blit(temp_surf, (0,0))
        
        surf_rect = surf.get_rect()
        element.set_surface(surf, surf_rect)

    ##############################################
    ###############################################

    def getStateById(self,id_:str):
        if id_ in self.states:
            return self.states[id_]
        log(f'ID {id_} not a valid State, skipping operation',LogLevel.WARNING)

    def __state_modify_callback__(self,state:State):
        deps = state.dependents
        for dep in deps:
            self.__create_image_individual__(self.getElementById(dep),0)
        self.__recalc_rendered_frames__()
        # from here i still need to make the function which finds the highest scope to rerender images from

    def __element_modify_callback__(self, element:Element):
        self.__create_image_individual__(element,0)
        self.__recalc_rendered_frames__()
    ###############################################
    ###############################################

    def getElementById(self,id_:str) -> Element:
        element = self.elements.get(id_,None)
        if element is None:
            log(f"{id_} not found in getElementById function, returning None",LogLevel.WARNING)

        return element 


    def passEvent(self,event:pg.Event, global_dict):
        self.eventlistener.run(event, global_dict)
    
    def createElement(self,type_:str,id_:str,parent_id:str) -> Element:
        if type_ not in ELEMENTS:
            log(f"CREATE ELEMENT: --> INVALID TYPE: element type {type_} does not exist. Skipping Operation", LogLevel.WARNING)
            return
        current:Element = ELEMENTS[type_](parent_id,{},id_,[])
        if parent_id not in self.elements:
            log(f"CREATE ELEMENT: Parent id {parent_id} doesn't exist. Skipping operation",LogLevel.WARNING)
            return
        if current.id in self.elements:
            log(f"CREATE ELEMENT: ID {current.id} already in use. Overwriting old ID.", LogLevel.WARNING)
        if type_ == 'frame':
            if parent_id != 'global':
                log(f"CREATE ELEMENT: New frame must have an ID of global. Skipping operation", LogLevel.WARNING)
                return
            self.frames[current.id] = []
            
        elif parent_id == 'global':
            log(f"CREATE ELEMENT: New element must not have an ID of global except if frame. Skipping operation", LogLevel.WARNING)
            return
        else:
            # This needs to be a recursive search to find the correct frame
            parent = self.getElementById(current.parent_id)
            while parent.type != 'frame':
                parent = self.getElementById(parent.parent_id)
                
            self.frames[parent.id].append(current)
        


        current.set_callback_hook(self.__element_modify_callback__)
        self.elements[parent_id].children.append(current)
        self.elements[current.id] = current
        
        self.__create_image_individual__(current)
        self.__recalc_rendered_frames__()
        return current
    

    def deleteElement(self,id_:str):

        # kills an element and it's children
        el:Element = self.getElementById(id_)
        delete_queue = deque()
        delete_queue.append(el)
        parent = self.getElementById(el.parent_id)
        parent.children.remove(el)
        while delete_queue:
            el = delete_queue.popleft()
            for child in el.children: # add children to be iteratively erased
                delete_queue.append(child)
            del self.elements[el.id]
            # frame logic

            # delete from frames
            if el.type == 'frame':
                del self.frames[el.id]
                if el.id in self.frame_stack:
                    self.frame_stack.remove(el.id)
            else:
                for frame in self.frames: 
                    if el.id in self.frames[frame]:
                        del self.frames[frame][el.id]
            
            # removes el from states
            for state_id in self.states:
                if el.id in self.states[state_id].get_dependents():
                    self.states[state_id].remove_dependent(el.id)
            del el
        self.__recalc_rendered_frames__()
            

    def stateAssign(self,element_id:str,state_id:str):
        if element_id not in self.elements:
             log(f"STATE ASSIGN: --> INVALID ELEMENT ID: element id {element_id} does not exist")
        
        if state_id not in self.states:
            log(f"STATE ASSIGN: --> INVALID STATE ID: state id {state_id} does not exist")

        state = self.getStateById(state_id)
        state.dependents.append(element_id)
    
    def noRender(self):
        return self.factory.createNoRender()

    class ContextFactory:
        def __init__(self,View):
            self.View = View
        
        def createNoRender(self):
            return self.noRender(self.View)
        
        class noRender:
            def __enter__(self,View):
                self.View = View
                self.View.flags['noRender'] = True
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.View.flags['noRender'] = False
                ...
        

            

        

    







####################################
# Pass Objects from compiler to View
####################################

def initialize(path:str, size:list[int,int]) -> View:
    # transfers finished objects from compiler to view
    reset_log()
    compiler = Compiler(path)
    state_objects = compiler.states
    elements = compiler.compiled
    frames = compiler.frames
    return View(elements=elements,states=state_objects, size=size, frames=frames)

# read file from relative path
def relative_path_file(relative_path):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    relative_path = relative_path.replace('\\','/')
    file_path = os.path.join(script_dir, *relative_path.split('/'))
    return file_path
