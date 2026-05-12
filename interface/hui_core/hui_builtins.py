import random
import uuid
import base64
import hashlib
import time
from pathlib import Path
import json
import yaml
from .log import log
from typing import Any
from faker import Faker


def current_time(f: str = '%Y-%m-%d %H:%M:%S') -> str:
    """获取当前时间，默认格式 2022-12-16 22:13:00"""
    return time.strftime(f)


def timestamp(ms: bool = False) -> int:
    """获取当前时间戳
    :param ms: True 返回毫秒级，False 返回秒级
    """
    t = time.time()
    return int(t * 1000) if ms else int(t)


def rand_value(target: list):
    """从 list 结果中随机取一个值"""
    if isinstance(target, list):
        return target[random.randint(0, len(target) - 1)]
    return target


def rand_int(start: int = 0, end: int = 9999) -> int:
    """生成随机整数 ${rand_int(1, 100)}"""
    return random.randint(start, end)


def rand_str(len_start=None, len_end=None) -> str:
    """生成随机字符串
        ${rand_str()}      → 32位
        ${rand_str(3)}     → 3位
        ${rand_str(3, 10)} → 3~10位
    """
    uuid_str = str(uuid.uuid4()).replace('-', '')
    if not len_start and not len_end:
        return uuid_str
    if not len_end:
        return uuid_str[:len_start]
    return uuid_str[:random.randint(len_start, len_end)]


def to_json(obj: Any) -> str:
    """Python 对象转 JSON 字符串"""
    return json.dumps(obj, ensure_ascii=False)


def from_json(s: str) -> Any:
    """JSON 字符串转 Python 对象"""
    return json.loads(s)


# ── 加密 / 解密 ──────────────────────────────────────────────

def b64_encode(s: str) -> str:
    """Base64 编码  ${b64_encode('hello')}"""
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')


def b64_decode(s: str) -> str:
    """Base64 解码  ${b64_decode('aGVsbG8=')}"""
    return base64.b64decode(s.encode('utf-8')).decode('utf-8')


def md5(s: str) -> str:
    """MD5 摘要  ${md5('hello')}"""
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def sha256(s: str) -> str:
    """SHA-256 摘要  ${sha256('hello')}"""
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def encrypt(s: str, method: str = 'base64') -> str:
    """统一加密入口
    :param s: 待加密字符串
    :param method: base64 | md5 | sha256
    """
    method = method.lower()
    if method == 'base64':
        return b64_encode(s)
    elif method == 'md5':
        return md5(s)
    elif method == 'sha256':
        return sha256(s)
    log.error(f"encrypt: 不支持的加密方式 {method}，支持 base64/md5/sha256")
    return s


def decrypt(s: str, method: str = 'base64') -> str:
    """统一解密入口（目前仅 base64 可逆）
    :param s: 待解密字符串
    :param method: base64
    """
    method = method.lower()
    if method == 'base64':
        return b64_decode(s)
    log.error(f"decrypt: 不支持的解密方式 {method}，仅支持 base64")
    return s


# ── Faker 数据生成 ────────────────────────────────────────────

fake = Faker(locale="zh_CN")


# ── 文件参数化 ────────────────────────────────────────────────

def p(file_path: str, title: bool = True) -> list:
    """读取 json / yaml / txt / csv 文件，用于参数化
    :param file_path: 文件路径（相对项目根目录或绝对路径）
    :param title: csv/txt 第一行是否为列名
    :return: list
    """
    f = Path(file_path)
    res = []
    if not f.exists():
        from . import g
        if g.get('root_path'):
            f = g.get('root_path').joinpath(file_path)
            if not f.exists():
                log.error(f"文件路径不存在: {f.absolute()}")
                return res
        else:
            log.error(f"文件路径不存在: {f.absolute()}")
            return res
    log.info(f"读取文件路径: {f.absolute()}")
    if f.suffix == '.json':
        res = json.loads(f.read_text(encoding='utf8'))
    elif f.suffix in ['.yml', '.yaml']:
        res = yaml.safe_load(f.read_text(encoding='utf8'))
    elif f.suffix in ['.txt', '.csv']:
        with f.open(mode='r', encoding="utf-8") as fp:
            if title:
                first_list = fp.readline().rstrip('\n').split(',')
                for item in fp:
                    item_list = item.rstrip('\n').split(',')
                    res.append({k: v for k, v in zip(first_list, item_list)})
            else:
                for item in fp:
                    res.append(item.rstrip('\n').split(','))
    else:
        log.error("parameters 文件仅支持 .txt .csv .yml .yaml .json")
    return res


def P(file_path: str, title: bool = True) -> list:
    """p() 的大写别名，兼容旧写法"""
    return p(file_path, title)
