from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

game_session = {}

class StartRequest(BaseModel):
    room: str
    password: str
    name: str

class MoveRequest(BaseModel):
    room_name: str
    player: str
    index: int

class RestartRequest(BaseModel):
    room: str
    name: str

def check_winner(board):
    wins = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # горизонтали
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # вертикали
        [0, 4, 8], [2, 4, 6]  # диагонали
    ]
    for combo in wins:
        if board[combo[0]] == board[combo[1]] == board[combo[2]] != " ":
            return board[combo[0]]
    if " " not in board:
        return "Ничья"
    return None

@app.post("/start", summary="Подключение к комнате / создание комнаты")
def start(data: StartRequest):
    if not data.room or not data.password or not data.name:
        raise HTTPException(400, detail="Все поля ('room', 'password', 'name') обязательны")

    session = game_session.get(data.room)
    if session is None:
        game_session[data.room] = {
            "password": data.password,
            "players": {"X": data.name},
            "board": [" "] * 9,
            "turn": "X",
            "winner": None,
            "restart": set()
        }
        return {"symbol": "X", "message": "Комната создана. Вы игрок - X."}

    if session["password"] != data.password:
        raise HTTPException(403, detail="Неверный пароль")

    if "O" not in session["players"]:
        session["players"]["O"] = data.name
        return {"symbol": "O", "message": "Вы подключились к комнате как O."}

    raise HTTPException(400, detail="Комната уже заполнена двумя игроками")

@app.get("/state", summary="Получить информацию о комнате")
def state(room_name: str):
    game = game_session.get(room_name)
    if not game:
        raise HTTPException(404, detail=f"Комната {room_name} не найдена")
    return {
        "board": game["board"],
        "turn": game["turn"],
        "players": game["players"],
        "winner": game["winner"]
    }

@app.put("/move", summary="Сделать ход")
def make_move(data: MoveRequest):
    game = game_session.get(data.room_name)
    if not game:
        raise HTTPException(404, detail=f"Комната {data.room_name} не найдена")

    if data.index < 0 or data.index > 8:
        raise HTTPException(400, detail="Недопустимый индекс ячейки (0-8)")

    if game["board"][data.index] != " ":
        raise HTTPException(400, detail="Ячейка уже занята")

    if data.player not in game["players"].values():
        raise HTTPException(403, detail="Игрок не найден в комнате")

    # Проверяем, что ход делает правильный игрок
    symbol = "X" if game["players"]["X"] == data.player else "O"
    if symbol != game["turn"]:
        raise HTTPException(400, detail="Сейчас не ваш ход")

    game["board"][data.index] = symbol
    game["winner"] = check_winner(game["board"])

    if not game["winner"]:
        game["turn"] = "O" if game["turn"] == "X" else "X"

    return {
        "board": game["board"],
        "turn": game["players"][game["turn"]],
        "message": f"Ход выполнил игрок {data.player}",
        "winner": game["winner"]
    }

@app.post("/restart", summary="Перезапуск игры")
def restart(data: RestartRequest):
    session = game_session.get(data.room)
    if not session:
        raise HTTPException(404, detail=f"Комната {data.room} не найдена")

    if data.name not in session["players"].values():
        raise HTTPException(403, detail="Игрок не найден в комнате")

    session["restart"].add(data.name)
    if len(session["restart"]) == 2:
        session["board"] = [" "] * 9
        session["turn"] = "X"
        session["winner"] = None
        session["restart"].clear()
        return {"message": "Игра перезапущена"}
    return {"message": f"Игрок {data.name} проголосовал за перезапуск. Ждем второго игрока"}