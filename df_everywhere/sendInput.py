#
# Converts submitted command string to a key command to "type" into a window
#
#
import win32gui
import third_party.SendKeys

class SendInput:
    """
    Converts received commands (text) and sends them to the window after sanitation.
    """
    
    def __init__(self, hwnd):
        #The window that commands are sent to
        self.hwnd = hwnd
        
        #Codes to use with SendKeys
        self._command = { 'a': 'a',
                        'b': 'b',
                        'c': 'c',
                        'd': 'd',
                        'e': 'e',
                        'f': 'f',
                        'g': 'g',
                        'h': 'h',
                        'i': 'i',
                        'j': 'j',
                        'k': 'k',
                        'l': 'l',
                        'm': 'm',
                        'n': 'n',
                        'o': 'o',
                        'p': 'p',
                        'q': 'q',
                        'r': 'r',
                        's': 's',
                        't': 't',
                        'u': 'u',
                        'v': 'v',
                        'w': 'w',
                        'x': 'x',
                        'y': 'y',
                        'z': 'z',
                        'A': '+a',
                        'B': '+b',
                        'C': '+c',
                        'D': '+d',
                        'E': '+e',
                        'F': '+f',
                        'G': '+g',
                        'H': '+h',
                        'I': '+i',
                        'J': '+j',
                        'K': '+k',
                        'L': '+l',
                        'M': '+m',
                        'N': '+n',
                        'O': '+o',
                        'P': '+p',
                        'Q': '+q',
                        'R': '+r',
                        'S': '+s',
                        'T': '+t',
                        'U': '+u',
                        'V': '+v',
                        'W': '+w',
                        'X': '+x',
                        'Y': '+y',
                        'Z': '+y',
                        '0': '0',
                        '1': '1',
                        '2': '2',
                        '3': '3',
                        '4': '4',
                        '5': '5',
                        '6': '6',
                        '7': '7',
                        '8': '8',
                        '9': '9',
                        '!': '!',
                        '"': '"',
                        '#': '#',
                        '$': '$',
                        '%': '%',
                        '&': '&',
                        '\'': '\'',
                        '(': '(',
                        ')': ')',
                        '*': '*',
                        '+': '+',
                        ',': ',',
                        '-': '-',
                        '.': '.',
                        '/': '/',
                        ':': ':',
                        ';': ';',
                        '<': '<',
                        '=': '=',
                        '>': '>',
                        '?': '?',
                        '@': '@',
                        '[': '[',
                        '\\': '\\',
                        ']': ']',
                        '^': '^',
                        '_': '_',
                        '`': '`',
                        '{': '{',
                        '|': '|',
                        '}': '}',
                        '~': '~',
                        'tab': '{TAB}',
                        'enter': '{ENTER}',
                        'esc': '{ESC}',
                        'space': '{SPACE}',
                        'pageup': '{PGUP}',
                        'pagedown': '{PGDN}',
                        'end': '{END}',
                        'home': '{HOME}',
                        'left': '{LEFT}',
                        'up': '{UP}',
                        'right': '{RIGHT}',
                        'down': '{DOWN}',
        }
    
    def _sanitizeCommand(self, dirtyCommand):
        #return command from dictionary. If it doesn't exist, return 'None'
        return self._command.get(dirtyCommand, None)
    
    def _sendCommand(self, com):
        #This makes the window active and sends keyboard events directly.
        #Windows only.
        
        result = win32gui.SetForegroundWindow(self.hwnd)
        SendKeys.SendKeys(com)
        
        
    def receiveCommand(self, dirtyCommand):
        """
        Sanitizes command then sends it to window.
        """
        #print("received: %s" % dirtyCommand)
        cleanCommand = self._sanitizeCommand(dirtyCommand)
        #print("cleaned: %s" % cleanCommand)
        if cleanCommand is not None:
            self._sendCommand(cleanCommand)
        