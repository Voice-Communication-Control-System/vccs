from asgiref.sync import async_to_sync
import json
import queue
import re
import threading
from time import sleep
from channels.generic.websocket import AsyncWebsocketConsumer
from loguru import logger

import panel.vatsim_data as vatsim_data

global channel_list
global start_thread
start_thread = False
channel_list = set()

VATSIM_DATA = vatsim_data.Vatsim()


class VccsConsumer(AsyncWebsocketConsumer):

    global vccs_channels
    global vccs_sockets
    global channel_queue
    channel_queue = queue.Queue()
    vccs_channels = set()
    vccs_sockets = set()

    async def connect(self):
        """What do to on receive connection"""
        global start_thread
        await self.accept()
        if not start_thread:
            start_thread = True
            rx_thread = threading.Thread(target=self.vatsim_controller_update, daemon=True)
            rx_thread.start()
            logger.success("VATSIM poll started...")
    
    @async_to_sync
    async def vatsim_controller_update(self):
        """Update the VATSIM controller list and send updates to clients"""
        async def broadcast(command, callsign):
            global vccs_channels
            # broadcast to every channel
            for channel in vccs_channels:
                json_msg = {"command": command, "peer_id": callsign}
                tx_msg = json.dumps(json_msg)
                await self.send_to_group(tx_msg, channel)
                logger.success("Sent message {} to {}", tx_msg, channel)

        cs_list = set()
        while True:
            active_callsigns = VATSIM_DATA.get_controller()
            for callsign in active_callsigns:
                if re.match(r"^(EG[A-Z]{2}\_|LON\_|LTC\_|SCO\_|MAN\_)", callsign):
                    logger.trace("ADD Check: {}", callsign)
                    # check if the callsign exists in the cs_list. If not, add it.
                    if callsign not in cs_list:
                        cs_list.add(callsign)
                        await broadcast("vatsim_add", callsign)
            if len(cs_list) > 0:
                for callsign in cs_list.copy():
                    if re.match(r"^(EG[A-Z]{2}\_|LON\_|LTC\_|SCO\_|MAN\_)", callsign):
                        logger.trace("REMOVE Check: {}", callsign)
                        # check that all callsigns exist in the active_callsigns list. If not, remove them.
                        if callsign not in active_callsigns:
                            cs_list.remove(callsign)
                            await broadcast("vatsim_remove", callsign)
            sleep(15)
                
    async def disconnect(self, message):
        """What to do on disconnect"""
        pass
        
    async def websocket_receive(self, message):
        """What to do on receive frame"""
        global vccs_channels
        logger.debug(message)
        rx_msg = json.loads(message["text"])

        if rx_msg["header"]["to"] != "server":
            # if not to the server, pass straight through to recipient
            await self.send_to_group(json.dumps(rx_msg), rx_msg["header"]["to"])
            logger.debug("Direct send: {}", json.dumps(rx_msg))
        elif rx_msg["data"]["command"] == "helo" and rx_msg["header"]["to"] == "server":
            # on client connection
            add_position = rx_msg["header"]["from"]
            if add_position not in vccs_channels:
                logger.debug("Client {} has connected", add_position)
                # add the client to their own group
                await self.channel_layer.group_add(
                    rx_msg["header"]["from"],
                    self.channel_name
                )
                logger.debug("Add channel {} detail {}", rx_msg["header"]["from"], self.channel_name)
                # add the position into the channel list
                vccs_channels.add(add_position)
                await self.broadcast_add("add_peer")                
            else:
                logger.warning("Connection already exists for {}", add_position)
        elif rx_msg["data"]["command"] == "bye" and rx_msg["header"]["to"] == "server":
            # on client disconnection
            msg = json.loads(message["text"])
            vccs_channels.remove(msg["header"]["from"])
            await self.broadcast_remove(msg["header"]["from"])
        elif rx_msg["data"]["command"] == "call":
            # if message is a call command
            try:
                json_msg = json.loads(rx_msg["data"])
            except TypeError:
                json_msg = rx_msg["data"]
            json_msg["from"] = rx_msg["header"]["from"]
            tx_msg = json.dumps(json_msg)
            await self.send_to_group(tx_msg, rx_msg["header"]["to"])
            logger.success("Sent message {} to {}", tx_msg, rx_msg["header"]["to"])
        elif rx_msg["data"]["command"] == "candidate":
            # notify other peers of candidate information
            json_data = rx_msg["data"]
            # tx_msg = json.dumps(json_msg)
            for channel in vccs_channels:
                json_msg = {"command": "candidate", "peer_id": rx_msg["header"]["from"], "desc": json_data}
                tx_msg = json.dumps(json_msg)
                await self.send_to_group(tx_msg, channel)
                logger.success("Sent message {} to {}", tx_msg, channel)
    
    async def send_to_group(self, text_data, msg_to):
        """Prepares a group message"""
        await self.channel_layer.group_send(
            msg_to,
            {
                "type": "message.rebro",
                "text": text_data,
            },
        )
    
    async def message_rebro(self, event):
        """Sends a group message"""
        await self.send(text_data=event["text"])
    
    async def broadcast_add(self, command):
        """broadcast all connected channels to all users"""
        global vccs_channels
        logger.debug(vccs_channels)
        for channel in vccs_channels:
            for user in vccs_channels:
                if channel != user:
                    json_msg = {"command": command, "peer_id": channel}
                    tx_msg = json.dumps(json_msg)
                    await self.send_to_group(tx_msg, user)
                    logger.success("Sent message {} to {}", tx_msg, user)
    
    async def broadcast_remove(self, remove_channel):
        """broadcast all connected channels to all users"""
        global vccs_channels
        logger.debug(vccs_channels)
        for channel in vccs_channels:
            json_msg = {"command": "remove_peer", "peer_id": remove_channel}
            tx_msg = json.dumps(json_msg)
            await self.send_to_group(tx_msg, channel)
            logger.success("Sent message {} to {}", tx_msg, channel)
