#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io>"
__version__ = (0, 0, 1)

KEYS = (
    "id", "parent_id", "name", "path", "sha1", "pick_code", "is_directory", 
    "size", "ctime", "mtime", "atime", "thumb", "star", 
)

from argparse import ArgumentParser, RawTextHelpFormatter

parser = ArgumentParser(description="115 文件夹信息遍历导出", formatter_class=RawTextHelpFormatter)
parser.add_argument("path", nargs="?", default="0", help="文件夹路径或 id，默认值 0，即根目录")
parser.add_argument("-c", "--cookie", help="115 登录 cookie，如果缺失，则从 115-cookie.txt 文件中获取，此文件可以在 当前工作目录、此脚本所在目录 或 用户根目录 下")
parser.add_argument("-k", "--keys", nargs="*", choices=KEYS, help=f"选择输出的 key，默认输出所有可选值")
parser.add_argument("-t", "--output-type", choices=("log", "json", "csv"), default="log", help="""输出类型，默认为 json
- log   每行输出一条数据，每条数据输出为一个 json 的 object
- json  输出一个 json 的 list，每条数据输出为一个 json 的 object
- csv   输出一个 csv，第 1 行为表头，以后每行输出一条数据
""")
parser.add_argument("-o", "--output-file", help="保存到文件，此时命令行会输出进度条")
args = parser.parse_args()

try:
    from p115 import P115FileSystem
except ImportError:
    from subprocess import run
    from sys import executable
    run([executable, "-m", "pip", "install", "python-115"], check=True)
    from p115 import P115FileSystem

from os.path import expanduser, dirname, join as joinpath


cookie = args.cookie
if not cookie:
    for dir_ in (".", expanduser("~"), dirname(__file__)):
        try:
            cookie = open(joinpath(dir_, "115-cookie.txt")).read()
            if cookie:
                break
        except FileNotFoundError:
            pass

fs = P115FileSystem.login(cookie)
if fs.client.cookie != cookie:
    open("115-cookie.txt", "w").write(fs.client.cookie)

keys = args.keys or KEYS
output_type = args.output_type

path = args.path
if path.isdecimal():
    fid = int(path)
else:
    attr = fs.attr(path)
    fid = attr["id"]

path_it = fs.iter(fid, max_depth=-1)

output_file = args.output_file
if output_file:
    try:
        from tqdm import tqdm
    except ImportError:
        run([executable, "-m", "pip", "install", "tqdm"], check=True)
        from tqdm import tqdm
    file = open(output_file, "w")
    path_it = tqdm(path_it)
else:
    from sys import stdout as file

try:
    if output_type == "json":
        from json import dumps
        write = file.buffer.write
        write(b"[")
        for i, p in enumerate(path_it):
            if i:
                write(b", ")
            record = {k: p[k] for k in keys}
            write(bytes(dumps(record, ensure_ascii=False), "utf-8"))
        write(b"]")
    elif output_type == "log":
        from json import dumps
        write = file.buffer.write
        flush = file.buffer.flush
        for p in path_it:
            record = {k: p[k] for k in keys}
            write(bytes(dumps(record, ensure_ascii=False), "utf-8"))
            write(b"\n")
            flush()
    else:
        from csv import DictWriter
        writer = DictWriter(file, fieldnames=keys)
        writer.writeheader()
        for p in path_it:
            writer.writerow({k: p[k] for k in keys})
except KeyboardInterrupt:
    pass
except BrokenPipeError:
    from sys import stderr
    stderr.close()
finally:
    file.close()

