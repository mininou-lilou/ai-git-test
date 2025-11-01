from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import typer

app = FastAPI()
templates = Jinja2Templates(directory="templates")
cli = typer.Typer()

USERS = {"admin": "secret123"}

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.get_template("login.html").render({"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if USERS.get(username) == password:
        return {"message": f"Bienvenue {username}!"}
    return {"error": "Identifiants incorrects"}

@cli.command()
def run():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    cli()