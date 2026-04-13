import os
import traceback
from io import BytesIO

import PIL
import httpx
import urllib.parse
import asyncio
from lxml import etree
from PicImageSearch import Network, SauceNAO, Ascii2D, Bing
from PIL import Image, ImageFont, ImageDraw, ImageFilter

from utils import imgLocalPathToBase64, extractImgUrls
from kusa_base import plugin_config
from multi_platform import send_finish, get_user_id, is_onebot_v11_event
from nonebot import on_command, on_message
from nonebot.adapters import Bot, Event
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message as OneBotMessage, PrivateMessageEvent
from .reply_commands import reply_command, ReplyCommandResult, store_result, get_stored_result

proxy = plugin_config.get('web', {}).get('proxy', None)
saucenaoApiKey = plugin_config.get('web', {}).get('saucenao', {}).get('key', '')
fontPath = plugin_config.get('basePath', '') + r'\font' if plugin_config.get('basePath') else r'.\font'
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
generalHeader = {
    "sec-ch-ua": '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"',
    "user-agent": plugin_config.get('web', {}).get('userAgent', '')
}
searchWaitingUsers = {}


搜图_cmd = on_command('搜图', aliases={'picsearch'}, priority=5, block=True)


@搜图_cmd.handle()
async def handle_搜图(bot: Bot, event: Event, args: Message = CommandArg()):
    global searchWaitingUsers

    if not is_onebot_v11_event(event):
        await send_finish(搜图_cmd, "该功能目前仅支持OneBot平台")
        return

    user_id = await get_user_id(event)
    imgUrls = extractImgUrls(args)

    if imgUrls:
        await 搜图_cmd.send("正在搜索……")
        resultDict = await getSearchResult(imgUrls[0])
        if not resultDict or not resultDict["info"]:
            await 搜图_cmd.finish('没有搜索到结果^ ^')
            return

        sendMsgInfo = await 搜图_cmd.send(imgLocalPathToBase64(os.path.join(CACHE_DIR, 'picsearch.jpg')))
        store_result(sendMsgInfo['message_id'], {'info': resultDict['info']})
    else:
        searchWaitingUsers[user_id] = True
        await 搜图_cmd.send('已启用图片搜索，请发送图片')


搜图等待_handler = on_message(priority=6, block=False)


@搜图等待_handler.handle()
async def handle_搜图等待(bot: Bot, event: Event):
    global searchWaitingUsers

    if not is_onebot_v11_event(event):
        return

    if not isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
        return

    user_id = await get_user_id(event)

    if user_id not in searchWaitingUsers:
        return

    del searchWaitingUsers[user_id]

    message = event.get_message()
    plain_text = message.extract_plain_text().strip()

    if plain_text:
        await 搜图等待_handler.send("搜图已取消")
        return

    imgUrls = extractImgUrls(message)
    if not imgUrls:
        await 搜图等待_handler.send("非图片，搜图已取消")
        return

    await 搜图等待_handler.send("正在搜索……")
    resultDict = await getSearchResult(imgUrls[0])
    if not resultDict or not resultDict["info"]:
        await 搜图等待_handler.finish('没有搜索到结果^ ^')
        return

    sendMsgInfo = await 搜图等待_handler.send(imgLocalPathToBase64(os.path.join(CACHE_DIR, 'picsearch.jpg')))
    store_result(sendMsgInfo['message_id'], {'info': resultDict['info']})


提取url_handler = on_message(priority=14, block=False)


@提取url_handler.handle()
async def handle_提取url(bot: Bot, event: Event):
    if not is_onebot_v11_event(event):
        return

    if not isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
        return

    message = event.get_message()
    reply_msg_id = None

    if hasattr(event, 'reply') and event.reply:
        reply_msg_id = str(event.reply.message_id)

    if not reply_msg_id:
        for seg in message:
            if seg.type == 'reply':
                reply_msg_id = str(seg.data.get('id'))
                break

    if not reply_msg_id:
        return

    stored = get_stored_result(reply_msg_id)
    if not stored or 'info' not in stored:
        return

    resultDict = stored['info']
    plain_text = message.extract_plain_text().strip()
    if not plain_text:
        return

    try:
        args = list(set(map(int, plain_text.split()))  )
        args = [arg for arg in args if 1 <= arg <= len(resultDict)]
        args.sort()

        if not args:
            await 提取url_handler.send("未找到对应图片链接, 请检查输入是否正确")
            return

        msg = "\n".join(f"{index} - {resultDict[index - 1]['url']}" for index in args)
        await 提取url_handler.send(drawTextToImage(msg))

    except (IndexError, ValueError):
        await 提取url_handler.send("未找到对应图片链接, 请检查输入是否正确")


@reply_command('picurl')
async def picurl_cmd(event: GroupMessageEvent, img_url: str, bot: Bot) -> str:
    return img_url


@reply_command('url')
async def url_cmd(event: GroupMessageEvent, img_url: str, bot: Bot) -> str:
    return img_url


@reply_command('搜图')
@reply_command('picsearch')
@reply_command('search')
async def 快捷搜图_cmd(event, img_url: str, bot: Bot):
    await bot.send(event=event, message="正在搜索……")
    resultDict = await getSearchResult(img_url)
    if not resultDict or not resultDict["info"]:
        return '没有搜索到结果^ ^'

    return ReplyCommandResult(message=imgLocalPathToBase64(os.path.join(CACHE_DIR, 'picsearch.jpg')), stored_id={'info': resultDict['info']})


async def getSearchResult(imgUrl):
    try:
        async with httpx.AsyncClient() as client:
            search = ImgExploration(pic_url=imgUrl, client=client, proxies=proxy, header=generalHeader)
            await search.doSearch()
        return search.getResultDict()
    except Exception as e:
        traceback.print_exc()
        return None


def drawTextToImage(text: str):
    splitText = text.split('\n')
    fontSize, splitSize = 20, 15
    width = max([len(i) for i in splitText]) * int(fontSize * 0.6) + 50
    height = len(splitText) * fontSize + (len(splitText) - 1) * splitSize + 50

    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(os.path.join(fontPath, 'HarmonyOS_Sans_SC_Regular.ttf'), fontSize)
    except:
        font = ImageFont.load_default()
    for i, line in enumerate(splitText):
        y = 25 + i * fontSize + i * splitSize
        draw.text((25, y), line, font=font, fill=(0, 0, 0))

    img.save(os.path.join(CACHE_DIR, "picsearchUrl.jpg"), format="JPEG", quality=95)
    return imgLocalPathToBase64(os.path.join(CACHE_DIR, "picsearchUrl.jpg"))


class ImgExploration:
    def __init__(self, pic_url, client: httpx.AsyncClient, proxies, header):
        self.__result_info = None
        self.__picNinfo = None
        self.client = client
        self.__proxy = proxies
        self.__pic_url = pic_url
        self.__generalHeader = header
        self.setFont(big_size=25, normal_size=20, small_size=15)

    def setFont(self, big_size: int, normal_size: int, small_size: int):
        self.__font_b_size = big_size
        try:
            self.__font_b = ImageFont.truetype(os.path.join(fontPath, 'HarmonyOS_Sans_SC_Regular.ttf'), big_size)
            self.__font_n = ImageFont.truetype(os.path.join(fontPath, 'HarmonyOS_Sans_SC_Bold.ttf'), normal_size)
            self.__font_s = ImageFont.truetype(os.path.join(fontPath, 'HarmonyOS_Sans_SC_Light.ttf'), small_size)
        except:
            self.__font_b = ImageFont.load_default()
            self.__font_n = ImageFont.load_default()
            self.__font_s = ImageFont.load_default()

    @staticmethod
    async def ImageBatchDownload(urls: list, client: httpx.AsyncClient) -> list:
        if not urls:
            return []
        tasks = [asyncio.create_task(client.get(url)) for url in urls]
        return [(await task).content for task in tasks]

    async def __draw(self) -> bytes:
        try:
            font_size = self.__font_b_size
            font = self.__font_b
            font2 = self.__font_n
            font3 = self.__font_s
            num = len(self.__result_info)
            width = 900
            height = 200
            total_height = height * num if num != 0 else 10
            line_width = 2
            line_fill = (200, 200, 200)
            text_x = 300
            img = Image.new(mode="RGB", size=(width, total_height + 75), color=(255, 255, 255))

            draw = ImageDraw.Draw(img)
            margin = 20
            for i in range(1, num):
                draw.line(
                    (margin, i * height, width - margin, i * height),
                    fill=line_fill,
                    width=line_width,
                )

            vernier = 0
            seat = 0

            for single in self.__result_info:
                seat += 1

                if "thumbnail_bytes" in single:
                    thumbnail = single["thumbnail_bytes"]
                    try:
                        thumbnail = Image.open(fp=BytesIO(thumbnail)).convert("RGB")
                    except PIL.UnidentifiedImageError:
                        thumbnail = Image.new(mode="RGB", size=(200, 200), color=(255, 255, 255))

                    thumbnail = thumbnail.resize(
                        (int((height - 2 * margin) * thumbnail.width / thumbnail.height), height - 2 * margin))
                    if single["source"] == "ascii2d":
                        thumbnail = thumbnail.filter(ImageFilter.GaussianBlur(radius=3))

                    if thumbnail.width > text_x - 2 * margin:
                        thumbnail = thumbnail.crop((0, 0, text_x - 2 * margin, thumbnail.height))
                        img.paste(im=thumbnail, box=(margin, vernier + margin))
                    else:
                        img.paste(im=thumbnail, box=(text_x - thumbnail.width - margin, vernier + margin))

                text_ver = 2 * margin
                draw.text(
                    xy=(width - margin, vernier + 10),
                    text=f"NO.{seat} from {single['source']}",
                    fill=(150, 150, 150),
                    font=font2,
                    anchor="ra",
                )

                if single["title"]:
                    text = single["title"].replace("\n", "")
                    draw.text(xy=(text_x, vernier + text_ver), text="Title: ", fill=(160, 160, 160), font=font,
                              anchor="la")
                    draw.text(xy=(text_x + 60, vernier + text_ver),
                              text=f"{text[:20]}{'...' if len(text) >= 20 else ''}", fill=(0, 0, 0), font=font,
                              anchor="la")
                    text_ver = text_ver + font_size + margin / 2

                if ("similarity" in single) and single["similarity"]:
                    text = single["similarity"]
                    draw.text(xy=(text_x, vernier + text_ver), text="similarity: ", fill=(160, 160, 160), font=font,
                              anchor="la")
                    draw.text(xy=(text_x + 115, vernier + text_ver), text=f"{text}", fill=(0, 0, 0), font=font,
                              anchor="la")
                    text_ver = text_ver + font_size + margin / 2

                if ("description" in single) and single["description"]:
                    text = single["description"]
                    draw.text(xy=(text_x, vernier + text_ver), text=f"{text[:30]}{'...' if len(text) >= 30 else ''}",
                              fill=(0, 0, 0), font=font, anchor="la")
                    text_ver = text_ver + font_size + margin / 2

                if ("episode" in single) and single["episode"]:
                    text = single["episode"]
                    draw.text(xy=(text_x, vernier + text_ver), text=f"Episode: {text}",
                              fill=(0, 0, 0), font=font, anchor="la")
                    text_ver = text_ver + font_size + margin / 2

                if single["url"]:
                    url = single["url"]
                    draw.text(xy=(text_x, vernier + text_ver), text=f"{url[:80]}{'......' if len(url) >= 80 else ''}",
                              fill=(100, 100, 100), font=font3, anchor="la")
                vernier += height

            bottom_text = "若需要提取url，请回复此消息，在回复中输入[图片编号] ，如：1 2"
            draw.text(xy=(width // 2, total_height + 25), text=bottom_text,
                      fill=(0, 0, 0), font=font, anchor="mm",
                      )

            save = BytesIO()
            img.save(os.path.join(CACHE_DIR, "picsearch.jpg"), format="JPEG", quality=95)
            return save.getvalue()
        except Exception as e:
            traceback.print_exc()
            raise e

    async def __saucenao_build_result(self, result_num=5, minSim=50) -> list:
        resList = []
        try:
            async with Network(proxies=self.__proxy, timeout=100) as client:
                saucenao = SauceNAO(client=client, api_key=saucenaoApiKey, numres=result_num)
                saucenao_result = await saucenao.search(url=self.__pic_url)

                for single in saucenao_result.raw:
                    if single.similarity < minSim:
                        continue
                    if not single.url or not single.thumbnail:
                        continue

                    resList.append({
                        "title": single.title,
                        "thumbnail": single.thumbnail,
                        "url": urllib.parse.unquote(single.url),
                        "similarity": single.similarity,
                        "source": "SauceNAO",
                    })

                if resList:
                    thumbnail_urls = [r["thumbnail"] for r in resList]
                    thumbnail_bytes = await self.ImageBatchDownload(thumbnail_urls, self.client)
                    for i, r in enumerate(resList):
                        r["thumbnail_bytes"] = thumbnail_bytes[i]

        except Exception as e:
            print(f"saucenao error: {e}")
            traceback.print_exc()
        finally:
            print(f"saucenao result:{len(resList)}")
        return resList

    async def __bing_build_result(self, result_num=3) -> list:
        resList = []
        try:
            async with Network(proxies=self.__proxy, timeout=60) as client:
                bing = Bing(client=client)
                bing_result = await bing.search(url=self.__pic_url)

                for i, single in enumerate(bing_result.raw[:result_num]):
                    if not single.url or not single.thumbnail:
                        continue

                    resList.append({
                        "title": single.title or "",
                        "thumbnail": single.thumbnail,
                        "url": urllib.parse.unquote(single.url),
                        "source": "Bing",
                    })

                if resList:
                    thumbnail_urls = [r["thumbnail"] for r in resList]
                    thumbnail_bytes = await self.ImageBatchDownload(thumbnail_urls, self.client)
                    for i, r in enumerate(resList):
                        r["thumbnail_bytes"] = thumbnail_bytes[i]

        except Exception as e:
            print(f"bing error: {e}")
            traceback.print_exc()
        finally:
            print(f"bing result:{len(resList)}")
        return resList

    def __ascii2d_get_external_url(self, rawHtml):
        rawHtml = str(rawHtml)
        external_url_li = etree.HTML(rawHtml).xpath('//div[@class="external"]/a[1]/@href')
        if external_url_li:
            return external_url_li[0]
        return None

    async def __ascii2d_build_result(self, sh_num: int = 1, tz_num: int = 1) -> list:
        result_li = []
        try:
            async with Network(proxies=self.__proxy, timeout=100) as client:
                ascii2d_sh = Ascii2D(client=client, bovw=False)
                ascii2d_tz = Ascii2D(client=client, bovw=True)

                ascii2d_sh_result = await asyncio.create_task(ascii2d_sh.search(url=self.__pic_url))
                ascii2d_tz_result = await asyncio.create_task(ascii2d_tz.search(url=self.__pic_url))

                thumbnail_urls = []
                for single in ascii2d_tz_result.raw[0:tz_num] + ascii2d_sh_result.raw[0:sh_num]:
                    external_url_li = self.__ascii2d_get_external_url(single.origin)
                    url = single.url or external_url_li
                    if not url:
                        continue
                    sin_di = {
                        "title": single.title,
                        "thumbnail": single.thumbnail,
                        "url": urllib.parse.unquote(url),
                        "source": "Ascii2D",
                    }
                    thumbnail_urls.append(single.thumbnail)
                    result_li.append(sin_di)
                if thumbnail_urls:
                    thumbnail_bytes = await self.ImageBatchDownload(thumbnail_urls, self.client)
                    for i, single in enumerate(result_li):
                        single["thumbnail_bytes"] = thumbnail_bytes[i]
        except Exception as e:
            print(f"ascii2d: {e}")
            traceback.print_exc()
        finally:
            print(f"ascii2d result:{len(result_li)}")
        return result_li

    async def doSearch(self):
        task_saucenao = asyncio.create_task(self.__saucenao_build_result())
        task_bing = asyncio.create_task(self.__bing_build_result())
        task_ascii2d = asyncio.create_task(self.__ascii2d_build_result())

        results = await asyncio.gather(
            task_saucenao, task_bing, task_ascii2d,
            return_exceptions=True
        )

        self.__result_info = []
        for result in results:
            if isinstance(result, list):
                self.__result_info.extend(result)

        result_pic = await self.__draw()

        self.__picNinfo = {
            "pic": result_pic,
            "info": self.__result_info,
        }

    def getResultDict(self):
        return self.__picNinfo