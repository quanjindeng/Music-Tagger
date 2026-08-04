import os
import re
import time
import requests
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, USLT, TIT2, TPE1, ID3NoHeaderError
from mutagen.flac import FLAC, Picture

# ================= 1. 文本清洗与过滤模块 =================

def sanitize_filename(name):
    """清除 Windows 文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def remove_track_number(filename_no_ext):
    """移除文件名开头的轨号/序号前缀 (如 '01. ', '01 - ', 'A1_', '1-01 ')"""
    pattern = r'^\s*(\d{1,3}[\.\-_ \t]|track\d{1,3}[\.\-_ \t]|\d{1,2}-\d{1,2}[\.\-_ \t])\s*'
    return re.sub(pattern, '', filename_no_ext, flags=re.IGNORECASE)

def clean_metadata_text(text):
    """
    清洗提取出的艺术家或歌曲名文本：
    1. 移除半角/全角圆括号、方括号、花括号、角括号及其内部的所有内容
    2. 移除常见质量/版本噪音词
    3. 清理多余空格与末尾符号
    """
    if not text:
        return text

    # 1. 匹配并移除各种括号及内容: (), （）, [], 【】, {}, 「」, 『』
    brackets_pattern = r'[\(\（\[\【\{\「\『].*?[\)\）\]\】\}\」\』]'
    text = re.sub(brackets_pattern, '', text)

    # 2. 移除常见的单字质量/格式噪音词 (不区分大小写)
    noise_keywords = [
        r'\b320k\b', r'\bflac\b', r'\bmp3\b', r'\blossless\b', 
        r'\bhi-res\b', r'\b24bit\b', r'\b16bit\b', r'\bmv\b', 
        r'\bofficial\b', r'\bvideo\b', r'\bremastered?\b', r'\bhd\b'
    ]
    for kw in noise_keywords:
        text = re.sub(kw, '', text, flags=re.IGNORECASE)

    # 3. 规范化空格，清除首尾残留的符号
    text = re.sub(r'\s+', ' ', text)
    text = text.strip(" -_.\t")
    
    return text


# ================= 2. 网络请求模块 =================

def fetch_cover_itunes(artist, title):
    url = "https://itunes.apple.com/search"
    params = {"term": f"{artist} {title}", "entity": "song", "limit": 1}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('resultCount', 0) > 0:
            artwork_url = data['results'][0]['artworkUrl100'].replace('100x100bb', '1000x1000bb')
            img_response = requests.get(artwork_url, timeout=10)
            img_response.raise_for_status()
            return img_response.content
    except Exception as e:
        print(f"      [网络] 获取封面失败: {e}")
    return None

def fetch_lyrics_lrclib(artist, title):
    url = "https://lrclib.net/api/get"
    params = {"artist_name": artist, "track_name": title}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('syncedLyrics') or data.get('plainLyrics')
    except Exception as e:
        print(f"      [网络] 获取歌词失败: {e}")
    return None


# ================= 3. 标签写入模块 =================

def embed_mp3_tags(filepath, artist, title, cover_data, lyrics_text, clear_tags):
    if clear_tags:
        try:
            audio = MP3(filepath)
            audio.delete()
            audio.save()
        except Exception:
            pass

    try:
        audio = MP3(filepath, ID3=ID3)
    except ID3NoHeaderError:
        audio = mutagen.File(filepath, options=[ID3])

    if getattr(audio, 'tags', None) is None:
        audio.add_tags()

    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=artist))

    if cover_data:
        audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data))
    if lyrics_text:
        audio.tags.add(USLT(encoding=3, lang='XXX', desc='', text=lyrics_text))

    audio.save()

def embed_flac_tags(filepath, artist, title, cover_data, lyrics_text, clear_tags):
    audio = FLAC(filepath)
    if clear_tags:
        audio.delete()
        audio.save()
        audio = FLAC(filepath)

    audio['title'] = title
    audio['artist'] = artist

    if cover_data:
        pic = Picture()
        pic.type = 3
        pic.mime = "image/jpeg"
        pic.desc = "Cover"
        pic.data = cover_data
        audio.add_picture(pic)

    if lyrics_text:
        audio['LYRICS'] = lyrics_text

    audio.save()

def update_basic_tags(filepath, artist, title, clear_tags):
    if clear_tags:
        try:
            audio = mutagen.File(filepath)
            if audio:
                audio.delete()
                audio.save()
        except Exception:
            pass

    audio = mutagen.File(filepath, easy=True)
    if getattr(audio, 'tags', None) is None:
        try:
            audio.add_tags()
        except Exception:
            pass

    try:
        audio['title'] = [title]
        audio['artist'] = [artist]
    except KeyError:
        audio['Title'] = title
        audio['Artist'] = artist
    audio.save()


# ================= 4. 主控制逻辑 =================

def process_single_file(filepath, filename, raw_artist, raw_title, config):
    # 过滤与清洗处理
    if config['clean_noise']:
        artist = clean_metadata_text(raw_artist)
        title = clean_metadata_text(raw_title)
    else:
        artist = raw_artist.strip()
        title = raw_title.strip()

    print(f"\n正在处理: {filename}")
    print(f"  -> 原始解析: 艺术家[{raw_artist}] | 歌曲[{raw_title}]")
    if config['clean_noise'] and (artist != raw_artist or title != raw_title):
        print(f"  -> 提纯去噪: 艺术家[{artist}] | 歌曲[{title}]")

    directory = os.path.dirname(filepath)
    ext = os.path.splitext(filename)[1].lower()

    # 重命名逻辑
    if config['rename_files']:
        safe_artist = sanitize_filename(artist)
        safe_title = sanitize_filename(title)
        new_filename = f"{safe_artist} - {safe_title}{ext}"

        if new_filename != filename:
            new_filepath = os.path.join(directory, new_filename)
            if config['dry_run']:
                print(f"  -> [预览改名] {filename} => {new_filename}")
            else:
                try:
                    if os.path.exists(new_filepath) and filepath.lower() != new_filepath.lower():
                        new_filename = f"{safe_artist} - {safe_title}_1{ext}"
                        new_filepath = os.path.join(directory, new_filename)

                    os.rename(filepath, new_filepath)
                    filepath = new_filepath
                    filename = new_filename
                    print(f"  -> [改名成功] => {new_filename}")
                except Exception as e:
                    print(f"  -> [改名失败] {e}")

    if config['dry_run']:
        if config['clear_tags']: print("  -> [预览] 旧有标签字段将被彻底清除")
        if config['use_network']: print("  -> [预览] 将使用提纯后的名称请求封面与歌词")
        return True

    # 网络匹配与写入
    cover_data, lyrics_text = None, None
    if config['use_network'] and ext in ['.mp3', '.flac']:
        print("  -> 正在联网匹配封面与歌词...")
        cover_data = fetch_cover_itunes(artist, title)
        lyrics_text = fetch_lyrics_lrclib(artist, title)
        print(f"  -> 资源状态: 封面 [{'成功' if cover_data else '未找到'}] | 歌词 [{'成功' if lyrics_text else '未找到'}]")
        time.sleep(1.2)

    try:
        if ext == '.mp3':
            embed_mp3_tags(filepath, artist, title, cover_data, lyrics_text, config['clear_tags'])
        elif ext == '.flac':
            embed_flac_tags(filepath, artist, title, cover_data, lyrics_text, config['clear_tags'])
        else:
            update_basic_tags(filepath, artist, title, config['clear_tags'])
        print("  -> [完成] 标签已更新。")
        return True
    except Exception as e:
        print(f"  -> [失败] 写入出错: {e}")
        return False


# ================= 5. 交互菜单 =================

def main():
    print("="*55)
    print("      🎶 音乐标签自动处理工具 Ultimate 🎶")
    print("="*55)

    config = {
        'directory': '',
        'regex': None,
        'clean_noise': True,
        'rename_files': False,
        'clear_tags': False,
        'use_network': True,
        'dry_run': True
    }

    # 1. 路径输入
    while True:
        directory = input("\n[1] 请输入音乐文件夹绝对路径 (输入 . 表示当前目录): ").strip()
        config['directory'] = os.getcwd() if directory == "." else directory
        if os.path.isdir(config['directory']): break
        print("错误：目录不存在！")

    # 2. 匹配规则
    print("\n[2] 匹配规则:")
    print("  1. 智能标准模式 (兼容: 艺术家-歌曲名, 艺术家 _ 歌曲名 等)")
    print("  2. 自定义正则表达式")
    if input("请选择 (默认 1): ").strip() == '2':
        custom = input("请输入正则(必须含 (?P<artist>...) 和 (?P<title>...)):\n> ").strip()
        config['regex'] = re.compile(custom)
    else:
        config['regex'] = re.compile(r"^\s*(?P<artist>.+?)\s*[-_]\s*(?P<title>.+?)\s*$")

    # 3. 智能噪声过滤（括号、轨号、无损标签等）
    print("\n[3] 智能去噪清洗 (推荐开启):")
    print("是否自动滤除括号内容 ()/（）/[]/【】、轨号前缀(如 01.) 及 320k/FLAC 等无用标记？")
    config['clean_noise'] = True if input("(Y/n 默认 Y): ").strip().lower() != 'n' else False

    # 4. 规范重命名
    print("\n[4] 文件规范重命名:")
    print("是否将文件重命名为清洗后的纯净标准格式 '艺术家 - 歌曲名.后缀'？")
    config['rename_files'] = True if input("(Y/n 默认 Y): ").strip().lower() != 'n' else False

    # 5. 清除旧标签
    print("\n[5] 彻底抹除旧标签 (解决乱码):")
    print("是否在写入前彻底清除原有标签（强烈建议开启以防乱码残留）？")
    config['clear_tags'] = True if input("(Y/n 默认 Y): ").strip().lower() != 'n' else False

    # 6. 网络功能
    print("\n[6] 联网获取封面与歌词:")
    config['use_network'] = False if input("(Y/n 默认 Y): ").strip().lower() == 'n' else True

    # 7. 试运行模式
    print("\n[7] 试运行模式 (Dry Run):")
    print("是否开启试运行？(仅打印预览，不改名不写入文件)")
    config['dry_run'] = False if input("(Y/n 默认 Y): ").strip().lower() == 'n' else True

    # 总结与确认
    print("\n" + "="*55)
    print("运行配置确认：")
    print(f"工作目录: {config['directory']}")
    print(f"去噪清洗: {'开启' if config['clean_noise'] else '关闭'}")
    print(f"规范改名: {'开启' if config['rename_files'] else '关闭'}")
    print(f"抹除旧签: {'开启 (防乱码)' if config['clear_tags'] else '关闭'}")
    print(f"网络功能: {'开启' if config['use_network'] else '关闭'}")
    print(f"执行模式: {'【试运行预览】' if config['dry_run'] else '【!! 正式修改 !!】'}")
    print("="*55)
    input("按回车键开始执行...")

    success, fail, skip = 0, 0, 0
    supported_exts = {'.mp3', '.flac', '.ape', '.ogg', '.m4a', '.wav'}

    for filename in os.listdir(config['directory']):
        filepath = os.path.join(config['directory'], filename)
        if not os.path.isfile(filepath): continue

        name_without_ext, ext = os.path.splitext(filename)
        if ext.lower() not in supported_exts: continue

        # 匹配前先剥离开头的轨号前缀，避免轨号影响正则切割
        clean_filename_for_match = remove_track_number(name_without_ext)

        match = config['regex'].match(clean_filename_for_match)
        if match:
            try:
                raw_artist = match.group('artist')
                raw_title = match.group('title')
            except IndexError:
                print(f"[跳过] {filename} (正则解析分组错误)")
                skip += 1
                continue

            is_success = process_single_file(filepath, filename, raw_artist, raw_title, config)
            if is_success: success += 1
            else: fail += 1
        else:
            print(f"\n[跳过] {filename} (无法从文件名提取歌手和歌曲名)")
            skip += 1

    print("\n" + "="*55)
    mode_text = "【试运行预览结束】" if config['dry_run'] else "【全部处理完成】"
    print(f"{mode_text} 成功: {success} | 失败: {fail} | 跳过: {skip}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户取消操作。")
