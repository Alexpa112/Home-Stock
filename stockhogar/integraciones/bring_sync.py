"""
Integracion opcional con Bring! usando la libreria no oficial `bring-api`
(la misma que usa Home Assistant). Bring! no ofrece una API publica, por lo
que esto puede dejar de funcionar si Bring cambia su backend interno.
"""
import asyncio

import aiohttp
from bring_api import Bring


async def _obtener_listas_async(email, password):
    async with aiohttp.ClientSession() as session:
        bring = Bring(session, email, password)
        await bring.login()
        datos = await bring.load_lists()
        return [{"uuid": l["listUuid"], "nombre": l["name"]} for l in datos["lists"]]


def obtener_listas(email, password):
    return asyncio.run(_obtener_listas_async(email, password))


async def _sincronizar_async(email, password, lista_uuid, nombres):
    async with aiohttp.ClientSession() as session:
        bring = Bring(session, email, password)
        await bring.login()
        for nombre in nombres:
            await bring.save_item(lista_uuid, nombre)


def sincronizar_items(email, password, lista_uuid, nombres):
    if not nombres:
        return
    asyncio.run(_sincronizar_async(email, password, lista_uuid, nombres))
