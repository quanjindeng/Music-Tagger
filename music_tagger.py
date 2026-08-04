import os
import re
import time
import requests
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, USLT, TIT2, TPE1, ID3NoHeaderError
from mutagen.flac import FLAC, Picture

# ================= 1. 辅助工具模块 =================

def sanitize_filename(name):
    """清除 Windows 文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

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
    # 如果选择清除标签，先抹除所有现有标签
    if clear_tags:
        try:
            audio = MP3(filepath)
            audio.delete()
            audio.save()
        except Exception:
            pass # 可能本来就没有标签
            
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
    # 擦除 FLAC 所有的 Vorbis Comments 和图片
    if clear_tags:
        audio.delete()
        audio.save()
        audio = FLAC(filepath) # 重新加载干净的文件

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
    """用于 MP3/FLAC 之外的格式的基础写入"""
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
        except:
            pass
            
    try:
        audio['title'] = [title]
        audio['artist'] = [artist]
    except KeyError:
        audio['Title'] = title
        audio['Artist'] = artist
    audio.save()

# ================= 4. 主控制逻辑 =================

def process_single_file(filepath, filename, artist, title, config):
    print(f"\n正在处理: {filename}")
    print(f"  -> 解析信息: 艺术家[{artist}] | 歌曲[{title}]")
    
    # --- 1. 文件重命名阶段 ---
    directory = os.path.dirname(filepath)
    ext = os.path.splitext(filename)[1].lower()
    
    if config['rename_files']:
        safe_artist = sanitize_filename(artist)
        safe_title = sanitize_filename(title)
        new_filename = f"{safe_artist} - {safe_title}{ext}"
        
        if new_filename != filename:
            new_filepath = os.path.join(directory, new_filename)
            if config['dry_run']:
                print(f"  -> [预览重命名] {filename} 将被改名为 => {new_filename}")
            else:
                try:
                    # 如果目标文件名已存在，防冲突处理
                    if os.path.exists(new_filepath) and filepath.lower() != new_filepath.lower():
                        new_filename = f"{safe_artist} - {safe_title}_1{ext}"
                        new_filepath = os.path.join(directory, new_filename)
                        
                    os.rename(filepath, new_filepath)
                    filepath = new_filepath
                    filename = new_filename
                    print(f"  -> [重命名成功] => {new_filename}")
                except Exception as e:
                    print(f"  -> [重命名失败] {e}")

    # 试运行模式拦截实际写入
    if config['dry_run']:
        if config['clear_tags']: print("  -> [预览] 原有所有标签将被抹除")
        if config['use_network']: print("  -> [预览] 将连接网络获取封面和歌词并嵌入")
        return True

    # --- 2. 网络请求与写入阶段 ---
    cover_data, lyrics_text = None, None
    if config['use_network'] and ext in ['.mp3', '.flac']:
        print("  -> 正在联网匹配封面与歌词...")
        cover_data = fetch_cover_itunes(artist, title)
        lyrics_text = fetch_lyrics_lrclib(artist, title)
        print(f"  -> 资源状态: 封面 [{'成功' if cover_data else '未找到'}] | 歌词 [{'成功' if lyrics_text else '未找到'}]")
        time.sleep(1.5) # API 速率控制

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

# ================= 5. 交互式菜单 =================

def main():
    print("="*55)
    print("      🎶 音乐标签自动处理工具 Pro Max 🎶")
    print("="*55)

    # 配置字典
    config = {
        'directory': '',
        'regex': None,
        'rename_files': False,
        'clear_tags': False,
        'use_network': True,
        'dry_run': True
    }

    # 1. 输入路径
    while True:
        directory = input("\n[1] 请输入音乐文件夹绝对路径 (输入 . 表示当前目录): ").strip()
        config['directory'] = os.getcwd() if directory == "." else directory
        if os.path.isdir(config['directory']): break
        print("错误：目录不存在！")

    # 2. 匹配规则 (优化了默认匹配，支持短横线和下划线，忽略空格)
    print("\n[2] 请选择文件名匹配规则:")
    print("  1. 智能标准模式 (兼容: 艺术家-歌曲名, 艺术家 - 歌曲名, 艺术家_歌曲名)")
    print("  2. 自定义正则表达式")
    if input("请选择 (默认 1): ").strip() == '2':
        custom = input("请输入正则(必须含 (?P<artist>...) 和 (?P<title>...)):\n> ").strip()
        config['regex'] = re.compile(custom)
    else:
        config['regex'] = re.compile(r"^\s*(?P<artist>.+?)\s*[-_]\s*(?P<title>.+?)\s*$")

    # 3. 重命名功能
    print("\n[3] 文件重命名功能:")
    print("如果当前文件名不标准，是否自动将文件重命名为标准的 '艺术家 - 歌曲名' 格式？")
    config['rename_files'] = True if input("(Y/n 默认 Y): ").strip().lower() != 'n' else False

    # 4. 彻底清除标签 (防乱码)
    print("\n[4] 彻底清除旧标签 (解决乱码/多余信息):")
    print("是否在写入前【彻底抹除】该文件原有的所有标签字段？（强烈建议开启以防乱码残留）")
    config['clear_tags'] = True if input("(Y/n 默认 Y): ").strip().lower() != 'n' else False

    # 5. 网络功能
    print("\n[5] 网络匹配封面与歌词:")
    config['use_network'] = False if input("(Y/n 默认 Y): ").strip().lower() == 'n' else True

    # 6. 试运行开关
    print("\n[6] 试运行模式 (Dry Run):")
    print("是否开启试运行？(仅打印分析结果，不改名也不修改文件，用于预检查！)")
    config['dry_run'] = False if input("(Y/n 默认 Y): ").strip().lower() == 'n' else True

    # 执行确认
    print("\n" + "="*55)
    print("配置清单：")
    print(f"工作目录: {config['directory']}")
    print(f"自动改名: {'是' if config['rename_files'] else '否'}")
    print(f"抹除旧签: {'是 (防乱码)' if config['clear_tags'] else '否 (追加写入)'}")
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
            
        match = config['regex'].match(name_without_ext)
        if match:
            try:
                artist = match.group('artist').strip()
                title = match.group('title').strip()
            except IndexError:
                print(f"[跳过] {filename} (正则异常)")
                skip += 1
                continue
            
            is_success = process_single_file(filepath, filename, artist, title, config)
            if is_success: success += 1
            else: fail += 1
        else:
            print(f"\n[跳过] {filename} (不符合命名结构，无法提取艺术家和歌曲名)")
            skip += 1

    print("\n" + "="*55)
    mode_text = "【试运行预览结束】" if config['dry_run'] else "【全部处理完成】"
    print(f"{mode_text} 成功: {success} | 失败: {fail} | 跳过: {skip}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已通过键盘中断操作。")
