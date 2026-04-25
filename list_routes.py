from server.app import app
from fastapi.routing import APIRoute
from starlette.routing import Mount

def list_routes(app, indent=""):
    for route in app.routes:
        if isinstance(route, APIRoute):
            print(f"{indent}{route.path} {route.methods}")
        elif isinstance(route, Mount):
            print(f"{indent}Mount: {route.path}")
            list_routes(route.app, indent + "  ")
        else:
            print(f"{indent}{route.path} {getattr(route, 'methods', 'No Methods')}")

list_routes(app)
