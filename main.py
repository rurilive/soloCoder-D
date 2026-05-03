from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

app = FastAPI(title="番茄工作法计时器")

app.mount("/static", StaticFiles(directory="static"), name="static")

# 直接使用Jinja2 Environment，避免FastAPI和Jinja2的兼容性问题
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(
    loader=FileSystemLoader(templates_dir),
    autoescape=select_autoescape(["html", "xml"])
)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    template = env.get_template("index.html")
    return HTMLResponse(content=template.render(request=request))
