const ws = new WebSocket("ws://192.168.1.101:8765");

ws.onopen = () => {
    console.log("Connected");

    ws.send(JSON.stringify({
        type: "shell_start"
    }));
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