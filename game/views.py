from django.http import HttpResponse

def game_view(request):
    html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>게임 스트리밍</title>
        <style>
            body {
                font-family: sans-serif;
                text-align: center;
                background: #111;
                color: white;
            }
            #screen {
                border: 3px solid #555;
                border-radius: 8px;
                margin-top: 20px;
                width: 640px;
                height: 480px;
                background: #000;
            }
        </style>
    </head>
    <body>
        <h1>🎮 실시간 게임 화면</h1>
        <p id="frameinfo"></p>
        <img id="screen" alt="게임 화면 로딩중...">

        <script>
            let ws = new WebSocket("ws://127.0.0.1:8000/ws/stream/");

            ws.onopen = () => {
                console.log("✅ WebSocket 연결됨");
            };

            ws.onmessage = (event) => {
                let msg = JSON.parse(event.data);
                if (msg.payload) {
                    document.getElementById("screen").src = "data:image/jpeg;base64," + msg.payload;
                }
                if (msg.frame_no !== undefined) {
                    document.getElementById("frameinfo").innerText = "Frame #" + msg.frame_no;
                }
            };

            ws.onclose = () => {
                console.log("❌ WebSocket 연결 끊김");
            };
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)
