from aiohttp import ClientSession, ClientTimeout, web

async def client(app):
    async with ClientSession(timeout=ClientTimeout(total=None, sock_connect=10, sock_read=600)) as session:
        app["client"] = session
        yield

async def completion(request):
    body = await request.json()
    body["temperature"] = 0
    messages = body["messages"]
    if messages and messages[0].get("role") == "system" and isinstance(messages[0].get("content"), str):
        messages[0]["content"] += "\n\nActive deployment: text-only chat. No tools or filesystem are available. Answer directly using the final-answer label for this turn. For an HTML or file request, provide the complete source inline in a fenced code block and explain that the user can save it. Never emit tool-call markup, shell file-writing commands, attachment links, or claims that a file was created."
    body.pop("tools", None)
    body.pop("tool_choice", None)
    body["chat_template_kwargs"] = {"enable_thinking": False}
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
web.run_app(app, host="127.0.0.1", port=18185)
