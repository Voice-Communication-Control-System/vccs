// init session storage
sessionStorage.setItem("userAircraftLat", 0);
sessionStorage.setItem("userAircraftLon", 0);

// authenticate to websocket server
const heroSocket = new WebSocket(
    'ws://localhost:8000/connect/?auth_key={{ token }}'
);

// do this when the websocket has opened
heroSocket.onopen = function(event) {
    let open_msg = JSON.stringify({'header': {'from': 'webapp-{{ user.username }}', 'to': 'server'}, 'data': {'route': 'control', 'command': 'helo'}});
    heroSocket.send(open_msg);
};

// do this when a message is received
heroSocket.onmessage = function(event) {
    console.log(event);
    let received_msg = JSON.parse(event.data);
    if (received_msg.data.route == "webapp") {
        if (received_msg.data.command == "ping") {
            var pong = JSON.stringify({"header": {"from": "webapp-{{ user.username }}", "to": received_msg.header.from}, "data": {"route": "simconnect", "command": "pong"}})
            heroSocket.send(pong);
        };
    } else if (received_msg.data.route == "simconnect") {
        sessionStorage.setItem("userAircraftLat", received_msg.data.data["PLANE_LATITUDE"]);
        sessionStorage.setItem("userAircraftLon", received_msg.data.data["PLANE_LONGITUDE"]);
        // convert radians to degrees
        let radians = received_msg.data.data["PLANE_HEADING_DEGREES_TRUE"]
        let degrees = radians * 57.2958;
        sessionStorage.setItem("userAircraftHdg", degrees);
    };
};