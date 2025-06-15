import time, threading as th
import pygame as pg
from pygame.locals import QUIT
from typing import Any
from ..utils.logging import log, LogLevel

class EventListener:
    clock:pg.Clock
    event_callbacks:dict[str,callable]
    mouse_x = 0
    mouse_y = 0

    def __init__(self):
        self.clock = pg.Clock()
        self.event_callbacks:dict[str,list] = {
            'mousemove':[],
            'mousedown':[],
            'mouseup':[],
            'keydown':[],
            'keyup':[],
        }
        self.listener_addrs = {
            pg.MOUSEMOTION:'mousemove',
            pg.MOUSEBUTTONDOWN:'mousedown',
            pg.MOUSEBUTTONUP:'mouseup',
            pg.KEYDOWN:'keydown',
            pg.KEYUP:'keyup',
        }
        self.keys_down = {

        }

    def add_callback(self,event:str,callback:Any):
        if event not in self.event_callbacks:
            log(f'Event {event} not an event. Skipping operation', LogLevel.WARNING)
            return
        elif not callable(callback):
            log(f'Callback {callback} not a method. Skipping operation', LogLevel.WARNING)
            return
        elif any(callback is already_listening for already_listening in self.event_callbacks[event]): # use is for this otherwise it fails
            log(f'Callback {callback} already in events. Skipping operation', LogLevel.WARNING)
            return
    
        self.event_callbacks[event].append(callback)

    def remove_callback(self,event:str,callback:Any):
        if event not in self.event_callbacks:
            log(f'Event {event} not an event. Skipping operation', LogLevel.WARNING)
            return
        elif not callable(callback):
            log(f'Callback {callback} not a method. Skipping operation', LogLevel.WARNING)
            return
        try:
            self.event_callbacks[event].remove(callback)
        except ValueError:
            log(f'Callback {callback} not found in event {event}. Skipping operation', LogLevel.WARNING)

    def run(self, event:pg.Event, global_dict):
        # check for any callbacks
        
        for event_addr in self.listener_addrs:
            if event.type == event_addr:
                
                for callback in [ x for x in self.event_callbacks[
                    self.listener_addrs[event_addr]
                    ]]:

                    callback(event, global_dict)
            
    
    