# DF Everywhere
# Copyright (C) 2014  Travis Painter

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

#
# 
#
from twisted.internet import reactor, threads
from twisted.internet.defer import inlineCallbacks   

from util import wamp_local, sendInput, utils, prettyConsole

class Game():
    """
    Object to hold all program states and connections.
    """
    
    def __init__(self, web_topic, web_key, shotFunction, window_hnd, fps = False):
        ### FPS reports
        self.fps = fps
        self.fps_counter = 0
        
        ### Tileset
        self.tileset = None
        
        ### Commands
        self.shotFunction = shotFunction
        self.window_hnd = window_hnd
        self.controlWindow = sendInput.SendInput(self.window_hnd)
        
        ### Timing delays
        self.screenDelay = 0.0
        self.screenDelaySlowed = 0.5
        self.filenameDelay = 5
        self.sizeDelay = 5
        self.heartbeatDelay = 1
        self.screenCycles = 0
        
        ### WAMP details
        self.web_topic = web_topic
        self.web_key = web_key
        self.topicPrefix = "df_everywhere.%s" % self.web_topic
        self.connected = False
        self.connection = None
        self.defereds = {}
        self.subscriptions = {}
        self.rpcs = {}
        self.retryWaits = 0 #number of cycles program has waited for connection
        self.retryAttempts = 0 #number of retry attempts. Used to increase wait time. 
        self.reconnecting = False
        self.sendFullMaps = True #whether or not to always send full maps
        
        ### Heartbeats
        self.heartbeatCounter = 120
        self.slowed = False
        
        ### Connect to WAMP router
        self.connection = wamp_local.wampClient("ws://router1.dfeverywhere.com:7081/ws", "tcp:router1.dfeverywhere.com:7081", self.web_topic, self.web_key)
        
        ### Wait for WAMP connection before initializing loops in reactor
        reactor.callLater(0, self._waitForConnection)        
            
    def _waitForConnection(self):
        """
        Handles waiting for WAMP connection before continuing loading program.
        """
        if self.connection is None:
            prettyConsole.console('log', "Waiting for connection...")
            #Wait and test again
            self.retryWaits += 1
            if self.retryWaits > 20:
                #wait about 10 seconds for connection. Then try reconnecting
                self.retryWaits = 0
                self.reconnecting = False
                #prettyConsole.console('log', "aaaaaa")
                prettyConsole.console('log', 'Will attempt reconnect in %d seconds.' % (1 + 2 ** self.retryAttempts))
                reactor.callLater(1 + 2 ** self.retryAttempts, self.reconnect)
                return
                
            reactor.callLater(0.5, self._waitForConnection)
        else:
            try:
                a = self.connection[0]
            except:
                prettyConsole.console('log', "Still waiting for connection...")
                ##Wait and test again
                self.retryWaits += 1
                if self.retryWaits > 20:
                    #wait about 20seconds for connection. Then try reconnecting
                    self.retryWaits = 0
                    self.reconnecting = False
                    #prettyConsole.console('log', "bbbb")
                    prettyConsole.console('log', 'Will attempt reconnect in %d seconds.' % (1 + 2 ** self.retryAttempts))
                    reactor.callLater(1 + 2 ** self.retryAttempts, self.reconnect)
                    return
                    
                reactor.callLater(0.5, self._waitForConnection)
            else:
                prettyConsole.console('log', "Connected...")
                self.connected = True
                self.reconnecting = False
                self.retryWaits = 0
                self.retryAttempts = 0
                reactor.callLater(0.1, self._registerRPC)
                reactor.callLater(0.2, self._subscribeCommands)
                reactor.callLater(0.3, self._subscribeHeartbeats)
                
                ### Initialize reactor loops
                reactor.callLater(self.screenDelay, self._loopScreen)
                reactor.callLater(self.filenameDelay, self._loopFilename)
                reactor.callLater(self.sizeDelay, self._loopTileSize)
                reactor.callLater(self.sizeDelay, self._loopScreenSize)
                reactor.callLater(self.heartbeatDelay, self._loopHeartbeat)
                if self.fps:
                    reactor.callLater(5, self._loopPrintFps)
            
    @inlineCallbacks
    def _registerRPC(self):
        """
        Registers function for remote procedure calls.
        """
        try:
            d = yield self.connection[0].register(self.tileset.wampSend, '%s.tilesetimage' % self.topicPrefix)
            self.rpcs['tileset'] = d
        except Exception as inst:
            prettyConsole.console('log', inst)
            reactor.callLater(1, self.reconnect)
    
    @inlineCallbacks
    def _subscribeCommands(self):
        """
        Subscribes to incomming commands.
        """
        try:
            d = yield self.connection[0].subscribe(self.controlWindow.receiveCommand, '%s.commands' % self.topicPrefix)
            self.subscriptions['commands'] = d
        except:
            prettyConsole.console('log', 'Command sub error')
    
    @inlineCallbacks
    def _subscribeHeartbeats(self):
        """
        Subscribes to incomming heartbeats.
        """
        try:
            d = yield self.connection[0].subscribe(self._receiveHeartbeats, '%s.heartbeats' % self.topicPrefix)
            self.subscriptions['heartbeats'] = d
        except:
            prettyConsole.console('log', 'Heartbeat sub error')
        
    def _receiveHeartbeats(self, recv):
        """
        Tracks heartbeats from clients. Ignore 'recv'.
        """
        #On hearbeat, reset counter.
        self.heartbeatCounter = 120
        if self.slowed:
            prettyConsole.console('log', "Viewer connected. Resuming...")
            self.slowed = False
            
    def _loopHeartbeat(self):
        """
        Handles periodically decreasing heartbeat timer.
        """
        if self.heartbeatCounter > 0:
            self.heartbeatCounter -= 1
            
        if self.heartbeatCounter < 1:
            if not self.slowed:
                prettyConsole.console('log', "No viewers connected, slowing...")
            self.slowed = True
        else:
            self.slowed = False            
        
        self.defereds['heartbeat'] = reactor.callLater(self.heartbeatDelay, self._loopHeartbeat)
        
    #@inlineCallbacks
    def _loopScreen(self):
        """
        Handles periodically running screen grabs.
        """
        try:
            shot = self.shotFunction(self.window_hnd, debug = False)
            #Need to check that an image was returned.
            shot_x, shot_y = shot.size
        except:
            print("Error getting image. Exiting.")
            #reactor.stop()
            self.stopClean()
            return
        
        trimmedShot = utils.trim(shot, debug = False) 
        
        if trimmedShot is not None:
            
            #Only send a full tile map every 20 cycles, otherwise just send changes
            #Is this needed anymore? Javascript expects full maps all the time.
            #This is slower with deferToThread
            if self.sendFullMaps or (self.screenCycles) % 20 == 0:
                tileMap = self.tileset.parseImageArray(trimmedShot, returnFullMap = True)
                #tileMap = yield threads.deferToThread(self.tileset.parseImageArray, trimmedShot, returnFullMap = True)
            else:
                tileMap = self.tileset.parseImageArray(trimmedShot, returnFullMap = False)
                #tileMap = yield threads.deferToThread(self.tileset.parseImageArray, trimmedShot, returnFullMap = False)
        else:
            #If there was an error getting the tilemap, fake one.
            prettyConsole.console('log', "Error reading game window.")
            tileMap = []
        
        self._sendTileMap(tileMap)
        self.screenCycles += 1
        
        if self.fps:
            self.fps_counter += 1
        
        if self.slowed:
            self.defereds['screen'] = reactor.callLater(self.screenDelaySlowed, self._loopScreen)
        else:
            self.defereds['screen'] = reactor.callLater(self.screenDelay, self._loopScreen)
        
    def _loopFilename(self):
        """
        Handles periodically sending the current tileset filename.
        """
        if self.connected:
            if self.tileset.filename is not None:
                try:
                    self.connection[0].publish("%s.tileset" % self.topicPrefix, self.tileset.filename)
                except:
                    #connection lost, reconnect
                    self.reconnect()
                    
        self.defereds['filename'] = reactor.callLater(self.filenameDelay, self._loopFilename)
        
    def _loopTileSize(self):
        """
        Handles periodically sending the current tile dimensions.
        """
        if self.connected:
            if (self.tileset.tile_x is not None) and (self.tileset.tile_y is not None):
                try:
                    self.connection[0].publish("%s.tilesize" % self.topicPrefix, [self.tileset.tile_x, self.tileset.tile_y])
                except:
                    #connection lost, reconnect
                    self.reconnect()
        self.defereds['tileSize'] = reactor.callLater(self.sizeDelay, self._loopTileSize)
        
    def _loopScreenSize(self):
        """
        Handles periodically sending the current screen dimensions.
        """
        if self.connected:
            if (self.tileset.screen_x is not None) and (self.tileset.screen_y is not None):
                #Only send screen size update if it makes sense
                if (self.tileset.screen_x % self.tileset.tile_x == 0) and (self.tileset.screen_y % self.tileset.tile_y == 0):
                    try:
                        self.connection[0].publish("%s.screensize" % self.topicPrefix, [self.tileset.screen_x, self.tileset.screen_y])
                    except:
                        #connection lost, reconnect
                        self.reconnect()
        self.defereds['screenSize'] = reactor.callLater(self.sizeDelay, self._loopScreenSize)
        
    def _sendTileMap(self, tilemap):
        """
        Sends tilemap over connection.
        """
        if self.connected:
            if tilemap != []:
                try:
                    self.connection[0].publish("%s.map" % self.topicPrefix, tilemap)
                except:
                    #connection lost, reconnect
                    reactor.callLater(1, self.reconnect)
                
    def _loopPrintFps(self):
        """
        Print number of screen grabs per second.
        """
        prettyConsole.console('update', "FPS: %0.1f" % (self.fps_counter/5.0))
        self.fps_counter = 0
        
        if self.fps:
            self.defereds['fps'] = reactor.callLater(5, self._loopPrintFps)
            
    def stopClean(self):
        """
        Cleanly stop connection and shutdown.
        """
        #Cancel pending callbacks
        for k, v in self.defereds.iteritems():
            if v.active():
                v.cancel()
        self.connected = False
        try:
            self.connection[0].disconnect()
        except:
            pass
        reactor.callLater(1, reactor.stop)
        
    def reconnect(self):
        """
        Handles reconnecting to WAMP server.
        """       
        
        
        if self.reconnecting:
            #don't try to reconnect if it has already been tried
            prettyConsole.console('log', "Already reconnecting...")
            return
            
        
        self.reconnecting = True
        self.retryAttempts += 1
        prettyConsole.console('log', "Reconnecting to server...")
        
        #Cancel pending callbacks
        for k, v in self.defereds.iteritems():
            if v.active():
                v.cancel()
        self.defereds.clear()
        
        #Try to cancel RPC and subscriptions
        for text, sub in self.subscriptions.iteritems():
            try:
                sub.unsubscribe()
            except:
                prettyConsole.console('log', "Unable to unsubscribe to: %s" % text)
                
        for text, rpc in self.rpcs.iteritems():
            try:
                rpc.unregister()
            except:
                prettyConsole.console('log', "Unable to unsubscribe to: %s" % text)
        
        #Reset back to original state
        self.connected = False
        try:
            self.connection[0].leave()
        except:
            prettyConsole.console('log', "Unable to cleanly close connection.")
            pass
        self.connection = None
        self.subscriptions.clear()
        self.rpcs.clear()
        
        #Restart connection
        self.connection = wamp_local.wampClient("ws://router1.dfeverywhere.com:7081/ws", "tcp:router1.dfeverywhere.com:7081", self.web_topic, self.web_key)
        #self.connection[0].connect()
        
        reactor.callLater(0.5, self._waitForConnection)
        