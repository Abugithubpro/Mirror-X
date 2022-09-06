from threading import Thread
from telegram.ext import CommandHandler, CallbackQueryHandler
from time import sleep
from re import split as re_split

from bot import bot, DOWNLOAD_DIR, dispatcher, BOT_PM, LOGGER
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, auto_delete_message, auto_delete_upload_message
from bot.helper.telegram_helper import button_build
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_url
from bot.helper.mirror_utils.download_utils.yt_dlp_download_helper import YoutubeDLHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from .listener import MirrorLeechListener
from bot.helper.telegram_helper.button_build import ButtonMaker
listener_dict = {}
def _ytdl(bot, message, isZip=False, isLeech=False):
    mssg = message.text
    user_id = message.from_user.id
    msg_id = message.message_id
    multi=1
    buttons = ButtonMaker()
    if BOT_PM and message.chat.type != 'private':
        try:
            msg1 = f'Bro - Added your Requested link\n'
            send = bot.sendMessage(user_id, text=msg1)
            send.delete()
        except Exception as e:
            LOGGER.warning(e)
            bot_d = bot.get_me()
            b_uname = bot_d.username
            uname = message.from_user.mention_html(message.from_user.first_name)
            botstart = f"http://t.me/{b_uname}"
            buttons.buildbutton("Confirm", f"{botstart}")
            startwarn = f"<b>Bro {uname}, Every Leeching Files Is Encrypted Directly You ! Nobody Can Access Your Files</b>"
            mesg = sendMarkup(startwarn, bot, message, buttons.build_menu(2))
            sleep(15)
            mesg.delete()
            message.delete()
            return
    link = mssg.split()
    if len(link) > 1:
        link = link[1].strip()
        if link.strip().isdigit():
            multi = int(link)
            link = ''
        elif link.strip().startswith(("|", "pswd:", "args:")):
            link = ''
    else:
        link = ''

    name = mssg.split('|', maxsplit=1)
    if len(name) > 1:
        if 'args: ' in name[0] or 'pswd: ' in name[0]:
            name = ''
        else:
            name = name[1]
        if name != '':
            name = re_split('pswd:|args:', name)[0]
            name = name.strip()
    else:
        name = ''

    pswd = mssg.split(' pswd: ')
    if len(pswd) > 1:
        pswd = pswd[1]
        pswd = pswd.split(' args: ')[0]
    else:
        pswd = None

    args = mssg.split(' args: ')
    if len(args) > 1:
        args = args[1]
    else:
        args = None

    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)

    reply_to = message.reply_to_message
    if reply_to is not None:
        if len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)

    if not is_url(link):
        help_msg = """
<b>Send link along with command line:</b>
<code>/command</code> {link} |newname pswd: mypassword [zip] args: x:y|x1:y1

<b>By replying to link:</b>
<code>/command</code> |newname pswd: mypassword [zip] args: x:y|x1:y1

<b>Args Example:</b> args: playliststart:^10|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{"ffmpeg": ["-threads", "4"]}|wait_for_video:(5, 100)

<b>Args Note:</b> Add `^` before integer, some values must be integer and some string.
Like playlist_items:10 works with string, so no need to add `^` before the number but playlistend works only with integer so you must add `^` before the number like example above.
You can add tuple and dict also. Use double quotes inside dict. Also you can add format manually, whatever what quality button you have pressed.

Check all arguments from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L178'>FILE</a>.
                    """
        return sendMessage(help_msg, bot, message)
    listener = MirrorLeechListener(bot, message, isZip, isLeech=isLeech, pswd=pswd, tag=tag)
    buttons = button_build.ButtonMaker()
    best_video = "bv*+ba/b"
    best_audio = "ba/b"
    ydl = YoutubeDLHelper(listener)
    try:
        result = ydl.extractMetaData(link, name, args, True)
    except Exception as e:
        msg = str(e).replace('<', ' ').replace('>', ' ')
        return sendMessage(tag + " " + msg, bot, message)
    if 'entries' in result:
        for i in ['144', '240', '360', '480', '720', '1080', '1440', '2160']:
            video_format = f"bv*[height<=?{i}][ext=mp4]+ba/b[height<=?{i}]"
            buttons.sbutton(f"{i}-mp4", f"qu {msg_id} {video_format} t")
            video_format = f"bv*[height<=?{i}][ext=webm]+ba/b[height<=?{i}]"
            buttons.sbutton(f"{i}-webm", f"qu {msg_id} {video_format} t")
        buttons.sbutton("MP3", f"qu {msg_id} mp3 t")
        buttons.sbutton("⚡️Videos", f"qu {msg_id} {best_video} t")
        buttons.sbutton("⚡️Audios", f"qu {msg_id} {best_audio} t")
        buttons.sbutton("Cancel !", f"qu {msg_id} cancel")
        YTBUTTONS = buttons.build_menu(3)
        listener_dict[msg_id] = [listener, user_id, link, name, YTBUTTONS, args]
        bmsg = sendMarkup('Bro - Choose Playlist Videos Quality ', bot, message, YTBUTTONS)
    else:
        formats = result.get('formats')
        formats_dict = {}
        if formats is not None:
            for frmt in formats:
                if frmt.get('tbr'):

                    format_id = frmt['format_id']

                    if frmt.get('filesize'):
                        size = frmt['filesize']
                    elif frmt.get('filesize_approx'):
                        size = frmt['filesize_approx']
                    else:
                        size = 0

                    if frmt.get('height'):
                        height = frmt['height']
                        ext = frmt['ext']
                        fps = frmt['fps'] if frmt.get('fps') else ''
                        b_name = f"{height}p{fps}-{ext}"
                        v_format = f"bv*[format_id={format_id}]+ba/b[height={height}]"
                    elif frmt.get('video_ext') == 'none' and frmt.get('acodec') != 'none':
                        b_name = f"{frmt['acodec']}-{frmt['ext']}"
                        v_format = f"ba[format_id={format_id}]"

                    if b_name in formats_dict:
                        formats_dict[b_name][frmt['tbr']] = [size, v_format]
                    else:
                        subformat = {}
                        subformat[frmt['tbr']] = [size, v_format]
                        formats_dict[b_name] = subformat

            for b_name, d_dict in formats_dict.items():
                if len(d_dict) == 1:
                    d_data = list(d_dict.values())[0]
                    buttonName = f"{b_name} ({get_readable_file_size(d_data[0])})"
                    buttons.sbutton(buttonName, f"qu {msg_id} {d_data[1]}")
                else:
                    buttons.sbutton(b_name, f"qu {msg_id} dict {b_name}")
        buttons.sbutton("MP3", f"qu {msg_id} mp3")
        buttons.sbutton("⚡Video", f"qu {msg_id} {best_video}")
        buttons.sbutton("⚡️Audio", f"qu {msg_id} {best_audio}")
        buttons.sbutton("Cancel!", f"qu {msg_id} cancel")
        YTBUTTONS = buttons.build_menu(2)
        listener_dict[msg_id] = [listener, user_id, link, name, YTBUTTONS, args, formats_dict]
        bmsg = sendMarkup('Bro - Choose Video Quality ', bot, message, YTBUTTONS)

    Thread(target=_auto_cancel, args=(bmsg, msg_id)).start()
    Thread(target=auto_delete_upload_message, args=(bot, message, bmsg)).start()
    if multi > 1:
        sleep(4)
        nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
        nextmsg = sendMessage(mssg.replace(str(multi), str(multi - 1), 1), bot, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        sleep(4)
        Thread(target=_ytdl, args=(bot, nextmsg, isZip, isLeech)).start()

def _qual_subbuttons(task_id, b_name, msg):
    buttons = button_build.ButtonMaker()
    task_info = listener_dict[task_id]
    formats_dict = task_info[6]
    for tbr, d_data in formats_dict[b_name].items():
        buttonName = f"{tbr}K ({get_readable_file_size(d_data[0])})"
        buttons.sbutton(buttonName, f"qu {task_id} {d_data[1]}")
    buttons.sbutton("Back", f"qu {task_id} back")
    buttons.sbutton("Cancel", f"qu {task_id} cancel")
    SUBBUTTONS = buttons.build_menu(2)
    editMessage(f"Bro - Choose Bit rate for <b>{b_name}</b> ", msg, SUBBUTTONS)

def _mp3_subbuttons(task_id, msg, playlist=False):
    buttons = button_build.ButtonMaker()
    audio_qualities = [64, 128, 320]
    for q in audio_qualities:
        if playlist:
            i = 's'
            audio_format = f"ba/b-{q} t"
        else:
            i = ''
            audio_format = f"ba/b-{q}"
        buttons.sbutton(f"{q}K-mp3", f"qu {task_id} {audio_format}")
    buttons.sbutton("Back", f"qu {task_id} back")
    buttons.sbutton("Cancel", f"qu {task_id} cancel")
    SUBBUTTONS = buttons.build_menu(2)
    editMessage(f"Bro - Choose Audio{i} Bitrate ", msg, SUBBUTTONS)

def select_format(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    msg = query.message
    data = data.split(" ")
    task_id = int(data[1])
    try:
        task_info = listener_dict[task_id]
    except:
        return editMessage("Bro - Error This is an old task", msg)
    uid = task_info[1]
    if user_id != uid and not CustomFilters._owner_query(user_id):
        return query.answer(text="Error This task is not for you!", show_alert=True)
    elif data[2] == "dict":
        query.answer()
        b_name = data[3]
        _qual_subbuttons(task_id, b_name, msg)
        return
    elif data[2] == "back":
        query.answer()
        return editMessage('Bro - Choose Video Quality ', msg, task_info[4])
    elif data[2] == "mp3":
        query.answer()
        if len(data) == 4:
            playlist = True
        else:
            playlist = False
        _mp3_subbuttons(task_id, msg, playlist)
        return
    elif data[2] == "cancel":
        query.answer()
        editMessage('Task cancelled Bot Is on Rest Mode', msg)
    else:
        query.answer()
        listener = task_info[0]
        link = task_info[2]
        name = task_info[3]
        args = task_info[5]
        qual = data[2]
        if len(data) == 4:
            playlist = True
        else:
            playlist = False
        ydl = YoutubeDLHelper(listener)
        Thread(target=ydl.add_download, args=(link, f'{DOWNLOAD_DIR}{task_id}', name, qual, playlist, args)).start()
        query.message.delete()
    del listener_dict[task_id]

def _auto_cancel(msg, msg_id):
    sleep(120)
    try:
        del listener_dict[msg_id]
        editMessage('Error Timed out! Task has been cancelled', msg)
    except:
        pass

def ytdl(update, context):
    _ytdl(context.bot, update.message)

def ytdlZip(update, context):
    _ytdl(context.bot, update.message, True)

def ytdlleech(update, context):
    _ytdl(context.bot, update.message, isLeech=True)

def ytdlZipleech(update, context):
    _ytdl(context.bot, update.message, True, True)

ytdl_handler = CommandHandler(BotCommands.YtdlCommand, ytdl,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
ytdl_zip_handler = CommandHandler(BotCommands.YtdlZipCommand, ytdlZip,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
ytdl_leech_handler = CommandHandler(BotCommands.YtdlLeechCommand, ytdlleech,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
ytdl_zip_leech_handler = CommandHandler(BotCommands.YtdlZipLeechCommand, ytdlZipleech,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
quality_handler = CallbackQueryHandler(select_format, pattern="qu", run_async=True)

dispatcher.add_handler(ytdl_handler)
dispatcher.add_handler(ytdl_zip_handler)
dispatcher.add_handler(ytdl_leech_handler)
dispatcher.add_handler(ytdl_zip_leech_handler)
dispatcher.add_handler(quality_handler)
