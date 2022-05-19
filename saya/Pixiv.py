import httpx
import random
import asyncio

from datetime import datetime

from graia.saya import Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Group, Member, MemberPerm
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.message.element import Forward, ForwardNode, Image, Plain
from graia.ariadne.message.parser.twilight import (
    Twilight,
    FullMatch,
    RegexMatch,
    RegexResult,
)

from config import yaml_data
from util.sendMessage import safeSendGroupMessage
from util.control import Function, Interval, Permission, Rest

channel = Channel.current()

proxies = {
    "http://": "http://127.0.0.1:1080",
    "https://": "http://127.0.0.1:1080"
}


async def sendPixivMessage(data, app: Ariadne, group: Group, member: Member):
    if yaml_data["Saya"]["Pixiv"]["Forward"]:
        if member.permission == MemberPerm.Owner:
            name = "群主"
        elif member.permission == MemberPerm.Administrator:
            name = "管理员"
        elif member.permission == MemberPerm.Member:
            name = "高层群员"

        forwardnode = [
            ForwardNode(
                senderId=member.id,
                time=datetime.now(),
                senderName=member.name,
                messageChain=MessageChain.create(f"我是发涩图的{name}，请大家坐稳扶好，涩图要来咯！"),
            )
        ]
        group_members = await app.getMemberList(group)
        for pic in data:
            member = random.choice(group_members)
            forwardnode.append(
                ForwardNode(
                    senderId=member.id,
                    time=datetime.now(),
                    senderName=member.name,
                    messageChain=MessageChain.create(
                        [
                            Plain(f"ID：{pic['pid']}\n"),
                            Plain(f"NAME：{pic['title']}\n"),
                            Plain(f"AUTHOR：{pic['author']}\n"),
                            Plain(f"R18: {pic['r18']}"),
                        ]
                    ),
                )
            )
            forwardnode.append(
                ForwardNode(
                    senderId=member.id,
                    time=datetime.now(),
                    senderName=member.name,
                    messageChain=MessageChain.create(
                        [
                            Image(url=pic["urls"]['original']),
                        ]
                    ),
                )
            )
        message = MessageChain.create(Forward(nodeList=forwardnode))
    else:
        pic = data[0]
        message = MessageChain.create(
            [
                Plain(f"ID：{pic['pid']}\n"),
                Plain(f"NAME：{pic['title']}\n"),
                Plain(f"AUTHOR：{pic['author']}\n"),
                Plain(f"R18: {pic['r18']}"),
                Image(url=pic["urls"]['original']),
            ]
        )

    msg = await safeSendGroupMessage(group, message)
    if yaml_data["Saya"]["Pixiv"]["Recall"]:
        await asyncio.sleep(
            yaml_data["Saya"]["Pixiv"]["Interval"]
            if yaml_data["Saya"]["Pixiv"]["Interval"] < 110
            else 110
        )
        try:
            await app.recallMessage(msg)
        except Exception:
            pass


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight(
                [
                    "tag1" @ RegexMatch(r".+", optional=True),
                    FullMatch("涩图"),
                    "tag2" @ RegexMatch(r".+", optional=True),
                ],
            )
        ],
        decorators=[
            Function.require("Pixiv"),
            Permission.require(),
            Rest.rest_control(),
            Interval.require(),
        ],
    )
)
async def main(
    app: Ariadne, group: Group, member: Member, tag1: RegexResult, tag2: RegexResult
):
    if yaml_data["Saya"]["Pixiv"]["san"] == "r18":
        san = 1
    elif yaml_data["Saya"]["Pixiv"]["san"] == "r16":
        san = 0
    else:
        san = 2
    if tag1.matched or tag2.matched:
        tag = tag1.result.asDisplay() if tag1.matched else tag2.result.asDisplay()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://api.lolicon.app/setu/v2?r18={san}tag={tag}"
            )
            res = r.json()
        if res.get("error") == "":
            await sendPixivMessage(res.get('data'), app, group, member)
        elif res.get("code", False) == 404:
            await safeSendGroupMessage(group, MessageChain.create("未找到相应tag的色图"))
        else:
            await safeSendGroupMessage(group, MessageChain.create("慢一点慢一点，别冲辣！"))
    else:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"https://api.lolicon.app/setu/v2?r18={san}")
            res = r.json()
        if res.get("error") == "":
            await sendPixivMessage(res.get('data'), app, group, member)
        else:
            await safeSendGroupMessage(group, MessageChain.create("慢一点慢一点，别冲辣！"))
