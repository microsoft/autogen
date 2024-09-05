import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union

import websockets
from fastapi import WebSocket, WebSocketDisconnect


class WebSocketConnectionManager:
    """
    Manages WebSocket connections including sending, broadcasting, and managing the lifecycle of connections.
    """

    def __init__(
        self,
        active_connections: List[Tuple[WebSocket, str]] = None,
        active_connections_lock: asyncio.Lock = None,
    ) -> None:
        """
        Initializes WebSocketConnectionManager with an optional list of active WebSocket connections.

        :param active_connections: A list of tuples, each containing a WebSocket object and its corresponding client_id.
        """
        if active_connections is None:
            active_connections = []
        self.active_connections_lock = active_connections_lock
        self.active_connections: List[Tuple[WebSocket, str]] = active_connections

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Accepts a new WebSocket connection and appends it to the active connections list.

        :param websocket: The WebSocket instance representing a client connection.
        :param client_id: A string representing the unique identifier of the client.
        """
        await websocket.accept()
        async with self.active_connections_lock:
            self.active_connections.append((websocket, client_id))
            print(f"New Connection: {client_id}, Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnects and removes a WebSocket connection from the active connections list.

        :param websocket: The WebSocket instance to remove.
        """
        async with self.active_connections_lock:
            try:
                self.active_connections = [conn for conn in self.active_connections if conn[0] != websocket]
                print(f"Connection Closed. Total: {len(self.active_connections)}")
            except ValueError:
                print("Error: WebSocket connection not found")

    async def disconnect_all(self) -> None:
        """
        Disconnects all active WebSocket connections.
        """
        for connection, _ in self.active_connections[:]:
            await self.disconnect(connection)

    async def send_message(self, message: Union[Dict, str], websocket: WebSocket) -> None:
        """
        Sends a JSON message to a single WebSocket connection.

        :param message: A JSON serializable dictionary containing the message to send.
        :param websocket: The WebSocket instance through which to send the message.
        """
        try:
            async with self.active_connections_lock:
                await websocket.send_json(message)
        except WebSocketDisconnect:
            print("Error: Tried to send a message to a closed WebSocket")
            await self.disconnect(websocket)
        except websockets.exceptions.ConnectionClosedOK:
            print("Error: WebSocket connection closed normally")
            await self.disconnect(websocket)
        except Exception as e:
            print(f"Error in sending message: {str(e)}", message)
            await self.disconnect(websocket)

    async def get_input(self, prompt: Union[Dict, str], websocket: WebSocket, timeout: int = 60) -> str:
        """
        Sends a JSON message to a single WebSocket connection as a prompt for user input.
        Waits on a user response or until the given timeout elapses.

        :param prompt: A JSON serializable dictionary containing the message to send.
        :param websocket: The WebSocket instance through which to send the message.
        """
        response = "Error: Unexpected response.\nTERMINATE"
        try:
            async with self.active_connections_lock:
                await websocket.send_json(prompt)
                result = await asyncio.wait_for(websocket.receive_json(), timeout=timeout)
                data = result.get("data")
                if data:
                    response = data.get("content", "Error: Unexpected response format\nTERMINATE")
                else:
                    response = "Error: Unexpected response format\nTERMINATE"

        except asyncio.TimeoutError:
            response = f"The user was timed out after {timeout} seconds of inactivity.\nTERMINATE"
        except WebSocketDisconnect:
            print("Error: Tried to send a message to a closed WebSocket")
            await self.disconnect(websocket)
            response = "The user was disconnected\nTERMINATE"
        except websockets.exceptions.ConnectionClosedOK:
            print("Error: WebSocket connection closed normally")
            await self.disconnect(websocket)
            response = "The user was disconnected\nTERMINATE"
        except Exception as e:
            print(f"Error in sending message: {str(e)}", prompt)
            await self.disconnect(websocket)
            response = f"Error: {e}\nTERMINATE"

        return response

    async def broadcast(self, message: Dict) -> None:
        """
        Broadcasts a JSON message to all active WebSocket connections.

        :param message: A JSON serializable dictionary containing the message to broadcast.
        """
        # Create a message dictionary with the desired format
        message_dict = {"message": message}

        for connection, _ in self.active_connections[:]:
            try:
                if connection.client_state == websockets.protocol.State.OPEN:
                    # Call send_message method with the message dictionary and current WebSocket connection
                    await self.send_message(message_dict, connection)
                else:
                    print("Error: WebSocket connection is closed")
                    await self.disconnect(connection)
            except (WebSocketDisconnect, websockets.exceptions.ConnectionClosedOK) as e:
                print(f"Error: WebSocket disconnected or closed({str(e)})")
                await self.disconnect(connection)
