//    ws://192.168.0.101:8765/
const ws = new WebSocket("ws://192.168.0.101:8765");

ws.onopen = () => {
  console.log("Connected");
  ws.send("Hello server");
};

ws.onmessage = (event) => {
  console.log("Message:", event.data);
};

ws.onclose = () => {
  console.log("Disconnected");
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};