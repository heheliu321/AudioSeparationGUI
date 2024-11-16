import os
import threading
import tkinter as tk
import queue
from datetime import timedelta, datetime

import ffmpeg
from tkinter import filedialog, messagebox
from funasr import AutoModel

# 创建窗口
root = tk.Tk()
root.title("说话人分离 https://blog.lukeewin.top")

# 获取屏幕宽度和高度
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# 设置窗口大小
window_width = 400
window_height = 200

# 计算居中位置
x_coordinate = (screen_width // 2) - (window_width // 2)
y_coordinate = (screen_height // 2) - (window_height // 2)

# 设置窗口大小和位置
root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

home_directory = os.path.expanduser("~")
asr_model_path = os.path.join(home_directory, ".cache", "modelscope", "hub", "iic", "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
asr_model_revision = "v2.0.4"
vad_model_path = os.path.join(home_directory, ".cache", "modelscope", "hub", "iic", "speech_fsmn_vad_zh-cn-16k-common-pytorch")
vad_model_revision = "v2.0.4"
punc_model_path = os.path.join(home_directory, ".cache", "modelscope", "hub", "iic", "punc_ct-transformer_zh-cn-common-vocab272727-pytorch")
punc_model_revision = "v2.0.4"
spk_model_path = os.path.join(home_directory, ".cache", "modelscope", "hub", "iic", "speech_campplus_sv_zh-cn_16k-common")
spk_model_revision = "v2.0.4"
ngpu = 1
device = "cuda"
ncpu = 4

# ASR 模型
model = AutoModel(model=asr_model_path,
                  model_revision = asr_model_revision,
                  vad_model=vad_model_path,
                  vad_model_revision=vad_model_revision,
                  punc_model=punc_model_path,
                  punc_model_revision=punc_model_revision,
                  spk_model=spk_model_path,
                  spk_model_revision = spk_model_revision,
                  ngpu=ngpu,
                  ncpu=ncpu,
                  device=device,
                  disable_pbar=True,
                  disable_log=True,
                  disable_update=True
                  )

# 创建一个队列，用于线程间通信
result_queue = queue.Queue()

input_frame = tk.Frame(root)
input_frame.pack(side=tk.TOP, padx=10, pady=2)
output_frame = tk.Frame(root)
output_frame.pack(side=tk.TOP, padx=10, pady=2)
start_trans_frame = tk.Frame(root)
start_trans_frame.pack(side=tk.TOP, padx=10, pady=2)
show_frame = tk.Frame(root)
show_frame.pack(side=tk.TOP,padx=10, pady=2)

selected_file_list = []
# 选择需要分离的音频
def select_multi_file():
    selected_file_list.clear()
    selected_files = filedialog.askopenfilenames(title='选择多个文件', filetypes=[('音频文件', '*.mp3 *.wav *.ogg *.flac *.aac'), ('视频文件', '*.mp4 *.avi *.mov *.mkv')])
    for tmp_file in selected_files:
        selected_file_list.append(tmp_file)
        print(f"选择的音频或视频：{tmp_file}")
select_input_file_button = tk.Button(input_frame, text='选择音频', command=select_multi_file)
select_input_file_button.pack(side=tk.LEFT, padx=10, pady=2)

# 指定转写后的保存路径
output_label = tk.Label(output_frame, text="保存路径")
output_label.pack(side=tk.LEFT, padx=10, pady=2)

save_path = tk.StringVar(None)
# 指定保存路径
def save_dir():
    save_directory = filedialog.askdirectory(title='选择保存路径')
    if save_directory:
        save_path.set(save_directory)
        output_label.config(text=save_directory)
tk.Button(output_frame, text='选择保存目录', command=save_dir).pack(side=tk.LEFT, padx=10, pady=2)

def copy_output_path():
    # 获取label中的文本内容
    text_to_copy = output_label.cget("text")
    # 清空剪贴板
    root.clipboard_clear()
    # 将文本内容添加到剪贴板
    root.clipboard_append(text_to_copy)

# 复制
copy_button = tk.Button(output_frame, text="复制路径", command=copy_output_path)
copy_button.pack(side=tk.RIGHT, padx=10, pady=2)

def to_date(milliseconds):
    """将时间戳转换为SRT格式的时间"""
    time_obj = timedelta(milliseconds=milliseconds)
    return f"{time_obj.seconds // 3600:02d}:{(time_obj.seconds // 60) % 60:02d}:{time_obj.seconds % 60:02d}.{time_obj.microseconds // 1000:03d}"


def to_milliseconds(time_str):
    time_obj = datetime.strptime(time_str, "%H:%M:%S.%f")
    time_delta = time_obj - datetime(1900, 1, 1)
    milliseconds = int(time_delta.total_seconds() * 1000)
    return milliseconds

# 转写获取时间戳，根据时间戳进行切分，然后根据 spk id 进行分类
# audio: 音频
# return 切分后按照 spk id 的地址
def trans():
    if len(selected_file_list) != 0 and save_path.get() != '' and save_path.get() is not None:
        for audio in selected_file_list:
            if os.path.exists(audio):
                audio_name = os.path.splitext(os.path.basename(audio))[0]
                _, audio_extension = os.path.splitext(audio)
                show_info_label.config(text=f'正在执行中，请勿关闭程序。{audio}')
                # 音频预处理
                try:
                    audio_bytes, _ = (
                        ffmpeg.input(audio, threads=0, hwaccel='cuda')
                        .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=16000)
                        .run(cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True)
                    )
                    res = model.generate(input=audio_bytes, batch_size_s=300, is_final=True, sentence_timestamp=True)
                    rec_result = res[0]
                    asr_result_text = rec_result['text']
                    if asr_result_text != '':
                        sentences = []
                        for sentence in rec_result["sentence_info"]:
                            start = to_date(sentence["start"])
                            end = to_date(sentence["end"])
                            if sentences and sentence["spk"] == sentences[-1]["spk"]:
                                sentences[-1]["text"] += "" + sentence["text"]
                                sentences[-1]["end"] = end
                            else:
                                sentences.append(
                                    {"text": sentence["text"], "start": start, "end": end, "spk": sentence["spk"]}
                                )

                        # 剪切音频或视频片段
                        i = 0
                        for stn in sentences:
                            start = stn['start']
                            end = stn['end']
                            tmp_start = to_milliseconds(start)
                            tmp_end = to_milliseconds(end)
                            duration = (tmp_end - tmp_start) / 1000
                            spk = stn['spk']
                            # 根据文件名和 spk 创建目录
                            final_save_path = os.path.join(save_path.get(), datetime.now().strftime("%Y-%m-%d"), audio_name, str(spk))
                            os.makedirs(final_save_path, exist_ok=True)
                            final_save_file = os.path.join(final_save_path, str(i)+'.mp3')
                            i += 1
                            try:
                                (
                                    ffmpeg.input(audio, threads=0, ss=start, t=duration, hwaccel='cuda')
                                    .output(final_save_file, codec='libmp3lame', preset='medium')
                                    .run(cmd=["ffmpeg", "-nostdin"], overwrite_output=True, capture_stdout=True,
                                         capture_stderr=True)
                                )
                            except ffmpeg.Error as e:
                                print(f"剪切音频发生错误，错误信息：{e}")
                        ret = {"text": asr_result_text, "sentences": sentences}
                        print(f'{audio} 切分完成')
                        result_queue.put(f'{audio} 切分完成')
                        show_info_label.config(text=f'{audio} 切分完成')
                        print(f'转写结果：{ret}')
                    else:
                        print("没有转写结果")
                except Exception as e:
                    print(f"转写异常：{e}")
            else:
                print("输入的文件不存在")
                messagebox.showinfo("提醒", "输入的文件不存在")
    else:
        print("没有填写输入输出")
        messagebox.showinfo("提醒", "没有填写选择文件或保存路径")

def start_transcription_thread():
    # 创建并启动转写线程
    thread = threading.Thread(target=trans)
    thread.start()

btn_start = tk.Button(start_trans_frame, text="分离", command=start_transcription_thread)
btn_start.pack(side=tk.LEFT, padx=10, pady=2)

# 显示分离情况
show_info_label = tk.Label(show_frame, text="")
show_info_label.pack(side=tk.LEFT, padx=10, pady=2)

def show_info():
    res = result_queue.get()
    show_info_label.config(text=res)

threading.Thread(target=show_info).start()

if __name__ in '__main__':
    root.mainloop()
