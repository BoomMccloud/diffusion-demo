from aiohttp import ClientSession, ClientTimeout, web

async def client(app):
    async with ClientSession(timeout=ClientTimeout(total=None, sock_connect=10, sock_read=600)) as session:
        app["client"] = session
        yield

async def completion(request):
    body = await request.json()
    body["temperature"] = 0
    async with request.app["client"].post("http://127.0.0.1:18182/v1/chat/completions", json=body) as upstream:
        response = web.StreamResponse(status=upstream.status, headers={"Content-Type": upstream.headers["Content-Type"]})
        await response.prepare(request)
        async for chunk in upstream.content.iter_any():
            await response.write(chunk)
        return response

async def models(request):
    async with request.app["client"].get("http://127.0.0.1:18182/v1/models") as upstream:
        return web.Response(body=await upstream.read(), status=upstream.status, content_type="application/json")

app = web.Application(client_max_size=64 * 1024**2)
app.cleanup_ctx.append(client)
app.router.add_post("/v1/chat/completions", completion)
app.router.add_get("/v1/models", models)
web.run_app(app, host="127.0.0.1", port=18184)
