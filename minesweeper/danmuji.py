import asyncio
import zlib
import json
import requests
from aiowebsocket.converses import AioWebSocket
import re
import threading


class Danmuji:
    def __init__(self, room_id):
        # get full roomID
        self.room_id = room_id
        if len(self.room_id) <= 3:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 \
(KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE'}
            html = requests.get('https://live.bilibili.com/' + self.room_id, headers=headers).text
            for line in html.split('\n'):
                if '"roomid":' in line:
                    self.room_id = line.split('"roomid":')[1].split(',')[0]
        
        # data
        self.danmu_list = []     # [(name1, pos1, op1), (name2, pos2, op2), ...]
        
        # thread lock
        self.lock = threading.Lock()

    def get_danmu_list(self):
        self.lock.acquire()
        danmu_list = self.danmu_list.copy()
        self.danmu_list.clear()
        self.lock.release()
        return danmu_list

    async def startup(self):
        url = r'wss://broadcastlv.chat.bilibili.com:2245/sub'
        data_raw = '000000{headerLen}0010000100000007000000017b22726f6f6d6964223a{roomid}7d'
        data_raw = data_raw.format(headerLen=hex(27 + len(self.room_id))[2:],
                                   roomid=''.join(map(lambda x: hex(ord(x))[2:], list(self.room_id))))
        async with AioWebSocket(url) as aws:
            converse = aws.manipulator
            await converse.send(bytes.fromhex(data_raw))
            tasks = [self.recv_danmu(converse), self.send_heartbeat(converse)]
            await asyncio.wait(tasks)

    @staticmethod
    async def send_heartbeat(websocket):
        hb = '00000010001000010000000200000001'
        while True:
            await asyncio.sleep(30)
            await websocket.send(bytes.fromhex(hb))

    async def recv_danmu(self, websocket):
        while True:
            recv_text = await websocket.receive()
            self.decode_danmu(recv_text)

    def decode_danmu(self, data):
        packet_len = int(data[:4].hex(), 16)
        ver = int(data[6:8].hex(), 16)
        op = int(data[8:12].hex(), 16)

        if len(data) > packet_len:
            self.decode_danmu(data[packet_len:])
            data = data[:packet_len]

        if ver == 2:
            data = zlib.decompress(data[16:])
            self.decode_danmu(data)
            return

        if ver == 1:
            if op == 3:
                # print('[RENQI]  {}'.format(int(data[16:].hex(),16)))
                pass
            return

        if op == 5:
            try:
                jd = json.loads(data[16:].decode('utf-8', errors='ignore'))
                if jd['cmd'] == 'SEND_GIFT':
                    d = jd['data']
                    gift_info = (d['uname'], d['num'], d['giftName'])
                    print(gift_info)
                    if gift_info[2] == "吃瓜":
                        self.lock.acquire()
                        self.danmu_list.append((gift_info[0], "gift", ""))
                        self.lock.release()
                # elif jd['cmd'] == 'COMBO_SEND':
                #     d = jd['data']
                #     gift_info = (d['uname'], d['batch_combo_num'], d['gift_name'])
                #     print(gift_info)
                #     self.lock.acquire()
                #     self.danmu_list.append((gift_info[0], "gift", ""))
                #     self.lock.release()
                elif jd['cmd'] == 'GUARD_BUY':
                    d = jd['data']
                    gift_info = (d['username'], '1', 'captain')
                    print(gift_info)
                    self.lock.acquire()
                    self.danmu_list.append((gift_info[0], "gift", ""))
                    self.lock.release()
                elif jd['cmd'] == 'DANMU_MSG':
                    info = jd['info'][2][1], jd['info'][1]
                    print(info)
                    m = re.match("(!?!?|！?！?)([a-z]|[A-Z])(\d\d|\d)", info[1])
                    if m is not None:
                        self.lock.acquire()
                        if m.group(1) == "!" or m.group(1) == "！":
                            self.danmu_list.append((info[0], "check",
                                                    (ord(m.group(2).lower()) - ord('a'), int(m.group(3)))))
                        elif m.group(1) == "!!" or m.group(1) == "！！":
                            self.danmu_list.append((info[0], "uncheck",
                                                    (ord(m.group(2).lower()) - ord('a'), int(m.group(3)))))
                        else:
                            self.danmu_list.append((info[0], "open",
                                                    (ord(m.group(2).lower()) - ord('a'), int(m.group(3)))))
                        self.lock.release()
                        print('decode:', m.group())
                    else:
                        m = re.match("(!?!?|！?！?)(\d\d|\d)([a-z]|[A-Z])", info[1])
                        if m is not None:
                            self.lock.acquire()
                            if m.group(1) == "!" or m.group(1) == "！":
                                self.danmu_list.append((info[0], "check",
                                                        (ord(m.group(3).lower()) - ord('a'), int(m.group(2)))))
                            elif m.group(1) == "!!" or m.group(1) == "！！":
                                self.danmu_list.append((info[0], "uncheck",
                                                        (ord(m.group(3).lower()) - ord('a'), int(m.group(2)))))
                            else:
                                self.danmu_list.append((info[0], "open",
                                                        (ord(m.group(3).lower()) - ord('a'), int(m.group(2)))))
                            self.lock.release()
                            print('decode:', m.group())
                        else:
                            m = re.match("(easy|normal|EASY|NORMAL)", info[1])
                            if m is not None:
                                self.lock.acquire()
                                self.danmu_list.append((info[0], "difficulty", m.group(1).upper()))
                                print("decode", m.group())
                                self.lock.release()
            except Exception as e:
                print(e)
    
    @staticmethod
    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()
    
    def run(self):
        loop = asyncio.new_event_loop()
        t = threading.Thread(target=self.start_loop, args=(loop,))
        t.setDaemon(True)
        t.start()
        asyncio.run_coroutine_threadsafe(self.startup(), loop)
